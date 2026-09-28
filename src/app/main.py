from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.app.models.schemas import UserRole
from src.app.routers import intake
from src.app.services.auth import DEMO_USER_ROLES

app = FastAPI(title="Risk Assessment Workbench")

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)

app.include_router(intake.router)


@app.get("/")
async def root(request: Request):
    user = request.cookies.get("demo_user")
    role = request.cookies.get("demo_role")
    authenticated_role = DEMO_USER_ROLES.get(user) if user else None
    if authenticated_role is None or role != authenticated_role.value:
        return RedirectResponse(url="/intake/login")

    dashboard_urls = {
        UserRole.product_owner: "/intake/product-owner/dashboard/demo",
        UserRole.analyst: "/intake/analyst/dashboard/demo",
        UserRole.committee: "/intake/committee/dashboard/demo",
    }
    return RedirectResponse(url=dashboard_urls[authenticated_role])


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
