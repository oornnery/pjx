# Troubleshooting

Common errors, their causes, and how to fix them.

---

## Template Not Found

**Symptom:** A `TemplateNotFound` error at render time, even though the file
exists on disk.

### Common causes

| Cause                                  | Fix                                                                                                                           |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Wrong path in `pjx.page(template=...)` | The path is relative to `template_dirs`, not the project root. Use `"pages/Home.jinja"`, not `"templates/pages/Home.jinja"`.  |
| `template_dirs` not configured         | Set `template_dirs = ["templates"]` in `pjx.toml`.                                                                            |
| File not inside any template directory | Move the file into a directory listed in `template_dirs`.                                                                     |
| Typo in filename or extension          | PJX expects `.jinja` files. Double-check case sensitivity on Linux.                                                           |
| File-based routing mismatch            | `pjx.auto_routes()` scans `pages/` inside the first template directory. Ensure the file is at `templates/pages/<name>.jinja`. |

### How to debug

1. Print the resolved template directories:

```python
print(pjx.config.template_dirs)
```

2. Verify the file exists relative to each directory:

```python
from pathlib import Path
for d in pjx.config.template_dirs:
    print(Path(d) / "pages/Home.jinja", (Path(d) / "pages/Home.jinja").exists())
```

3. Set `debug = true` in `pjx.toml` -- PJX logs every template path it
   attempts to resolve.

4. Check that your working directory is the project root when starting the
   server. Relative paths in `template_dirs` are resolved from the CWD.

---

## PropValidationError

**Symptom:** `PropValidationError` raised at render time with a message like:

```text
PropValidationError: Validation failed for 'UserCard':
  - name: Field required
  - age: Input should be a valid integer, got 'abc'
```

### What it means

When `validate_props = true` (the default), PJX generates a Pydantic
`BaseModel` from each component's `props {}` block and validates incoming
values at render time. A `PropValidationError` means the data passed to the
component does not match its declared types.

### How to read the error

The error message contains:

- **Component name** -- which component failed validation.
- **Field name** -- which prop is invalid.
- **Reason** -- what Pydantic expected vs what it received.

### Common fixes

| Problem                                 | Fix                                                                                       |
| --------------------------------------- | ----------------------------------------------------------------------------------------- |
| Missing required prop                   | Pass the prop when using the component: `<UserCard name="Alice" />`.                      |
| Type mismatch                           | Ensure the value matches the declared type. `age: int` requires an integer, not a string. |
| Constraint violation                    | Check `Annotated` constraints. `Annotated[int, Gt(0)]` rejects `0` and negative numbers.  |
| Passing a Jinja expression as a literal | Use `{{ variable }}` syntax for dynamic values: `<UserCard name="{{ user.name }}" />`.    |

### Disabling validation

In production, disable validation for performance:

```toml
# pjx.toml
validate_props = false
```

Or in Python:

```python
config = PJXConfig(validate_props=False)
```

---

## ImportResolutionError

**Symptom:** `ImportResolutionError` during compilation or when running
`pjx check`:

```text
ImportResolutionError: Cannot resolve import 'Button' from './Button.jinja'
  in templates/pages/Home.jinja
```

### Common causes

| Cause                                   | Fix                                                                                                                                                                              |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| File does not exist                     | Create the component file or fix the path.                                                                                                                                       |
| Relative path is wrong                  | Paths are relative to the importing file, not the project root. `"./Button.jinja"` means "same directory". `"../shared/Button.jinja"` means "one level up, then into `shared/`". |
| Missing `.jinja` extension              | Always include the extension: `import Button from "./Button.jinja"`.                                                                                                             |
| Directory import without trailing slash | When importing from a directory, use a trailing slash: `import { Card, Badge } from "./ui/"`.                                                                                    |
| Circular import                         | Component A imports B which imports A. Restructure to break the cycle or extract shared logic into a third component.                                                            |

### How to debug

1. Run `pjx check .` to validate all imports statically.
2. Check the exact file path from the error message.
3. Verify the file exists at the resolved path:

```bash
ls templates/components/Button.jinja
```

4. For directory imports, verify every named component exists:

```bash
ls templates/ui/Card.jinja templates/ui/Badge.jinja
```

---

## CSRF Token Missing (403)

**Symptom:** HTMX POST/PUT/PATCH/DELETE requests return `403 Forbidden` with
a CSRF validation error.

### Common causes

| Cause                              | Fix                                                                                                 |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| Missing `hx-headers` on `<body>`   | Add `hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'` to the `<body>` tag in your layout.        |
| Missing hidden field in HTML forms | Add `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` inside `<form>` tags.      |
| SSE/webhook endpoint not exempted  | Add the path to `csrf_exempt_paths`: `PJX(app, csrf_exempt_paths={"/sse/clock", "/api/webhooks"})`. |
| SessionMiddleware not configured   | CSRF requires sessions. Add `SessionMiddleware` before enabling CSRF.                               |
| Secret key mismatch                | Ensure `csrf_secret` matches across restarts. Use an environment variable.                          |

### Correct setup

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ["PJX_SECRET_KEY"],
)

pjx = PJX(
    app,
    csrf=True,
    csrf_secret=os.environ["PJX_SECRET_KEY"],
    csrf_exempt_paths={"/sse/clock"},
)
```

Layout template:

```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
```

HTML form:

```html
<form action:post="/submit">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <!-- fields -->
</form>
```

---

## SSE Connection Limit (429)

**Symptom:** SSE connections are rejected with HTTP 429 or silently dropped
after a certain number of open connections from the same IP.

### What is happening

`EventStream` tracks open connections per client IP. When the limit is
exceeded, new connections are refused to prevent resource exhaustion.

### How to fix

1. **Increase the limit** if your application legitimately needs many
   concurrent SSE connections per client:

```python
from pjx.sse import EventStream

stream = EventStream(
    request,
    max_connections_per_ip=20,   # default is 10
    max_duration=3600,
)
```

2. **Close unused connections** -- ensure the client disconnects old SSE
   streams before opening new ones. In HTMX, use `close="event"` to
   terminate the connection on a specific event:

```html
<div live="/events/dashboard" close="navigate-away">
    <span channel="stats">0</span>
</div>
```

3. **Check for connection leaks** -- if navigating between pages without a
   full reload, previous SSE connections may remain open. Use
   `hx-trigger="load"` with `hx-swap="outerHTML"` so HTMX replaces the
   element and closes the old connection.

4. **Exempt SSE paths from CSRF** -- CSRF middleware on SSE endpoints can
   cause spurious connection failures:

```python
pjx = PJX(app, csrf=True, csrf_exempt_paths={"/sse/clock", "/events/dashboard"})
```

---

## Alpine.js Not Reactive

**Symptom:** State is declared in the frontmatter but the element does not
update when state changes. `x-data` is missing from the compiled output.

### Common causes

| Cause                                         | Fix                                                                                                                                                                               |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Missing `reactive` attribute                  | Add `reactive` to the root element that needs Alpine.js reactivity: `<div class="counter" reactive>`.                                                                             |
| `reactive` on wrong element                   | `reactive` must be on the element or an ancestor that contains the Alpine expressions. Alpine scopes `x-data` to the element and its descendants.                                 |
| State declared but not used in body           | PJX only generates `x-data` when `reactive` is present. Declaring `state count = 0` alone does nothing without `reactive`.                                                        |
| Using `bind:model` without `reactive`         | `bind:model` compiles to `x-model` which requires `x-data` on an ancestor. Add `reactive` to the form or container.                                                               |
| Explicit `reactive="{ ... }"` overrides state | When you write `reactive="{ count: 0 }"`, PJX uses your literal value instead of auto-generating from `state` declarations. Ensure the explicit object includes all needed state. |

### How to verify

1. Inspect the compiled HTML in browser devtools. Look for `x-data` on the
   element.

2. If `x-data` is missing, add `reactive` to the element:

```html
---
state count = 0
---

<div class="counter" reactive>
    <button on:click="count--">-</button>
    <span x-text="count">0</span>
    <button on:click="count++">+</button>
</div>
```

3. Install the [Alpine.js devtools](https://alpinejs.dev/essentials/debugging)
   browser extension to inspect component state at runtime.

---

## HTMX Swaps Not Working

**Symptom:** Clicking an HTMX-enabled element sends the request (visible in
the Network tab) but the DOM does not update, or the wrong element is updated.

### Common causes

| Cause                            | Fix                                                                                                                                     |
| -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Wrong target selector            | Verify `target="#result"` matches an element with `id="result"` in the DOM.                                                             |
| Target element does not exist    | The target must exist in the DOM before the swap. If the target is inside a conditional `<Show>`, it may not be rendered.               |
| Swap mode mismatch               | `swap="innerHTML"` replaces the target's children. `swap="outerHTML"` replaces the target itself. Use the right mode for your response. |
| Response is not an HTML fragment | HTMX expects raw HTML in the response body. Returning JSON will not trigger a swap. Use `HTMLResponse(pjx.render(...))` in the handler. |
| `swap="none"` set intentionally  | If `swap="none"` is present, no DOM update occurs. This is for fire-and-forget actions.                                                 |
| `into=` shorthand syntax error   | `into="#result"` defaults to `innerHTML`. For `outerHTML`, use `into="#result:outerHTML"`.                                              |
| CSRF blocking the request        | Check the Network tab for 403 responses. See [[Troubleshooting#csrf-token-missing-403]].                                                |

### How to debug

1. Open browser devtools, Network tab. Verify the request returns 200 and
   the response body contains HTML.

2. Check the Console tab for HTMX errors.

3. Enable the HTMX debug extension to log all events:

```html
<script>
    htmx.logAll();
</script>
```

4. Verify the target element exists:

```javascript
document.querySelector("#result");  // should not be null
```

5. Test the endpoint directly in the browser or with `curl`:

```bash
curl -s http://localhost:8000/htmx/todos/add -X POST -d "text=test"
```

---

## pjx check Failures

**Symptom:** `pjx check .` reports errors. The output lists issues grouped by
file.

### How to read the output

Each error includes:

- **File path** -- the component with the issue.
- **Error type** -- `ImportResolutionError`, `PropError`, `SlotError`, etc.
- **Description** -- what is wrong and where.

### Common issues

| Error                      | Meaning                                                                   | Fix                                                                                 |
| -------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `Unresolved import`        | An imported component file does not exist.                                | Create the file or fix the import path.                                             |
| `Circular import detected` | Two or more components import each other in a cycle.                      | Break the cycle by extracting shared logic.                                         |
| `Missing required prop`    | A child component declares a required prop that the parent does not pass. | Add the missing prop to the component usage.                                        |
| `Unknown prop`             | A prop is passed to a component that does not declare it.                 | The prop will be passed through via `{{ attrs }}`. This is a warning, not an error. |
| `Undeclared slot`          | A named slot is passed to a component that does not declare it.           | Add `slot <name>` to the child component's frontmatter, or remove the slot pass.    |
| `Unused slot`              | A slot is declared but never rendered with `<Slot:name />`.               | Remove the declaration or add `<Slot:name />` to the template body.                 |

### Running checks

```bash
# Check all components
pjx check .

# Check a specific file
pjx check templates/components/UserCard.jinja

# Check with verbose output
pjx check . --verbose
```

---

## Debugging Tips

### Enable debug mode

Set `debug = true` in `pjx.toml` to enable:

- Verbose template compilation logging.
- Detailed error messages with source context.
- Template recompilation on every request (no caching).

```toml
# pjx.toml
debug = true
log_level = "DEBUG"
```

### Logging

PJX uses Python's `logging` module. Set the log level to `DEBUG` for full
output:

```toml
# pjx.toml
log_level = "DEBUG"
```

Or via environment variable:

```bash
export PJX_LOG_LEVEL=DEBUG
```

For structured JSON logs (useful with log aggregation tools):

```toml
log_json = true
```

### Browser devtools

| Tool                 | What it shows                              | Install                                                        |
| -------------------- | ------------------------------------------ | -------------------------------------------------------------- |
| Alpine.js devtools   | Component state, watchers, events          | [Browser extension](https://alpinejs.dev/essentials/debugging) |
| HTMX debug extension | All HTMX events (triggers, swaps, targets) | `htmx.logAll()` in console, or load the `debug` extension      |
| Network tab          | Request/response for HTMX and SSE          | Built into browser                                             |

### Template compilation output

To see the compiled Jinja2 output for a component, use `pjx build` and
inspect the output files, or enable `DEBUG` logging to see compiled templates
in the console.

### Common debug workflow

1. Set `debug = true` and `log_level = "DEBUG"` in `pjx.toml`.
2. Run `pjx dev .` and reproduce the issue.
3. Check the terminal for compilation errors and template resolution logs.
4. Open browser devtools:
   - Network tab for HTTP/SSE issues.
   - Console for Alpine.js and HTMX errors.
   - Elements tab to inspect `x-data`, `hx-*` attributes on compiled output.
5. Run `pjx check .` for static analysis of imports, props, and slots.

---

## FAQ

### Can I use PJX without HTMX?

Yes. If you do not use any `action:*`, `target`, `swap`, `trigger`, `into`,
`live`, `channel`, or `loading:*` attributes, PJX will not generate any
`hx-*` attributes. The output will be standard Jinja2 + Alpine.js (if state
is used) or plain Jinja2.

### Can I use PJX without Alpine.js?

Yes. If you do not use `state`, `reactive`, `bind:*`, or `on:*` attributes,
PJX will not generate any Alpine.js directives. The output will be standard
Jinja2 + HTMX (if actions are used) or plain Jinja2. You can remove the
Alpine.js `<script>` tag from your layout.

### Can I use PJX with Django?

Not currently. PJX is built on FastAPI and uses Starlette's request/response
model, session middleware, and SSE support. Django integration is not on the
roadmap.

### Can I use plain Jinja2 templates alongside PJX components?

Yes. PJX components are `.jinja` files that compile down to standard Jinja2.
You can mix PJX components with plain Jinja2 templates in the same project.
Plain templates will not have PJX features (props, state, control flow tags)
but will render normally through the same template engine.

### How do I add custom Jinja2 filters and globals?

Use the engine's `add_global()` method to register custom functions, filters,
or variables that are available in all templates:

```python
pjx.engine.add_global("format_date", my_date_formatter)
pjx.engine.add_global("app_version", "1.2.3")
```

For filters:

```python
pjx.engine.env.filters["currency"] = lambda v: f"${v:,.2f}"
```

### How do I handle errors in production?

Create an `error.jinja` file in your pages directory. It receives
`status_code` and `message` in the template context:

```html
---
props {
    status_code: int = 500,
    message: str = "Something went wrong.",
}
---

<div class="error-page">
    <h1>{{ props.status_code }}</h1>
    <p>{{ props.message }}</p>
</div>
```

### How do I deploy PJX to production?

PJX runs on FastAPI + Uvicorn. Deploy like any ASGI application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Set production configuration:

```toml
# pjx.toml
debug = false
validate_props = false
log_json = true
log_level = "INFO"
```

---

## See also

- [[Installation]]
- [[Configuration-Reference]]
- [[CLI-Reference]]
- [[SSE-and-Realtime]]
- [[State-and-Reactivity]]
- [[HTMX-Integration]]
