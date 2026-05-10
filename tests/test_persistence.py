"""Tests for pipeline state save/load round-trips via PipelineManager."""
import pytest
from datetime import datetime

from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep
from pipeline_backend.variables import String, Integer, Float, VariablePath, Dictionary
from pipeline_backend.manager import pipelineManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_workflow(uuid, name="Test"):
    wf = Workflow(pipelineManager.ctx)
    wf.uuid = uuid
    wf.name = name
    pipelineManager.ctx.workflows[uuid] = wf
    return wf


def save_and_restore(tmp_path):
    """Save current state to a temp file, clear ctx, restore from file."""
    state_file = str(tmp_path / "state.json")
    pipelineManager.save_state(state_file)
    pipelineManager.ctx.workflows.clear()
    pipelineManager.ctx.instances.clear()
    pipelineManager.ctx.variables.clear()
    pipelineManager.restore_state(state_file)


def save_and_restore_secrets(tmp_path):
    """Save current secrets to a temp file, clear, restore."""
    secrets_file = str(tmp_path / "secrets.json")
    pipelineManager.save_secrets(secrets_file)
    pipelineManager.ctx.secrets.clear()
    pipelineManager.restore_secrets(secrets_file)


# ---------------------------------------------------------------------------
# Workflow persistence
# ---------------------------------------------------------------------------

class TestWorkflowPersistence:
    def test_workflow_name_and_uuid_survive(self, tmp_path):
        make_workflow("wf-1", "My Workflow")
        save_and_restore(tmp_path)
        assert "wf-1" in pipelineManager.ctx.workflows
        assert pipelineManager.ctx.workflows["wf-1"].name == "My Workflow"

    def test_workflow_state_survives(self, tmp_path):
        wf = make_workflow("wf-1")
        wf.state = RunStates.Paused
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.workflows["wf-1"].state == RunStates.Paused

    def test_workflow_constants_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        wf.constants["limit"] = Integer(10)
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.workflows["wf-1"].constants["limit"].value == 10

    def test_workflow_setup_variables_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        wf.setup_variables["name"] = String("default")
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.workflows["wf-1"].setup_variables["name"].value == "default"

    def test_workflow_user_notes_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        wf.user_notes = "some notes"
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.workflows["wf-1"].user_notes == "some notes"

    def test_procedure_steps_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        wf.procedures["start"] = [
            ProcessingStep("log", msg=String("hello")),
            ProcessingStep("pause_this_instance"),
        ]
        save_and_restore(tmp_path)
        steps = pipelineManager.ctx.workflows["wf-1"].procedures["start"]
        assert len(steps) == 2
        assert steps[0].command_name == "log"
        assert steps[0].variables["msg"].value == "hello"
        assert steps[1].command_name == "pause_this_instance"

    def test_multiple_workflows_survive(self, tmp_path):
        make_workflow("wf-a", "Alpha")
        make_workflow("wf-b", "Beta")
        save_and_restore(tmp_path)
        assert "wf-a" in pipelineManager.ctx.workflows
        assert "wf-b" in pipelineManager.ctx.workflows

    def test_empty_workflows_survive(self, tmp_path):
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.workflows == {}


# ---------------------------------------------------------------------------
# Instance persistence
# ---------------------------------------------------------------------------

class TestInstancePersistence:
    def test_instance_uuid_and_workflow_uuid_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        uuid = inst.uuid
        save_and_restore(tmp_path)
        assert uuid in pipelineManager.ctx.instances
        assert pipelineManager.ctx.instances[uuid].workflow_uuid == "wf-1"

    def test_instance_state_survives(self, tmp_path):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        inst.state = RunStates.Paused
        uuid = inst.uuid
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.instances[uuid].state == RunStates.Paused

    def test_instance_processing_step_survives(self, tmp_path):
        wf = make_workflow("wf-1")
        wf.procedures["other"] = []
        inst = wf.spawn_instance()
        inst.processing_step = ("other", 3)
        uuid = inst.uuid
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.instances[uuid].processing_step == ("other", 3)

    def test_instance_variables_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        inst.variables["counter"] = Integer(7)
        uuid = inst.uuid
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.instances[uuid].variables["counter"].value == 7

    def test_instance_console_log_survives(self, tmp_path):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        inst.console_log = "line 1\nline 2\n"
        uuid = inst.uuid
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.instances[uuid].console_log == "line 1\nline 2\n"

    def test_instance_next_processing_time_survives(self, tmp_path):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        target = datetime(2030, 6, 15, 12, 0, 0)
        inst.next_processing_time = target
        uuid = inst.uuid
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.instances[uuid].next_processing_time == target

    def test_multiple_instances_survive(self, tmp_path):
        wf = make_workflow("wf-1")
        a = wf.spawn_instance()
        b = wf.spawn_instance()
        save_and_restore(tmp_path)
        assert a.uuid in pipelineManager.ctx.instances
        assert b.uuid in pipelineManager.ctx.instances


# ---------------------------------------------------------------------------
# Global variable persistence
# ---------------------------------------------------------------------------

class TestGlobalVariablePersistence:
    def test_global_variable_survives(self, tmp_path):
        pipelineManager.ctx.variables["g"] = String("global_val")
        save_and_restore(tmp_path)
        assert "g" in pipelineManager.ctx.variables
        assert pipelineManager.ctx.variables["g"].value == "global_val"

    def test_multiple_global_variables_survive(self, tmp_path):
        pipelineManager.ctx.variables["a"] = Integer(1)
        pipelineManager.ctx.variables["b"] = Float(2.5)
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.variables["a"].value == 1
        assert pipelineManager.ctx.variables["b"].value == 2.5

    def test_empty_globals_survive(self, tmp_path):
        save_and_restore(tmp_path)
        assert pipelineManager.ctx.variables == {}


# ---------------------------------------------------------------------------
# Secrets persistence
# ---------------------------------------------------------------------------

class TestSecretsPersistence:
    def test_secret_survives_roundtrip(self, tmp_path):
        pipelineManager.ctx.secrets["api_key"] = String("secret123")
        save_and_restore_secrets(tmp_path)
        assert "api_key" in pipelineManager.ctx.secrets
        assert pipelineManager.ctx.secrets["api_key"].value == "secret123"

    def test_secrets_cleared_on_load(self, tmp_path):
        secrets_file = str(tmp_path / "secrets.json")
        pipelineManager.ctx.secrets["old"] = String("old_val")
        pipelineManager.save_secrets(secrets_file)          # save with only "old"
        pipelineManager.ctx.secrets["extra"] = String("extra")
        pipelineManager.ctx.secrets.clear()
        pipelineManager.restore_secrets(secrets_file)       # restore — "extra" not saved
        assert "extra" not in pipelineManager.ctx.secrets
        assert "old" in pipelineManager.ctx.secrets

    def test_empty_secrets_survive(self, tmp_path):
        save_and_restore_secrets(tmp_path)
        assert pipelineManager.ctx.secrets == {}


# ---------------------------------------------------------------------------
# Full pipeline state round-trip
# ---------------------------------------------------------------------------

class TestFullStateRoundtrip:
    def test_workflows_instances_and_globals_together(self, tmp_path):
        wf = make_workflow("wf-1", "Full Test")
        wf.constants["max"] = Integer(5)
        wf.procedures["start"] = [ProcessingStep("log", msg=String("hi"))]
        inst = wf.spawn_instance()
        inst.variables["x"] = String("value")
        pipelineManager.ctx.variables["shared"] = Float(3.14)
        uuid = inst.uuid

        save_and_restore(tmp_path)

        assert pipelineManager.ctx.workflows["wf-1"].constants["max"].value == 5
        assert pipelineManager.ctx.workflows["wf-1"].procedures["start"][0].command_name == "log"
        assert pipelineManager.ctx.instances[uuid].variables["x"].value == "value"
        assert pipelineManager.ctx.variables["shared"].value == 3.14

    def test_loaded_state_replaces_existing(self, tmp_path):
        state_file = str(tmp_path / "state.json")
        make_workflow("wf-old", "Old")
        pipelineManager.save_state(state_file)
        # Add something after saving
        make_workflow("wf-new", "New")
        pipelineManager.restore_state(state_file)
        assert "wf-old" in pipelineManager.ctx.workflows
        assert "wf-new" not in pipelineManager.ctx.workflows
