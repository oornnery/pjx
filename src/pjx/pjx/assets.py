from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable
from urllib.error import URLError
from urllib.request import Request, urlopen

AssetMode = Literal["cdn", "vendor", "off"]
AssetPlacement = Literal["head", "body"]
AssetKind = Literal["script", "style"]

_DOCUMENT_MARKERS = ("<!doctype", "<html", "</head>", "</body>")


@dataclass(frozen=True, slots=True)
class BrowserAssetFile:
    relative_path: str
    source_url: str
    npm_package: str | None = None
    npm_dist_path: str | None = None


@dataclass(frozen=True, slots=True)
class BrowserAsset:
    name: str
    kind: AssetKind
    placement: AssetPlacement
    cdn_url: str | None = None
    vendor_file: BrowserAssetFile | None = None
    attributes: tuple[tuple[str, str | None], ...] = ()
    presence_tokens: tuple[str, ...] = ()

    def identifier(self) -> str:
        return self.name

    def is_present(self, html: str, *, mode: AssetMode, base_url: str) -> bool:
        return any(token in html for token in self._presence_tokens(mode=mode, base_url=base_url))

    def render_tag(self, *, mode: AssetMode, base_url: str) -> str | None:
        if mode == "off":
            return None

        url = self.cdn_url if mode == "cdn" else self._vendor_url(base_url)
        if not url:
            return None

        attrs = list(self.attributes)
        if self.kind == "style":
            attrs = [("rel", "stylesheet"), *attrs, ("href", url)]
            attr_text = _format_attrs(attrs)
            return f'<link data-pjx-asset="{escape(self.name)}"{attr_text}>'

        attrs = [*attrs, ("src", url)]
        attr_text = _format_attrs(attrs)
        return f'<script data-pjx-asset="{escape(self.name)}"{attr_text}></script>'

    def _presence_tokens(self, *, mode: AssetMode, base_url: str) -> tuple[str, ...]:
        tokens = [f'data-pjx-asset="{self.name}"', *self.presence_tokens]
        if self.cdn_url:
            tokens.append(self.cdn_url)
        if self.vendor_file is not None:
            tokens.append(self.vendor_file.relative_path)
            vendor_url = self._vendor_url(base_url)
            if vendor_url:
                tokens.append(vendor_url)
        return tuple(token for token in tokens if token)

    def _vendor_url(self, base_url: str) -> str | None:
        if self.vendor_file is None:
            return None
        return _join_url(base_url, self.vendor_file.relative_path)


@runtime_checkable
class BrowserAssetProvider(Protocol):
    name: str

    def matches(self, html: str) -> bool: ...

    def get_assets(self) -> Iterable[BrowserAsset]: ...


@dataclass(frozen=True, slots=True)
class VendorAssetWrite:
    provider: str
    asset: str
    output_path: Path
    source_url: str


@dataclass(frozen=True, slots=True)
class VendorBuildResult:
    writes: tuple[VendorAssetWrite, ...]

    @property
    def files_written(self) -> int:
        return len(self.writes)


def inject_browser_assets(
    html: str,
    *,
    mode: AssetMode = "cdn",
    base_url: str = "/static/vendor/pjx",
    providers: Iterable[BrowserAssetProvider] = (),
) -> str:
    if mode == "off" or not _looks_like_document(html):
        return html

    providers = list(providers)
    if not providers:
        return html

    head_tags: list[str] = []
    body_tags: list[str] = []
    seen: set[str] = set()

    for provider in providers:
        if not provider.matches(html):
            continue

        for asset in provider.get_assets():
            key = asset.identifier()
            if key in seen or asset.is_present(html, mode=mode, base_url=base_url):
                continue
            tag = asset.render_tag(mode=mode, base_url=base_url)
            if tag is None:
                continue
            seen.add(key)
            if asset.placement == "head":
                head_tags.append(tag)
            else:
                body_tags.append(tag)

    if head_tags:
        html = _inject_before_closing_tag(html, "</head>", head_tags)
    if body_tags:
        html = _inject_before_closing_tag(html, "</body>", body_tags)
    return html


def build_vendor_assets(
    output_dir: Path,
    *,
    providers: Iterable[BrowserAssetProvider] | None = None,
    fetcher: Callable[[str], bytes] | None = None,
) -> VendorBuildResult:
    import json
    import shutil
    import subprocess

    all_providers = list(providers or discover_asset_providers())
    manifest = load_manifest(output_dir)
    writes: list[VendorAssetWrite] = []

    npm_deps: dict[str, str] = {}
    npm_copies: list[tuple[str, str, str, str]] = []  # (provider, asset, dist_path, output_rel)
    url_assets: list[tuple[BrowserAssetProvider, BrowserAsset]] = []

    for provider in all_providers:
        for asset in provider.get_assets():
            if asset.vendor_file is None:
                continue
            if asset.vendor_file.npm_package:
                pkg_name, pkg_version = _parse_npm_spec(asset.vendor_file.npm_package)
                npm_deps[pkg_name] = pkg_version
                npm_copies.append(
                    (
                        provider.name,
                        asset.name,
                        asset.vendor_file.npm_dist_path or "",
                        asset.vendor_file.relative_path,
                    )
                )
            else:
                url_assets.append((provider, asset))

    for name, entry in manifest.items():
        pkg_name, pkg_version = _parse_npm_spec(entry.npm_package)
        npm_deps[pkg_name] = pkg_version
        npm_copies.append(
            (
                "manifest",
                name,
                entry.npm_dist_path,
                entry.output_path,
            )
        )

    if npm_copies:
        node_dir = output_dir / ".pjx-build"
        node_dir.mkdir(parents=True, exist_ok=True)

        package_json = {
            "private": True,
            "description": "PJX vendored browser assets",
            "dependencies": npm_deps,
        }
        (node_dir / "package.json").write_text(json.dumps(package_json, indent=2) + "\n")

        subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=str(node_dir),
            check=True,
            capture_output=True,
        )

        for prov_name, asset_name, dist_path, output_rel in npm_copies:
            src = node_dir / "node_modules" / dist_path
            if not src.is_file():
                raise OSError(f"npm installed but dist file not found: {src}")

            output_path = output_dir / output_rel
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, output_path)
            writes.append(
                VendorAssetWrite(
                    provider=prov_name,
                    asset=asset_name,
                    output_path=output_path,
                    source_url=dist_path,
                )
            )

        for name in ("package.json", "package-lock.json"):
            src_file = node_dir / name
            if src_file.exists():
                shutil.copy2(src_file, output_dir / name)

        shutil.rmtree(node_dir)

    downloader = fetcher or _download_asset
    for provider, asset in url_assets:
        vf = asset.vendor_file
        assert vf is not None
        output_path = output_dir / vf.relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(downloader(vf.source_url))
        writes.append(
            VendorAssetWrite(
                provider=provider.name,
                asset=asset.name,
                output_path=output_path,
                source_url=vf.source_url,
            )
        )

    return VendorBuildResult(writes=tuple(writes))


def discover_asset_providers(
    *,
    names: Iterable[str] | None = None,
) -> list[BrowserAssetProvider]:
    from pjx.extension import ExtensionRegistry

    registry = ExtensionRegistry()
    registry.discover()

    requested = set(names) if names else None
    providers: list[BrowserAssetProvider] = []
    for ext in registry.extensions:
        provider = ext.get_asset_provider()
        if provider is None:
            continue
        if requested and provider.name not in requested:
            continue
        providers.append(provider)

    return providers


def available_asset_provider_names() -> tuple[str, ...]:
    return tuple(p.name for p in discover_asset_providers())


MANIFEST_FILE = "pjx-assets.json"


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    npm_package: str
    npm_dist_path: str
    output_path: str
    kind: AssetKind = "script"
    placement: AssetPlacement = "head"


def load_manifest(directory: Path) -> dict[str, ManifestEntry]:
    import json

    manifest_path = directory / MANIFEST_FILE
    if not manifest_path.exists():
        return {}

    data = json.loads(manifest_path.read_text())
    entries: dict[str, ManifestEntry] = {}
    for name, entry in data.get("assets", {}).items():
        entries[name] = ManifestEntry(
            npm_package=entry["npm_package"],
            npm_dist_path=entry["npm_dist_path"],
            output_path=entry["output_path"],
            kind=entry.get("kind", "script"),
            placement=entry.get("placement", "head"),
        )
    return entries


def save_manifest(directory: Path, entries: dict[str, ManifestEntry]) -> None:
    import json

    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "assets": {
            name: {
                "npm_package": e.npm_package,
                "npm_dist_path": e.npm_dist_path,
                "output_path": e.output_path,
                "kind": e.kind,
                "placement": e.placement,
            }
            for name, e in sorted(entries.items())
        }
    }
    (directory / MANIFEST_FILE).write_text(json.dumps(data, indent=2) + "\n")


def add_manifest_entry(directory: Path, name: str, entry: ManifestEntry) -> None:
    entries = load_manifest(directory)
    entries[name] = entry
    save_manifest(directory, entries)


def remove_manifest_entry(directory: Path, name: str) -> bool:
    entries = load_manifest(directory)
    if name not in entries:
        return False
    del entries[name]
    save_manifest(directory, entries)
    return True


def _format_attrs(attrs: Iterable[tuple[str, str | None]]) -> str:
    parts: list[str] = []
    for key, value in attrs:
        if value is None:
            parts.append(f" {escape(key)}")
            continue
        parts.append(f' {escape(key)}="{escape(value, quote=True)}"')
    return "".join(parts)


def _join_url(base_url: str, relative_path: str) -> str:
    return f"{base_url.rstrip('/')}/{relative_path.lstrip('/')}"


def _inject_before_closing_tag(html: str, closing_tag: str, tags: Iterable[str]) -> str:
    marker = closing_tag.lower()
    index = html.lower().rfind(marker)
    block = "  " + "\n  ".join(tags) + "\n"
    if index == -1:
        return f"{html}\n{block}"
    return f"{html[:index]}{block}{html[index:]}"


def _looks_like_document(html: str) -> bool:
    lowered = html.lower()
    return any(marker in lowered for marker in _DOCUMENT_MARKERS)


def _parse_npm_spec(spec: str) -> tuple[str, str]:
    """Parse 'htmx.org@2.0.4' or '@tailwindcss/browser@4' into (name, version)."""
    if spec.startswith("@"):
        rest = spec[1:]
        parts = rest.rsplit("@", 1)
        if len(parts) == 2:
            return f"@{parts[0]}", f"^{parts[1]}"
        return f"@{rest}", "*"
    parts = spec.rsplit("@", 1)
    if len(parts) == 2:
        return parts[0], f"^{parts[1]}"
    return spec, "*"


def _download_asset(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "pjx-assets/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except URLError as exc:
        raise OSError(f"Failed to download {url}: {exc}") from exc


__all__ = [
    "AssetMode",
    "BrowserAsset",
    "BrowserAssetFile",
    "BrowserAssetProvider",
    "ManifestEntry",
    "VendorBuildResult",
    "VendorAssetWrite",
    "add_manifest_entry",
    "available_asset_provider_names",
    "build_vendor_assets",
    "discover_asset_providers",
    "inject_browser_assets",
    "load_manifest",
    "remove_manifest_entry",
]
