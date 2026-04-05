from __future__ import annotations


def cn(*classes: str | bool | None) -> str:
    """Merge class names, filtering out falsy values.

    Usage in Jinja2 templates:
        class="{{ cn('base', condition and 'active', other and 'extra') }}"

    Falsy values (False, None, empty string) are filtered out.
    Remaining strings are joined with spaces and deduplicated.
    """
    parts: list[str] = []
    seen: set[str] = set()
    for cls in classes:
        if not cls or cls is True:
            continue
        for token in str(cls).split():
            if token and token not in seen:
                seen.add(token)
                parts.append(token)
    return " ".join(parts)
