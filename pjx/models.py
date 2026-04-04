from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ImportDecl:
    source: str
    names: list[str]


@dataclass(frozen=True, slots=True)
class PropDecl:
    name: str
    type_annotation: str
    default: str | None = None


@dataclass(frozen=True, slots=True)
class SlotDecl:
    name: str


@dataclass
class TemplateMetadata:
    imports: list[ImportDecl] = field(default_factory=list)
    props: list[PropDecl] = field(default_factory=list)
    slots: list[SlotDecl] = field(default_factory=list)

    def imported_names(self) -> set[str]:
        names: set[str] = set()
        for imp in self.imports:
            names.update(imp.names)
        return names

    def resolve_import(self, name: str, current_file: str | None = None) -> str | None:
        for imp in self.imports:
            if name not in imp.names:
                continue
            source = imp.source
            if source.startswith("..") or source.startswith("."):
                if current_file is None:
                    return None
                parts = current_file.replace("\\", "/").split("/")
                dir_parts = parts[:-1]
                module_parts = source.split(".")
                for part in module_parts:
                    if part == "":
                        if dir_parts:
                            dir_parts.pop()
                    else:
                        dir_parts.append(part)
                return "/".join(dir_parts) + f"/{name}.jinja"
            else:
                module_path = source.replace(".", "/")
                return f"{module_path}/{name}.jinja"
        return None
