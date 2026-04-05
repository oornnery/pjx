# pjx-tailwind

Tailwind CSS extension for PJX.

This package provides `TailwindExtension`, which registers `cn()` as a Jinja2
global for class-name merging and injects the Tailwind browser build on full
HTML pages. Install it directly, or use `pjx[tailwind]` or `pjx[all]`.

## Installation

```bash
pip install pjx-tailwind
# or
pip install pjx[tailwind]
```

## What It Adds

`cn()` merges class names, filters falsy values, and deduplicates repeated
tokens.

## Example

```html
---
computed:
  btn_class: cn(
    "btn",
    is_primary and "btn-primary",
    disabled and "opacity-50",
  )
---

<button class={btn_class}>Save</button>
```

Results:

```text
cn("foo", "bar") -> "foo bar"
cn("base", false, "extra") -> "base extra"
cn("a b", "b c") -> "a b c"
```

## Extension

`TailwindExtension` implements the `PJXExtension` ABC. It is discovered
automatically via the `pjx.extensions` entry point when the package is
installed:

```toml
[project.entry-points."pjx.extensions"]
tailwind = "pjx_tailwind.extension:TailwindExtension"
```

You can also register it explicitly:

```python
from pjx import PJXEnvironment
from pjx_tailwind.extension import TailwindExtension

env = PJXEnvironment(
    loader=FileSystemLoader("templates"),
    extensions=[TailwindExtension()],
)
```

## Browser Asset Injection

On full HTML pages, PJX auto-injects the Tailwind browser build when it
detects common utility classes or `text/tailwindcss`. To vendor the asset
locally instead of using a CDN:

```bash
pjx assets build static/vendor/pjx --provider tailwind
```

## Links

- Repository: <https://github.com/oornnery/pjx>
- Core package: <https://pypi.org/project/pjx/>
