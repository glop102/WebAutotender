"""Tests for pipeline state save/load round-trips via PipelineManager."""
import os
import pytest
from datetime import datetime
from unittest.mock import patch

from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep
from pipeline_backend.variables import String, Integer, Float, VariablePath, Dictionary
from pipeline_backend.manager import PipelineManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_workflow(mgr, uuid, name="Test"):
    wf = Workflow(mgr.ctx)
    wf.uuid = uuid
    wf.name = name
    mgr.ctx.workflows[uuid] = wf
    return wf


def save_and_restore(mgr, tmp_path):
    """Save current state to a temp file, clear ctx, restore from file."""
    state_file = str(tmp_path / "state.json")
    mgr.save_state(state_file)
    mgr.ctx.workflows.clear()
    mgr.ctx.instances.clear()
    mgr.ctx.variables.clear()
    mgr.restore_state(state_file)


def save_and_restore_secrets(mgr, tmp_path):
    """Save current secrets to a temp file, clear, restore."""
    secrets_file = str(tmp_path / "secrets.json")
    mgr.save_secrets(secrets_file)
    mgr.ctx.secrets.clear()
    mgr.restore_secrets(secrets_file)


# ---------------------------------------------------------------------------
# Workflow persistence
# ---------------------------------------------------------------------------

class TestWorkflowPersistence:
    def test_workflow_name_and_uuid_survive(self, mgr, tmp_path):
        make_workflow(mgr, "wf-1", "My Workflow")
        save_and_restore(mgr, tmp_path)
        assert "wf-1" in mgr.ctx.workflows
        assert mgr.ctx.workflows["wf-1"].name == "My Workflow"

    def test_workflow_state_survives(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        wf.state = RunStates.Paused
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.workflows["wf-1"].state == RunStates.Paused

    def test_workflow_constants_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        wf.constants["limit"] = Integer(10)
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.workflows["wf-1"].constants["limit"].value == 10

    def test_workflow_setup_variables_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        wf.setup_variables["name"] = String("default")
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.workflows["wf-1"].setup_variables["name"].value == "default"

    def test_workflow_user_notes_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        wf.user_notes = "some notes"
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.workflows["wf-1"].user_notes == "some notes"

    def test_procedure_steps_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        wf.procedures["start"] = [
            ProcessingStep("log", msg=String("hello")),
            ProcessingStep("pause_this_instance"),
        ]
        save_and_restore(mgr, tmp_path)
        steps = mgr.ctx.workflows["wf-1"].procedures["start"]
        assert len(steps) == 2
        assert steps[0].command_name == "log"
        assert steps[0].variables["msg"].value == "hello"
        assert steps[1].command_name == "pause_this_instance"

    def test_multiple_workflows_survive(self, mgr, tmp_path):
        make_workflow(mgr, "wf-a", "Alpha")
        make_workflow(mgr, "wf-b", "Beta")
        save_and_restore(mgr, tmp_path)
        assert "wf-a" in mgr.ctx.workflows
        assert "wf-b" in mgr.ctx.workflows

    def test_empty_workflows_survive(self, mgr, tmp_path):
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.workflows == {}


# ---------------------------------------------------------------------------
# Instance persistence
# ---------------------------------------------------------------------------

class TestInstancePersistence:
    def test_instance_uuid_and_workflow_uuid_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        inst = wf.spawn_instance()
        uuid = inst.uuid
        save_and_restore(mgr, tmp_path)
        assert uuid in mgr.ctx.instances
        assert mgr.ctx.instances[uuid].workflow_uuid == "wf-1"

    def test_instance_state_survives(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        inst = wf.spawn_instance()
        inst.state = RunStates.Paused
        uuid = inst.uuid
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.instances[uuid].state == RunStates.Paused

    def test_instance_processing_step_survives(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        wf.procedures["other"] = []
        inst = wf.spawn_instance()
        inst.processing_step = ("other", 3)
        uuid = inst.uuid
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.instances[uuid].processing_step == ("other", 3)

    def test_instance_variables_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        inst = wf.spawn_instance()
        inst.variables["counter"] = Integer(7)
        uuid = inst.uuid
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.instances[uuid].variables["counter"].value == 7

    def test_instance_console_log_survives(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        inst = wf.spawn_instance()
        inst.console_log = "line 1\nline 2\n"
        uuid = inst.uuid
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.instances[uuid].console_log == "line 1\nline 2\n"

    def test_instance_next_processing_time_survives(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        inst = wf.spawn_instance()
        target = datetime(2030, 6, 15, 12, 0, 0)
        inst.next_processing_time = target
        uuid = inst.uuid
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.instances[uuid].next_processing_time == target

    def test_multiple_instances_survive(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1")
        a = wf.spawn_instance()
        b = wf.spawn_instance()
        save_and_restore(mgr, tmp_path)
        assert a.uuid in mgr.ctx.instances
        assert b.uuid in mgr.ctx.instances


# ---------------------------------------------------------------------------
# Global variable persistence
# ---------------------------------------------------------------------------

class TestGlobalVariablePersistence:
    def test_global_variable_survives(self, mgr, tmp_path):
        mgr.ctx.variables["g"] = String("global_val")
        save_and_restore(mgr, tmp_path)
        assert "g" in mgr.ctx.variables
        assert mgr.ctx.variables["g"].value == "global_val"

    def test_multiple_global_variables_survive(self, mgr, tmp_path):
        mgr.ctx.variables["a"] = Integer(1)
        mgr.ctx.variables["b"] = Float(2.5)
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.variables["a"].value == 1
        assert mgr.ctx.variables["b"].value == 2.5

    def test_empty_globals_survive(self, mgr, tmp_path):
        save_and_restore(mgr, tmp_path)
        assert mgr.ctx.variables == {}


# ---------------------------------------------------------------------------
# Secrets persistence
# ---------------------------------------------------------------------------

class TestSecretsPersistence:
    def test_secret_survives_roundtrip(self, mgr, tmp_path):
        mgr.ctx.secrets["api_key"] = String("secret123")
        save_and_restore_secrets(mgr, tmp_path)
        assert "api_key" in mgr.ctx.secrets
        assert mgr.ctx.secrets["api_key"].value == "secret123"

    def test_secrets_cleared_on_load(self, mgr, tmp_path):
        secrets_file = str(tmp_path / "secrets.json")
        mgr.ctx.secrets["old"] = String("old_val")
        mgr.save_secrets(secrets_file)          # save with only "old"
        mgr.ctx.secrets["extra"] = String("extra")
        mgr.ctx.secrets.clear()
        mgr.restore_secrets(secrets_file)       # restore — "extra" not saved
        assert "extra" not in mgr.ctx.secrets
        assert "old" in mgr.ctx.secrets

    def test_empty_secrets_survive(self, mgr, tmp_path):
        save_and_restore_secrets(mgr, tmp_path)
        assert mgr.ctx.secrets == {}


# ---------------------------------------------------------------------------
# Full pipeline state round-trip
# ---------------------------------------------------------------------------

class TestFullStateRoundtrip:
    def test_workflows_instances_and_globals_together(self, mgr, tmp_path):
        wf = make_workflow(mgr, "wf-1", "Full Test")
        wf.constants["max"] = Integer(5)
        wf.procedures["start"] = [ProcessingStep("log", msg=String("hi"))]
        inst = wf.spawn_instance()
        inst.variables["x"] = String("value")
        mgr.ctx.variables["shared"] = Float(3.14)
        uuid = inst.uuid

        save_and_restore(mgr, tmp_path)

        assert mgr.ctx.workflows["wf-1"].constants["max"].value == 5
        assert mgr.ctx.workflows["wf-1"].procedures["start"][0].command_name == "log"
        assert mgr.ctx.instances[uuid].variables["x"].value == "value"
        assert mgr.ctx.variables["shared"].value == 3.14

    def test_loaded_state_replaces_existing(self, mgr, tmp_path):
        state_file = str(tmp_path / "state.json")
        make_workflow(mgr, "wf-old", "Old")
        mgr.save_state(state_file)
        # Add something after saving
        make_workflow(mgr, "wf-new", "New")
        mgr.restore_state(state_file)
        assert "wf-old" in mgr.ctx.workflows
        assert "wf-new" not in mgr.ctx.workflows


# ---------------------------------------------------------------------------
# Atomic saves
# ---------------------------------------------------------------------------

class TestAtomicSaves:
    def test_save_state_replaces_existing_file(self, mgr, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("old contents")
        make_workflow(mgr, "wf-1", "Atomic")

        mgr.save_state(str(state_file))

        assert "old contents" not in state_file.read_text()
        assert not (tmp_path / "state.json.tmp").exists()

    def test_save_state_preserves_existing_file_if_replace_fails(self, mgr, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("old contents")
        make_workflow(mgr, "wf-1", "Atomic")

        with patch("pipeline_backend.manager.os.replace", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError):
                mgr.save_state(str(state_file))

        assert state_file.read_text() == "old contents"
        assert not (tmp_path / "state.json.tmp").exists()

    def test_save_secrets_uses_atomic_replace(self, mgr, tmp_path):
        secrets_file = tmp_path / "secrets.json"
        mgr.ctx.secrets["api_key"] = String("secret123")

        with patch("pipeline_backend.manager.os.replace", wraps=os.replace) as mock_replace:
            mgr.save_secrets(str(secrets_file))

        mock_replace.assert_called_once_with(str(secrets_file) + ".tmp", str(secrets_file))
        assert not (tmp_path / "secrets.json.tmp").exists()
