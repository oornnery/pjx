# Middleware

## Overview

PJX supports two complementary middleware patterns for request processing:

1. **Named middleware** -- registered with `@pjx.middleware("name")` and declared
   in component or page frontmatter. These run *inside* the PJX request cycle,
   after Starlette/FastAPI middleware and before the page handler.

2. **Standard Starlette/FastAPI middleware** -- added via `app.add_middleware()`.
   These wrap the entire ASGI application and run on every request regardless
   of which route matched.

Named middleware is the idiomatic PJX approach for page-level guards (auth,
feature flags, A/B tests). Standard middleware is better suited for
cross-cutting concerns that apply globally (CORS, sessions, compression).

PJX ships with one built-in middleware -- `CSRFMiddleware` -- and provides
first-class integration points for popular third-party middleware like
`SessionMiddleware` and `slowapi`.

---

## Registering Named Middleware

Use the `@pjx.middleware()` decorator to register a named middleware function.
The function receives a Starlette `Request` and should raise an
`HTTPException` to block the request:

```python
from fastapi import HTTPException, Request
from pjx import PJX

app = FastAPI()
pjx = PJX(app)


@pjx.middleware("auth")
async def auth_middleware(request: Request):
    """Block unauthenticated requests."""
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Login required")


@pjx.middleware("admin")
async def admin_middleware(request: Request):
    """Restrict access to admin users."""
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
```

Key points:

- The decorator argument (`"auth"`, `"admin"`) is the identifier used in
  frontmatter declarations.
- Middleware functions must be `async`. They receive a single `Request`
  argument.
- To allow the request through, simply return (or return `None`).
- To block the request, raise `HTTPException` with the appropriate status
  code. The exception propagates to FastAPI's exception handler, which
  returns the error response.
- Named middleware is stored in `pjx._middleware_registry` -- a plain
  `dict[str, Callable]`.

---

## Declaring in Frontmatter

Once registered, named middleware is activated per-page by declaring it in
the template frontmatter:

```jinja
---
middleware "auth"
---

<h1>Dashboard</h1>
<p>Welcome back, {{ user.name }}.</p>
```

Multiple middleware can be declared in a single statement, separated by
commas:

```jinja
---
middleware "auth", "rate_limit"
---

<h1>API Settings</h1>
```

Alternatively, use multiple `middleware` declarations:

```jinja
---
middleware "auth"
middleware "admin"
---

<h1>Admin Panel</h1>
```

When PJX registers a page route (via `@pjx.page()` or `auto_routes()`), it
parses the template frontmatter and extracts all middleware names. At request
time, each named middleware is looked up in the registry and called in
sequence before the page handler executes.

---

## Execution Order

Middleware executes in a well-defined order:

1. **Starlette/FastAPI middleware** runs first (outermost layer). This
   includes `SessionMiddleware`, `CORSMiddleware`, `CSRFMiddleware`, and any
   other middleware added via `app.add_middleware()`.

2. **Layout middleware** (if using file-based routing with layouts that
   declare middleware) runs next.

3. **Page middleware** runs last, in the order declared in the frontmatter.

Within a single frontmatter declaration, middleware executes left-to-right:

```jinja
---
middleware "auth", "rate_limit", "feature_flag"
---
```

Execution order: `auth` -> `rate_limit` -> `feature_flag` -> page handler.

If any middleware raises an exception, subsequent middleware and the page
handler are skipped entirely. This means you should declare the most
restrictive checks first:

```jinja
---
middleware "auth", "admin"
---
```

Here `auth` runs before `admin` -- there is no point checking admin role if
the user is not authenticated at all.

---

## Auth Middleware Example

A complete login-required guard with session check and redirect:

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from pjx import PJX

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-session-secret")

pjx = PJX(app)


@pjx.middleware("auth")
async def require_login(request: Request):
    """Redirect unauthenticated users to the login page."""
    user = request.session.get("user")
    if not user:
        # Store the original URL so we can redirect back after login
        request.session["next"] = str(request.url)
        raise HTTPException(
            status_code=302,
            headers={"Location": "/login"},
        )


@pjx.page("/login", methods=["GET", "POST"])
async def login(request: Request):
    if request.method == "POST":
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")
        user = await authenticate(username, password)
        if user:
            request.session["user"] = {"id": user.id, "name": user.name}
            next_url = request.session.pop("next", "/dashboard")
            return RedirectResponse(next_url, status_code=303)
        return {"error": "Invalid credentials"}
    return {}


@pjx.page("/dashboard")
async def dashboard(request: Request):
    """Protected page -- requires login via frontmatter middleware."""
    user = request.session["user"]
    return {"user": user}
```

The `dashboard.jinja` template declares the middleware:

```jinja
---
middleware "auth"
---

<h1>Dashboard</h1>
<p>Hello, {{ user.name }}.</p>
```

With this setup, any unauthenticated request to `/dashboard` is redirected
to `/login`. After successful login, the user is sent back to the original
URL.

---

## CSRF Middleware

PJX ships with `CSRFMiddleware`, a double-submit cookie implementation that
protects against cross-site request forgery attacks. It is built on
Starlette's `BaseHTTPMiddleware`.

### How It Works

1. On every response, the middleware sets a signed CSRF cookie (readable by
   JavaScript, `httponly=False`).
2. On unsafe HTTP methods (`POST`, `PUT`, `DELETE`, `PATCH`), the middleware
   validates that the token submitted in the request (via header or form
   field) matches the cookie value.
3. Tokens are signed with HMAC-SHA256 to prevent forgery.
4. Token comparison uses `hmac.compare_digest` to prevent timing attacks.

### Enabling CSRF Protection

Pass `csrf=True` and a secret key to the `PJX` constructor:

```python
from fastapi import FastAPI
from pjx import PJX

app = FastAPI()
pjx = PJX(
    app,
    csrf=True,
    csrf_secret="a-long-random-secret-key-change-in-production",
)
```

If `csrf_secret` is omitted, a default placeholder is used. Always set a
proper secret in production.

### Configuration Options

| Parameter           | Type            | Default | Description                                    |
| ------------------- | --------------- | ------- | ---------------------------------------------- |
| `csrf`              | `bool`          | `False` | Enable CSRF middleware.                        |
| `csrf_secret`       | `str` or `None` | `None`  | HMAC signing key. Falls back to a placeholder. |
| `csrf_exempt_paths` | `set[str]`      | `set()` | URL paths to skip CSRF validation on.          |

The underlying `CSRFMiddleware` class accepts additional parameters when
instantiated directly:

| Parameter      | Type       | Default         | Description                            |
| -------------- | ---------- | --------------- | -------------------------------------- |
| `cookie_name`  | `str`      | `"_csrf"`       | Name of the CSRF cookie.               |
| `header_name`  | `str`      | `"X-CSRFToken"` | HTTP header checked for the token.     |
| `form_field`   | `str`      | `"csrf_token"`  | Form field name checked for the token. |
| `max_age`      | `int`      | `3600`          | Cookie max-age in seconds.             |
| `exempt_paths` | `set[str]` | `set()`         | URL paths exempt from CSRF checks.     |

### Exempt Paths

Some endpoints (webhooks, API callbacks) need to accept POST requests
without a CSRF token. Use `csrf_exempt_paths`:

```python
pjx = PJX(
    app,
    csrf=True,
    csrf_secret="your-secret",
    csrf_exempt_paths={"/webhooks/stripe", "/api/callback"},
)
```

Safe HTTP methods (`GET`, `HEAD`, `OPTIONS`, `TRACE`) are always exempt
and never require a token.

---

## CSRF with HTMX

HTMX sends requests via JavaScript, so it needs the CSRF token in a request
header. The simplest approach is to set `hx-headers` on the `<body>` tag so
that every HTMX request automatically includes the token:

```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
    <!-- All HTMX requests from this page include the CSRF token -->
    <button hx-post="/api/delete-item" hx-target="#items">
        Delete
    </button>
</body>
```

The `csrf_token()` function is automatically available in templates when
CSRF middleware is active. It returns the signed token string from the
current request.

For layouts, place the `hx-headers` attribute in your base layout so it
applies to all pages:

```jinja
{# layouts/Base.jinja #}
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{{ seo.title }}</title>
</head>
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
    {{ body }}
</body>
</html>
```

---

## CSRF with Forms

For traditional HTML form submissions (non-HTMX), include the CSRF token as
a hidden form field:

```html
<form method="post" action="/settings">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

    <label for="name">Display Name</label>
    <input type="text" id="name" name="name" value="{{ user.name }}">

    <button type="submit">Save</button>
</form>
```

The middleware checks the `csrf_token` form field when the request
`Content-Type` is form data and no `X-CSRFToken` header is present.

For forms that also use HTMX (e.g. `hx-post`), the header approach from
the previous section is preferred since the form field is not sent with
HTMX requests by default.

### Combined Example

A form that works both with and without JavaScript:

```html
<form method="post" action="/contact"
      hx-post="/contact" hx-target="#result">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

    <input type="text" name="message" placeholder="Your message">
    <button type="submit">Send</button>
</form>
<div id="result"></div>
```

When HTMX is active, the `hx-headers` on `<body>` provides the token via
header. When JavaScript is disabled, the hidden field provides the token
via form data. Both paths are validated by the middleware.

---

## Session Middleware

PJX does not ship its own session middleware. Use Starlette's built-in
`SessionMiddleware` for signed cookie-based sessions:

```python
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from pjx import PJX

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-session-secret")

pjx = PJX(app)
```

Sessions are available in handlers and middleware via `request.session`:

```python
@pjx.middleware("auth")
async def require_login(request: Request):
    if not request.session.get("user"):
        raise HTTPException(status_code=401)


@pjx.page("/profile")
async def profile(request: Request):
    return {"user": request.session["user"]}
```

### Session Configuration

`SessionMiddleware` accepts the following parameters:

| Parameter        | Type   | Default         | Description                           |
| ---------------- | ------ | --------------- | ------------------------------------- |
| `secret_key`     | `str`  | (required)      | Key for signing the session cookie.   |
| `session_cookie` | `str`  | `"session"`     | Name of the session cookie.           |
| `max_age`        | `int`  | `1209600` (14d) | Cookie max-age in seconds.            |
| `same_site`      | `str`  | `"lax"`         | SameSite cookie attribute.            |
| `https_only`     | `bool` | `False`         | Restrict cookie to HTTPS connections. |

For production deployments, always set `https_only=True` and use a strong,
unique `secret_key`.

---

## Rate Limiting

PJX does not include built-in rate limiting. The recommended approach is
[slowapi](https://github.com/laurentS/slowapi), which wraps
[limits](https://limits.readthedocs.io/) for use with FastAPI/Starlette.

### Installation

```bash
uv add slowapi
```

### Setup

```python
from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from pjx import PJX

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

pjx = PJX(app)
```

### Applying Rate Limits

Use the `@limiter.limit()` decorator on individual route handlers:

```python
@app.post("/api/login")
@limiter.limit("5/minute")
async def api_login(request: Request):
    form = await request.form()
    # ... authenticate
    return {"status": "ok"}


@app.get("/api/search")
@limiter.limit("30/minute")
async def api_search(request: Request):
    # ... search logic
    return {"results": []}
```

Note that `@limiter.limit()` is applied to FastAPI route functions directly,
not to PJX page handlers. For rate-limiting PJX pages, apply the decorator
to the underlying route or use a named middleware wrapper:

```python
@pjx.middleware("rate_limit")
async def rate_limit_middleware(request: Request):
    """Apply a general rate limit to pages that declare this middleware."""
    # slowapi checks are typically decorator-based;
    # for middleware-style limiting, use the limits library directly:
    from limits import parse as parse_limit
    from limits.storage import MemoryStorage

    storage = MemoryStorage()
    limit = parse_limit("60/minute")
    key = get_remote_address(request)
    if not storage.check(limit, key):
        raise HTTPException(status_code=429, detail="Too many requests")
```

### Rate Limit Headers

slowapi automatically adds standard rate limit headers to responses:

- `X-RateLimit-Limit` -- the rate limit ceiling
- `X-RateLimit-Remaining` -- remaining requests in the window
- `X-RateLimit-Reset` -- UTC epoch time when the window resets
- `Retry-After` -- seconds until the client can retry (on 429 responses)

---

## See Also

- [[Security]] -- CSRF best practices, Content-Security-Policy, and other
  security considerations
- [[FastAPI Integration]] -- full PJX/FastAPI integration guide
- [[HTMX Integration]] -- HTMX patterns including headers and request
  lifecycle
