# CSS and Assets

PJX provides scoped CSS per component, a frontmatter-based asset declaration
system, and a build pipeline that collects, deduplicates, and bundles all
CSS and JS dependencies across the component tree.

---

## Scoped CSS

Components can include a `<style scoped>` block after the closing `---` of the
frontmatter. PJX automatically scopes these styles to the component using a
hash-based class prefix, preventing name collisions between components.

### Input

```html
---
props { type: str = "info" }
---

<style scoped>
  .alert { padding: 1rem; border-radius: 8px; }
  .alert-success { background: #d1fae5; color: #065f46; }
  .alert-error { background: #fee2e2; color: #991b1b; }
</style>

<div class="alert alert-{{ props.type }}">
  <Slot />
</div>
```

### Compiled output

PJX generates a unique hash from the component file path and rewrites the
selectors and the root element:

```html
<div class="alert alert-info" data-pjx-a1b2c3>
  ...
</div>
```

```css
.alert[data-pjx-a1b2c3] { padding: 1rem; border-radius: 8px; }
.alert-success[data-pjx-a1b2c3] { background: #d1fae5; color: #065f46; }
.alert-error[data-pjx-a1b2c3] { background: #fee2e2; color: #991b1b; }
```

---

## How Scoping Works

1. **Hash generation** -- PJX computes a short hash (e.g. `a1b2c3`) from the
   component's file path. This hash is stable across builds as long as the
   file path does not change.

2. **Attribute injection** -- The component's root element receives a
   `data-pjx-<hash>` attribute.

3. **Selector rewriting** -- Every selector in the `<style scoped>` block is
   suffixed with `[data-pjx-<hash>]`, limiting its scope to elements within
   that specific component instance.

### What scoping prevents

Without scoping, two components that both define `.card` would conflict:

```html
<!-- components/UserCard.jinja -->
<style scoped>
  .card { background: white; }
</style>

<!-- components/ProductCard.jinja -->
<style scoped>
  .card { background: #f0f9ff; }
</style>
```

With scoping, each `.card` rule only applies to its own component. The two
definitions coexist without interference.

### Limitations

- Scoped styles apply to the component's own elements only. They do not
  penetrate into child components.
- Global styles (without `scoped`) are not rewritten and apply normally.

---

## CSS Frontmatter

Components can declare external CSS dependencies in the frontmatter using the
`css` keyword. These are not inlined -- they are collected and rendered as
`<link>` tags in the final HTML.

```html
---
css "components/datepicker.css"
---

<div class="datepicker">
  ...
</div>
```

Multiple CSS files can be declared:

```html
---
css "components/card.css"
css "vendor/animate.css"
---
```

The path is relative to the configured `static_dir`. At render time, PJX
resolves it to the full URL (e.g. `/static/components/datepicker.css`).

---

## JS Frontmatter

External JavaScript dependencies use the `js` keyword in the frontmatter:

```html
---
js "components/chart-init.js"
---

<div class="chart-container">
  <canvas id="chart"></canvas>
</div>
```

Multiple JS files:

```html
---
js "vendor/chart.js"
js "components/chart-init.js"
---
```

JS assets are rendered as `<script type="module">` tags by default. To render
without the `module` type, call `render_js(module=False)` explicitly.

---

## Asset Collection

PJX uses `AssetCollector` to gather all `css` and `js` declarations from the
entire component tree. When a page is rendered, the collector walks the
component hierarchy (including all imports) and builds a deduplicated list
of assets.

### Rendering assets in a layout

Use `{{ pjx_assets.render() }}` in the layout's `<head>` to emit all
collected `<link>` and `<script>` tags:

```html
<!-- templates/layouts/Base.jinja -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{{ seo.title|default("PJX App") }}</title>
  {{ pjx_assets.render() }}
</head>
<body>
  <Slot />
</body>
</html>
```

### Separate CSS and JS rendering

For finer control, render CSS and JS assets independently:

```html
<head>
  {{ pjx_assets.render_css() }}
</head>
<body>
  <Slot />
  {{ pjx_assets.render_js() }}
</body>
```

This places CSS in the `<head>` and JS at the end of `<body>`, which is a
common pattern for faster page loads.

### Generated output

Given a page that imports components declaring `css "components/card.css"`,
`css "vendor/animate.css"`, and `js "components/chart-init.js"`:

```html
<head>
  <link rel="stylesheet" href="/static/components/card.css" />
  <link rel="stylesheet" href="/static/vendor/animate.css" />
  <script src="/static/components/chart-init.js" type="module"></script>
</head>
```

CSS tags are always rendered before JS tags.

---

## Asset Deduplication

When the same asset is declared in multiple components, PJX includes it only
once. The `AssetCollector` tracks seen assets by `(kind, path)` tuples.

### Example

Suppose three components all declare the same CSS:

```html
<!-- components/CardA.jinja -->
---
css "shared/card-base.css"
---

<!-- components/CardB.jinja -->
---
css "shared/card-base.css"
---

<!-- components/CardC.jinja -->
---
css "shared/card-base.css"
css "components/card-c.css"
---
```

A page that uses all three components will produce:

```html
<link rel="stylesheet" href="/static/shared/card-base.css" />
<link rel="stylesheet" href="/static/components/card-c.css" />
```

The `card-base.css` link appears exactly once, in the order it was first
encountered during the component tree traversal.

---

## Building CSS

The `pjx build` command compiles all `.jinja` components in the project and
generates a unified CSS bundle containing all scoped styles.

```bash
pjx build
```

This produces `static/css/pjx-components.css`, which contains every `<style
scoped>` block from every component, each rewritten with its hash-based scope.

### Including the bundle

Add the compiled bundle to the base layout:

```html
<head>
  <link rel="stylesheet" href="/static/css/pjx-components.css" />
  {{ pjx_assets.render() }}
</head>
```

### Development vs production

In development (`pjx dev`), scoped styles are injected inline for fast
iteration. In production, run `pjx build` to generate the consolidated bundle,
which reduces the number of HTTP requests.

### Build output structure

```text
static/
  css/
    pjx-components.css    <-- all scoped styles, compiled
    pjx-layout.css        <-- built-in layout component styles
    base.css              <-- your project's base styles
  js/
    app.js
  vendor/
    alpine.min.js
    htmx.min.js
```

---

## Vendor Packages

PJX provides a package manager for frontend dependencies. The `pjx add`
command downloads a package and copies its distribution files into the
configured `vendor_static_dir` (default: `static/vendor/`).

### Adding a package

```bash
pjx add alpinejs
```

This downloads Alpine.js and copies `alpine.min.js` to `static/vendor/`.

### Removing a package

```bash
pjx remove alpinejs
```

This removes the vendor files from `static/vendor/`.

### Using vendor files

Reference vendor files in the base layout:

```html
<head>
  <script defer src="/static/vendor/alpine.min.js"></script>
  <script src="/static/vendor/htmx.min.js"></script>
</head>
```

Or declare them in component frontmatter:

```html
---
js "vendor/chart.min.js"
---
```

### Directory configuration

The vendor directory is configured in `pjx.toml`:

```toml
static_dir = "static"
```

Vendor files are placed in `static/vendor/` by default. The project directory
structure after adding packages:

```text
static/
  vendor/
    alpine.min.js
    htmx.min.js
    chart.min.js
  css/
  js/
```

---

## Tailwind CSS

PJX supports Tailwind CSS integration. Enable it in `pjx.toml`:

```toml
tailwind = true
```

When Tailwind is enabled, `pjx build` runs the Tailwind compiler as part of
the build pipeline, scanning all `.jinja` files for utility classes.

### Setup

1. Enable Tailwind in configuration:

   ```toml
   tailwind = true
   ```

2. Create a `tailwind.config.js` (or let `pjx init` scaffold one):

   ```js
   /** @type {import('tailwindcss').Config} */
   module.exports = {
     content: ["./templates/**/*.jinja"],
     theme: { extend: {} },
     plugins: [],
   }
   ```

3. Create a base CSS file with Tailwind directives:

   ```css
   /* static/css/base.css */
   @tailwind base;
   @tailwind components;
   @tailwind utilities;
   ```

4. Build:

   ```bash
   pjx build
   ```

### Using Tailwind with layout components

Layout components work alongside Tailwind classes. Use the `class` prop to
add utility classes:

```html
<Container max="1200px" class="py-8">
  <VStack gap="1rem" class="bg-white rounded-lg shadow p-6">
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <Grid cols="3" gap="1rem">
      <div class="p-4 bg-blue-50 rounded">Card 1</div>
      <div class="p-4 bg-blue-50 rounded">Card 2</div>
      <div class="p-4 bg-blue-50 rounded">Card 3</div>
    </Grid>
  </VStack>
</Container>
```

### Tailwind with scoped CSS

Scoped CSS and Tailwind can coexist. Tailwind utilities apply globally while
scoped styles are isolated to the component:

```html
---
props { variant: str = "default" }
---

<style scoped>
  .widget { border: 2px solid #e5e7eb; transition: border-color 0.2s; }
  .widget:hover { border-color: #3b82f6; }
</style>

<div class="widget p-4 rounded-lg">
  <Slot />
</div>
```

---

## See Also

- [[Component Syntax]] -- Frontmatter keywords including `css` and `js`
- [[Layout Components]] -- Built-in layout primitives and their CSS classes
- [[Configuration Reference]] -- `pjx.toml` settings for `static_dir`, `tailwind`, and build options
