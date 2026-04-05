# pjx-htmx

HTMX and SSE extension for PJX.

This package provides `HTMXExtension`, which adds HTMX and SSE attribute aliases
to PJX templates and injects the HTMX browser script on full HTML pages.
Install it directly, or use `pjx[htmx]`.

## Installation

```bash
pip install pjx-htmx
# or
pip install pjx[htmx]
```

## What It Adds

- `htmx:post` -> `hx-post`
- `htmx:get` -> `hx-get`
- `htmx:target` -> `hx-target`
- `htmx:swap` -> `hx-swap`
- `sse:connect` -> `sse-connect`
- `sse:swap` -> `sse-swap`

## Example

```html
<button htmx:post="/users" htmx:target="#list" htmx:swap="innerHTML">
  Save
</button>

<div sse:connect="/events" sse:swap="message"></div>
```

Compiles to:

```html
<button hx-post="/users" hx-target="#list" hx-swap="innerHTML">
  Save
</button>

<div sse-connect="/events" sse-swap="message"></div>
```

## Extension

`HTMXExtension` implements the `PJXExtension` ABC. It is discovered
automatically via the `pjx.extensions` entry point when the package is
installed:

```toml
[project.entry-points."pjx.extensions"]
htmx = "pjx_htmx.extension:HTMXExtension"
```

You can also register it explicitly:

```python
from pjx import PJXEnvironment
from pjx_htmx.extension import HTMXExtension

env = PJXEnvironment(
    loader=FileSystemLoader("templates"),
    extensions=[HTMXExtension()],
)
```

## Browser Asset Injection

On full HTML pages, PJX auto-injects the HTMX browser script when it detects
`hx-*` or `sse-*` attributes. To vendor the asset locally instead of using a
CDN:

```bash
pjx assets build static/vendor/pjx --provider htmx
```

## Links

- Repository: <https://github.com/oornnery/pjx>
- Core package: <https://pypi.org/project/pjx/>
