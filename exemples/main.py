from pathlib import Path

from starlette.staticfiles import StaticFiles

from exemples.api.routers.actions import router as actions_router
from exemples.api.routers.api import router as api_router
from exemples.api.routers.pages import router as pages_router
from exemples.catalog import catalog
from pjx.web import FastAPI

app = FastAPI(title="PJX Example App")
BASE_DIR = Path(__file__).parent

# The app keeps a reference to the catalog so routers, actions and middleware
# can share the same component registry.
app.state.catalog = catalog

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(pages_router)
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(actions_router, prefix="/actions", tags=["actions"])
