# HTMX Integration

PJX provides shorthand attributes that compile directly to
[HTMX](https://htmx.org/) attributes. Instead of writing raw `hx-*`
attributes, you use PJX's declarative syntax -- `action:*`, `target`, `swap`,
`trigger`, and friends -- and the compiler emits the correct HTMX output. This
keeps templates readable while giving you access to the full HTMX feature set.

---

## Table of Contents

1. [Overview](#overview)
2. [HTTP Verbs](#http-verbs)
3. [Targets and Swaps](#targets-and-swaps)
4. [The `into` Shorthand](#the-into-shorthand)
5. [Triggers](#triggers)
6. [Boost](#boost)
7. [Select and Out-of-Band](#select-and-out-of-band)
8. [Confirmation](#confirmation)
9. [Indicators](#indicators)
10. [URL Management](#url-management)
11. [Advanced Attributes](#advanced-attributes)
12. [CSRF with HTMX](#csrf-with-htmx)
13. [Complete Compilation Table](#complete-compilation-table)
14. [Examples](#examples)
15. [See Also](#see-also)

---

## Overview

Every HTMX interaction in PJX follows a consistent pattern:

1. An **action** attribute declares which HTTP verb and URL to call.
2. Optional **target**, **swap**, and **trigger** attributes control where the
   response goes, how it replaces content, and what event fires the request.
3. The PJX compiler translates these into standard `hx-*` attributes at build
   time.

```html
<!-- PJX source -->
<button action:get="/api/items"
        target="#item-list"
        swap="innerHTML"
        trigger="click">
    Load Items
</button>

<!-- Compiled output -->
<button hx-get="/api/items"
        hx-target="#item-list"
        hx-swap="innerHTML"
        hx-trigger="click">
    Load Items
</button>
```

No runtime transformation occurs -- the compiler produces static Jinja2
templates with HTMX attributes baked in. The browser sees only standard HTMX.

---

## HTTP Verbs

The `action:` prefix maps to HTMX HTTP verb attributes. PJX supports all five
verbs that HTMX provides.

### GET

Fetch data from the server without side effects.

```html
<button action:get="/api/items">Load Items</button>
<!-- Compiles to: <button hx-get="/api/items">Load Items</button> -->
```

### POST

Create a new resource. Commonly used with forms.

```html
<form action:post="/api/items">
    <input name="title" required />
    <button type="submit">Create</button>
</form>
<!-- Compiles to: <form hx-post="/api/items">...</form> -->
```

### PUT

Replace an existing resource entirely.

```html
<button action:put="/api/items/1">Replace</button>
<!-- Compiles to: <button hx-put="/api/items/1">Replace</button> -->
```

### PATCH

Partially update an existing resource.

```html
<button action:patch="/api/items/1/toggle">Toggle Status</button>
<!-- Compiles to: <button hx-patch="/api/items/1/toggle">Toggle Status</button> -->
```

### DELETE

Remove a resource.

```html
<button action:delete="/api/items/1">Remove</button>
<!-- Compiles to: <button hx-delete="/api/items/1">Remove</button> -->
```

### Verb Compilation Table

| PJX Attribute            | Compiled Output          |
| ------------------------ | ------------------------ |
| `action:get="/url"`      | `hx-get="/url"`          |
| `action:post="/url"`     | `hx-post="/url"`         |
| `action:put="/url"`      | `hx-put="/url"`          |
| `action:patch="/url"`    | `hx-patch="/url"`        |
| `action:delete="/url"`   | `hx-delete="/url"`       |

---

## Targets and Swaps

### Targets

The `target` attribute specifies where the server response is placed in the
DOM. It compiles to `hx-target`.

```html
<!-- Target by ID -->
<button action:get="/api/items" target="#result">
    Load
</button>
<!-- Compiles to: hx-target="#result" -->
```

HTMX extended CSS selectors work as target values:

```html
<!-- Closest ancestor matching selector -->
<button target="closest li">Delete</button>

<!-- Next sibling matching selector -->
<button target="next .panel">Expand</button>

<!-- Previous sibling matching selector -->
<button target="previous .item">Update</button>

<!-- Descendant within the current element -->
<button target="find .content">Load</button>
```

When no `target` is specified, HTMX defaults to the element that issued the
request.

### Swaps

The `swap` attribute controls **how** the response replaces content in the
target. It compiles to `hx-swap`.

```html
<div action:get="/api/data" swap="innerHTML">
    <!-- Response replaces the inner content -->
</div>
```

#### Swap Strategies

| Strategy      | Description                                          |
| ------------- | ---------------------------------------------------- |
| `innerHTML`   | Replace the inner content of the target (default)    |
| `outerHTML`   | Replace the entire target element                    |
| `beforebegin` | Insert before the target element                     |
| `afterbegin`  | Insert as the first child of the target              |
| `beforeend`   | Insert as the last child of the target               |
| `afterend`    | Insert after the target element                      |
| `delete`      | Remove the target element from the DOM               |
| `none`        | Do not swap -- fire-and-forget request               |

#### Swap Modifiers

Append modifiers after the strategy, separated by spaces:

```html
<!-- Transition animation -->
<div swap="innerHTML transition:true">

<!-- Settle delay (wait before removing old content) -->
<div swap="innerHTML settle:300ms">

<!-- Scroll the target to top after swap -->
<div swap="innerHTML scroll:top">

<!-- Show the top of the page after swap -->
<div swap="innerHTML show:top">

<!-- Control focus scrolling after swap -->
<div swap="innerHTML focus-scroll:true">
```

Multiple modifiers can be combined:

```html
<div swap="outerHTML transition:true settle:200ms scroll:top">
```

All swap values compile directly: `swap="outerHTML"` becomes
`hx-swap="outerHTML"`.

---

## The `into` Shorthand

The `into` attribute is a PJX convenience that combines `target` and `swap`
into a single attribute. This reduces boilerplate for the most common
interaction pattern.

### Basic Usage

When you provide only a selector, `into` defaults to `innerHTML`:

```html
<!-- PJX source -->
<button action:get="/api/items" into="#result">Load</button>

<!-- Compiled output -->
<button hx-get="/api/items"
        hx-target="#result"
        hx-swap="innerHTML">Load</button>
```

### With Explicit Swap Strategy

Append the swap strategy after a colon:

```html
<!-- PJX source -->
<button action:get="/api/items" into="#result:outerHTML">Load</button>

<!-- Compiled output -->
<button hx-get="/api/items"
        hx-target="#result"
        hx-swap="outerHTML">Load</button>
```

### Comparison

Without `into`, you write two attributes:

```html
<button action:get="/api/items" target="#result" swap="outerHTML">Load</button>
```

With `into`, one attribute handles both:

```html
<button action:get="/api/items" into="#result:outerHTML">Load</button>
```

Both compile to identical output.

### `into` Compilation

| PJX Attribute              | Compiled Output                                |
| -------------------------- | ---------------------------------------------- |
| `into="#sel"`              | `hx-target="#sel" hx-swap="innerHTML"`         |
| `into="#sel:outerHTML"`    | `hx-target="#sel" hx-swap="outerHTML"`         |
| `into="#sel:beforeend"`    | `hx-target="#sel" hx-swap="beforeend"`         |
| `into="#sel:delete"`       | `hx-target="#sel" hx-swap="delete"`            |

---

## Triggers

The `trigger` attribute controls which event fires the HTMX request. It
compiles to `hx-trigger`.

### Basic Triggers

```html
<!-- Click (default for buttons) -->
<button action:get="/api/data" trigger="click">Load</button>

<!-- Form submission -->
<form action:post="/api/items" trigger="submit">...</form>

<!-- Input change -->
<input action:get="/api/search" trigger="input" />
```

### Special Triggers

HTMX provides several non-DOM triggers:

```html
<!-- Fire on page load -->
<div action:get="/api/stats" trigger="load">
    Loading stats...
</div>

<!-- Fire when element becomes visible -->
<div action:get="/api/more" trigger="revealed">
    Loading more...
</div>

<!-- Fire when element enters viewport (IntersectionObserver) -->
<div action:get="/api/analytics" trigger="intersect">
    Tracking...
</div>

<!-- Polling at interval -->
<div action:get="/api/notifications" trigger="every 5s">
    <span id="notification-count">0</span>
</div>
```

### Trigger Modifiers

Modifiers refine when and how often the trigger fires.

#### `once`

Fire only on the first occurrence of the event:

```html
<div action:get="/api/welcome" trigger="load once">
    Welcome message loads once.
</div>

<button action:post="/api/track" trigger="click once">
    Track (fires only once)
</button>
```

#### `delay` / `debounce`

Wait before firing. If the event fires again within the delay, the timer
resets (debounce behavior):

```html
<!-- Debounced search input -->
<input action:get="/api/search"
       trigger="input changed delay:300ms"
       target="#results" />
```

The `debounce` shorthand is also available:

```html
<input action:get="/api/search"
       trigger="input changed"
       debounce="500ms"
       target="#results" />
<!-- debounce="500ms" adds delay:500ms to the hx-trigger value -->
```

#### `throttle`

Limit the trigger to at most once per interval:

```html
<button action:post="/api/like"
        trigger="click throttle:1s">
    Like
</button>
```

The `throttle` shorthand is also available:

```html
<button action:post="/api/like"
        trigger="click"
        throttle="500ms">
    Like
</button>
<!-- throttle="500ms" adds throttle:500ms to the hx-trigger value -->
```

#### `queue`

Control how events are queued when a request is in flight:

```html
<!-- Process only the first queued event -->
<button trigger="click queue:first">First</button>

<!-- Process only the last queued event (default) -->
<button trigger="click queue:last">Last</button>

<!-- Process all queued events -->
<button trigger="click queue:all">All</button>
```

#### `from`

Listen for events on a different element:

```html
<!-- This div reacts to clicks on #other-button -->
<div action:get="/api/data"
     trigger="click from:#other-button"
     target="#output">
    Waiting for button click...
</div>
```

#### JavaScript Filters

Add a JS expression in brackets to conditionally fire:

```html
<!-- Only fire on Ctrl+Click -->
<div trigger="click[ctrlKey]">Ctrl+Click me</div>

<!-- Only fire on Enter key -->
<div trigger="keyup[key=='Enter'] from:body">Listening for Enter...</div>
```

#### Combining Triggers

Separate multiple triggers with commas:

```html
<div action:get="/api/data"
     trigger="load, click, keyup[key=='Enter'] from:body">
    Fires on load, click, or Enter key.
</div>
```

### Trigger Modifier Compilation

| PJX Shorthand      | Compiled Effect                             |
| ------------------ | ------------------------------------------- |
| `debounce="500ms"` | Adds `delay:500ms` to `hx-trigger` value    |
| `throttle="500ms"` | Adds `throttle:500ms` to `hx-trigger` value |

---

## Boost

The `boost` attribute enables HTMX progressive enhancement. When applied to a
container, all descendant links and forms are automatically converted to AJAX
requests. This gives SPA-like navigation without rewriting any markup.

```html
<!-- PJX source -->
<nav boost>
    <a href="/about">About</a>
    <a href="/contact">Contact</a>
</nav>

<!-- Compiled output -->
<nav hx-boost="true">
    <a href="/about">About</a>
    <a href="/contact">Contact</a>
</nav>
```

With boost enabled, clicking a link issues `hx-get` to the `href` and swaps
the body content. Forms similarly convert their `method` to the appropriate
HTMX verb.

```html
<form boost action="/submit" method="post">
    <input name="query" />
    <button type="submit">Search</button>
</form>
<!-- Compiles to: <form hx-boost="true" action="/submit" method="post">...</form> -->
<!-- HTMX intercepts the submit and issues hx-post="/submit" -->
```

| PJX Attribute | Compiled Output    |
| ------------- | ------------------ |
| `boost`       | `hx-boost="true"`  |

---

## Select and Out-of-Band

### `select`

The `select` attribute tells HTMX to extract only a portion of the server
response before swapping. This is useful when the server returns a full page
but you only need one fragment.

```html
<button action:get="/dashboard"
        target="#main"
        select="#content">
    Refresh Content
</button>
<!-- Compiles to: hx-select="#content" -->
<!-- Only the #content element from the response is swapped into #main -->
```

### `select-oob`

The `select-oob` attribute enables **out-of-band** (OOB) swaps -- updating
additional elements beyond the primary target. The server response must contain
elements with matching IDs.

```html
<button action:get="/dashboard"
        target="#main"
        select="#content"
        select-oob="#sidebar">
    Refresh
</button>
<!-- Compiles to: hx-select-oob="#sidebar" -->
<!-- #content goes into #main, #sidebar is swapped OOB by ID match -->
```

Multiple OOB selectors can be comma-separated:

```html
<button select-oob="#sidebar, #notifications, #footer">
```

### Multi-Target Update Pattern

Combining `select` and `select-oob` allows a single request to update multiple
independent parts of the page:

```html
<button action:get="/api/refresh-all"
        target="#main-content"
        select="#main-content"
        select-oob="#sidebar, #header-stats">
    Refresh Everything
</button>
```

The server returns a response containing `#main-content`, `#sidebar`, and
`#header-stats`. HTMX swaps the primary target normally and updates the OOB
elements in place.

---

## Confirmation

The `confirm` attribute displays a browser confirmation dialog before the
request fires. This is essential for destructive actions.

```html
<button action:delete="/api/items/1"
        confirm="Are you sure you want to delete this item?">
    Delete
</button>
<!-- Compiles to: hx-confirm="Are you sure you want to delete this item?" -->
```

The request only proceeds if the user clicks OK. Clicking Cancel aborts the
request entirely.

```html
<!-- Confirm before bulk operations -->
<button action:post="/api/items/archive-all"
        confirm="Archive all items? This cannot be undone.">
    Archive All
</button>

<!-- Confirm before navigation -->
<a href="/logout"
   boost
   confirm="Are you sure you want to log out?">
    Log Out
</a>
```

| PJX Attribute    | Compiled Output          |
| ---------------- | ------------------------ |
| `confirm="msg"`  | `hx-confirm="msg"`       |

---

## Indicators

The `indicator` attribute points to an element that HTMX shows during the
request lifecycle. The target element should have the `htmx-indicator` CSS
class, which HTMX toggles to visible while the request is in flight.

```html
<button action:get="/api/data"
        indicator="#spinner">
    Load Data
</button>
<span id="spinner" class="htmx-indicator">Loading...</span>
<!-- Compiles to: hx-indicator="#spinner" -->
```

HTMX manages the visibility automatically:

1. Before the request, the indicator element is hidden (via `opacity: 0`).
2. When the request starts, HTMX adds `htmx-request` class to the indicator,
   making it visible.
3. When the response arrives, the class is removed.

For more fine-grained control over loading feedback, see
[[Loading States]].

| PJX Attribute      | Compiled Output        |
| ------------------ | ---------------------- |
| `indicator="#id"`  | `hx-indicator="#id"`   |

---

## URL Management

### `push-url`

Push a new entry into the browser history stack after the swap completes. This
updates the URL bar without a full page reload.

```html
<!-- Push the request URL -->
<a action:get="/about" push-url>About</a>
<!-- Compiles to: hx-push-url="true" -->

<!-- Push a custom URL -->
<button action:get="/api/items" push-url="/items">
    Load Items
</button>
<!-- Compiles to: hx-push-url="/items" -->
```

### `replace-url`

Replace the current history entry instead of pushing a new one. Useful for
filters and search operations that should not create back-button entries.

```html
<input action:get="/api/search"
       trigger="input changed delay:300ms"
       replace-url>
<!-- Compiles to: hx-replace-url="true" -->
```

| PJX Attribute          | Compiled Output              |
| ---------------------- | ---------------------------- |
| `push-url`             | `hx-push-url="true"`         |
| `push-url="/path"`     | `hx-push-url="/path"`        |
| `replace-url`          | `hx-replace-url="true"`      |
| `replace-url="/path"`  | `hx-replace-url="/path"`     |

---

## Advanced Attributes

### `vals`

Send additional values with the request as JSON:

```html
<button action:post="/api/items"
        vals='{"status": "active", "page": 1}'>
    Load Active Items
</button>
<!-- Compiles to: hx-vals='{"status": "active", "page": 1}' -->
```

### `headers`

Send custom HTTP headers with the request:

```html
<button action:get="/api/data"
        headers='{"X-Custom-Header": "value"}'>
    Fetch
</button>
<!-- Compiles to: hx-headers='{"X-Custom-Header": "value"}' -->
```

### `encoding`

Set the encoding type for the request. Required for file uploads:

```html
<form action:post="/api/upload"
      encoding="multipart/form-data">
    <input type="file" name="document" />
    <button type="submit">Upload</button>
</form>
<!-- Compiles to: hx-encoding="multipart/form-data" -->
```

### `preserve`

Preserve an element across page loads. The element keeps its state even when
the surrounding DOM is swapped:

```html
<video id="main-video" preserve>
    <source src="/video.mp4" type="video/mp4" />
</video>
<!-- Compiles to: hx-preserve="true" -->
```

### `sync`

Control request synchronization between elements. Prevents race conditions when
multiple elements can trigger requests on the same target:

```html
<!-- Abort previous request when a new one starts -->
<input action:get="/api/search"
       trigger="input changed delay:300ms"
       sync="closest form:abort"
       target="#results" />
<!-- Compiles to: hx-sync="closest form:abort" -->
```

Sync strategies:

| Strategy   | Behavior                                          |
| ---------- | ------------------------------------------------- |
| `drop`     | Drop the new request if one is in flight          |
| `abort`    | Abort the in-flight request and send the new one  |
| `replace`  | Abort the in-flight request, send the new one     |
| `queue`    | Queue the request (with first/last/all modifiers) |

### `disabled-elt`

Disable an element while the request is in flight:

```html
<button action:post="/api/save"
        disabled-elt="this">
    Save
</button>
<!-- Compiles to: hx-disabled-elt="this" -->
<!-- The button is disabled during the request -->
```

You can target other elements:

```html
<form action:post="/api/submit"
      disabled-elt="#submit-btn, #cancel-btn">
    <button id="submit-btn" type="submit">Submit</button>
    <button id="cancel-btn" type="button">Cancel</button>
</form>
<!-- Both buttons are disabled during the request -->
```

For more loading feedback options, see [[Loading States]].

---

## CSRF with HTMX

PJX includes built-in CSRF middleware based on double-submit cookies with HMAC
signatures. When enabled, every unsafe request (POST, PUT, DELETE, PATCH) must
include a valid CSRF token.

### Enabling CSRF

```python
pjx = PJX(
    app,
    csrf=True,
    csrf_secret="your-secret-key",
    csrf_exempt_paths={"/api/webhooks", "/sse/clock"},
)
```

### How It Works

1. The middleware generates a signed CSRF token and sets it as a `_csrf`
   cookie on every response.
2. On unsafe methods, the middleware validates that the token sent via the
   `X-CSRFToken` header or the `csrf_token` form field matches the cookie.
3. Mismatched or missing tokens result in HTTP 403.

### Automatic HTMX Integration

Add `hx-headers` on the `<body>` tag in your layout to send the CSRF token
with every HTMX request automatically:

```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
    <!-- All HTMX requests in this body include the CSRF token -->
</body>
```

In PJX layout syntax, this is:

```html
<body headers='{"X-CSRFToken": "{{ csrf_token() }}"}'>
```

### Traditional Forms

For non-HTMX forms, include a hidden input:

```html
<form method="post" action="/submit">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}" />
    <!-- form fields -->
    <button type="submit">Submit</button>
</form>
```

### Exempting Paths

Webhook endpoints and SSE connections typically need CSRF exemption:

```python
pjx = PJX(
    app,
    csrf=True,
    csrf_secret="your-secret-key",
    csrf_exempt_paths={"/api/webhooks", "/sse/clock"},
)
```

For more on middleware configuration, see [[Middleware]].

---

## Complete Compilation Table

Every PJX HTMX attribute and its compiled output:

| PJX Attribute                    | Compiled Output                             |
| -------------------------------- | ------------------------------------------- |
| `action:get="/url"`              | `hx-get="/url"`                             |
| `action:post="/url"`             | `hx-post="/url"`                            |
| `action:put="/url"`              | `hx-put="/url"`                             |
| `action:patch="/url"`            | `hx-patch="/url"`                           |
| `action:delete="/url"`           | `hx-delete="/url"`                          |
| `swap="x"`                       | `hx-swap="x"`                               |
| `target="x"`                     | `hx-target="x"`                             |
| `trigger="x"`                    | `hx-trigger="x"`                            |
| `into="#sel"`                    | `hx-target="#sel" hx-swap="innerHTML"`      |
| `into="#sel:outerHTML"`          | `hx-target="#sel" hx-swap="outerHTML"`      |
| `select="x"`                     | `hx-select="x"`                             |
| `select-oob="x"`                 | `hx-select-oob="x"`                         |
| `confirm="msg"`                  | `hx-confirm="msg"`                          |
| `indicator="#id"`                | `hx-indicator="#id"`                        |
| `push-url`                       | `hx-push-url="true"`                        |
| `push-url="/path"`               | `hx-push-url="/path"`                       |
| `replace-url`                    | `hx-replace-url="true"`                     |
| `replace-url="/path"`            | `hx-replace-url="/path"`                    |
| `vals='{"k":"v"}'`               | `hx-vals='{"k":"v"}'`                       |
| `headers='{"X-H":"v"}'`          | `hx-headers='{"X-H":"v"}'`                  |
| `encoding="multipart/form-data"` | `hx-encoding="multipart/form-data"`         |
| `preserve`                       | `hx-preserve="true"`                        |
| `sync="closest form:abort"`      | `hx-sync="closest form:abort"`              |
| `disabled-elt="this"`            | `hx-disabled-elt="this"`                    |
| `boost`                          | `hx-boost="true"`                           |
| `debounce="500ms"`               | Adds `delay:500ms` to `hx-trigger` value    |
| `throttle="500ms"`               | Adds `throttle:500ms` to `hx-trigger` value |

---

## Examples

### Search with Debounce

A search input that queries the server after the user stops typing for 300ms:

```html
---
props {
    placeholder: str = "Search..."
}
---

<div>
    <input type="search"
           name="q"
           placeholder="{{ props.placeholder }}"
           action:get="/api/search"
           trigger="input changed delay:300ms"
           target="#search-results"
           indicator="#search-spinner"
           sync="closest form:abort"
           replace-url />

    <span id="search-spinner" class="htmx-indicator">
        Searching...
    </span>

    <div id="search-results">
        <!-- Results appear here -->
    </div>
</div>
```

Compiled output:

```html
<div>
    <input type="search"
           name="q"
           placeholder="Search..."
           hx-get="/api/search"
           hx-trigger="input changed delay:300ms"
           hx-target="#search-results"
           hx-indicator="#search-spinner"
           hx-sync="closest form:abort"
           hx-replace-url="true" />

    <span id="search-spinner" class="htmx-indicator">
        Searching...
    </span>

    <div id="search-results"></div>
</div>
```

### Todo CRUD

A complete todo list with create, toggle, and delete:

```html
---
import TodoItem from "./TodoItem.jinja"
---

<section id="todo-app">
    <!-- Create form -->
    <form action:post="/api/todos"
          into="#todo-list:beforeend"
          swap="beforeend"
          trigger="submit">
        <input name="title" required placeholder="New todo..." />
        <button type="submit"
                loading:disabled
                loading:class="opacity-50">
            Add
        </button>
    </form>

    <!-- Todo list -->
    <ul id="todo-list">
        <For each="todo in todos">
            <li id="todo-{{ todo.id }}">
                <input type="checkbox"
                       action:patch="/api/todos/{{ todo.id }}/toggle"
                       target="closest li"
                       swap="outerHTML" />
                <span>{{ todo.title }}</span>
                <button action:delete="/api/todos/{{ todo.id }}"
                        target="closest li"
                        swap="outerHTML"
                        confirm="Delete this todo?">
                    Remove
                </button>
            </li>
        </For>
    </ul>
</section>
```

### Infinite Scroll

Load more items as the user scrolls to the bottom:

```html
<div id="item-feed">
    <For each="item in items">
        <article class="item-card">
            <h3>{{ item.title }}</h3>
            <p>{{ item.summary }}</p>
        </article>
    </For>

    <!-- Sentinel element: loads next page when revealed -->
    <div action:get="/api/items?page={{ next_page }}"
         trigger="revealed"
         into="#item-feed:beforeend"
         select=".item-card"
         swap="beforeend">
        <span class="htmx-indicator">Loading more...</span>
    </div>
</div>
```

When the sentinel div scrolls into view, HTMX fetches the next page and
appends the new `.item-card` elements to `#item-feed`. The sentinel itself
is replaced with a new sentinel pointing to the subsequent page.

### Delete with Confirmation

A delete button with confirmation dialog, target cleanup, and visual feedback:

```html
<tr id="row-{{ item.id }}">
    <td>{{ item.name }}</td>
    <td>{{ item.status }}</td>
    <td>
        <button action:delete="/api/items/{{ item.id }}"
                target="closest tr"
                swap="outerHTML swap:500ms"
                confirm="Delete {{ item.name }}? This action cannot be undone."
                indicator="#delete-spinner-{{ item.id }}">
            Delete
        </button>
        <span id="delete-spinner-{{ item.id }}" class="htmx-indicator">
            Deleting...
        </span>
    </td>
</tr>
```

The server returns an empty response (or a fade-out element). The `swap:500ms`
modifier gives CSS transitions time to complete before the element is removed.

### Tabs with URL Push

Navigation tabs that update content and push the URL:

```html
<nav boost>
    <a href="/dashboard/overview"
       action:get="/dashboard/overview"
       target="#tab-content"
       select="#tab-content"
       push-url>
        Overview
    </a>
    <a href="/dashboard/analytics"
       action:get="/dashboard/analytics"
       target="#tab-content"
       select="#tab-content"
       push-url>
        Analytics
    </a>
    <a href="/dashboard/settings"
       action:get="/dashboard/settings"
       target="#tab-content"
       select="#tab-content"
       push-url>
        Settings
    </a>
</nav>

<div id="tab-content">
    <!-- Active tab content -->
</div>
```

---

## See Also

- [[State and Reactivity]] -- Client-side state management with Alpine.js
- [[Loading States]] -- Visual feedback during HTMX requests
- [[SSE and Realtime]] -- Server-Sent Events for live updates
- [[Middleware]] -- CSRF protection, authentication, and request middleware
- [[File Based Routing]] -- Automatic route generation from file structure
- [[Compilation Reference]] -- Full compilation table for all PJX attributes
