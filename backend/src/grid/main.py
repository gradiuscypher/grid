import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from grid.api.v1.auth import router as auth_router
from grid.api.v1.cases import router as cases_router
from grid.api.v1.edges import router as edges_router
from grid.api.v1.entity_types import router as entity_types_router
from grid.api.v1.groups import router as groups_router
from grid.api.v1.health import router as health_router
from grid.api.v1.nodes import router as nodes_router
from grid.api.v1.notes import router as notes_router
from grid.api.v1.transform_runs import router as transform_runs_router
from grid.api.v1.transforms import router as transforms_router
from grid.api.v1.waypoints import router as waypoints_router
from grid.api.v1.ws_tickets import router as ws_tickets_router
from grid.api.ws import router as ws_router
from grid.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from grid.db.session import async_session_maker
from grid.events.listener import run_listener
from grid.services.transforms import sync_builtin_transforms


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    async with async_session_maker() as db:
        await sync_builtin_transforms(db)
    listener_task = asyncio.create_task(run_listener())
    try:
        yield
    finally:
        listener_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await listener_task


app = FastAPI(title="Grid API", lifespan=_lifespan)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(entity_types_router, prefix="/api/v1")
app.include_router(nodes_router, prefix="/api/v1")
app.include_router(edges_router, prefix="/api/v1")
app.include_router(notes_router, prefix="/api/v1")
app.include_router(waypoints_router, prefix="/api/v1")
app.include_router(groups_router, prefix="/api/v1")
app.include_router(transforms_router, prefix="/api/v1")
app.include_router(transform_runs_router, prefix="/api/v1")
app.include_router(ws_tickets_router, prefix="/api/v1")
app.include_router(ws_router)


def _as_json(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
def _handle_not_found(_request: Request, exc: NotFoundError) -> JSONResponse:
    return _as_json(404, exc)


@app.exception_handler(ForbiddenError)
def _handle_forbidden(_request: Request, exc: ForbiddenError) -> JSONResponse:
    return _as_json(403, exc)


@app.exception_handler(UnauthorizedError)
def _handle_unauthorized(_request: Request, exc: UnauthorizedError) -> JSONResponse:
    return _as_json(401, exc)


@app.exception_handler(ConflictError)
def _handle_conflict(_request: Request, exc: ConflictError) -> JSONResponse:
    return _as_json(409, exc)


@app.exception_handler(ValidationError)
def _handle_validation(_request: Request, exc: ValidationError) -> JSONResponse:
    return _as_json(422, exc)
