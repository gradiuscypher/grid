from temporalio.client import Client

from grid.core.config import get_settings

# A fresh connection per call is fine at MVP scale (this is only hit on transform-run
# start, not a hot path) — worth caching on app.state if that ever changes.


async def get_temporal_client() -> Client:
    settings = get_settings()
    return await Client.connect(settings.temporal_address)
