# pjx-stimulus

Stimulus extension for PJX.

This package provides `StimulusExtension`, which adds Stimulus-friendly aliases
like `stimulus:controller` and `stimulus:target` to PJX templates, and injects
the Stimulus browser script on full HTML pages. Install it directly, or use
`pjx[stimulus]`.

## Installation

```bash
pip install pjx-stimulus
# or
pip install pjx[stimulus]
```

## What It Adds

- `stimulus:controller="dropdown"` -> `data-controller="dropdown"`
- `stimulus:action="click->dropdown#toggle"` -> `data-action="click->dropdown#toggle"`
- `stimulus:target="menu"` -> `data-dropdown-target="menu"`
- `stimulus:value-name="foo"` -> `data-dropdown-name-value="foo"`

The processor tracks active controllers so `target`, `value`, `class`, and
`outlet` aliases resolve to the correct `data-*` attribute.

## Example

```html
<div stimulus:controller="dropdown">
  <button stimulus:action="click->dropdown#toggle">Menu</button>
  <div stimulus:target="menu">Content</div>
</div>
```

Compiles to:

```html
<div data-controller="dropdown">
  <button data-action="click->dropdown#toggle">Menu</button>
  <div data-dropdown-target="menu">Content</div>
</div>
```

## Extension

`StimulusExtension` implements the `PJXExtension` ABC. It is discovered
automatically via the `pjx.extensions` entry point when the package is
installed:

```toml
[project.entry-points."pjx.extensions"]
stimulus = "pjx_stimulus.extension:StimulusExtension"
```

You can also register it explicitly:

```python
from pjx import PJXEnvironment
from pjx_stimulus.extension import StimulusExtension

env = PJXEnvironment(
    loader=FileSystemLoader("templates"),
    extensions=[StimulusExtension()],
)
```

## Browser Asset Injection

On full HTML pages, PJX auto-injects the Stimulus browser script when it
detects Stimulus `data-*` attributes. To vendor the asset locally instead of
using a CDN:

```bash
pjx assets build static/vendor/pjx --provider stimulus
```

## Links

- Repository: <https://github.com/oornnery/pjx>
- Core package: <https://pypi.org/project/pjx/>
