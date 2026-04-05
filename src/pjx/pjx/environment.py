from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any

from jinja2 import BaseLoader, Environment, select_autoescape

from pjx.cache import TemplateCache
from pjx.core.pipeline import PreprocessorPipeline
from pjx.core.types import PreprocessResult


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
    def __init__(self, loader: BaseLoader, **kwargs: Any) -> None:
        kwargs.setdefault(
            "autoescape",
            select_autoescape(["jinja", "html", "htm"]),
        )

        pjx_loader = PJXLoader(loader)
        super().__init__(loader=pjx_loader, **kwargs)
        self._pjx_loader = pjx_loader
        self._discover_jinja_globals()

    def _discover_jinja_globals(self) -> None:
        eps = entry_points(group="pjx.jinja_globals")
        for ep in eps:
            func = ep.load()
            self.globals[ep.name] = func

    def get_preprocessed_source(self, template_name: str) -> str | None:
        result = self._pjx_loader.get_preprocess_result(template_name)
        return result.source if result else None

    def get_preprocess_result(self, template_name: str) -> PreprocessResult | None:
        return self._pjx_loader.get_preprocess_result(template_name)
