from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz", operation_id="healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
