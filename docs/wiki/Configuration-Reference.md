# Configuration Reference

## Overview

PJX is configured through three sources, listed from highest to lowest
priority:

1. **Constructor kwargs** -- passed directly to `PJXConfig()` or `PJX()`.
2. **Environment variables** -- prefixed with `PJX_`.
3. **`pjx.toml`** -- a TOML configuration file in the project root.
4. **Built-in defaults** -- hardcoded in `PJXConfig`.

This layered approach lets you define a base configuration in `pjx.toml`,
override specific values per-environment with `PJX_` variables, and
fine-tune at runtime with constructor arguments.

Configuration is powered by
[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
which handles type coercion, validation, and source merging automatically.

---

## Complete Field Reference

All fields below are available in `pjx.toml`, as environment variables
(with the `PJX_` prefix), and as constructor kwargs to `PJXConfig()`.

### Engine and Runtime

| Field            | Type                                                  | Default     | Description                                                                                                                                                                                            |
| ---------------- | ----------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `engine`         | `"hybrid"` \| `"jinja2"` \| `"minijinja"` \| `"auto"` | `"hybrid"`  | Template engine backend. `"hybrid"` uses Jinja2 for full templates and MiniJinja for leaf partials. `"jinja2"` and `"minijinja"` force a single engine. `"auto"` selects based on template complexity. |
| `debug`          | `bool`                                                | `false`     | Enable debug mode. Enables verbose logging, disables template caching, and exposes detailed error pages.                                                                                               |
| `validate_props` | `bool`                                                | `true`      | Validate component props at render time using generated Pydantic models. Disable in production for a small performance gain.                                                                           |
| `render_mode`    | `"include"` \| `"inline"`                             | `"include"` | Template composition strategy. `"include"` uses Jinja2 `{% include %}` directives. `"inline"` flattens all components into a single source string (faster, but collapses variable scopes).             |

### Directory Paths

All paths are relative to the `pjx.toml` file's parent directory unless
specified as absolute paths.

| Field                  | Type         | Default                      | Description                                                             |
| ---------------------- | ------------ | ---------------------------- | ----------------------------------------------------------------------- |
| `template_dirs`        | `list[Path]` | `["app/templates"]`          | Directories to search for templates, in order. The first match wins.    |
| `static_dir`           | `Path`       | `"app/static"`               | Directory for static assets. Automatically mounted at `/static`.        |
| `pages_dir`            | `Path`       | `"app/templates/pages"`      | Directory for file-based routing. Templates here map to URL paths.      |
| `components_dir`       | `Path`       | `"app/templates/components"` | Directory for reusable component templates.                             |
| `layouts_dir`          | `Path`       | `"app/templates/layouts"`    | Directory for layout templates.                                         |
| `ui_dir`               | `Path`       | `"app/templates/ui"`         | Directory for UI primitives and design system components.               |
| `vendor_templates_dir` | `Path`       | `"app/templates/vendor"`     | Directory for third-party or vendored templates.                        |
| `vendor_static_dir`    | `Path`       | `"app/static/vendor"`        | Directory for third-party static assets (JS libraries, CSS frameworks). |

### Server

| Field  | Type  | Default       | Description                              |
| ------ | ----- | ------------- | ---------------------------------------- |
| `host` | `str` | `"127.0.0.1"` | Host address for the development server. |
| `port` | `int` | `8000`        | Port number for the development server.  |

### Frontend Libraries

These flags control whether PJX injects `<script>` and `<link>` tags for
the corresponding libraries in layout templates.

| Field      | Type   | Default | Description                                                    |
| ---------- | ------ | ------- | -------------------------------------------------------------- |
| `alpine`   | `bool` | `true`  | Include Alpine.js for client-side reactivity (`x-data`, etc.). |
| `htmx`     | `bool` | `true`  | Include HTMX for HTML-over-the-wire interactions.              |
| `tailwind` | `bool` | `false` | Include Tailwind CSS. Requires additional build setup.         |

### Logging

| Field       | Type   | Default  | Description                                                                |
| ----------- | ------ | -------- | -------------------------------------------------------------------------- |
| `log_json`  | `bool` | `false`  | Output structured JSON logs instead of human-readable text.                |
| `log_level` | `str`  | `"INFO"` | Minimum log level. One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

### CORS

Cross-Origin Resource Sharing settings. When `cors_origins` is non-empty,
PJX automatically adds Starlette's `CORSMiddleware`.

| Field              | Type        | Default   | Description                                                                                                                             |
| ------------------ | ----------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `cors_origins`     | `list[str]` | `[]`      | Allowed origins. Set to `["*"]` to allow all origins (not recommended for production). An empty list disables CORS middleware entirely. |
| `cors_methods`     | `list[str]` | `["GET"]` | Allowed HTTP methods.                                                                                                                   |
| `cors_headers`     | `list[str]` | `[]`      | Allowed request headers beyond the CORS-safelisted set.                                                                                 |
| `cors_credentials` | `bool`      | `false`   | Allow credentials (cookies, authorization headers) in CORS requests.                                                                    |

---

## Environment Variables

Every `PJXConfig` field can be set via an environment variable with the
`PJX_` prefix. The variable name is the uppercase version of the field name:

| Field              | Environment Variable   | Example Value                |
| ------------------ | ---------------------- | ---------------------------- |
| `debug`            | `PJX_DEBUG`            | `true`                       |
| `engine`           | `PJX_ENGINE`           | `jinja2`                     |
| `validate_props`   | `PJX_VALIDATE_PROPS`   | `false`                      |
| `render_mode`      | `PJX_RENDER_MODE`      | `inline`                     |
| `host`             | `PJX_HOST`             | `0.0.0.0`                    |
| `port`             | `PJX_PORT`             | `3000`                       |
| `log_json`         | `PJX_LOG_JSON`         | `true`                       |
| `log_level`        | `PJX_LOG_LEVEL`        | `WARNING`                    |
| `alpine`           | `PJX_ALPINE`           | `false`                      |
| `htmx`             | `PJX_HTMX`             | `false`                      |
| `tailwind`         | `PJX_TAILWIND`         | `true`                       |
| `template_dirs`    | `PJX_TEMPLATE_DIRS`    | `["templates","vendor/tpl"]` |
| `static_dir`       | `PJX_STATIC_DIR`       | `public`                     |
| `cors_origins`     | `PJX_CORS_ORIGINS`     | `["http://localhost:3000"]`  |
| `cors_methods`     | `PJX_CORS_METHODS`     | `["GET","POST","PUT"]`       |
| `cors_headers`     | `PJX_CORS_HEADERS`     | `["Authorization"]`          |
| `cors_credentials` | `PJX_CORS_CREDENTIALS` | `true`                       |

Boolean values accept `true`/`false`, `1`/`0`, `yes`/`no` (case-insensitive).
List values use JSON array syntax.

Environment variables override `pjx.toml` values but are overridden by
constructor kwargs.

---

## Resolution Order

When the same field is set in multiple sources, the highest-priority source
wins:

```text
Constructor kwargs  (highest priority)
        |
   Environment variables (PJX_*)
        |
   pjx.toml file
        |
   Built-in defaults  (lowest priority)
```

This is implemented via pydantic-settings' `settings_customise_sources`
method. The source order is:

1. `init_settings` -- constructor kwargs
2. `env_settings` -- environment variables with `PJX_` prefix
3. `TomlConfigSettingsSource` -- values from `pjx.toml` (only if the file
   exists)
4. `dotenv_settings` and `file_secret_settings` -- additional pydantic-settings
   sources (available but not used by default)

### Example

Given these three sources:

```toml
# pjx.toml
debug = true
port = 3000
log_level = "DEBUG"
```

```bash
# Environment
export PJX_PORT=4000
```

```python
# Python
config = PJXConfig(log_level="WARNING")
```

The resolved configuration is:

- `debug` = `true` (from pjx.toml; no env var or kwarg overrides it)
- `port` = `4000` (env var overrides pjx.toml)
- `log_level` = `"WARNING"` (kwarg overrides both env var and pjx.toml)

---

## Path Resolution

All relative `Path` fields in `PJXConfig` are resolved against the parent
directory of the `pjx.toml` file. This ensures consistent behavior
regardless of where the application is started from.

For example, given this project layout:

```text
myproject/
  pjx.toml
  app/
    main.py
    templates/
      pages/
      components/
      layouts/
    static/
```

And this configuration:

```toml
# myproject/pjx.toml
template_dirs = ["app/templates"]
static_dir = "app/static"
pages_dir = "app/templates/pages"
```

All paths resolve relative to `myproject/`:

- `template_dirs` -> `["/absolute/path/to/myproject/app/templates"]`
- `static_dir` -> `"/absolute/path/to/myproject/app/static"`
- `pages_dir` -> `"/absolute/path/to/myproject/app/templates/pages"`

If you provide an absolute path, it is used as-is without resolution:

```toml
template_dirs = ["/opt/shared/templates", "templates"]
```

Here `/opt/shared/templates` stays absolute while `templates` resolves
against the `pjx.toml` directory.

### Explicit TOML Path

By default, `PJXConfig` looks for `pjx.toml` in the current working
directory. To use a different location:

```python
config = PJXConfig(toml_path="examples/demo/pjx.toml")
```

All relative paths in the config then resolve against `examples/demo/`.

If the specified `pjx.toml` does not exist, path resolution is skipped and
relative paths remain as-is (relative to the process working directory).

---

## Development Config

A typical `pjx.toml` for local development:

```toml
# pjx.toml — development
debug = true
engine = "hybrid"
validate_props = true
render_mode = "include"

template_dirs = ["app/templates"]
static_dir = "app/static"
pages_dir = "app/templates/pages"
components_dir = "app/templates/components"
layouts_dir = "app/templates/layouts"

host = "127.0.0.1"
port = 8000

alpine = true
htmx = true
tailwind = false

log_json = false
log_level = "DEBUG"
```

Key characteristics:

- `debug = true` enables auto-reload, verbose error pages, and disables
  template caching.
- `validate_props = true` catches prop type errors during development.
- `log_level = "DEBUG"` provides detailed request/response logging.
- `log_json = false` keeps logs human-readable in the terminal.

---

## Production Config

A hardened `pjx.toml` for production deployment:

```toml
# pjx.toml — production
debug = false
engine = "hybrid"
validate_props = false
render_mode = "include"

template_dirs = ["app/templates"]
static_dir = "app/static"
pages_dir = "app/templates/pages"
components_dir = "app/templates/components"
layouts_dir = "app/templates/layouts"

host = "0.0.0.0"
port = 8000

alpine = true
htmx = true
tailwind = true

log_json = true
log_level = "WARNING"

cors_origins = ["https://example.com"]
cors_methods = ["GET", "POST", "PUT", "DELETE"]
cors_headers = ["Authorization", "Content-Type"]
cors_credentials = true
```

Key characteristics:

- `debug = false` disables verbose errors and enables template caching.
- `validate_props = false` skips runtime prop validation for performance.
- `log_json = true` produces structured logs for aggregation (ELK,
  Datadog, CloudWatch).
- `log_level = "WARNING"` reduces log volume.
- `cors_origins` is restricted to the production domain.
- `host = "0.0.0.0"` binds to all interfaces (required behind a reverse
  proxy).
- `tailwind = true` includes the Tailwind CSS build output.

Override specific values per environment with environment variables:

```bash
# staging overrides
export PJX_DEBUG=true
export PJX_LOG_LEVEL=DEBUG
export PJX_CORS_ORIGINS='["https://staging.example.com"]'
```

---

## PJX Constructor Parameters

The `PJX()` class accepts parameters beyond what `PJXConfig` provides.
These are runtime integration options that do not belong in `pjx.toml`:

| Parameter           | Type            | Default  | Description                                                                                                    |
| ------------------- | --------------- | -------- | -------------------------------------------------------------------------------------------------------------- |
| `app`               | `FastAPI`       | required | The FastAPI application instance to integrate with.                                                            |
| `config`            | `PJXConfig`     | `None`   | Configuration object. A default `PJXConfig()` is created if not provided.                                      |
| `layout`            | `str` or `None` | `None`   | Default layout template path (e.g. `"layouts/Base.jinja"`). All pages wrap in this layout unless overridden.   |
| `seo`               | `SEO` or `None` | `None`   | Default SEO metadata applied to all pages. Per-page SEO merges on top.                                         |
| `csrf`              | `bool`          | `False`  | Enable the built-in CSRF protection middleware.                                                                |
| `csrf_secret`       | `str` or `None` | `None`   | Secret key for CSRF token signing (HMAC-SHA256). Falls back to a placeholder -- always set this in production. |
| `csrf_exempt_paths` | `set[str]`      | `None`   | URL paths exempt from CSRF validation (e.g. webhook endpoints).                                                |
| `health`            | `bool`          | `False`  | Register health check endpoints (`/health`, `/ready`).                                                         |

### Usage Example

```python
from fastapi import FastAPI
from pjx import PJX, SEO
from pjx.config import PJXConfig

app = FastAPI()

config = PJXConfig(toml_path="pjx.toml")

pjx = PJX(
    app,
    config=config,
    layout="layouts/Base.jinja",
    seo=SEO(
        title="My App",
        description="A PJX application",
        og_type="website",
    ),
    csrf=True,
    csrf_secret="change-me-in-production",
    csrf_exempt_paths={"/webhooks/stripe"},
    health=True,
)
```

### Relationship Between PJXConfig and PJX

`PJXConfig` holds *project-level* settings that are portable across
environments (paths, feature flags, logging). These belong in `pjx.toml`.

`PJX` constructor params hold *runtime* settings that depend on the
application instance or contain secrets (`csrf_secret`, `layout`, `seo`).
These are set in Python code, often reading from environment variables:

```python
import os

pjx = PJX(
    app,
    csrf=True,
    csrf_secret=os.environ["CSRF_SECRET"],
    health=os.environ.get("ENABLE_HEALTH", "false").lower() == "true",
)
```

---

## See Also

- [[Project Structure]] -- recommended directory layout and file conventions
- [[Template Engines]] -- details on the hybrid, jinja2, and minijinja
  engine backends
- [[Security]] -- CSRF configuration, Content-Security-Policy, and
  production hardening
- [[Deployment]] -- production deployment guides and environment
  configuration
