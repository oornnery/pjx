# SSE and Realtime

## Overview

PJX supports **Server-Sent Events (SSE)** and **WebSocket** connections for
real-time, server-push interfaces. Both are built on top of the
[HTMX SSE extension](https://htmx.org/extensions/sse/) and
[HTMX WebSocket extension](https://htmx.org/extensions/ws/), with a concise
DSL that compiles down to the verbose `hx-ext` / `sse-*` / `ws-*` attributes
automatically.

On the server side PJX ships an `EventStream` helper class (in `pjx.sse`) that
handles connection limiting, max-duration enforcement, and optional Jinja
template rendering over the SSE channel. For projects that prefer it, PJX is
also fully compatible with the third-party `sse-starlette` library.

Key capabilities:

- Declarative SSE and WebSocket connections in `.jinja` templates.
- Automatic compilation from short DSL attributes to HTMX extension markup.
- Built-in per-IP connection limiting with HTTP 429 protection.
- Configurable maximum stream duration.
- `send_html()` for streaming rendered Jinja components to the browser.
- Works with both the built-in `EventStream` class and `sse-starlette`.

---

## SSE in Templates

PJX introduces three template attributes that compile to HTMX SSE extension
markup. You write the short form; the compiler produces the long form.

### Connecting to an SSE endpoint

Use `live` on any element to establish an SSE connection:

```html
<div live="/sse/clock">
    <span channel="clock">--:--:--</span>
</div>
```

Compiles to:

```html
<div hx-ext="sse" sse-connect="/sse/clock">
    <span sse-swap="clock">--:--:--</span>
</div>
```

### Receiving events on named channels

The `channel` attribute subscribes a child element to a specific SSE event
name. When the server sends an event with that name, HTMX replaces the
element's content with the event data.

```html
<div live="/events/dashboard">
    <span channel="user-count">0</span>
    <div channel="notifications" swap="beforeend"></div>
    <div channel="stats-update" swap="outerHTML"></div>
</div>
```

Compiles to:

```html
<div hx-ext="sse" sse-connect="/events/dashboard">
    <span sse-swap="user-count">0</span>
    <div sse-swap="notifications" hx-swap="beforeend"></div>
    <div sse-swap="stats-update" hx-swap="outerHTML"></div>
</div>
```

When a `channel` element also carries a `swap` attribute, PJX compiles `swap`
into `hx-swap` so you can control how the incoming HTML is inserted
(`innerHTML`, `beforeend`, `outerHTML`, etc.).

### Closing the connection

Use `close` to specify an event name that terminates the SSE connection when
received:

```html
<div live="/events/chat" close="closeChat">
    <div channel="message" swap="beforeend"></div>
</div>
```

Compiles to:

```html
<div hx-ext="sse" sse-connect="/events/chat" sse-close="closeChat">
    <div sse-swap="message" hx-swap="beforeend"></div>
</div>
```

### Attribute summary

| PJX attribute              | Compiled output                   |
| -------------------------- | --------------------------------- |
| `live="/url"`              | `hx-ext="sse" sse-connect="/url"` |
| `channel="event"`          | `sse-swap="event"`                |
| `channel="event" swap="x"` | `sse-swap="event" hx-swap="x"`    |
| `close="event"`            | `sse-close="event"`               |

### Extension script

Layouts must load the HTMX SSE extension before any SSE-enabled component is
used. Add this to your base layout's `<head>`:

```html
<script defer src="https://unpkg.com/htmx-ext-sse@2/sse.js"></script>
```

Or, if you vendor the file:

```html
<script defer src="/static/vendor/htmx-ext-sse.js"></script>
```

---

## EventStream Class

The `pjx.sse` module provides the `EventStream` class, a high-level async
helper for building SSE endpoints in FastAPI.

### Constructor

```python
from pjx.sse import EventStream

stream = EventStream(
    request,                    # FastAPI Request object
    engine=None,                # Optional EngineProtocol for send_html()
    max_connections_per_ip=10,  # Per-IP connection limit
    max_duration=3600,          # Max stream lifetime in seconds (0 = unlimited)
)
```

| Parameter                | Type                    | Default | Description                                         |
| ------------------------ | ----------------------- | ------- | --------------------------------------------------- |
| `request`                | `Request`               | --      | The incoming FastAPI request.                       |
| `engine`                 | `EngineProtocol | None` | `None`  | Template engine instance for `send_html()`.         |
| `max_connections_per_ip` | `int`                   | `10`    | Maximum concurrent SSE connections from one IP.     |
| `max_duration`           | `int`                   | `3600`  | Maximum stream duration in seconds. `0` = no limit. |

### Methods

#### `send(event, data)`

Send a raw SSE event. The `event` string becomes the SSE event name and `data`
is the payload.

```python
await stream.send("clock", "<span>12:00:00</span>")
```

Wire format produced:

```text
event: clock
data: <span>12:00:00</span>

```

#### `send_html(event, template, context)`

Render a Jinja template string through the engine and send the resulting HTML
as an SSE event. Requires that `engine` was passed to the constructor.

```python
await stream.send_html(
    "clock",
    "<span>{{ time }}</span>",
    {"time": "12:00:00"},
)
```

Raises `RuntimeError` if no engine was provided.

| Parameter  | Type                    | Description                   |
| ---------- | ----------------------- | ----------------------------- |
| `event`    | `str`                   | SSE event name.               |
| `template` | `str`                   | Jinja template source string. |
| `context`  | `dict[str, Any] | None` | Template context variables.   |

#### `close()`

Signal the stream to terminate gracefully. Internally places a sentinel `None`
on the message queue; the generator loop exits on the next iteration.

```python
await stream.close()
```

#### `response()`

Create and return a `StreamingResponse` suitable for returning from a FastAPI
route handler. Sets the correct `text/event-stream` media type and
cache/connection headers.

```python
return stream.response()
```

The returned response includes these headers:

| Header               | Value          |
| -------------------- | -------------- |
| `Cache-Control`      | `no-cache`     |
| `Connection`         | `keep-alive`   |
| `X-Accel-Buffering`  | `no`           |

---

## Basic SSE Endpoint

A minimal SSE endpoint using `EventStream`:

```python
import asyncio

from fastapi import FastAPI, Request
from pjx.sse import EventStream

app = FastAPI()


@app.get("/sse/ping")
async def sse_ping(request: Request):
    """Send a 'ping' event every 2 seconds."""
    stream = EventStream(request)

    async def producer():
        count = 0
        while True:
            await asyncio.sleep(2)
            count += 1
            await stream.send("ping", f"count={count}")

    asyncio.create_task(producer())
    return stream.response()
```

Template that connects to this endpoint:

```html
<div live="/sse/ping">
    <span channel="ping">waiting...</span>
</div>
```

---

## Templated SSE

Use `send_html()` to render Jinja components and stream them as SSE events.
This is the recommended approach for sending rich HTML fragments.

```python
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from pjx import PJX
from pjx.sse import EventStream

app = FastAPI()
pjx = PJX(app)


@app.get("/sse/dashboard")
async def sse_dashboard(request: Request):
    """Stream rendered dashboard stats every 5 seconds."""
    stream = EventStream(request, engine=pjx.engine)

    async def producer():
        while not await request.is_disconnected():
            now = datetime.now(timezone.utc)
            await stream.send_html(
                "stats",
                "<div class='stats'>"
                "<span>{{ active_users }} active</span>"
                "<span>Updated {{ timestamp }}</span>"
                "</div>",
                {
                    "active_users": await get_active_user_count(),
                    "timestamp": now.strftime("%H:%M:%S"),
                },
            )
            await asyncio.sleep(5)
        await stream.close()

    asyncio.create_task(producer())
    return stream.response()
```

Template:

```html
<div live="/sse/dashboard">
    <div channel="stats" swap="outerHTML">
        <div class="stats">
            <span>Loading...</span>
        </div>
    </div>
</div>
```

The key advantage of `send_html()` is that you keep your presentation logic in
Jinja templates rather than building HTML strings in Python.

---

## Using sse-starlette

PJX is fully compatible with the `sse-starlette` library as an alternative to
the built-in `EventStream`. This is useful if you already depend on
`sse-starlette` or prefer its generator-based API.

### Installation

```bash
uv add sse-starlette
```

### Generator pattern

Define an async generator that yields dicts with `event` and `data` keys, then
wrap it in `EventSourceResponse`:

```python
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

from pjx import PJX

app = FastAPI()
pjx = PJX(app)


def _clock_html() -> str:
    """Render the Clock component with current server time."""
    now = datetime.now(timezone.utc).astimezone()
    return pjx.partial(
        "components/Clock.jinja",
        time=now.strftime("%H:%M:%S"),
        date=now.strftime("%d %b %Y"),
        weekday=now.strftime("%A"),
        timezone=now.strftime("%Z (UTC%z)"),
    )


async def _clock_generator():
    """Yield clock HTML every second as SSE events."""
    while True:
        yield {"event": "clock", "data": _clock_html()}
        await asyncio.sleep(1)


@app.get("/sse/clock")
async def sse_clock():
    """SSE endpoint -- streams the clock component every second."""
    return EventSourceResponse(_clock_generator())
```

This is the pattern used in the PJX demo application (`examples/demo/app.py`).

### When to use which

| Feature                  | `EventStream`    | `sse-starlette`       |
| ------------------------ | ---------------- | --------------------- |
| Connection limiting      | Built-in         | Roll your own         |
| Max duration enforcement | Built-in         | Roll your own         |
| `send_html()` rendering  | Built-in         | Use `pjx.partial()`   |
| Generator-based API      | No (queue-based) | Yes                   |
| Third-party dependency   | No               | Yes (`sse-starlette`) |

---

## Connection Limits

PJX tracks active SSE connections per client IP address using an in-memory
counter protected by an `asyncio.Lock`. This prevents a single client from
exhausting server resources.

### Default limits

| Parameter                | Default | Description                             |
| ------------------------ | ------- | --------------------------------------- |
| `max_connections_per_ip` | `10`    | Maximum concurrent streams per IP.      |
| `max_duration`           | `3600`  | Maximum stream lifetime (seconds).      |

### How limiting works

When `EventStream._generate()` starts, it calls the internal
`_acquire_connection()` function. If the client IP already has
`max_connections_per_ip` active streams, the generator yields a single error
event and returns immediately:

```text
event: error
data: Too many connections
```

When a stream ends (client disconnect, max duration, or explicit `close()`),
the connection slot is released via `_release_connection()`.

### Pre-check with `check_sse_limit()`

For routes where you want to reject the request early (before constructing the
stream), use the `check_sse_limit()` helper. It raises `HTTPException(429)` if
the limit is exceeded:

```python
from fastapi import Request
from pjx.sse import EventStream, check_sse_limit


@app.get("/sse/feed")
async def sse_feed(request: Request):
    check_sse_limit(request, max_per_ip=5)
    stream = EventStream(request, max_connections_per_ip=5)
    # ... set up producer ...
    return stream.response()
```

### Customizing limits

Pass different values when constructing the stream:

```python
# Allow 20 concurrent connections, no duration limit
stream = EventStream(
    request,
    max_connections_per_ip=20,
    max_duration=0,
)
```

### Duration enforcement

If `max_duration > 0`, the generator checks `time.monotonic()` on each
iteration. When the elapsed time exceeds the limit, the stream closes
gracefully. A log message is emitted at `INFO` level:

```text
SSE max duration reached for 192.168.1.100
```

---

## WebSocket

PJX also supports WebSocket connections through the HTMX WebSocket extension.
The DSL provides two attributes: `socket` for connecting and `send` for
sending messages.

### Connecting

```html
<div socket="/ws/chat">
    <div channel="message" swap="beforeend"></div>
    <form send="message">
        <input name="text" />
        <button type="submit">Send</button>
    </form>
</div>
```

Compiles to:

```html
<div hx-ext="ws" ws-connect="/ws/chat">
    <div sse-swap="message" hx-swap="beforeend"></div>
    <form ws-send="message">
        <input name="text" />
        <button type="submit">Send</button>
    </form>
</div>
```

### Sending messages

The `send` attribute on a `<form>` element compiles to `ws-send`. When the
form is submitted, HTMX serializes the form data and sends it over the
WebSocket connection.

### Extension script

Load the HTMX WebSocket extension in your layout:

```html
<script defer src="https://unpkg.com/htmx-ext-ws@2/ws.js"></script>
```

### Server-side handler (FastAPI)

PJX does not provide a built-in WebSocket handler class. Use FastAPI's native
WebSocket support:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

connected_clients: list[WebSocket] = []


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Broadcast the message to all connected clients
            html = f'<div class="message">{data["text"]}</div>'
            for client in connected_clients:
                await client.send_text(html)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
```

---

## Compilation Table

Complete reference of SSE and WebSocket DSL attributes and their compiled
output.

### SSE attributes

| PJX DSL                    | Compiled HTML                     | Notes                      |
| -------------------------- | --------------------------------- | -------------------------- |
| `live="/url"`              | `hx-ext="sse" sse-connect="/url"` | Establishes SSE connection |
| `channel="event"`          | `sse-swap="event"`                | Subscribes to named event  |
| `channel="event" swap="x"` | `sse-swap="event" hx-swap="x"`    | Custom swap strategy       |
| `close="event"`            | `sse-close="event"`               | Close connection on event  |

### WebSocket attributes

| PJX DSL           | Compiled HTML                         | Notes                          |
| ----------------- | ------------------------------------- | ------------------------------ |
| `socket="/url"`   | `hx-ext="ws" ws-connect="/url"`       | Establishes WebSocket          |
| `send="event"`    | `ws-send="event"`                     | Send form data over WS         |

### Combined example

A component that uses both SSE for receiving and a form for user interaction:

```html
<div live="/sse/notifications">
    <ul channel="notification" swap="beforeend"></ul>
    <div channel="status">Connecting...</div>
</div>
```

---

## Full Example

A live clock with auto-reconnect that demonstrates the complete SSE workflow
from template to server endpoint.

### Template: `pages/ClockDemo.jinja`

```html
---
props {
  clock: str = "",
}
---

<section class="clock-demo">
    <h2>Live Server Clock</h2>
    <p>This clock updates every second via Server-Sent Events.</p>

    <div live="/sse/clock" close="done">
        <div channel="clock" swap="innerHTML">
            {{ props.clock }}
        </div>
    </div>
</section>
```

Compiled output:

```html
<section class="clock-demo">
    <h2>Live Server Clock</h2>
    <p>This clock updates every second via Server-Sent Events.</p>

    <div hx-ext="sse" sse-connect="/sse/clock" sse-close="done">
        <div sse-swap="clock" hx-swap="innerHTML">
            <!-- initial clock HTML from server -->
        </div>
    </div>
</section>
```

### Component: `components/Clock.jinja`

```html
---
props {
  time:     str,
  date:     str,
  weekday:  str,
  timezone: str,
}
---

<div class="clock-face">
    <span class="clock-time">{{ props.time }}</span>
    <span class="clock-date">{{ props.weekday }}, {{ props.date }}</span>
    <span class="clock-tz">{{ props.timezone }}</span>
</div>
```

### Server: SSE endpoint using `EventStream`

```python
import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from pjx import PJX
from pjx.sse import EventStream, check_sse_limit

app = FastAPI()
pjx = PJX(app)


def _clock_html() -> str:
    now = datetime.now(timezone.utc).astimezone()
    return pjx.partial(
        "components/Clock.jinja",
        time=now.strftime("%H:%M:%S"),
        date=now.strftime("%d %b %Y"),
        weekday=now.strftime("%A"),
        timezone=now.strftime("%Z (UTC%z)"),
    )


@app.get("/sse/clock")
async def sse_clock(request: Request):
    check_sse_limit(request, max_per_ip=10)
    stream = EventStream(request, engine=pjx.engine)

    async def tick():
        while not await request.is_disconnected():
            await stream.send("clock", _clock_html())
            await asyncio.sleep(1)
        await stream.close()

    asyncio.create_task(tick())
    return stream.response()
```

### Server: SSE endpoint using `sse-starlette`

```python
import asyncio

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

app = FastAPI()


async def _clock_generator():
    while True:
        yield {"event": "clock", "data": _clock_html()}
        await asyncio.sleep(1)


@app.get("/sse/clock")
async def sse_clock():
    return EventSourceResponse(_clock_generator())
```

### Page handler

```python
@pjx.page("/clock", template="pages/ClockDemo.jinja", title="Clock -- PJX")
async def clock() -> dict[str, object]:
    return {"clock": _clock_html()}
```

The page handler renders the initial clock HTML on first load. Once the browser
connects to the SSE endpoint, the `channel="clock"` element receives live
updates every second. If the connection drops, HTMX automatically reconnects
(the SSE extension has built-in exponential backoff).

---

## See Also

- [[State-and-Reactivity]] -- Alpine.js reactive state and HTMX server actions
- [[Installation]] -- Setting up dependencies including `sse-starlette`
- [[Quick-Start]] -- Getting a PJX application running
