"""`RunTransformWorkflow`: resolve credentials -> invoke -> merge (ARCHITECTURE §6).
All side effects live in activities; this file only orchestrates them, so it stays
deterministic and safe to replay (CLAUDE.md Temporal discipline). Retries/timeouts
are `RetryPolicy`/`start_to_close_timeout` on each activity call, not hand-rolled
try/except loops around the actual work.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

# activities.py imports sqlalchemy/httpx/dns at module level (real side effects at
# import time via the DB engine), which the workflow sandbox would otherwise
# reject — safe here because the workflow only ever references these as function
# pointers for `execute_activity`, never calls their bodies directly.
with workflow.unsafe.imports_passed_through():
    from grid.workflows.activities import (
        invoke_transform_activity,
        mark_run_failed_activity,
        mark_run_running_activity,
        merge_results_activity,
        prepare_invocation_activity,
    )

_SHORT_TIMEOUT = timedelta(seconds=10)
_SHORT_RETRY = RetryPolicy(maximum_attempts=3)


@workflow.defn(name="RunTransformWorkflow")
class RunTransformWorkflow:
    @workflow.run
    async def run(self, run_id: str) -> None:
        try:
            await workflow.execute_activity(
                mark_run_running_activity,
                run_id,
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_SHORT_RETRY,
            )
            prep = await workflow.execute_activity(
                prepare_invocation_activity,
                run_id,
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_SHORT_RETRY,
            )
            result = await workflow.execute_activity(
                invoke_transform_activity,
                args=[run_id, prep["credentials"]],
                start_to_close_timeout=timedelta(seconds=prep["timeout_s"]),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )
            await workflow.execute_activity(
                merge_results_activity,
                args=[run_id, result],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=_SHORT_RETRY,
            )
        except Exception as exc:
            # Activity failures arrive wrapped in ActivityError, whose own message is
            # the generic "Activity task failed" — the real reason is on __cause__.
            error = str(exc.__cause__) if exc.__cause__ is not None else str(exc)
            await workflow.execute_activity(
                mark_run_failed_activity,
                args=[run_id, error],
                start_to_close_timeout=_SHORT_TIMEOUT,
                retry_policy=_SHORT_RETRY,
            )
            raise
