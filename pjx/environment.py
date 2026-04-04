from __future__ import annotations

from collections.abc import Callable

from jinja2 import BaseLoader, Environment, select_autoescape

from pjx.core.pipeline import PreprocessResult, PreprocessorPipeline


class PJXLoader(BaseLoader):
    def __init__(self, inner: BaseLoader) -> None:
        self.inner = inner
        self.pipeline = PreprocessorPipeline()
        self.preprocess_cache: dict[str, PreprocessResult] = {}

    def get_source(
        self, environment: Environment, template: str
    ) -> tuple[str, str | None, Callable[[], bool] | None]:
        source, filename, uptodate = self.inner.get_source(environment, template)
        # Use template name (relative to loader) for import resolution,
        # not the absolute filesystem path
        result = self.pipeline.process(source, filename=template)

        self.preprocess_cache[template] = result

        return result.source, filename, uptodate

    def list_templates(self) -> list[str]:
        if hasattr(self.inner, "list_templates"):
            return self.inner.list_templates()
        return []


class PJXEnvironment(Environment):
    def __init__(self, loader: BaseLoader | None = None, **kwargs) -> None:
        kwargs.setdefault(
            "autoescape",
            select_autoescape(["jinja", "html", "htm"]),
        )

        pjx_loader = PJXLoader(loader) if loader else None
        super().__init__(loader=pjx_loader, **kwargs)
        self._pjx_loader = pjx_loader

    def get_preprocessed_source(self, template_name: str) -> str | None:
        if not self._pjx_loader:
            return None
        result = self._pjx_loader.preprocess_cache.get(template_name)
        return result.source if result else None

    def get_preprocess_result(self, template_name: str) -> PreprocessResult | None:
        if not self._pjx_loader:
            return None
        return self._pjx_loader.preprocess_cache.get(template_name)
