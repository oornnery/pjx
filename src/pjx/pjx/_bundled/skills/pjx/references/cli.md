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

Vendor browser assets exposed by installed PJX extras or third-party providers:

```bash
pjx assets build static/vendor/pjx
pjx assets build static/vendor/pjx --provider htmx
pjx assets build static/vendor/pjx --provider htmx --provider stimulus
```

This works with the browser-asset registry used by `PJXEnvironment`. A package
can contribute to it through the `pjx.assets` entry point.
To use the vendored files at runtime, set `PJXEnvironment(asset_mode="vendor")`
and point `asset_base_url` at your static mount when needed.

## Typical Workflow

```bash
uvx pjx check templates/
uvx pjx check templates/ --fix
uvx pjx format templates/ --check
uvx pjx assets build static/vendor/pjx
uvx pjx skills --claude
uvx pjx sitemap templates/ --base-url https://example.com
```
