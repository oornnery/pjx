# Layout Components

PJX includes a set of built-in layout components inspired by Chakra UI. These
components are always available in any `.jinja` file without an import statement.
The compiler recognizes them directly and compiles them to semantic HTML with
CSS class-based styling.

All layout components render as `<div>` elements (except `<Divider>`, which
renders as `<hr>`) with `pjx-*` CSS classes. The associated stylesheet
`pjx-layout.css` is included automatically when using PJX's asset pipeline.

## Quick Reference

| Component       | Description                          | Key Props                         |
| --------------- | ------------------------------------ | --------------------------------- |
| `<Center>`      | Centers content on both axes         | `class`                           |
| `<HStack>`      | Horizontal flex stack                | `gap`, `align`, `justify`         |
| `<VStack>`      | Vertical flex stack                  | `gap`, `align`, `justify`         |
| `<Grid>`        | Responsive CSS grid                  | `cols`, `gap`, `min`              |
| `<Spacer>`      | Flexible space between items         | `class`                           |
| `<Container>`   | Max-width centered wrapper           | `max`                             |
| `<Divider>`     | Horizontal rule                      | `class`                           |
| `<Wrap>`        | Flex wrap with gap                   | `gap`                             |
| `<AspectRatio>` | Fixed aspect ratio container         | `ratio`                           |
| `<Hide>`        | Responsive show/hide by breakpoint   | `below`, `above`                  |

Every layout component also accepts a `class` prop for additional CSS classes
and supports `{{ attrs }}` passthrough for arbitrary HTML attributes.

---

## Component Reference

### Center

Centers its children both horizontally and vertically using flexbox.

#### Props

| Prop    | Type  | Default | Description                    |
| ------- | ----- | ------- | ------------------------------ |
| `class` | `str` | `""`    | Additional CSS classes         |

#### Compiled output

```html
<div class="pjx-center">...</div>
```

#### CSS

```css
.pjx-center {
  display: flex;
  justify-content: center;
  align-items: center;
}
```

#### Example

```html
<Center>
  <img src="/logo.png" alt="Logo" />
</Center>
```

Use `Center` to vertically center a loading spinner or a hero message:

```html
<Center class="hero" style="height: 80vh">
  <VStack gap="1rem">
    <h1>Welcome to the App</h1>
    <p>Get started by creating your first component.</p>
  </VStack>
</Center>
```

---

### HStack

Arranges children in a horizontal row using flexbox. Items are placed
left-to-right with a configurable gap.

#### Props

| Prop      | Type  | Default | Description                                    |
| --------- | ----- | ------- | ---------------------------------------------- |
| `gap`     | `str` | `""`    | Space between items (e.g. `"1rem"`, `"8px"`)   |
| `align`   | `str` | `""`    | CSS `align-items` value (e.g. `"center"`)      |
| `justify` | `str` | `""`    | CSS `justify-content` value                    |
| `class`   | `str` | `""`    | Additional CSS classes                         |

#### Compiled output

```html
<div class="pjx-hstack"
     style="--pjx-gap:0.5rem;align-items:center;justify-content:space-between;">
  ...
</div>
```

#### CSS

```css
.pjx-hstack {
  display: flex;
  flex-direction: row;
  gap: var(--pjx-gap, 1rem);
}
```

The `gap` prop sets the `--pjx-gap` CSS custom property, which the base CSS
reads via `var()`. When no `gap` is provided, the default is `1rem`.

#### Example

```html
<HStack gap="0.5rem" align="center">
  <img src="/avatar.jpg" class="avatar" />
  <span>Jane Doe</span>
  <Badge variant="admin">Admin</Badge>
</HStack>
```

Navigation bar with items pushed apart:

```html
<HStack justify="space-between" align="center">
  <a href="/" class="logo">PJX</a>
  <HStack gap="1rem">
    <a href="/docs">Docs</a>
    <a href="/examples">Examples</a>
    <a href="/github">GitHub</a>
  </HStack>
</HStack>
```

---

### VStack

Arranges children in a vertical column using flexbox. Items are stacked
top-to-bottom with a configurable gap.

#### Props

| Prop      | Type  | Default | Description                                    |
| --------- | ----- | ------- | ---------------------------------------------- |
| `gap`     | `str` | `""`    | Space between items (e.g. `"1rem"`, `"8px"`)   |
| `align`   | `str` | `""`    | CSS `align-items` value (e.g. `"stretch"`)     |
| `justify` | `str` | `""`    | CSS `justify-content` value                    |
| `class`   | `str` | `""`    | Additional CSS classes                         |

#### Compiled output

```html
<div class="pjx-vstack" style="--pjx-gap:1rem;">
  ...
</div>
```

#### CSS

```css
.pjx-vstack {
  display: flex;
  flex-direction: column;
  gap: var(--pjx-gap, 1rem);
}
```

#### Example

```html
<VStack gap="1.5rem">
  <h2>Settings</h2>
  <FormField label="Username" />
  <FormField label="Email" />
  <FormField label="Password" type="password" />
  <Button label="Save" />
</VStack>
```

Form layout with left-aligned content:

```html
<VStack gap="1rem" align="flex-start">
  <label>Name</label>
  <input type="text" name="name" />
  <label>Bio</label>
  <textarea name="bio"></textarea>
</VStack>
```

---

### Grid

Creates a CSS Grid layout. When `cols` is specified, the grid uses a fixed
column count. The `min` prop sets the minimum column width for responsive
auto-fill behavior.

#### Props

| Prop    | Type  | Default | Description                                         |
| ------- | ----- | ------- | --------------------------------------------------- |
| `cols`  | `str` | `""`    | Number of columns (e.g. `"3"`)                      |
| `gap`   | `str` | `""`    | Gap between grid items (e.g. `"1rem"`)              |
| `min`   | `str` | `""`    | Minimum column width for auto-fill (e.g. `"300px"`) |
| `class` | `str` | `""`    | Additional CSS classes                              |

#### Compiled output

When `cols` is set:

```html
<div class="pjx-grid"
     style="--pjx-gap:1rem;grid-template-columns:repeat(3, minmax(var(--pjx-min, 250px), 1fr));">
  ...
</div>
```

When only `min` is set (auto-fill):

```html
<div class="pjx-grid" style="--pjx-gap:1rem;--pjx-min:300px;">
  ...
</div>
```

#### CSS

```css
.pjx-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--pjx-min, 250px), 1fr));
  gap: var(--pjx-gap, 1rem);
}
```

When `cols` is not provided, the grid uses `auto-fill` with `--pjx-min` to
create a responsive layout that automatically adjusts the number of columns
based on available width.

#### Example -- fixed columns

```html
<Grid cols="3" gap="1rem">
  <Card title="Users" count="1,234" />
  <Card title="Revenue" count="$56K" />
  <Card title="Orders" count="892" />
</Grid>
```

#### Example -- responsive auto-fill

Cards that reflow from 4 columns on wide screens to 1 column on mobile:

```html
<Grid gap="1rem" min="280px">
  <For each="products" as="product">
    <ProductCard name="{{ product.name }}" price="{{ product.price }}" />
  </For>
</Grid>
```

---

### Spacer

Fills available space between flex items. Renders as an empty `<div>` with
`flex: 1`. Use inside `<HStack>` or `<VStack>` to push items apart.

#### Props

| Prop    | Type  | Default | Description                    |
| ------- | ----- | ------- | ------------------------------ |
| `class` | `str` | `""`    | Additional CSS classes         |

#### Compiled output

```html
<div class="pjx-spacer"></div>
```

#### CSS

```css
.pjx-spacer { flex: 1; }
```

#### Example

Push a button to the right side of a header:

```html
<HStack align="center">
  <h1>Dashboard</h1>
  <Spacer />
  <Button label="Settings" />
</HStack>
```

Multiple spacers distribute items evenly:

```html
<HStack>
  <Spacer />
  <span>Centered content</span>
  <Spacer />
</HStack>
```

---

### Container

A max-width centered wrapper. Use it as the outermost layout element to
constrain page content to a readable width.

#### Props

| Prop    | Type  | Default | Description                                |
| ------- | ----- | ------- | ------------------------------------------ |
| `max`   | `str` | `""`    | Maximum width (e.g. `"1200px"`, `"80rem"`) |
| `class` | `str` | `""`    | Additional CSS classes                     |

#### Compiled output

```html
<div class="pjx-container" style="--pjx-max-w:1200px;">
  ...
</div>
```

#### CSS

```css
.pjx-container {
  max-width: var(--pjx-max-w, 960px);
  width: 100%;
  margin: 0 auto;
  padding: 0 1rem;
}
```

When no `max` is provided, the default maximum width is `960px`.

#### Example

```html
<Container max="1200px">
  <VStack gap="2rem">
    <h1>Blog</h1>
    <For each="posts" as="post">
      <PostCard title="{{ post.title }}" excerpt="{{ post.excerpt }}" />
    </For>
  </VStack>
</Container>
```

Narrow container for article content:

```html
<Container max="720px">
  <article>
    {{ content|safe }}
  </article>
</Container>
```

---

### Divider

Renders a horizontal rule (`<hr>`) to visually separate sections of content.

#### Props

| Prop    | Type  | Default | Description                    |
| ------- | ----- | ------- | ------------------------------ |
| `class` | `str` | `""`    | Additional CSS classes         |

#### Compiled output

```html
<hr class="pjx-divider" />
```

#### CSS

```css
.pjx-divider {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 1rem 0;
}
```

#### Example

```html
<VStack gap="1rem">
  <h2>Account</h2>
  <ProfileForm />
  <Divider />
  <h2>Notifications</h2>
  <NotificationSettings />
  <Divider />
  <h2>Danger Zone</h2>
  <DeleteAccount />
</VStack>
```

Custom styled divider:

```html
<Divider class="my-4" style="border-color: #ef4444;" />
```

---

### Wrap

A flex container that wraps children to the next line when they exceed
the available width. Useful for tag lists, button groups, and chip layouts.

#### Props

| Prop    | Type  | Default | Description                                |
| ------- | ----- | ------- | ------------------------------------------ |
| `gap`   | `str` | `""`    | Gap between items (e.g. `"0.5rem"`)        |
| `class` | `str` | `""`    | Additional CSS classes                     |

#### Compiled output

```html
<div class="pjx-wrap" style="--pjx-gap:0.5rem;">
  ...
</div>
```

#### CSS

```css
.pjx-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: var(--pjx-gap, 1rem);
}
```

#### Example

Tag list that wraps naturally:

```html
<Wrap gap="0.5rem">
  <For each="tags" as="tag">
    <span class="badge">{{ tag }}</span>
  </For>
</Wrap>
```

Button group:

```html
<Wrap gap="0.75rem">
  <Button label="Save" variant="primary" />
  <Button label="Cancel" variant="secondary" />
  <Button label="Delete" variant="danger" />
</Wrap>
```

---

### AspectRatio

Constrains its children to a fixed aspect ratio using the CSS `aspect-ratio`
property. Useful for images, videos, and embeds that need a consistent shape.

#### Props

| Prop    | Type  | Default | Description                           |
| ------- | ----- | ------- | ------------------------------------- |
| `ratio` | `str` | `""`    | Aspect ratio (e.g. `"16/9"`, `"1/1"`) |
| `class` | `str` | `""`    | Additional CSS classes                |

#### Compiled output

```html
<div class="pjx-aspect" style="--pjx-ratio:16/9;">
  ...
</div>
```

#### CSS

```css
.pjx-aspect {
  position: relative;
  aspect-ratio: var(--pjx-ratio, 16/9);
}
```

When no `ratio` is provided, the default is `16/9`.

#### Example

Widescreen video embed:

```html
<AspectRatio ratio="16/9">
  <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"
          style="width: 100%; height: 100%;"
          allowfullscreen></iframe>
</AspectRatio>
```

Square thumbnail grid:

```html
<Grid cols="4" gap="0.5rem">
  <For each="images" as="img">
    <AspectRatio ratio="1/1">
      <img src="{{ img.url }}" alt="{{ img.alt }}" style="object-fit: cover; width: 100%; height: 100%;" />
    </AspectRatio>
  </For>
</Grid>
```

---

### Hide

Hides content based on viewport width breakpoints. Uses CSS media queries with
predefined breakpoint classes. The element uses `display: contents` by default
so it does not create an extra box in the layout.

#### Props

| Prop    | Type  | Default | Description                                          |
| ------- | ----- | ------- | ---------------------------------------------------- |
| `below` | `str` | `""`    | Hide when viewport is narrower than this value       |
| `above` | `str` | `""`    | Hide when viewport is wider than this value          |
| `class` | `str` | `""`    | Additional CSS classes                               |

#### Predefined breakpoints

| Value  | Width    | Typical device      |
| ------ | -------- | ------------------- |
| `480`  | 480 px   | Small phone         |
| `640`  | 640 px   | Large phone         |
| `768`  | 768 px   | Tablet              |
| `1024` | 1024 px  | Laptop              |
| `1280` | 1280 px  | Desktop             |

#### Compiled output

```html
<div class="pjx-hide pjx-hide-below-768">
  ...
</div>
```

#### CSS

```css
.pjx-hide { display: contents; }

@media (max-width: 768px) {
  .pjx-hide-below-768 { display: none !important; }
}
@media (min-width: 1024px) {
  .pjx-hide-above-1024 { display: none !important; }
}
```

#### Example

Hide a sidebar on mobile:

```html
<HStack gap="2rem">
  <Hide below="768">
    <aside class="sidebar">
      <Navigation />
    </aside>
  </Hide>
  <main class="content">
    <Slot />
  </main>
</HStack>
```

Show a mobile menu button only on small screens:

```html
<Hide above="768">
  <button class="mobile-menu-toggle" on:click="menuOpen = !menuOpen">
    Menu
  </button>
</Hide>
```

---

## Composition

Layout components are designed to nest together for complex page structures.
Since each component is a simple `<div>` (or `<hr>`), there is no performance
cost to deep nesting.

### Sidebar layout

```html
<Container max="1400px">
  <HStack gap="2rem" align="flex-start">
    <Hide below="768">
      <VStack gap="1rem" class="sidebar" style="width: 260px; flex-shrink: 0;">
        <h3>Navigation</h3>
        <a href="/dashboard">Dashboard</a>
        <a href="/settings">Settings</a>
        <a href="/users">Users</a>
        <Divider />
        <a href="/logout">Log Out</a>
      </VStack>
    </Hide>
    <VStack gap="1.5rem" style="flex: 1;">
      <HStack justify="space-between" align="center">
        <h1>Dashboard</h1>
        <Spacer />
        <Button label="New Item" />
      </HStack>
      <Grid cols="3" gap="1rem" min="280px">
        <StatsCard title="Users" value="1,234" />
        <StatsCard title="Revenue" value="$56K" />
        <StatsCard title="Orders" value="892" />
      </Grid>
      <Divider />
      <section>
        <h2>Recent Activity</h2>
        <ActivityList />
      </section>
    </VStack>
  </HStack>
</Container>
```

### Page with header, content, and footer

```html
<VStack gap="0" style="min-height: 100vh;">
  <header>
    <Container max="1200px">
      <HStack justify="space-between" align="center" gap="1rem">
        <a href="/" class="logo">MyApp</a>
        <HStack gap="1rem">
          <a href="/docs">Docs</a>
          <a href="/pricing">Pricing</a>
        </HStack>
      </HStack>
    </Container>
  </header>

  <main style="flex: 1;">
    <Container max="1200px">
      <Slot />
    </Container>
  </main>

  <footer>
    <Container max="1200px">
      <HStack justify="space-between" align="center">
        <span>Built with PJX</span>
        <HStack gap="1rem">
          <a href="/terms">Terms</a>
          <a href="/privacy">Privacy</a>
        </HStack>
      </HStack>
    </Container>
  </footer>
</VStack>
```

### Card grid with empty state

```html
<Container max="1000px">
  <VStack gap="1.5rem">
    <HStack justify="space-between" align="center">
      <h1>Projects</h1>
      <Button label="New Project" action:post="/htmx/projects/create" />
    </HStack>

    <Show when="projects">
      <Grid gap="1rem" min="300px">
        <For each="projects" as="project">
          <ProjectCard name="{{ project.name }}" />
        </For>
      </Grid>
    </Show>

    <Show when="not projects">
      <Center style="height: 200px;">
        <VStack gap="0.5rem" align="center">
          <p>No projects yet.</p>
          <Button label="Create your first project" />
        </VStack>
      </Center>
    </Show>
  </VStack>
</Container>
```

---

## Custom Styling

Every layout component accepts a `class` prop and supports `{{ attrs }}`
passthrough. This means you can add custom classes, inline styles, or
any HTML attribute.

### Adding CSS classes

```html
<HStack gap="1rem" class="my-toolbar border-b pb-4">
  <Button label="Save" />
  <Button label="Cancel" />
</HStack>
```

### Inline styles via attrs passthrough

```html
<VStack gap="1rem" style="background: #f9fafb; padding: 2rem; border-radius: 8px;">
  <h2>Card Content</h2>
  <p>This VStack has custom background and padding.</p>
</VStack>
```

### Data attributes and HTMX

Because layout components pass through unrecognized attributes via `{{ attrs }}`,
you can use them with HTMX and Alpine.js:

```html
<VStack gap="1rem" id="todo-list" hx-get="/htmx/todos" hx-trigger="load">
  <p>Loading...</p>
</VStack>
```

### Overriding CSS variables

The layout components use CSS custom properties (`--pjx-gap`, `--pjx-max-w`,
`--pjx-min`, `--pjx-ratio`). You can override these globally in your own
stylesheet:

```css
:root {
  --pjx-gap: 0.75rem;    /* Change default gap for all stacks */
  --pjx-max-w: 1100px;   /* Change default container width */
}
```

Or override per-instance with the `style` attribute:

```html
<HStack style="--pjx-gap: 2rem;">
  <Card />
  <Card />
</HStack>
```

---

## Responsive Patterns

### Grid that collapses on mobile

Use `Grid` with `min` for automatic responsive behavior without media queries:

```html
<Grid gap="1rem" min="320px">
  <FeatureCard title="Fast" icon="bolt" />
  <FeatureCard title="Secure" icon="shield" />
  <FeatureCard title="Simple" icon="cube" />
</Grid>
```

On screens wider than 960px, this shows 3 columns. On a phone, it collapses
to a single column. No breakpoints needed.

### Show different content by screen size

Combine `Hide` to display different components at different breakpoints:

```html
<!-- Desktop: full sidebar navigation -->
<Hide below="768">
  <Sidebar />
</Hide>

<!-- Mobile: hamburger menu -->
<Hide above="768">
  <MobileMenu />
</Hide>
```

### Responsive dashboard

```html
<Container max="1400px">
  <VStack gap="2rem">
    <!-- Stats row: 4 columns on desktop, 2 on tablet, 1 on mobile -->
    <Grid gap="1rem" min="250px">
      <StatCard label="Users" value="12,345" />
      <StatCard label="Revenue" value="$89K" />
      <StatCard label="Conversion" value="3.2%" />
      <StatCard label="Sessions" value="45K" />
    </Grid>

    <!-- Chart: hidden on mobile -->
    <Hide below="640">
      <AspectRatio ratio="21/9">
        <div id="revenue-chart"></div>
      </AspectRatio>
    </Hide>

    <!-- Two-column layout on desktop, stacked on mobile -->
    <Grid gap="1.5rem" min="400px">
      <VStack gap="1rem">
        <h2>Recent Orders</h2>
        <OrderList />
      </VStack>
      <VStack gap="1rem">
        <h2>Top Products</h2>
        <ProductList />
      </VStack>
    </Grid>
  </VStack>
</Container>
```

### Media query-based hiding with named breakpoints

The `Hide` component uses pixel values for breakpoints. Common patterns map
to standard breakpoint names:

| Name   | `below` | `above` |
| ------ | ------- | ------- |
| sm     | `640`   | `640`   |
| md     | `768`   | `768`   |
| lg     | `1024`  | `1024`  |
| xl     | `1280`  | `1280`  |

```html
<!-- Hide below medium screens -->
<Hide below="768">
  <DesktopNav />
</Hide>

<!-- Hide above medium screens -->
<Hide above="768">
  <MobileNav />
</Hide>
```

---

## See Also

- [[Layouts and Inheritance]] -- Layout templates and `extends`/`<Slot />`
- [[CSS and Assets]] -- Scoped CSS, asset declarations, and the build pipeline
- [[Component Syntax]] -- Frontmatter, props, slots, and template body
