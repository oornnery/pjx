# PJXRouter Patterns

## Setup

```python
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader
from pjx import PJXEnvironment
from pjx.router import PJXRouter

app = FastAPI()
templates = Jinja2Templates(
    env=PJXEnvironment(loader=FileSystemLoader("templates"))
)
ui = PJXRouter(templates)
app.include_router(ui)
```

## Decorators

### @ui.page — Full page (GET)

```python
@ui.page("/", "pages/home.jinja")
async def home(request: Request) -> HomeProps:
    return HomeProps(title="Home")
```

### @ui.fragment — Partial HTML (HTMX swap)

```python
@ui.fragment("/users/{id}/edit", "partials/edit.jinja")
async def edit_form(request: Request, id: int) -> EditProps:
    return EditProps(user=get_user(id))

# Custom method
@ui.fragment("/users/{id}", "partials/user.jinja", method="PUT")
async def update_user(request: Request, id: int) -> UserProps:
    ...
```

### @ui.action — Form validation

```python
from pjx.router import FormData

@ui.action(
    "/users",
    success_template="partials/user_card.jinja",
    error_template="partials/form_error.jinja",
)
async def create_user(
    request: Request,
    data: CreateUserForm = FormData(CreateUserForm),
    svc: UserService = Depends(get_user_service),
) -> UserCardProps:
    user = svc.create(data)
    return UserCardProps(**user.model_dump())
```

- Success: renders `success_template` (200)
- Validation error: renders `error_template` (422)
- Custom status: return `ActionResult(data=props, status=201)`

### @ui.stream — SSE

```python
from pjx.router import SSEEvent

@ui.stream("/notifications", "partials/notification.jinja")
async def notifications(request: Request):
    async for event in event_source():
        yield SSEEvent(
            props=NotificationProps(message=event.text),
            id=str(event.id),
            event="notification",
        )
```

### ui.render — Manual

```python
@app.exception_handler(404)
async def not_found(request, exc):
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)
```

## Template Context

All decorators inject:

| Variable  | Content                       |
| --------- | ----------------------------- |
| `props`   | BaseModel returned by handler |
| `params`  | `request.path_params` dict    |
| `request` | Starlette Request             |

## Patterns

### Shared Service via Depends

```python
# api.py (JSON)
@router.get("/users")
async def list_users(svc = Depends(get_user_service)):
    return svc.list()

# views.py (HTML)
@ui.page("/", "pages/home.jinja")
async def home(request, svc = Depends(get_user_service)):
    return HomeProps(users=svc.list())
```

### Dynamic Routes with [slug]

```python
@ui.page("/users/{user_id}", "pages/users/[id].jinja")
async def user_detail(request, user_id: int):
    return UserDetailProps(user=get_user(user_id))
```

Template receives `params.user_id` automatically.

Common PJX convention is to use bracketed filenames for dynamic pages:

```text
pages/users/[id].jinja
pages/blog/[slug].jinja
pages/orgs/[org_slug]/repos/[repo_slug].jinja
```

The filename is for project organization and readability. The actual param names
still come from the FastAPI route:

```python
@ui.page("/blog/{post_slug}", "pages/blog/[slug].jinja")
async def post_detail(request, post_slug: str):
    ...
```

Inside the template you access:

```html
<a href={"/blog/" ~ params.post_slug}>Open</a>
```

So `[slug]` in the filename does not create `params.slug` by itself. `params`
always reflects `request.path_params`.

### Error Pages

```python
@app.exception_handler(404)
async def not_found(request, exc):
    return HTMLResponse(ui.render("pages/404.jinja"), status_code=404)

@app.exception_handler(500)
async def server_error(request, exc):
    return HTMLResponse(ui.render("pages/500.jinja"), status_code=500)
```
