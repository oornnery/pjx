# CLI Reference

## Overview

PJX ships a command-line interface built on Typer and Rich. Installing the
`pjx` package makes the `pjx` command available in your environment.

```bash
uv add pjx
pjx --help
```

The CLI provides commands for the full development lifecycle: project
scaffolding, development server, production server, compilation, static
analysis, formatting, and package management.

All commands that operate on a project accept an optional `directory` argument
(defaults to the current directory). PJX looks for `pjx.toml` in that
directory to load configuration.

### Command summary

| Command      | Description                                         |
| ------------ | --------------------------------------------------- |
| `pjx init`   | Scaffold a new PJX project                          |
| `pjx dev`    | Start the development server with auto-reload       |
| `pjx run`    | Start the production server                         |
| `pjx build`  | Compile all `.jinja` components and bundle CSS      |
| `pjx check`  | Validate imports, props, and slots across templates |
| `pjx format` | Verify all `.jinja` files parse correctly           |
| `pjx add`    | Install an npm package and vendor its dist files    |
| `pjx remove` | Remove a vendored npm package                       |

---

## pjx init

Scaffold a new PJX project with the standard directory structure.

### Usage

```bash
pjx init [DIRECTORY]
```

### Arguments

| Argument    | Type   | Default | Description                     |
| ----------- | ------ | ------- | ------------------------------- |
| `DIRECTORY` | `Path` | `.`     | Project directory to initialize |

### Behavior

Creates a complete, runnable PJX project with example app (similar to Create
React App). All files use the `_write_if_missing()` pattern — re-running `init`
on an existing project adds missing files without overwriting existing ones.

1. Creates `pjx.toml` configuration:

   ```toml
   engine = "hybrid"
   debug = true

   template_dirs = ["app/templates"]
   static_dir = "app/static"
   pages_dir = "app/templates/pages"
   components_dir = "app/templates/components"
   layouts_dir = "app/templates/layouts"
   ```

2. Creates the `app/` package with submodules:

   | File                      | Purpose                    |
   | ------------------------- | -------------------------- |
   | `app/main.py`             | FastAPI + PJX entrypoint   |
   | `app/core/config.py`      | Application settings       |
   | `app/pages/routes.py`     | HTMX counter endpoints     |
   | `app/services/counter.py` | In-memory counter state    |
   | `app/models/`             | Pydantic schemas (empty)   |
   | `app/api/v1/`             | JSON API endpoints (empty) |
   | `app/middleware/`         | Custom middleware (empty)  |

3. Creates example templates:

   | File                                     | Purpose                               |
   | ---------------------------------------- | ------------------------------------- |
   | `app/templates/layouts/Base.jinja`       | Base layout with navbar, footer, CSS  |
   | `app/templates/pages/Home.jinja`         | Home page with Alpine + HTMX counters |
   | `app/templates/pages/About.jinja`        | About page with project structure     |
   | `app/templates/components/Counter.jinja` | Server-side HTMX counter component    |
   | `app/static/css/style.css`               | Complete starter stylesheet           |

4. Creates all template and static directories from `pjx.toml` config.

### Example

```bash
pjx init my-app
cd my-app
pjx dev .
```

Output:

```text
  Created pjx.toml
  Created app/core/config.py
  Created app/main.py
  Created app/services/counter.py
  Created app/pages/routes.py
  Created app/templates/layouts/Base.jinja
  Created app/templates/pages/Home.jinja
  Created app/templates/pages/About.jinja
  Created app/templates/components/Counter.jinja
  Created app/static/css/style.css

✨ PJX project initialized in my-app/

  cd my-app && pjx dev .
  Open http://localhost:8000
```

---

## pjx dev

Start the development server with auto-reload. Uses Uvicorn under the hood
with file watching enabled.

### Usage

```bash
pjx dev [DIRECTORY] [--app APP] [--host HOST] [--port PORT]
```

### Arguments

| Argument    | Type   | Default | Description                               |
| ----------- | ------ | ------- | ----------------------------------------- |
| `DIRECTORY` | `Path` | `.`     | Project directory (containing `pjx.toml`) |

### Options

| Option   | Short | Type  | Default         | Description                          |
| -------- | ----- | ----- | --------------- | ------------------------------------ |
| `--app`  | `-a`  | `str` | auto-discovered | ASGI app path (e.g., `app.main:app`) |
| `--host` | `-h`  | `str` | from config     | Host to bind to                      |
| `--port` | `-p`  | `int` | from config     | Port to bind to                      |

### App discovery

If `--app` is not specified, PJX automatically searches for the ASGI
application by looking for these files in order:

1. `app/main.py` -- uses `app.main:app` (standard scaffold)
2. `app.py` -- uses `app:app`
3. `main.py` -- uses `main:app`
4. `server.py` -- uses `server:app`

If none are found, it defaults to `app.main:app`.

### File watching

The dev server watches the project directory and all configured template
directories. It reloads on changes to the following file types:

| Extension | Description       |
| --------- | ----------------- |
| `*.py`    | Python source     |
| `*.jinja` | PJX templates     |
| `*.css`   | Stylesheets       |
| `*.js`    | JavaScript        |
| `*.toml`  | Configuration     |

### Example

```bash
# Auto-discover app, use config defaults
pjx dev .

# Explicit app path and port
pjx dev . --app main:app --port 3000

# Bind to all interfaces
pjx dev . --host 0.0.0.0 --port 8080
```

Output:

```text
Starting dev server: app.main:app
Config: /path/to/pjx.toml
Watching: /path/to/project, /path/to/project/app/templates
```

---

## pjx run

Start the production server. Uses Uvicorn without auto-reload and supports
multiple worker processes.

### Usage

```bash
pjx run [DIRECTORY] [--app APP] [--host HOST] [--port PORT] [--workers N]
```

### Arguments

| Argument    | Type   | Default | Description                               |
| ----------- | ------ | ------- | ----------------------------------------- |
| `DIRECTORY` | `Path` | `.`     | Project directory (containing `pjx.toml`) |

### Options

| Option      | Short | Type  | Default         | Description                    |
| ----------- | ----- | ----- | --------------- | ------------------------------ |
| `--app`     | `-a`  | `str` | auto-discovered | ASGI app path                  |
| `--host`    |       | `str` | from config     | Host to bind to                |
| `--port`    |       | `int` | from config     | Port to bind to                |
| `--workers` | `-w`  | `int` | `1`             | Number of Uvicorn workers      |

### Differences from pjx dev

| Feature        | `pjx dev`           | `pjx run`             |
| -------------- | ------------------- | --------------------- |
| Auto-reload    | Yes                 | No                    |
| File watching  | Yes                 | No                    |
| Workers        | 1 (single process)  | Configurable (N)      |
| Use case       | Development         | Production            |

### Example

```bash
# Single worker, config defaults
pjx run .

# Production with 4 workers
pjx run . --workers 4 --host 0.0.0.0 --port 80

# Explicit app
pjx run . --app main:app --workers 8
```

---

## pjx build

Compile all `.jinja` components in the configured template directories and
bundle scoped CSS into a single stylesheet.

### Usage

```bash
pjx build [DIRECTORY]
```

### Arguments

| Argument    | Type   | Default | Description       |
| ----------- | ------ | ------- | ----------------- |
| `DIRECTORY` | `Path` | `.`     | Project directory |

### Behavior

1. Scans all configured `template_dirs` for `.jinja` files (recursively).
2. Parses each file through the PJX parser.
3. Compiles each parsed component through the PJX compiler.
4. Collects scoped CSS from all compiled components.
5. Writes the concatenated CSS to `static/css/pjx-components.css`.
6. Reports the number of compiled components.

If any file fails to parse or compile, the command prints the error and exits
with code 1.

### Output files

| File                            | Contents                                     |
| ------------------------------- | -------------------------------------------- |
| `static/css/pjx-components.css` | All scoped CSS from components, concatenated |

### Example

```bash
pjx build .
```

Output:

```text
Bundled CSS -> static/css/pjx-components.css
Compiled 47 components.
```

### When to run

Run `pjx build` before deploying to production. The build step ensures all
templates compile without errors and produces the bundled CSS file that should
be served as a static asset.

```bash
pjx build . && pjx run . --workers 4
```

---

## pjx check

Static analysis for PJX templates. Validates imports, props, and slots across
all `.jinja` files without running the server.

### Usage

```bash
pjx check [DIRECTORY]
```

### Arguments

| Argument    | Type   | Default | Description       |
| ----------- | ------ | ------- | ----------------- |
| `DIRECTORY` | `Path` | `.`     | Project directory |

### Two-phase validation

The check command runs in two phases:

#### Phase 1: Parse all components

Every `.jinja` file in the configured template directories is parsed and
registered in a `ComponentRegistry`. Parse errors are reported immediately.

#### Phase 2: Cross-reference validation

Once all components are registered, PJX runs static checks on each component
against the full registry:

| Check              | What it validates                                         |
| ------------------ | --------------------------------------------------------- |
| Import resolution  | All `import` paths resolve to existing `.jinja` files     |
| Props checking     | Required props are passed when invoking child components  |
| Slot checking      | Slot passes match the slots declared in child components  |

### Exit codes

| Code | Meaning                                         |
| ---- | ----------------------------------------------- |
| `0`  | All files parsed and checked without errors     |
| `1`  | One or more parse errors (hard failure)         |

Check warnings (Phase 2) are printed to stderr but do not cause a non-zero
exit code unless accompanied by parse errors.

### Example

```bash
pjx check .
```

Success output:

```text
Checked 47 files -- no errors.
```

Error output:

```text
ERROR: templates/components/Card.jinja: unexpected token at line 5
WARNING: templates/pages/Home.jinja: required prop "title" not passed to UserCard
Found 1 parse error(s) and 1 check warning(s) in 48 files.
```

### Integration with CI

Add `pjx check` to your continuous integration pipeline alongside linting
and type checking:

```bash
ruff check .
ty check
pjx check .
pjx build .
pytest -v
```

---

## pjx format

Verify that all `.jinja` files parse correctly. Currently operates as a
parse-validation pass.

### Usage

```bash
pjx format [DIRECTORY]
```

### Arguments

| Argument    | Type   | Default | Description       |
| ----------- | ------ | ------- | ----------------- |
| `DIRECTORY` | `Path` | `.`     | Project directory |

### Behavior

Scans all configured template directories for `.jinja` files and runs each
through the PJX parser. Files that fail to parse produce an error message.
Files that parse successfully are counted.

### Example

```bash
pjx format .
```

Output:

```text
Formatted 47 files.
```

If a file fails:

```text
ERROR: templates/components/Broken.jinja: unexpected token at line 12
Formatted 46 files.
```

---

## pjx add

Install an npm package and copy its minified distribution files to the
configured vendor static directory.

### Usage

```bash
pjx add <PACKAGE>
```

### Arguments

| Argument  | Type  | Required | Description              |
| --------- | ----- | -------- | ------------------------ |
| `PACKAGE` | `str` | Yes      | npm package name         |

### Prerequisites

The `npm` command must be available on your `PATH`. If npm is not found, the
command prints an error and exits with code 1.

### Behavior

1. Runs `npm install <package>` in the current directory.
2. Looks for `node_modules/<package>/dist/*.min.js` files.
3. Copies each minified JS file to the configured `vendor_static_dir`.

### Example

```bash
pjx add alpinejs
```

Output:

```text
Installed alpinejs
  Copied cdn.min.js -> static/vendor/cdn.min.js
```

### Use case

Use `pjx add` to vendor JavaScript dependencies (Alpine.js, HTMX, etc.)
locally instead of relying on CDN links. The vendored files are served from
your static directory and work offline.

```bash
pjx add alpinejs
pjx add htmx.org
```

---

## pjx remove

Remove a previously installed npm package.

### Usage

```bash
pjx remove <PACKAGE>
```

### Arguments

| Argument  | Type  | Required | Description              |
| --------- | ----- | -------- | ------------------------ |
| `PACKAGE` | `str` | Yes      | npm package name         |

### Prerequisites

The `npm` command must be available on your `PATH`.

### Behavior

Runs `npm uninstall <package>` in the current directory. This removes the
package from `node_modules/` and updates `package.json`.

Note: `pjx remove` does not automatically delete files that were previously
copied to the vendor static directory by `pjx add`. Remove those manually
if needed.

### Example

```bash
pjx remove alpinejs
```

Output:

```text
Removed alpinejs
```

---

## Common Workflows

### New project setup

```bash
pjx init my-app
cd my-app
pjx add alpinejs
pjx add htmx.org
pjx dev .
```

### Development cycle

The typical development workflow follows this pattern:

```text
pjx init  -->  pjx dev  -->  pjx check  -->  pjx build  -->  pjx run
  |              |              |                |               |
  scaffold       develop        validate         compile         deploy
```

1. **pjx init** -- create the project skeleton once.
2. **pjx dev** -- run the dev server with auto-reload while developing.
3. **pjx check** -- validate all templates before committing or deploying.
4. **pjx build** -- compile templates and bundle CSS for production.
5. **pjx run** -- start the production server.

### CI/CD pipeline

Using taskipy (configured in `pyproject.toml`):

```bash
uv run task ci                  # Full pipeline: check + typecheck + test
```

Or step by step:

```bash
uv run task check               # ruff format --check + ruff check + rumdl
uv run task typecheck            # ty check
pjx check .                     # PJX template validation
pjx build .                     # Compile + bundle CSS
uv run task test                 # pytest
```

### Adding vendor packages

```bash
pjx add alpinejs
pjx add htmx.org
pjx add @tailwindcss/typography
```

The vendored files end up in your static directory and can be referenced in
layouts:

```html
<script src="/static/vendor/cdn.min.js" defer></script>
```

### Production deployment

```bash
# Build all templates and CSS
pjx build .

# Start with multiple workers
pjx run . --host 0.0.0.0 --port 80 --workers 4
```

For production configuration, set environment variables:

```bash
export PJX_DEBUG=false
export PJX_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
pjx run . --workers 4
```

---

## See also

- [[Installation]] -- installing PJX and its dependencies
- [[Project Structure]] -- standard directory layout and file conventions
- [[Configuration Reference]] -- all `pjx.toml` fields and environment variables
