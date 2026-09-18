from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.app.routers import intake

app = FastAPI(title="Risk Assessment Workbench")

app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "static")),
    name="static",
)

app.include_router(intake.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/intake")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
