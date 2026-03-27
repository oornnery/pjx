# Security Guide

Production security checklist and best practices for PJX applications.

## Quick Checklist

- [ ] Set `PJX_SECRET_KEY` environment variable (unique, random, 32+ chars)
- [ ] Enable `SessionMiddleware` with the secret key
- [ ] Enable CSRF protection (`csrf=True` on `PJX()`)
- [ ] Add rate limiting on auth and mutation endpoints
- [ ] Set `debug=False` in production `pjx.toml`
- [ ] Configure CSP headers appropriate for your CDN sources
- [ ] Set `log_json=True` for structured log aggregation
- [ ] Enable health checks (`health=True`) for orchestration
- [ ] Configure CORS if exposing APIs to other origins
- [ ] Restrict file permissions on `pages_dir` (only trusted `.py` files)

## Session Security

PJX does not manage sessions internally. Use Starlette's `SessionMiddleware`
with a strong secret key:

```python
import os
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["PJX_SECRET_KEY"],
    session_cookie="session",
    max_age=3600,
    https_only=True,   # Always True in production
    same_site="lax",
)
```

**Never** store raw values in cookies. The `SessionMiddleware` signs cookies
with `itsdangerous` so tampering is detected automatically.

### Secret Key Management

Generate a strong key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Set it as an environment variable — never commit it to source control:

```bash
export PJX_SECRET_KEY="your-random-key-here"
```

## CSRF Protection

PJX includes a double-submit cookie CSRF middleware. Enable it:

```python
pjx = PJX(
    app,
    csrf=True,
    csrf_secret=os.environ["PJX_SECRET_KEY"],
    csrf_exempt_paths={"/api/webhooks", "/health", "/ready"},
)
```

### HTMX Integration

Add `hx-headers` to your layout `<body>` tag to automatically send the
CSRF token on every HTMX request:

```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
```

### HTML Forms

Include a hidden field in forms:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### Exempt Paths

Exempt paths skip CSRF validation. Use for:

- Webhook endpoints (validated by signature instead)
- SSE streaming endpoints
- Health check endpoints
- Public API endpoints with their own auth (API keys, JWT)

## Rate Limiting

Use `slowapi` to protect auth and mutation endpoints:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request): ...
```

## SSE Connection Limits

`EventStream` tracks connections per IP to prevent resource exhaustion:

```python
from pjx.sse import EventStream

stream = EventStream(
    request,
    max_connections_per_ip=10,  # Max concurrent SSE connections per IP
    max_duration=3600,          # Auto-disconnect after 1 hour
)
```

## Content Security Policy

Configure CSP headers to match your application's CDN sources.
Only include origins you actually use:

```python
response.headers["Content-Security-Policy"] = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'"
)
```

Avoid `'unsafe-eval'` in production. Only add it in debug mode if needed
for development tools.

## Handler Loading Security

File-based routing (`auto_routes()`) executes `.py` files found in
`pages_dir` via `importlib`. Ensure:

- `pages_dir` has restrictive file permissions (no write access for
  untrusted users)
- Never point `pages_dir` at a user-upload directory
- Review all `.py` files in `pages_dir` before deployment

## Template Security

### Auto-Escaping

Both Jinja2 and MiniJinja engines have auto-escaping enabled by default.
All template variables are HTML-escaped unless explicitly marked safe.

### `bind:html` / `x-html` Directive

The `bind:html` attribute compiles to Alpine's `x-html` directive, which
sets `innerHTML` without escaping. **Never** pass unsanitized user input
to `bind:html`:

```html
<!-- DANGEROUS — XSS if user_content is not sanitized -->
<div bind:html="user_content"></div>

<!-- SAFE — server-rendered and auto-escaped -->
<div>{{ user_content }}</div>
```

## Configuration Reference

Production `pjx.toml`:

```toml
debug = false
log_json = true
log_level = "INFO"
validate_props = true

# CORS (only if needed)
cors_origins = ["https://yourdomain.com"]
cors_methods = ["GET", "POST"]
cors_credentials = true
```

## Health Checks

Enable health endpoints for Kubernetes or container orchestration:

```python
pjx = PJX(app, health=True)
```

- `GET /health` — Liveness probe, always returns `{"status": "ok"}`
- `GET /ready` — Readiness probe, checks template directories exist
