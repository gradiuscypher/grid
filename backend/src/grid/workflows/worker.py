"""Temporal worker entrypoint (Phase 3a). Runs `RunTransformWorkflow` and its
activities on the shared task queue.
"""

import asyncio

from temporalio.worker import Worker

from grid.core.config import get_settings
from grid.core.temporal_client import get_temporal_client
from grid.workflows.activities import (
    invoke_transform_activity,
    mark_run_failed_activity,
    mark_run_running_activity,
    merge_results_activity,
    prepare_invocation_activity,
)
from grid.workflows.transform_workflow import RunTransformWorkflow


async def _run() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[RunTransformWorkflow],
        activities=[
            mark_run_running_activity,
            mark_run_failed_activity,
            prepare_invocation_activity,
            invoke_transform_activity,
            merge_results_activity,
        ],
    )
    print(
        f"grid worker: connected to {settings.temporal_address}, "
        f"task queue {settings.temporal_task_queue!r}"
    )
    await worker.run()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
