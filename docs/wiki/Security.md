# Security

This guide covers production security practices for PJX applications. PJX
builds on FastAPI and Starlette, so standard ASGI security patterns apply.
PJX adds a CSRF middleware, SSE connection limiting, template auto-escaping,
and path traversal protection out of the box.

---

## Production Checklist

Before deploying a PJX application, verify every item:

- [ ] Set `PJX_SECRET_KEY` as an environment variable (random, 32+ characters)
- [ ] Enable `SessionMiddleware` with the secret key
- [ ] Enable CSRF protection (`csrf=True` on `PJX()`)
- [ ] Add rate limiting on authentication and mutation endpoints
- [ ] Set `debug = false` in production `pjx.toml`
- [ ] Configure Content Security Policy headers for your CDN sources
- [ ] Set `log_json = true` for structured log aggregation
- [ ] Enable health checks (`health=True`) for orchestration probes
- [ ] Configure CORS only if exposing APIs to other origins
- [ ] Restrict file permissions on `pages_dir` (no write access for untrusted users)

See [[Deployment]] for the full production configuration walkthrough.

---

## CSRF Protection

PJX ships a double-submit cookie CSRF middleware. When enabled, the middleware:

1. Sets a signed CSRF token in a cookie on every response.
2. On unsafe HTTP methods (POST, PUT, PATCH, DELETE), validates that the
   request includes a matching token in either a header or form field.
3. Rejects requests that fail validation with HTTP 403.

### Enabling CSRF

Pass `csrf=True` and a secret to the `PJX` constructor:

```python
import os
from pjx import PJX

pjx = PJX(
    app,
    csrf=True,
    csrf_secret=os.environ["PJX_SECRET_KEY"],
    csrf_exempt_paths={"/api/webhooks", "/health", "/ready"},
)
```

The `csrf_secret` is used to sign the token cookie. Use the same value as
your session secret key, or a dedicated secret -- either way, load it from
an environment variable.

### How Double-Submit Cookies Work

The double-submit cookie pattern does not require server-side session storage:

1. The server sets a signed cookie containing a random CSRF token.
2. The client reads the cookie value and includes it in every state-changing
   request (via header or hidden form field).
3. The server compares the cookie value against the header/field value. An
   attacker on a different origin cannot read the cookie, so they cannot
   forge a matching header.

This approach is stateless and works well with load-balanced deployments
where sticky sessions are not available.

### HTMX Integration

HTMX sends requests via `XMLHttpRequest`, so you need to attach the CSRF
token as a custom header. The simplest approach is to add `hx-headers` to
the `<body>` tag in your layout template:

```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
    <!-- All HTMX requests from descendants inherit this header -->
    {{ slot() }}
</body>
```

The `csrf_token()` template function is registered automatically when
`csrf=True`. It reads the token from the request cookie and returns the
raw value suitable for inclusion in headers or form fields.

Every HTMX request (`hx-post`, `hx-put`, `hx-delete`, `hx-patch`) that
originates from a child of this body element will include the
`X-CSRFToken` header automatically.

### Form Integration

For traditional HTML forms (non-HTMX), include a hidden input field:

```html
<form method="post" action="/auth/login">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <input type="text" name="username" required>
    <button type="submit">Log in</button>
</form>
```

The CSRF middleware checks both the `X-CSRFToken` header and the
`csrf_token` form field, so either mechanism is sufficient.

### Exempt Paths

Some endpoints should skip CSRF validation entirely. Pass a set of paths
to `csrf_exempt_paths`:

```python
pjx = PJX(
    app,
    csrf=True,
    csrf_secret=os.environ["PJX_SECRET_KEY"],
    csrf_exempt_paths={
        "/api/webhooks",     # Validated by webhook signature
        "/sse/clock",        # SSE streaming (GET-only)
        "/health",           # Health check probes
        "/ready",            # Readiness probes
        "/api/users",        # API with its own auth (API key / JWT)
    },
)
```

Use exempt paths for:

- **Webhook endpoints** that validate requests with a signature (e.g.,
  Stripe, GitHub).
- **SSE streaming endpoints** that only accept GET requests.
- **Health and readiness probes** used by orchestration systems.
- **Public API endpoints** protected by API keys, JWT, or OAuth rather
  than cookie-based sessions.

Never exempt an endpoint that accepts form submissions from a browser
session. That defeats the purpose of CSRF protection.

---

## Session Security

PJX does not manage sessions internally. Use Starlette's
`SessionMiddleware`, which signs cookies with `itsdangerous` to detect
tampering.

### Setup

```python
import os
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["PJX_SECRET_KEY"],
    session_cookie="session",
    max_age=3600,           # Session expires after 1 hour
    https_only=True,        # Cookie sent only over HTTPS
    same_site="lax",        # Prevents cross-site request leakage
)
```

### Reading and Writing Session Data

Access the session dict on the Starlette `Request` object:

```python
@app.post("/auth/login")
async def login(request: Request) -> Response:
    form = await request.form()
    username = str(form.get("username", "")).strip()[:100]
    request.session["user"] = username
    return RedirectResponse("/protected", status_code=303)

@app.post("/auth/logout")
async def logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
```

### Cookie Flags

Always set these flags in production:

| Flag         | Value                 | Purpose                                |
| ------------ | --------------------- | -------------------------------------- |
| `https_only` | `True`                | Prevents cookie transmission over HTTP |
| `same_site`  | `"lax"` or `"strict"` | Blocks cross-origin cookie sending     |
| `max_age`    | `3600` (or shorter)   | Limits session lifetime                |

The `same_site="lax"` setting allows top-level GET navigations (e.g.,
clicking a link from an email) while blocking cross-origin POST requests.
Use `"strict"` if your application does not need cross-site navigation.

### How `itsdangerous` Signing Works

`SessionMiddleware` serializes the session dict to JSON, signs it with
HMAC-SHA1 using your secret key, and stores the signed blob in the cookie.
On each request, the middleware verifies the signature before deserializing.
If the signature does not match (i.e., someone tampered with the cookie),
the session is silently reset to empty.

This means:

- Session data is **not encrypted** -- do not store sensitive values
  (passwords, tokens) directly in the session.
- Session data **is tamper-proof** -- the server detects any modification.
- The secret key must remain confidential. If it leaks, an attacker can
  forge arbitrary session cookies.

---

## Rate Limiting

Use `slowapi` (a Starlette/FastAPI wrapper around `limits`) to protect
authentication and mutation endpoints from brute-force and abuse.

### Basic Setup

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Decorating Endpoints

Apply rate limits to specific routes:

```python
@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request) -> Response:
    """Allow at most 5 login attempts per minute per IP."""
    ...

@app.post("/auth/logout")
@limiter.limit("10/minute")
async def logout(request: Request) -> Response:
    ...

@app.post("/htmx/todos/add")
@limiter.limit("30/minute")
async def add_todo(request: Request) -> HTMLResponse:
    """Limit todo creation to prevent spam."""
    ...
```

### Custom Key Functions

The default `get_remote_address` uses the client IP. Behind a reverse
proxy, you may need to read `X-Forwarded-For` or use a session-based key:

```python
def get_user_or_ip(request: Request) -> str:
    """Rate limit by session user if logged in, otherwise by IP."""
    user = request.session.get("user")
    if user:
        return f"user:{user}"
    return get_remote_address(request)

limiter = Limiter(key_func=get_user_or_ip)
```

When running behind a load balancer or CDN, configure your proxy to set
`X-Real-IP` or `X-Forwarded-For` and use `slowapi.util.get_remote_address`
which reads these headers automatically.

### Recommended Limits

| Endpoint type    | Suggested limit         | Rationale                      |
| ---------------- | ----------------------- | ------------------------------ |
| Login / signup   | `5/minute`              | Prevent credential stuffing    |
| Password reset   | `3/minute`              | Prevent email flooding         |
| Form submissions | `30/minute`             | Allow normal usage, block bots |
| API reads        | `60/minute`             | Generous but bounded           |
| SSE connect      | Use `check_sse_limit()` | See next section               |

---

## SSE Connection Limits

Server-Sent Events hold a long-lived HTTP connection open. Without limits,
a single client could exhaust server resources by opening hundreds of
concurrent streams.

### EventStream Connection Tracking

`EventStream` tracks active connections per client IP:

```python
from pjx.sse import EventStream

stream = EventStream(
    request,
    max_connections_per_ip=10,   # Max concurrent SSE connections per IP
    max_duration=3600,           # Auto-disconnect after 1 hour (seconds)
)
```

When a client exceeds `max_connections_per_ip`, the stream emits an error
event and terminates immediately:

```text
event: error
data: Too many connections
```

When `max_duration` elapses, the stream closes gracefully. The client can
reconnect (SSE has built-in automatic reconnection), and the new connection
starts fresh against the limit.

### Pre-Check with `check_sse_limit()`

Use `check_sse_limit()` as a guard at the top of your SSE route handler to
reject requests early with HTTP 429, before allocating any resources:

```python
from pjx.sse import check_sse_limit

@app.get("/sse/updates")
async def sse_updates(request: Request):
    check_sse_limit(request, max_per_ip=10)
    # Only reached if the limit is not exceeded
    stream = EventStream(request, max_connections_per_ip=10)
    ...
```

If the limit is exceeded, `check_sse_limit()` raises:

```python
HTTPException(status_code=429, detail="Too many SSE connections")
```

This returns an immediate HTTP 429 response to the client rather than
opening a connection and sending an SSE error event.

### Client-Side Handling

When using HTMX's `sse-connect`, the client will automatically retry on
connection close. To handle 429 responses gracefully, add a fallback:

```html
<div hx-ext="sse"
     sse-connect="/sse/updates"
     sse-error="handleSSEError(event)">
    ...
</div>
```

---

## Content Security Policy

A Content Security Policy (CSP) header tells the browser which sources of
content are allowed, mitigating XSS and data injection attacks.

### Example from the Demo Application

The example app in `examples/demo/app.py` sets CSP via middleware:

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
        "https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "font-src 'self'"
    )
    return response
```

### Recommended Directives

For production, tighten the policy by removing `'unsafe-inline'` and
`'unsafe-eval'` where possible:

| Directive         | Development                                                     | Production                                                     |
| ----------------- | --------------------------------------------------------------- | -------------------------------------------------------------- |
| `default-src`     | `'self'`                                                        | `'self'`                                                       |
| `script-src`      | `'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net` | `'self' https://cdn.jsdelivr.net`                              |
| `style-src`       | `'self' 'unsafe-inline'`                                        | `'self' 'unsafe-inline'` (needed for Alpine.js `x-bind:style`) |
| `img-src`         | `'self' data:`                                                  | `'self' data: https://your-cdn.com`                            |
| `connect-src`     | `'self'`                                                        | `'self'` (add SSE/WebSocket origins if needed)                 |
| `font-src`        | `'self'`                                                        | `'self' https://your-cdn.com`                                  |
| `frame-ancestors` | (not set)                                                       | `'none'` (replaces X-Frame-Options)                            |

Notes:

- **Alpine.js** requires `'unsafe-eval'` if you use `x-data` expressions
  that call `eval()` internally. Alpine v3 with CSP build eliminates this
  requirement -- use `@alpinejs/csp` in production.
- **HTMX** does not require `'unsafe-eval'`.
- **Tailwind CSS** inline styles may require `'unsafe-inline'` in
  `style-src`. If you use a Tailwind build step that generates a static
  CSS file, you can remove it.
- Add your CDN origins to `script-src` and `style-src` as needed.

### Additional Security Headers

The example app also sets these recommended headers:

```python
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["X-XSS-Protection"] = "1; mode=block"
response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
```

In production, also consider:

- `Strict-Transport-Security: max-age=63072000; includeSubDomains` (HSTS)
- `Permissions-Policy: camera=(), microphone=(), geolocation=()` (disable
  unused browser APIs)

---

## Template Security

### Auto-Escaping

Both the Jinja2 and MiniJinja template engines have HTML auto-escaping
enabled by default. All template variables are escaped before rendering:

```html
<!-- If user.name is "<script>alert('xss')</script>" -->
<!-- Output: &lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt; -->
<p>{{ user.name }}</p>
```

This applies to all template variables rendered with `{{ ... }}` syntax.
No configuration is needed -- auto-escaping is always on.

### XSS Risk with `bind:html` and `x-html`

The `bind:html` attribute in PJX components compiles to Alpine.js's
`x-html` directive, which sets `innerHTML` **without escaping**. This is
inherently dangerous with user-supplied content:

```html
<!-- DANGEROUS -- XSS if user_content contains script tags or event handlers -->
<div bind:html="user_content"></div>

<!-- Compiles to: -->
<div x-html="user_content"></div>
```

Safe alternatives:

```html
<!-- SAFE -- server-rendered and auto-escaped by the template engine -->
<div>{{ user_content }}</div>

<!-- SAFE -- if you must use bind:html, sanitize server-side first -->
<div bind:html="sanitized_content"></div>
```

If you must render HTML from user input, sanitize it on the server with a
library like `bleach` or `nh3` before passing it to the template.

### The `| safe` Filter

The `| safe` filter marks a value as pre-escaped, bypassing auto-escaping:

```html
<!-- Auto-escaping is DISABLED for this variable -->
<div>{{ user_content | safe }}</div>
```

Never apply `| safe` to user-supplied input. Reserve it for HTML fragments
that you have generated server-side (e.g., from `pjx.partial()`).

---

## Path Traversal Protection

PJX validates that all template paths resolve to a location within the
configured template directories. This prevents an attacker from requesting
a template like `../../etc/passwd`.

### How It Works

The `_find_template()` method in the PJX integration layer:

1. Resolves the requested template path to an absolute path using
   `Path.resolve()`.
2. Calls `candidate.relative_to(tpl_root)` to verify the resolved path
   is a descendant of the template directory.
3. If `relative_to()` raises `ValueError`, the path is outside the
   allowed directory and the template is not loaded.

```python
# Simplified from pjx/integration.py
for tpl_dir in self.config.template_dirs:
    tpl_root = Path(tpl_dir).resolve()
    candidate = (Path(tpl_dir) / template).resolve()
    try:
        candidate.relative_to(tpl_root)
    except ValueError:
        continue  # Path escapes the template directory
    if candidate.exists():
        return candidate
```

This check runs on every template resolution, including:

- Page templates loaded by `@pjx.page()`
- Component templates loaded by `<Import>` and `pjx.partial()`
- Layout templates discovered by file-based routing

### Symlinks

`Path.resolve()` follows symlinks before the `relative_to()` check. A
symlink inside `templates/` that points to `/etc/passwd` will be rejected
because the resolved path falls outside the template directory. Do not
rely on symlinks to organize templates if your target paths are outside
the template roots.

---

## Handler Loading Security

File-based routing (`auto_routes()`) scans `pages_dir` and loads `.py`
files via `importlib`. This means any Python file in the pages directory
is **executed** when routes are scanned.

### What Gets Loaded

The router scans for two file types:

- **`.jinja` files** -- registered as page templates (not executed as code).
- **`.py` files** -- dynamically imported via `importlib.util.spec_from_file_location()`.
  The module is executed, and exported route handlers are registered.

Files starting with `_` (e.g., `_helpers.py`, `__init__.py`) are skipped.
Special files like `layout.jinja`, `loading.jinja`, and `error.jinja` are
skipped during page scanning (they are used for layout discovery).

### Securing `pages_dir`

- Set restrictive file permissions on the `pages_dir` directory. Only
  trusted users and deployment processes should have write access.
- Never point `pages_dir` at a user-upload directory or any path where
  untrusted users can create files.
- Review all `.py` files in `pages_dir` before deployment. Any Python code
  placed there will be executed by the application.
- In CI/CD pipelines, verify that no unexpected files appear in `pages_dir`
  before building the container image.

```bash
# Example: restrict pages_dir to owner-only write
chmod -R 755 pages/
chown -R appuser:appuser pages/
```

---

## Secret Key Management

The `PJX_SECRET_KEY` environment variable is used for session signing,
CSRF token generation, and any other cryptographic operations in your
application. Proper management of this key is critical.

### Generating a Strong Key

Use Python's `secrets` module to generate a cryptographically secure key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This produces a 43-character URL-safe string with 256 bits of entropy.

### Environment Variable Configuration

Set the key as an environment variable. Never hardcode it in source code
or commit it to version control:

```bash
# .env (excluded from git via .gitignore)
PJX_SECRET_KEY="your-random-key-here"

# Or export directly
export PJX_SECRET_KEY="your-random-key-here"
```

Load it in your application:

```python
import os

secret_key = os.environ["PJX_SECRET_KEY"]
```

Using `os.environ["PJX_SECRET_KEY"]` (with square brackets, not `.get()`)
ensures the application fails immediately at startup if the key is missing,
rather than running with an empty or default value.

### Key Rotation Strategy

When rotating the secret key:

1. All active sessions are invalidated (users must log in again).
2. All outstanding CSRF tokens become invalid (forms in open browser tabs
   will fail on submission).
3. Any other signed values (e.g., password reset tokens) become invalid.

To rotate:

1. Generate a new key.
2. Update the environment variable in your deployment configuration.
3. Restart all application instances simultaneously (or use a rolling
   restart if your middleware supports multiple valid keys).
4. Inform users that they may need to log in again.

For zero-downtime rotation, implement a middleware that accepts both the
old and new key during a transition window. Starlette's
`SessionMiddleware` does not support this natively, so you would need a
custom session middleware or a key versioning wrapper.

### Common Mistakes

| Mistake                        | Risk                                  | Fix                                             |
| ------------------------------ | ------------------------------------- | ----------------------------------------------- |
| Hardcoded secret in source     | Key exposed in version control        | Use `os.environ["PJX_SECRET_KEY"]`              |
| Default fallback value         | App runs with a known key             | Use `os.environ[]`, not `.get()` with a default |
| Short or predictable key       | Brute-force attacks on signed cookies | Use `secrets.token_urlsafe(32)` or longer       |
| Same key across environments   | Staging tokens valid in production    | Generate unique keys per environment            |
| Key committed to `.env` in git | Exposed in repository history         | Add `.env` to `.gitignore`, use secrets manager |

---

## See Also

- [[Middleware]] -- CSRF middleware internals, named middleware patterns
- [[Deployment]] -- Production configuration, Docker, reverse proxy setup
- [[Configuration Reference]] -- All `pjx.toml` options including security-related settings
- [[SSE and Realtime]] -- EventStream usage and connection management
- [[FastAPI Integration]] -- Starlette middleware, exception handlers
