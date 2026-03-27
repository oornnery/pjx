# Loading States

PJX provides a set of `loading:*` attributes and related directives that give
users visual feedback during HTMX requests. These compile to a combination of
HTMX attributes, CSS classes, and inline behavior that manage visibility,
disabled state, and ARIA properties while a request is in flight.

---

## Table of Contents

1. [Overview](#overview)
2. [Indicators](#indicators)
3. [Loading Show and Hide](#loading-show-and-hide)
4. [Loading Classes](#loading-classes)
5. [Loading Disabled](#loading-disabled)
6. [Loading Aria](#loading-aria)
7. [Disabled Elements](#disabled-elements)
8. [Skeleton Loading Pattern](#skeleton-loading-pattern)
9. [Full Example](#full-example)
10. [Compilation Table](#compilation-table)
11. [See Also](#see-also)

---

## Overview

When an HTMX request fires, there is a window of time between the request
leaving the browser and the response arriving. During this window, users see
no change -- the page appears frozen. Loading states solve this by providing
immediate visual feedback.

PJX offers several approaches, from simple to advanced:

| Approach           | Use Case                                    |
| ------------------ | ------------------------------------------- |
| `indicator`        | Show a separate spinner element             |
| `loading:show`     | Show inline text/element during request     |
| `loading:hide`     | Hide inline text/element during request     |
| `loading:class`    | Add CSS classes during request              |
| `loading:disabled` | Disable an element during request           |
| `loading:aria-busy`| Set `aria-busy` for accessibility           |
| `disabled-elt`     | Disable specific elements via HTMX          |

All of these can be combined on a single element to create rich loading
interactions.

---

## Indicators

The `indicator` attribute points to a separate element that HTMX toggles
visible during the request. The target element must have the
`htmx-indicator` CSS class.

### Basic Spinner

```html
<button action:post="/api/save"
        indicator="#save-spinner">
    Save
</button>
<span id="save-spinner" class="htmx-indicator">
    Saving...
</span>
```

Compiled output:

```html
<button hx-post="/api/save"
        hx-indicator="#save-spinner">
    Save
</button>
<span id="save-spinner" class="htmx-indicator">
    Saving...
</span>
```

### How Indicators Work

HTMX manages indicator visibility through CSS:

1. Elements with `htmx-indicator` are hidden by default (HTMX sets
   `opacity: 0` via its built-in stylesheet).
2. When the request starts, HTMX adds the `htmx-request` class to the
   indicator element, which sets `opacity: 1`.
3. When the response arrives, the `htmx-request` class is removed and the
   indicator returns to hidden.

### Spinner with CSS Animation

```html
<style>
    .spinner {
        display: inline-block;
        width: 1em;
        height: 1em;
        border: 2px solid currentColor;
        border-right-color: transparent;
        border-radius: 50%;
        animation: spin 0.6s linear infinite;
    }
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>

<button action:get="/api/data" indicator="#load-indicator">
    Refresh
</button>
<span id="load-indicator" class="htmx-indicator">
    <span class="spinner"></span> Loading...
</span>
```

### Shared Indicators

Multiple elements can share the same indicator:

```html
<span id="global-spinner" class="htmx-indicator">Working...</span>

<button action:get="/api/users" indicator="#global-spinner">Load Users</button>
<button action:get="/api/posts" indicator="#global-spinner">Load Posts</button>
<button action:get="/api/stats" indicator="#global-spinner">Load Stats</button>
```

| PJX Attribute      | Compiled Output        |
| ------------------ | ---------------------- |
| `indicator="#id"`  | `hx-indicator="#id"`   |

---

## Loading Show and Hide

The `loading:show` and `loading:hide` attributes create inline loading
indicators directly within the triggering element. Unlike the `indicator`
attribute (which targets a separate element), these operate on child elements
of the request source.

### `loading:show`

An element with `loading:show` is hidden by default and becomes visible when
the parent's HTMX request is in flight.

```html
<button action:post="/api/save">
    <span loading:hide>Save</span>
    <span loading:show>Saving...</span>
</button>
```

Before the request, the user sees "Save". During the request, "Save" disappears
and "Saving..." appears. When the response arrives, it reverts.

### `loading:hide`

An element with `loading:hide` is visible by default and becomes hidden when
the parent's HTMX request is in flight. This is the complement of
`loading:show`.

### Combined Show/Hide Pattern

The typical pattern pairs both attributes to swap visible content:

```html
<button action:post="/api/submit"
        loading:disabled>
    <span loading:hide>Submit Order</span>
    <span loading:show>
        <span class="spinner"></span> Processing...
    </span>
</button>
```

This pattern gives three feedback signals at once:

1. The button text changes from "Submit Order" to "Processing...".
2. A spinner animation appears.
3. The button is disabled (via `loading:disabled`).

### Compilation

The `loading:show` and `loading:hide` attributes compile to HTMX indicator
behavior. The elements are given the `htmx-indicator` class and managed via
CSS visibility toggling, with `loading:hide` using an inverted visibility
rule.

| PJX Attribute    | Compiled Behavior                    |
| ---------------- | ------------------------------------ |
| `loading:show`   | Element visible during request       |
| `loading:hide`   | Element hidden during request        |

---

## Loading Classes

The `loading:class` attribute adds one or more CSS classes to an element while
an HTMX request is in flight. The classes are removed when the response
arrives.

```html
<button action:post="/api/save"
        loading:class="opacity-50 cursor-wait">
    Save
</button>
```

During the request, the button receives both `opacity-50` and `cursor-wait`
classes, making it appear faded with a wait cursor. When the response arrives,
the classes are removed.

### Common Loading Class Patterns

```html
<!-- Fade the entire form during submission -->
<form action:post="/api/users"
      loading:class="opacity-50 pointer-events-none">
    <input name="name" />
    <button type="submit">Create</button>
</form>

<!-- Pulse animation during load -->
<div action:get="/api/stats"
     trigger="load"
     loading:class="animate-pulse">
    Loading stats...
</div>

<!-- Gray out a card while refreshing -->
<div action:get="/api/card/1"
     trigger="every 30s"
     loading:class="grayscale opacity-75">
    <h3>Live Data</h3>
    <p>Updates every 30 seconds.</p>
</div>
```

### With Tailwind CSS

The `loading:class` attribute works naturally with Tailwind utility classes:

```html
<button action:post="/api/save"
        loading:class="bg-gray-400 text-gray-600 cursor-not-allowed"
        loading:disabled>
    Save Changes
</button>
```

| PJX Attribute              | Compiled Behavior               |
| -------------------------- | ------------------------------- |
| `loading:class="classes"`  | Adds classes during request     |

---

## Loading Disabled

The `loading:disabled` attribute disables an element while an HTMX request is
in flight. This prevents double-submission of forms and duplicate action
triggers.

```html
<button action:post="/api/save"
        loading:disabled>
    Save
</button>
```

During the request, the button receives the `disabled` HTML attribute. When the
response arrives, `disabled` is removed.

### Preventing Double Submission

```html
<form action:post="/api/orders">
    <input name="item" required />
    <input name="quantity" type="number" required />
    <button type="submit"
            loading:disabled
            loading:class="opacity-50">
        <span loading:hide>Place Order</span>
        <span loading:show>Placing Order...</span>
    </button>
</form>
```

This combination ensures:

- The button is disabled (cannot be clicked again).
- The button appears faded.
- The text changes to indicate progress.

| PJX Attribute        | Compiled Behavior            |
| -------------------- | ---------------------------- |
| `loading:disabled`   | `disabled` during request    |

---

## Loading Aria

The `loading:aria-busy` attribute sets `aria-busy="true"` on an element during
an HTMX request. This communicates loading state to assistive technologies
like screen readers.

```html
<div action:get="/api/data"
     trigger="load"
     loading:aria-busy="true">
    <div class="skeleton"></div>
</div>
```

During the request, the element has `aria-busy="true"`. Screen readers
announce this state to users, and some browsers apply default styling to
indicate the busy state. When the response arrives, `aria-busy` is removed.

### Accessible Loading Pattern

Combine `loading:aria-busy` with visual indicators for full accessibility:

```html
<section action:get="/api/dashboard"
         trigger="load"
         loading:aria-busy="true"
         loading:class="opacity-50">
    <div loading:show role="status">
        <span class="spinner"></span>
        <span class="sr-only">Loading dashboard data...</span>
    </div>
    <div loading:hide>
        <!-- Dashboard content -->
    </div>
</section>
```

| PJX Attribute              | Compiled Behavior              |
| -------------------------- | ------------------------------ |
| `loading:aria-busy="true"` | `aria-busy` during request     |

---

## Disabled Elements

The `disabled-elt` attribute is a direct pass-through to HTMX's
`hx-disabled-elt`. It disables one or more elements while the request is in
flight.

Unlike `loading:disabled` (which disables the element itself), `disabled-elt`
lets you specify which elements to disable by CSS selector.

### Disable Self

```html
<button action:post="/api/save"
        disabled-elt="this">
    Save
</button>
<!-- Compiles to: hx-disabled-elt="this" -->
```

### Disable Other Elements

```html
<form action:post="/api/submit"
      disabled-elt="#submit-btn, #cancel-btn">
    <input name="data" />
    <button id="submit-btn" type="submit">Submit</button>
    <button id="cancel-btn" type="button">Cancel</button>
</form>
<!-- Both buttons are disabled during the request -->
```

### Disable All Form Inputs

```html
<form action:post="/api/register"
      disabled-elt="find input, find button">
    <input name="email" type="email" />
    <input name="password" type="password" />
    <button type="submit">Register</button>
</form>
<!-- All inputs and buttons within the form are disabled -->
```

| PJX Attribute          | Compiled Output            |
| ---------------------- | -------------------------- |
| `disabled-elt="this"`  | `hx-disabled-elt="this"`   |
| `disabled-elt="#id"`   | `hx-disabled-elt="#id"`    |

---

## Skeleton Loading Pattern

PJX's [[File Based Routing]] supports a special `loading.jinja` file that
defines a skeleton placeholder displayed while the page loads.

### How It Works

Place a `loading.jinja` file alongside your page templates:

```text
pages/
    layout.jinja
    loading.jinja      <-- Global skeleton
    index.jinja
    dashboard/
        loading.jinja  <-- Dashboard-specific skeleton
        index.jinja
        analytics.jinja
```

The `loading.jinja` file is rendered as the initial content of the page
container. When navigation occurs via HTMX, the skeleton is shown immediately
while the actual page content loads from the server.

### Example Skeleton

```html
<!-- pages/loading.jinja -->
<div class="skeleton-page" aria-busy="true" role="status">
    <div class="skeleton skeleton-header"></div>
    <div class="skeleton skeleton-text"></div>
    <div class="skeleton skeleton-text"></div>
    <div class="skeleton skeleton-text short"></div>
    <span class="sr-only">Loading page content...</span>
</div>
```

### Skeleton CSS

```css
.skeleton {
    background: linear-gradient(
        90deg,
        #e2e8f0 25%,
        #edf2f7 50%,
        #e2e8f0 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: 4px;
}

.skeleton-header {
    height: 2rem;
    width: 60%;
    margin-bottom: 1rem;
}

.skeleton-text {
    height: 1rem;
    width: 100%;
    margin-bottom: 0.75rem;
}

.skeleton-text.short {
    width: 40%;
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
```

### Directory-Level Skeletons

Nested `loading.jinja` files override parent skeletons. The
`pages/dashboard/loading.jinja` skeleton applies to all pages under
`/dashboard/`, while `pages/loading.jinja` applies everywhere else.

| File                             | Scope                          |
| -------------------------------- | ------------------------------ |
| `pages/loading.jinja`            | All pages (global)             |
| `pages/dashboard/loading.jinja`  | Pages under `/dashboard/`      |
| `pages/blog/loading.jinja`       | Pages under `/blog/`           |

---

## Full Example

A save button that combines multiple loading techniques for a polished user
experience:

```html
---
props {
    item_id: int
}

state saved = false
---

<div id="save-section-{{ props.item_id }}">
    <button action:post="/api/items/{{ props.item_id }}/save"
            target="#save-section-{{ props.item_id }}"
            swap="outerHTML"
            loading:disabled
            loading:class="opacity-50 cursor-wait"
            loading:aria-busy="true"
            disabled-elt="this">

        <!-- Default state -->
        <span loading:hide>
            <svg class="icon"><!-- save icon --></svg>
            Save Changes
        </span>

        <!-- Loading state -->
        <span loading:show>
            <span class="spinner"></span>
            Saving...
        </span>
    </button>

    <!-- Success feedback (rendered by server response) -->
    <Show when="saved">
        <span class="text-green-600" x-init="setTimeout(() => saved = false, 3000)">
            Saved successfully.
        </span>
    </Show>
</div>
```

This example provides five layers of feedback:

1. **Text swap** -- "Save Changes" becomes "Saving..." with a spinner.
2. **Visual dimming** -- `opacity-50` and `cursor-wait` indicate the button
   is processing.
3. **Disabled state** -- The button cannot be clicked again during the request.
4. **Accessibility** -- `aria-busy="true"` announces the loading state to
   screen readers.
5. **Success message** -- The server response includes a "Saved successfully"
   message that auto-dismisses after 3 seconds.

### Compiled Output

```html
<div id="save-section-42">
    <button hx-post="/api/items/42/save"
            hx-target="#save-section-42"
            hx-swap="outerHTML"
            hx-disabled-elt="this">

        <span>
            <svg class="icon"><!-- save icon --></svg>
            Save Changes
        </span>

        <span class="htmx-indicator">
            <span class="spinner"></span>
            Saving...
        </span>
    </button>
</div>
```

The `loading:class`, `loading:disabled`, and `loading:aria-busy` attributes
are compiled into JavaScript or CSS-based behavior that activates when the
`htmx-request` class is present on the element.

---

## Compilation Table

All loading-related PJX attributes and their compiled behavior:

| PJX Attribute              | Compiled Output / Behavior                 |
| -------------------------- | ------------------------------------------ |
| `indicator="#id"`          | `hx-indicator="#id"`                       |
| `loading`                  | Adds `htmx-indicator` class to the element |
| `loading:show`             | Element visible only during request        |
| `loading:hide`             | Element hidden during request              |
| `loading:class="classes"`  | CSS classes added during request           |
| `loading:disabled`         | `disabled` attribute set during request    |
| `loading:aria-busy="true"` | `aria-busy="true"` set during request      |
| `disabled-elt="this"`      | `hx-disabled-elt="this"`                   |
| `disabled-elt="#id"`       | `hx-disabled-elt="#id"`                    |

---

## See Also

- [[HTMX Integration]] -- Core HTMX attributes: actions, targets, swaps, and triggers
- [[File Based Routing]] -- `loading.jinja` skeleton files and route conventions
- [[CSS and Assets]] -- Styling loading states with scoped CSS and Tailwind
- [[State and Reactivity]] -- Client-side state for success/error feedback after loading
