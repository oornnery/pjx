# Deployment

## Overview

This guide covers taking a PJX application from development to production.
PJX applications are standard ASGI apps built on FastAPI, so they deploy
with the same tools as any Python web application: Uvicorn, Docker, and a
reverse proxy. PJX adds configuration options in `pjx.toml` for production
logging, health checks, CORS, and performance tuning.

---

## Production `pjx.toml`

A production configuration disables debug features, enables structured
logging, and turns off runtime overhead that is only useful during
development:

```toml
# pjx.toml -- production
debug = false
log_json = true
log_level = "WARNING"
validate_props = false

engine = "hybrid"
render_mode = "inline"

template_dirs = ["app/templates"]
pages_dir = "app/templates/pages"
static_dir = "app/static"

htmx = true
alpine = true
tailwind = false

# CORS (only if your API serves a different origin)
cors_origins = ["https://yourdomain.com"]
cors_methods = ["GET", "POST"]
cors_headers = []
cors_credentials = true
```

Key differences from development defaults:

| Setting          | Development | Production  | Why                                          |
| ---------------- | ----------- | ----------- | -------------------------------------------- |
| `debug`          | `true`      | `false`     | Disables detailed error pages, extra logging |
| `log_json`       | `false`     | `true`      | Machine-readable logs for aggregation        |
| `log_level`      | `"DEBUG"`   | `"WARNING"` | Reduces log volume                           |
| `validate_props` | `true`      | `false`     | Skips runtime type checks for performance    |
| `render_mode`    | `"include"` | `"inline"`  | Faster rendering for leaf components         |

See [[Configuration Reference]] for the full list of options.

---

## Running with Uvicorn

### Using the PJX CLI

The `pjx run` command starts a Uvicorn server with sensible defaults:

```bash
# Development (single worker, auto-reload)
pjx dev .

# Production (4 workers, no reload)
pjx run --workers 4
```

### Using Uvicorn Directly

For full control over Uvicorn options, invoke it directly:

```bash
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level warning
```

The `--workers` flag spawns multiple Uvicorn worker processes. Each worker
runs a separate copy of your application. As a starting point, set workers
to `2 * CPU_CORES + 1`.

### Using Gunicorn with Uvicorn Workers

For production deployments that need process management, graceful restarts,
and pre-fork worker handling, use Gunicorn as the process manager with
Uvicorn workers:

```bash
gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
```

Gunicorn handles:

- Worker process lifecycle (restart on crash, graceful shutdown)
- Pre-fork model (each worker is a separate OS process)
- Signal handling (SIGHUP for config reload, SIGTERM for shutdown)

### Systemd Service

For bare-metal or VM deployments, run under systemd:

```ini
# /etc/systemd/system/pjx-app.service
[Unit]
Description=PJX Application
After=network.target

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/pjx-app
Environment=PJX_SECRET_KEY=your-secret-key
ExecStart=/opt/pjx-app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pjx-app
sudo systemctl start pjx-app
```

---

## Health Endpoints

PJX provides built-in health and readiness endpoints for container
orchestration systems like Kubernetes, ECS, and Docker Swarm.

### Enabling Health Checks

Pass `health=True` to the PJX constructor:

```python
pjx = PJX(app, health=True)
```

This registers two endpoints:

| Endpoint      | Purpose         | Response                                                                             |
| ------------- | --------------- | ------------------------------------------------------------------------------------ |
| `GET /health` | Liveness probe  | `{"status": "ok"}` -- always succeeds                                                |
| `GET /ready`  | Readiness probe | `{"status": "ready", "checks": {...}}` or `{"status": "not_ready", "checks": {...}}` |

### How They Work

The **liveness probe** (`/health`) always returns `{"status": "ok"}` with
HTTP 200. It confirms the process is running and can handle HTTP requests.
If this endpoint stops responding, the orchestrator should restart the
container.

The **readiness probe** (`/ready`) checks that all configured template
directories exist on disk:

```python
# From pjx/health.py
@app.get("/ready")
async def ready() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for tpl_dir in config.template_dirs:
        checks[str(tpl_dir)] = tpl_dir.exists()
    all_ready = all(checks.values())
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
    }
```

If any template directory is missing (e.g., a volume mount has not
attached yet), the readiness probe returns `"not_ready"` and the
orchestrator will not route traffic to this instance.

### Kubernetes Probe Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pjx-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pjx-app
  template:
    metadata:
      labels:
        app: pjx-app
    spec:
      containers:
        - name: pjx-app
          image: your-registry/pjx-app:latest
          ports:
            - containerPort: 8000
          env:
            - name: PJX_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: pjx-secrets
                  key: secret-key
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 3
            periodSeconds: 5
            failureThreshold: 2
          resources:
            requests:
              memory: "128Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1000m"
```

### Docker Compose Health Check

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PJX_SECRET_KEY=${PJX_SECRET_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s
```

### CSRF Exemption

If CSRF protection is enabled, exempt the health endpoints to allow
unauthenticated probe requests:

```python
pjx = PJX(
    app,
    health=True,
    csrf=True,
    csrf_secret=os.environ["PJX_SECRET_KEY"],
    csrf_exempt_paths={"/health", "/ready"},
)
```

---

## Structured Logging

PJX's logging system supports two output modes: Rich (human-readable, for
development) and JSON (machine-readable, for production).

### Enabling JSON Logging

Set `log_json = true` in `pjx.toml`:

```toml
log_json = true
log_level = "WARNING"
```

Or via environment variable:

```bash
export PJX_LOG_JSON=true
export PJX_LOG_LEVEL=WARNING
```

### JSON Output Format

When `log_json` is enabled, PJX uses `python-jsonlogger` to emit
structured JSON lines:

```json
{"timestamp": "2026-03-27T14:30:00.000Z", "level": "WARNING", "name": "pjx", "module": "integration", "message": "Template not found: missing.jinja"}
{"timestamp": "2026-03-27T14:30:01.000Z", "level": "ERROR", "name": "pjx", "module": "router", "message": "Route handler raised exception"}
```

Each log line includes:

| Field       | Description                                       |
| ----------- | ------------------------------------------------- |
| `timestamp` | ISO 8601 timestamp                                |
| `level`     | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `name`      | Logger name (always `pjx` for framework logs)     |
| `module`    | Python module that emitted the log                |
| `message`   | Human-readable message                            |

### How It Works

The `setup_logging()` function in `pjx/log.py` configures the `pjx`
logger based on configuration:

```python
# Simplified from pjx/log.py
if json_output:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(module)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
            },
        )
    )
else:
    handler = RichHandler(rich_tracebacks=True, show_path=debug, markup=True)
```

In development (`log_json = false`), Rich provides colored output with
tracebacks. In production (`log_json = true`), JSON lines are emitted to
stdout for ingestion by log aggregators.

### Log Level Configuration

| Level      | Use case                                                        |
| ---------- | --------------------------------------------------------------- |
| `DEBUG`    | Development only. Verbose output including template resolution. |
| `INFO`     | Development or staging. Request lifecycle, route registration.  |
| `WARNING`  | Production default. Missing templates, deprecated features.     |
| `ERROR`    | Always logged. Unhandled exceptions, failed health checks.      |
| `CRITICAL` | Always logged. Application cannot continue.                     |

The `level` parameter in `setup_logging()` takes precedence over the
`debug` flag. If `level` is set, it is used directly. If `level` is not
set, `debug=True` sets DEBUG and `debug=False` sets INFO.

### Integration with Log Aggregators

JSON-formatted logs on stdout are compatible with:

- **ELK Stack** (Elasticsearch, Logstash, Kibana) -- Filebeat or Fluentd
  reads stdout from the container.
- **Datadog** -- The Datadog agent auto-detects JSON logs from Docker
  containers.
- **AWS CloudWatch** -- CloudWatch Logs agent ingests stdout from ECS
  tasks or Lambda.
- **Google Cloud Logging** -- Automatically parses JSON from GKE pod
  stdout.

No additional log shipping configuration is needed beyond directing
container stdout to your aggregator.

---

## CORS Configuration

Cross-Origin Resource Sharing (CORS) headers are needed when your API
serves requests from a different origin than your frontend (e.g., a
single-page application on a separate domain).

### Configuration in `pjx.toml`

```toml
cors_origins = ["https://app.yourdomain.com", "https://admin.yourdomain.com"]
cors_methods = ["GET", "POST", "PUT", "DELETE"]
cors_headers = ["Authorization", "X-CSRFToken"]
cors_credentials = true
```

| Setting            | Type        | Default         | Description                                |
| ------------------ | ----------- | --------------- | ------------------------------------------ |
| `cors_origins`     | `list[str]` | `[]` (disabled) | Allowed origins. Empty list disables CORS. |
| `cors_methods`     | `list[str]` | `["GET"]`       | Allowed HTTP methods.                      |
| `cors_headers`     | `list[str]` | `[]`            | Additional allowed request headers.        |
| `cors_credentials` | `bool`      | `false`         | Whether to allow credentials (cookies).    |

### Example: API + Frontend on Different Origins

```toml
# Frontend at https://app.example.com
# API at https://api.example.com
cors_origins = ["https://app.example.com"]
cors_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
cors_headers = ["Authorization", "X-CSRFToken", "Content-Type"]
cors_credentials = true
```

### Security Notes

- Never use `cors_origins = ["*"]` with `cors_credentials = true`. Browsers
  reject this combination.
- List specific origins rather than wildcards in production.
- If your frontend and API are on the same origin (common with PJX since
  it serves HTML and API from the same app), you do not need CORS at all.
  Leave `cors_origins` empty.

---

## Static Files

### Development: FastAPI Mount

During development, serve static files directly from FastAPI:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

PJX handles this automatically when `static_dir` is configured in
`pjx.toml`. Files are served with no caching in debug mode:

```python
# From examples/demo/app/main.py
if request.url.path.startswith("/static/"):
    response.headers["Cache-Control"] = "no-store"
```

### Production: Nginx

In production, serve static files directly from nginx to avoid consuming
Python worker processes:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Static files served by nginx
    location /static/ {
        alias /opt/pjx-app/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options "nosniff";
    }

    # Proxy everything else to Uvicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
    }
}
```

### Production: CDN

For high-traffic sites, put static assets behind a CDN (CloudFront,
Cloudflare, Fastly). Update your templates to reference the CDN URL:

```toml
# pjx.toml
static_url = "https://cdn.yourdomain.com/static"
```

Set long cache headers on the origin (nginx or S3) and use content hashing
or versioned paths for cache busting.

---

## Environment Variables

PJX reads configuration from environment variables with the `PJX_` prefix.
Environment variables override values in `pjx.toml`.

### Complete Checklist

| Variable             | Required | Default     | Description                                                |
| -------------------- | -------- | ----------- | ---------------------------------------------------------- |
| `PJX_SECRET_KEY`     | Yes      | (none)      | Secret for sessions, CSRF. Must be set in production.      |
| `PJX_DEBUG`          | No       | `false`     | Enable debug mode.                                         |
| `PJX_LOG_JSON`       | No       | `false`     | Enable JSON structured logging.                            |
| `PJX_LOG_LEVEL`      | No       | `"INFO"`    | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).         |
| `PJX_ENGINE`         | No       | `"hybrid"`  | Template engine (`hybrid`, `jinja2`, `minijinja`, `auto`). |
| `PJX_VALIDATE_PROPS` | No       | `true`      | Enable runtime prop type validation.                       |
| `PJX_RENDER_MODE`    | No       | `"include"` | Component render mode (`include` or `inline`).             |

### Precedence Order

Configuration values are resolved in this order (highest priority first):

1. Environment variables (`PJX_*`)
2. Values in `pjx.toml`
3. Constructor arguments to `PJXConfig()`
4. Built-in defaults

### Example `.env` File

```bash
# .env (add to .gitignore, never commit)
PJX_SECRET_KEY="nR7kX9pQ2mW4vB8yT1cA6dF3hJ5gL0eS"
PJX_DEBUG=false
PJX_LOG_JSON=true
PJX_LOG_LEVEL=WARNING
```

Load with a tool like `direnv`, Docker's `--env-file`, or your deployment
platform's secrets manager.

---

## Docker

### Minimal Dockerfile

```dockerfile
FROM python:3.14-slim AS base

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Build and Run

```bash
docker build -t pjx-app .
docker run -d \
    -p 8000:8000 \
    -e PJX_SECRET_KEY="your-secret-key" \
    -e PJX_LOG_JSON=true \
    -e PJX_LOG_LEVEL=WARNING \
    pjx-app
```

### Multi-Stage Build

For smaller images, use a multi-stage build that separates the build
environment from the runtime:

```dockerfile
# Stage 1: Build
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .

# Stage 2: Runtime
FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /app /app
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Docker Compose

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./static:/usr/share/nginx/html/static
    depends_on:
      app:
        condition: service_healthy
```

---

## Performance Tuning

### Engine Choice

PJX supports multiple template engines. Choose based on your workload:

| Engine             | Best for                  | Trade-off                                                         |
| ------------------ | ------------------------- | ----------------------------------------------------------------- |
| `hybrid` (default) | Most applications         | Uses Jinja2 for pages, MiniJinja for components. Good balance.    |
| `jinja2`           | Full Jinja2 compatibility | Slower for component-heavy pages. Full filter/extension support.  |
| `minijinja`        | Maximum render speed      | Limited filter set. Best for simple components.                   |
| `auto`             | Gradual migration         | Auto-selects per template. Slight overhead from engine detection. |

Set in `pjx.toml`:

```toml
engine = "hybrid"
```

### Disable Prop Validation in Production

When `validate_props = true`, PJX validates component prop types at render
time. This catches bugs during development but adds overhead in production:

```toml
# Development
validate_props = true

# Production
validate_props = false
```

Prop validation uses Pydantic models under the hood. Disabling it skips
model construction and validation on every component render call.

### Render Mode

PJX supports two component render modes:

| Mode                | Behavior                                           | Use case                           |
| ------------------- | -------------------------------------------------- | ---------------------------------- |
| `include` (default) | Components rendered as Jinja `{% include %}` calls | Deep component trees, shared state |
| `inline`            | Component templates inlined at compile time        | Leaf components, maximum speed     |

For leaf components (components with no children or slots), `inline` mode
eliminates the template include overhead:

```toml
render_mode = "inline"
```

In practice, `inline` mode provides the most benefit for pages that render
many small components (e.g., a list of cards or table rows).

### Worker Count

The number of Uvicorn workers determines how many concurrent requests your
application can handle. A good starting formula:

```text
workers = 2 * CPU_CORES + 1
```

For a 4-core machine:

```bash
uvicorn app.main:app --workers 9
```

If your application is IO-bound (database queries, external API calls),
you may benefit from more workers. If it is CPU-bound (heavy template
rendering), fewer workers with more memory per worker may be better.

### Caching Strategies

For pages that do not change frequently, consider:

- **HTTP caching** -- Set `Cache-Control` headers on responses. Use
  `stale-while-revalidate` for pages that can tolerate slightly stale
  content.
- **Reverse proxy caching** -- Configure nginx or Varnish to cache
  rendered HTML responses.
- **CDN caching** -- For fully static pages, serve from a CDN edge.

PJX does not include a built-in response cache. Use standard HTTP caching
mechanisms or add a caching middleware.

### Template Precompilation

Jinja2 supports bytecode caching to avoid re-parsing templates on every
request. PJX enables this automatically. Ensure the template cache
directory is writable by the application user:

```bash
# Default cache location
chmod 755 /app/__pycache__/
```

---

## See Also

- [[Security]] -- CSRF, sessions, rate limiting, secret key management
- [[Configuration Reference]] -- All `pjx.toml` settings with defaults
- [[Template Engines]] -- Engine comparison, MiniJinja vs Jinja2
- [[Middleware]] -- Custom middleware, CORS middleware integration
- [[SSE and Realtime]] -- SSE connection limits in production
