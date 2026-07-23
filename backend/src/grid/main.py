from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from grid.api.v1.auth import router as auth_router
from grid.api.v1.cases import router as cases_router
from grid.api.v1.entity_types import router as entity_types_router
from grid.api.v1.health import router as health_router
from grid.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

app = FastAPI(title="Grid API")

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(entity_types_router, prefix="/api/v1")


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
