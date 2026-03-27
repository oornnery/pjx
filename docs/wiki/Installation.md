# Installation

This page covers how to install PJX, verify the setup, and configure your
editor for the best development experience.

---

## Requirements

| Requirement | Minimum version | Notes                          |
| ----------- | --------------- | ------------------------------ |
| Python      | 3.14+           | Required (no older versions)   |
| uv          | latest          | Recommended package manager    |
| pip         | 21+             | Alternative to uv              |

PJX targets Python 3.14 and above. Earlier versions are **not** supported.

### Check your Python version

```bash
python --version
```

If you see a version below 3.14, install or update Python from
[python.org](https://www.python.org/downloads/) or via your system package
manager.

### Install uv (recommended)

[uv](https://docs.astral.sh/uv/) is the recommended package manager for PJX
projects. It handles virtual environments, dependency resolution, and lockfiles
in a single tool.

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verify the installation:

```bash
uv --version
```

---

## Install with uv (recommended)

Add PJX to an existing project:

```bash
uv add pjx
```

Or create a new project with PJX from scratch:

```bash
uv init my-app
cd my-app
uv add pjx
```

uv will create a virtual environment, resolve all dependencies, and generate a
lockfile automatically.

---

## Install with pip

If you prefer pip, install PJX into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

pip install pjx
```

---

## Verify installation

After installing, confirm that PJX is available:

```bash
pjx --version
```

You can also verify the package imports correctly:

```bash
python -c "import pjx; print(pjx.__version__)"
```

Both commands should print the installed version (e.g. `0.0.1`).

---

## Dependencies

PJX installs the following runtime dependencies automatically:

| Package              | Purpose                                   |
| -------------------- | ----------------------------------------- |
| `fastapi`            | Web framework                             |
| `jinja2`             | Primary template engine                   |
| `minijinja`          | Fast Rust-backed template engine          |
| `pydantic`           | Data validation and settings              |
| `pydantic-settings`  | Configuration from TOML and env vars      |
| `python-multipart`   | Form data parsing                         |
| `itsdangerous`       | Signed session cookies                    |
| `sse-starlette`      | Server-Sent Events streaming              |
| `python-json-logger` | Structured JSON logging                   |
| `rich`               | CLI output formatting                     |
| `typer`              | CLI framework                             |
| `uvicorn`            | ASGI server                               |

All of these are installed as part of the default `pjx` package. You do not
need to install them separately.

---

## Optional dependencies

The following packages are **not** required but enhance specific workflows:

### `slowapi` -- rate limiting (dev only)

Useful for protecting auth and mutation endpoints during development and
testing. Listed as a dev dependency in the PJX repository itself.

```bash
uv add --dev slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request): ...
```

### `httpx` -- test client

Required for running integration tests against FastAPI endpoints:

```bash
uv add --dev httpx
```

See [[FastAPI Integration]] for testing examples.

---

## Editor setup

### VS Code

Install the following extensions for the best experience with `.jinja` files:

- **Better Jinja** (`samuelcolvin.jinjahtml`) -- syntax highlighting and
  snippets for Jinja templates
- **Ruff** (`charliermarsh.ruff`) -- linting and formatting for Python files

Add these settings to `.vscode/settings.json` in your project:

```json
{
  "files.associations": {
    "*.jinja": "jinja-html"
  },
  "emmet.includeLanguages": {
    "jinja-html": "html"
  },
  "[jinja-html]": {
    "editor.defaultFormatter": "samuelcolvin.jinjahtml"
  }
}
```

This gives you HTML autocompletion, Emmet abbreviations, and Jinja syntax
highlighting inside `.jinja` files.

### Other editors

For any editor that supports TextMate grammars, associate `.jinja` files with
the `jinja-html` or `html` scope. Most editors with Jinja plugins will
recognize the `.jinja` extension automatically.

---

## Create your first project

Scaffold a new PJX project with the CLI:

```bash
pjx init my-app
```

This creates the following structure:

```text
my-app/
├── pjx.toml                # Configuration
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI + PJX entrypoint
│   ├── core/config.py       # Settings
│   ├── pages/               # Page route handlers
│   ├── api/v1/              # JSON API endpoints
│   ├── models/              # Pydantic schemas
│   ├── services/            # Business logic
│   ├── middleware/           # Custom middleware
│   ├── templates/
│   │   ├── pages/           # Page templates
│   │   ├── components/      # Reusable components
│   │   └── layouts/         # Base layouts
│   └── static/
│       ├── css/
│       ├── js/
│       └── images/
```

| File / directory              | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| `app/main.py`                 | FastAPI entry point with PJX integration  |
| `pjx.toml`                    | Engine, debug, template dirs, and more    |
| `app/templates/pages/`        | Page templates mapped to routes           |
| `app/templates/components/`   | Reusable `.jinja` components              |
| `app/templates/layouts/`      | Base layouts with `<Slot />` placeholders |
| `app/static/`                 | Static assets served by FastAPI           |

Start the development server:

```bash
cd my-app
pjx dev .
```

The server starts at `http://localhost:8000` with hot reload enabled.

See [[Project Structure]] for a detailed explanation of each directory and file
convention.

---

## Next steps

Head to [[Quick Start]] for a guided walkthrough that builds a working
application with components, state, HTMX interactions, and layouts.

---

## Troubleshooting

### `python: command not found` or wrong version

Make sure Python 3.14+ is installed and on your `PATH`. On systems with
multiple Python versions, you may need to use `python3` or `python3.14`
explicitly:

```bash
python3.14 --version
```

If using uv, you can pin the Python version:

```bash
uv python install 3.14
uv python pin 3.14
```

### `uv: command not found`

The uv binary is not on your `PATH`. Re-run the install script or add the
install directory to your shell profile:

```bash
# Default install location
export PATH="$HOME/.local/bin:$PATH"
```

Restart your shell or run `source ~/.bashrc` (or `~/.zshrc`) after editing.

### `pjx: command not found` after install

The `pjx` CLI entry point requires the virtual environment to be active. If
you installed with uv:

```bash
uv run pjx --version
```

If you installed with pip, activate the virtual environment first:

```bash
source .venv/bin/activate
pjx --version
```

### `ModuleNotFoundError: No module named 'pjx'`

This usually means you are running Python outside the virtual environment
where PJX is installed. Activate the environment or use `uv run`:

```bash
uv run python -c "import pjx; print(pjx.__version__)"
```

### Dependency conflicts

If you see resolver errors during installation, try creating a fresh
environment:

```bash
uv venv --python 3.14
uv add pjx
```

Or with pip:

```bash
python3.14 -m venv .venv --clear
source .venv/bin/activate
pip install pjx
```

### Permission errors on Linux / macOS

Avoid installing with `sudo pip`. Always use a virtual environment. If you see
permission errors with uv, check that `~/.local/bin` is writable:

```bash
ls -la ~/.local/bin/
```

For further help, see [[Troubleshooting]] or
[open an issue](https://github.com/oornnery/pjx/issues).
