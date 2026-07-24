"""RunTransformWorkflow orchestration, tested against Temporal's ephemeral
time-skipping test server with fake activities (registered under the real
activity names) — this exercises the workflow's own control flow (call order,
failure handling) in isolation from what the real activities actually do
(DB access, DNS, HTTP — covered separately in tests/services and
tests/transforms).
"""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from grid.workflows.transform_workflow import RunTransformWorkflow


@pytest.fixture
async def env() -> AsyncGenerator[WorkflowEnvironment]:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        yield environment


async def test_workflow_happy_path_calls_activities_in_order(env: WorkflowEnvironment) -> None:
    calls: list[str] = []

    @activity.defn(name="mark_run_running_activity")
    async def fake_mark_running(run_id: str) -> None:
        calls.append("running")

    @activity.defn(name="prepare_invocation_activity")
    async def fake_prepare(run_id: str) -> dict[str, Any]:
        calls.append("prepare")
        return {"credentials": {}, "timeout_s": 5}

    @activity.defn(name="invoke_transform_activity")
    async def fake_invoke(run_id: str, credentials: dict[str, str]) -> dict[str, Any]:
        calls.append("invoke")
        return {"nodes": [], "edges": [], "logs": ["ok"]}

    @activity.defn(name="merge_results_activity")
    async def fake_merge(run_id: str, result: dict[str, Any]) -> None:
        calls.append("merge")

    @activity.defn(name="mark_run_failed_activity")
    async def fake_failed(run_id: str, error: str) -> None:
        calls.append("failed")

    task_queue = f"test-{uuid.uuid4()}"
    async with Worker(
        env.client,
        task_queue=task_queue,
        workflows=[RunTransformWorkflow],
        activities=[fake_mark_running, fake_prepare, fake_invoke, fake_merge, fake_failed],
    ):
        await env.client.execute_workflow(
            RunTransformWorkflow.run,
            str(uuid.uuid4()),
            id=f"wf-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert calls == ["running", "prepare", "invoke", "merge"]


async def test_workflow_marks_run_failed_on_activity_error(env: WorkflowEnvironment) -> None:
    calls: list[str] = []

    @activity.defn(name="mark_run_running_activity")
    async def fake_mark_running(run_id: str) -> None:
        calls.append("running")

    @activity.defn(name="prepare_invocation_activity")
    async def fake_prepare(run_id: str) -> dict[str, Any]:
        calls.append("prepare")
        return {"credentials": {}, "timeout_s": 5}

    @activity.defn(name="invoke_transform_activity")
    async def fake_invoke(run_id: str, credentials: dict[str, str]) -> dict[str, Any]:
        calls.append("invoke")
        raise ApplicationError("transform blew up", non_retryable=True)

    @activity.defn(name="merge_results_activity")
    async def fake_merge(run_id: str, result: dict[str, Any]) -> None:
        calls.append("merge")

    @activity.defn(name="mark_run_failed_activity")
    async def fake_failed(run_id: str, error: str) -> None:
        calls.append("failed")
        assert "transform blew up" in error

    task_queue = f"test-{uuid.uuid4()}"
    async with Worker(
        env.client,
        task_queue=task_queue,
        workflows=[RunTransformWorkflow],
        activities=[fake_mark_running, fake_prepare, fake_invoke, fake_merge, fake_failed],
    ):
        with pytest.raises(WorkflowFailureError):
            await env.client.execute_workflow(
                RunTransformWorkflow.run,
                str(uuid.uuid4()),
                id=f"wf-{uuid.uuid4()}",
                task_queue=task_queue,
            )

    assert calls == ["running", "prepare", "invoke", "failed"]
