from fastapi import FastAPI

from grid.api.v1.health import router as health_router

app = FastAPI(title="Grid API")

app.include_router(health_router, prefix="/api/v1")
