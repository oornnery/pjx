from __future__ import annotations

from collections.abc import Callable
from typing import Any

from jinja2 import BaseLoader, Environment, Template, select_autoescape

from pjx.assets import AssetMode, inject_browser_assets
from pjx.cache import TemplateCache
from pjx.core.pipeline import PreprocessorPipeline
from pjx.core.types import PreprocessResult
from pjx.extension import ExtensionRegistry, PJXExtension


class PJXTemplate(Template):
    def render(self, *args: Any, **kwargs: Any) -> str:
        html = super().render(*args, **kwargs)
        inject = getattr(self.environment, "_inject_assets", None)
        return inject(html) if callable(inject) else html

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        html = await super().render_async(*args, **kwargs)
        inject = getattr(self.environment, "_inject_assets", None)
        return inject(html) if callable(inject) else html


class PJXLoader(BaseLoader):
    def __init__(self, inner: BaseLoader) -> None:
        self.inner = inner
        self.pipeline = PreprocessorPipeline()
        self.cache = TemplateCache()

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        source, filename, uptodate = self.inner.get_source(environment, template)

        cached = self.cache.get(template, filename)
        if cached is not None:
            return cached.source, filename, uptodate

        result = self.pipeline.process(source, filename=template)
        self.cache.put(template, result, filename)

        return result.source, filename, uptodate

    def get_preprocess_result(self, template: str) -> PreprocessResult | None:
        return self.cache.get(template)

    def list_templates(self) -> list[str]:
        if hasattr(self.inner, "list_templates"):
            return self.inner.list_templates()
        return []


class PJXEnvironment(Environment):
    def __init__(
        self,
        loader: BaseLoader,
        *,
        extensions: list[PJXExtension] | None = None,
        asset_mode: AssetMode = "cdn",
        asset_base_url: str = "/static/vendor/pjx",
        asset_providers: list[str] | tuple[str, ...] | None = None,
        **kwargs: Any,
    ) -> None:
        template_class = kwargs.pop("template_class", PJXTemplate)
        kwargs.setdefault(
            "autoescape",
            select_autoescape(["jinja", "html", "htm"]),
        )

        pjx_loader = PJXLoader(loader)
        super().__init__(loader=pjx_loader, **kwargs)
        self.template_class = template_class
        self._pjx_loader = pjx_loader
        self._asset_mode = asset_mode
        self._asset_base_url = asset_base_url
        self._asset_provider_names = tuple(asset_providers) if asset_providers else None
        self._asset_providers: list[Any] = []

        registry = ExtensionRegistry()
        for ext in extensions or []:
            registry.register(ext)
        registry.discover()
        self._extension_registry = registry
        self._apply_extensions()

    def _apply_extensions(self) -> None:
        for ext in self._extension_registry.extensions:
            for name, func in ext.get_jinja_globals().items():
                self.globals[name] = func

            for slot, processor in ext.get_processors():
                self._pjx_loader.pipeline.register_processor(slot, processor)

            provider = ext.get_asset_provider()
            if provider is None:
                continue
            if self._asset_provider_names and provider.name not in self._asset_provider_names:
                continue
            self._asset_providers.append(provider)

    def get_preprocessed_source(self, template_name: str) -> str | None:
        result = self._pjx_loader.get_preprocess_result(template_name)
        return result.source if result else None

    def get_preprocess_result(self, template_name: str) -> PreprocessResult | None:
        return self._pjx_loader.get_preprocess_result(template_name)

    def _inject_assets(self, html: str) -> str:
        return inject_browser_assets(
            html,
            mode=self._asset_mode,
            base_url=self._asset_base_url,
            providers=self._asset_providers,
        )
