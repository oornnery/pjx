# PJX CLI Guide

PJX ships with a small CLI for validating and formatting templates, plus
generating SEO files from your page templates and vendoring browser assets.

If you use `uv`, you can run it without installing globally:

```bash
uvx pjx --help
uvx pjx check templates/
uvx pjx check templates/ --fix
uvx pjx assets build static/vendor/pjx
```

## `pjx check`

Validate PJX templates in a file or directory:

```bash
pjx check templates/
pjx check templates/ --fix
pjx check templates/pages/home.jinja
pjx check templates/ --verbose
```

Use it to catch:

- unresolved component imports
- undefined variables
- circular `computed:` dependencies
- template-level diagnostics with file and line numbers

`--fix` is for safe technical autofixes only.
Formatting stays in `pjx format`.

## `pjx format`

Format PJX frontmatter consistently:

```bash
pjx format templates/
pjx format templates/ --check
pjx format templates/pages/home.jinja --verbose
```

The formatter keeps frontmatter sections in the expected order:

```text
imports -> props -> vars -> computed -> slots
```

## `pjx sitemap`

Generate `sitemap.xml` and `robots.txt` from your templates directory:

```bash
pjx sitemap templates/ --base-url https://example.com
pjx sitemap templates/ --base-url https://example.com --output static/
pjx sitemap templates/ --base-url https://example.com --disallow /admin,/internal
```

By default, output goes to `static/` next to your templates directory.

## `pjx skills`

Install the bundled PJX skill into local AI tooling folders:

```bash
pjx skills --claude
pjx skills --agents
pjx skills --claude --agents
```

This copies the PJX skill into:

- `.claude/skills/pjx`
- `.agents/skills/pjx`

## `pjx assets build`

Vendor browser assets exposed by installed PJX extensions and packages in the
local `pjx-assets.json` manifest. Merges both sources, generates a
`package.json`, runs `npm install`, and copies dist files into the output
directory:

```bash
pjx assets build static/vendor/pjx
pjx assets build static/vendor/pjx --provider htmx
pjx assets build static/vendor/pjx --provider htmx --provider stimulus
```

To use the vendored files at runtime, set `PJXEnvironment(asset_mode="vendor")`
and point `asset_base_url` at your static mount when needed.

## `pjx assets add`

Add an npm package to the local asset manifest (`pjx-assets.json`). Use
`--dist` to specify which file to copy from the package and `--out` for the
output path relative to the vendor directory:

```bash
pjx assets add alpinejs@3 --dist alpinejs/dist/cdn.min.js --out js/alpine.min.js
```

## `pjx assets list`

List all assets from installed extensions and the manifest:

```bash
pjx assets list
```

## `pjx assets remove`

Remove a package from the manifest:

```bash
pjx assets remove alpinejs
```

## Typical Workflow

```bash
uvx pjx check templates/
uvx pjx check templates/ --fix
uvx pjx format templates/ --check
uvx pjx assets add alpinejs@3 --dist alpinejs/dist/cdn.min.js --out js/alpine.min.js
uvx pjx assets build static/vendor/pjx
uvx pjx assets list
uvx pjx skills --claude
uvx pjx sitemap templates/ --base-url https://example.com
```
