"""Tests for the scheduling predicates and PipelineManager.run_due_instances / get_next_due_time."""
import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from pipeline_backend.procedure_runner import ProcedureRunner
from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep
from pipeline_backend.instances import Instance
from pipeline_backend.variables import String, Integer
from pipeline_backend.manager import PipelineManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_workflow(mgr, uuid="wf-sched", name="Sched Test"):
    wf = Workflow(mgr.ctx)
    wf.uuid = uuid
    wf.name = name
    wf.procedures["start"] = [ProcessingStep("pause_this_instance")]
    mgr.ctx.workflows[wf.uuid] = wf
    return wf


async def wait_for_running_tasks(mgr):
    tasks = list(mgr._running_instance_tasks.values())
    assert tasks
    await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# Instance.past_time_to_run
# ---------------------------------------------------------------------------

class TestPastTimeToRun:
    def test_returns_true_when_time_has_passed(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() - timedelta(seconds=10)
        assert inst.past_time_to_run() is True

    def test_returns_false_when_time_is_future(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() + timedelta(seconds=60)
        assert inst.past_time_to_run() is False

    def test_accepts_explicit_current_time(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime(2000, 1, 1)
        future_reference = datetime(2000, 1, 2)
        assert inst.past_time_to_run(future_reference) is True

    def test_none_processing_time_marks_error_and_returns_false(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = None
        assert inst.past_time_to_run() is False
        assert inst.state == RunStates.Error


# ---------------------------------------------------------------------------
# Instance.is_allowed_to_run
# ---------------------------------------------------------------------------

class TestIsAllowedToRun:
    def test_true_when_both_running(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        assert inst.is_allowed_to_run() is True

    def test_false_when_instance_paused(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.state = RunStates.Paused
        assert inst.is_allowed_to_run() is False

    def test_false_when_instance_error(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.state = RunStates.Error
        assert inst.is_allowed_to_run() is False

    def test_false_when_workflow_paused(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        wf.state = RunStates.Paused
        assert inst.is_allowed_to_run() is False

    def test_false_when_workflow_error(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        wf.state = RunStates.Error
        assert inst.is_allowed_to_run() is False

    def test_false_for_orphan_instance(self, mgr):
        inst = Instance(mgr.ctx)
        inst.uuid = "orphan"
        inst.workflow_uuid = "no-such-workflow"
        assert inst.is_allowed_to_run() is False


# ---------------------------------------------------------------------------
# PipelineManager.run_due_instances
# ---------------------------------------------------------------------------

class TestRunDueInstances:
    async def test_runs_due_instance(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() - timedelta(seconds=1)
        with patch.object(mgr, 'save_state'):
            await mgr.run_due_instances()
            assert inst.uuid in mgr._running_instance_tasks
            await wait_for_running_tasks(mgr)
        assert inst.state == RunStates.Paused  # pause_this_instance ran

    async def test_skips_future_instance(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() + timedelta(seconds=60)
        with patch.object(mgr, 'save_state'):
            await mgr.run_due_instances()
        assert mgr._running_instance_tasks == {}
        assert inst.state == RunStates.Running  # untouched

    async def test_skips_paused_instance(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() - timedelta(seconds=1)
        inst.state = RunStates.Paused
        with patch.object(mgr, 'save_state') as mock_save:
            await mgr.run_due_instances()
        mock_save.assert_not_called()
        assert mgr._running_instance_tasks == {}

    async def test_skips_instance_when_workflow_paused(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() - timedelta(seconds=1)
        wf.state = RunStates.Paused
        with patch.object(mgr, 'save_state') as mock_save:
            await mgr.run_due_instances()
        mock_save.assert_not_called()
        assert mgr._running_instance_tasks == {}
        assert inst.state == RunStates.Running  # untouched

    async def test_saves_state_when_instances_ran(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() - timedelta(seconds=1)
        with patch.object(mgr, 'save_state') as mock_save:
            await mgr.run_due_instances()
            await wait_for_running_tasks(mgr)
        mock_save.assert_called_once()

    async def test_does_not_save_state_when_nothing_ran(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() + timedelta(seconds=60)
        with patch.object(mgr, 'save_state') as mock_save:
            await mgr.run_due_instances()
        mock_save.assert_not_called()
        assert mgr._running_instance_tasks == {}

    async def test_runs_multiple_due_instances(self, mgr):
        wf = make_workflow(mgr)
        past = datetime.now() - timedelta(seconds=1)
        inst_a = wf.spawn_instance()
        inst_b = wf.spawn_instance()
        inst_a.next_processing_time = past
        inst_b.next_processing_time = past
        with patch.object(mgr, 'save_state'):
            await mgr.run_due_instances()
            assert set(mgr._running_instance_tasks) == {inst_a.uuid, inst_b.uuid}
            await wait_for_running_tasks(mgr)
        assert inst_a.state == RunStates.Paused
        assert inst_b.state == RunStates.Paused


# ---------------------------------------------------------------------------
# PipelineManager.get_next_due_time
# ---------------------------------------------------------------------------

class TestGetNextDueTime:
    def test_returns_none_when_no_instances(self, mgr):
        assert mgr.get_next_due_time() is None

    def test_returns_none_when_all_instances_paused(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.state = RunStates.Paused
        assert mgr.get_next_due_time() is None

    def test_returns_none_when_workflow_paused(self, mgr):
        wf = make_workflow(mgr)
        wf.spawn_instance()
        wf.state = RunStates.Paused
        assert mgr.get_next_due_time() is None

    def test_enforces_one_second_minimum_floor(self, mgr):
        wf = make_workflow(mgr)
        inst = wf.spawn_instance()
        inst.next_processing_time = datetime.now() - timedelta(seconds=10)
        result = mgr.get_next_due_time()
        assert result is not None
        assert result > datetime.now()

    def test_returns_soonest_of_multiple_instances(self, mgr):
        wf = make_workflow(mgr)
        soon = datetime.now() + timedelta(seconds=5)
        later = datetime.now() + timedelta(seconds=30)
        inst_a = wf.spawn_instance()
        inst_b = wf.spawn_instance()
        inst_a.next_processing_time = soon
        inst_b.next_processing_time = later
        result = mgr.get_next_due_time()
        assert result <= later
        assert result >= datetime.now()
