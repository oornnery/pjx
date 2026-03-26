"""PJX configuration — loads from ``pjx.toml`` and environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    TomlConfigSettingsSource,
)


# Module-level holder so settings_customise_sources can access toml_path
_toml_path_holder: list[Path] = [Path("pjx.toml")]


class PJXConfig(BaseSettings):
    """PJX project configuration.

    Loads settings from a TOML file and environment variables (``PJX_`` prefix).

    Args:
        toml_path: Path to the ``pjx.toml`` config file. All relative paths
            in the config are resolved relative to this file's parent directory.
            Defaults to ``pjx.toml`` in the current working directory.
        **kwargs: Override any config field directly.

    Examples::

        # Auto-discover pjx.toml in CWD
        config = PJXConfig()

        # Explicit path
        config = PJXConfig(toml_path="examples/pjx.toml")
    """

    model_config = {"env_prefix": "PJX_"}

    engine: Literal["hybrid", "jinja2", "minijinja", "auto"] = "hybrid"
    debug: bool = False
    template_dirs: list[Path] = [Path("templates")]
    static_dir: Path = Path("static")
    pages_dir: Path = Path("templates/pages")
    components_dir: Path = Path("templates/components")
    layouts_dir: Path = Path("templates/layouts")
    ui_dir: Path = Path("templates/ui")
    vendor_templates_dir: Path = Path("templates/vendor")
    vendor_static_dir: Path = Path("static/vendor")
    host: str = "127.0.0.1"
    port: int = 8000
    alpine: bool = True
    htmx: bool = True
    tailwind: bool = False
    validate_props: bool = True
    render_mode: Literal["include", "inline"] = "include"

    def __init__(self, toml_path: Path | str = "pjx.toml", **kwargs: Any) -> None:
        toml = Path(toml_path)
        _toml_path_holder[0] = toml
        super().__init__(**kwargs)
        # Resolve relative paths against the toml file's directory
        if toml.exists():
            self._resolve_paths(toml.parent.resolve())

    def _resolve_paths(self, root: Path) -> None:
        """Resolve all relative Path fields against the project root."""
        self.template_dirs = [
            root / d if not d.is_absolute() else d for d in self.template_dirs
        ]
        for attr in (
            "static_dir",
            "pages_dir",
            "components_dir",
            "layouts_dir",
            "ui_dir",
            "vendor_templates_dir",
            "vendor_static_dir",
        ):
            val = getattr(self, attr)
            if not val.is_absolute():
                object.__setattr__(self, attr, root / val)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Add TOML as a settings source after env vars."""
        toml = _toml_path_holder[0]
        sources: list[PydanticBaseSettingsSource] = [
            init_settings,
            env_settings,
        ]
        if toml.exists():
            sources.append(TomlConfigSettingsSource(settings_cls, toml_file=toml))
        sources.extend([dotenv_settings, file_secret_settings])
        return tuple(sources)
