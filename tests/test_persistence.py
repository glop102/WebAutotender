"""Tests for pipeline state save/load round-trips."""
import pytest
from datetime import datetime

from pipeline_backend.persistence import (
    save_pipeline_global_state,
    load_pipeline_global_state,
    save_secrets_state,
    load_secrets_state,
)
from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep, global_workflows
from pipeline_backend.instances import Instance, global_instances
from pipeline_backend.variables import (
    String, Integer, Float, VariablePath, Dictionary,
    global_variables, global_secrets,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def roundtrip(extra_setup=None):
    """Save current global state to JSON and reload it."""
    state = save_pipeline_global_state()
    global_workflows.clear()
    global_instances.clear()
    global_variables.clear()
    load_pipeline_global_state(state)


def make_workflow(uuid, name="Test"):
    wf = Workflow()
    wf.uuid = uuid
    wf.name = name
    global_workflows[uuid] = wf
    return wf


# ---------------------------------------------------------------------------
# Workflow persistence
# ---------------------------------------------------------------------------

class TestWorkflowPersistence:
    def test_workflow_name_and_uuid_survive(self):
        make_workflow("wf-1", "My Workflow")
        roundtrip()
        assert "wf-1" in global_workflows
        assert global_workflows["wf-1"].name == "My Workflow"

    def test_workflow_state_survives(self):
        wf = make_workflow("wf-1")
        wf.state = RunStates.Paused
        roundtrip()
        assert global_workflows["wf-1"].state == RunStates.Paused

    def test_workflow_constants_survive(self):
        wf = make_workflow("wf-1")
        wf.constants["limit"] = Integer(10)
        roundtrip()
        assert global_workflows["wf-1"].constants["limit"].value == 10

    def test_workflow_setup_variables_survive(self):
        wf = make_workflow("wf-1")
        wf.setup_variables["name"] = String("default")
        roundtrip()
        assert global_workflows["wf-1"].setup_variables["name"].value == "default"

    def test_workflow_user_notes_survive(self):
        wf = make_workflow("wf-1")
        wf.user_notes = "some notes"
        roundtrip()
        assert global_workflows["wf-1"].user_notes == "some notes"

    def test_procedure_steps_survive(self):
        wf = make_workflow("wf-1")
        wf.procedures["start"] = [
            ProcessingStep("log", msg=String("hello")),
            ProcessingStep("pause_this_instance"),
        ]
        roundtrip()
        steps = global_workflows["wf-1"].procedures["start"]
        assert len(steps) == 2
        assert steps[0].command_name == "log"
        assert steps[0].variables["msg"].value == "hello"
        assert steps[1].command_name == "pause_this_instance"

    def test_multiple_workflows_survive(self):
        make_workflow("wf-a", "Alpha")
        make_workflow("wf-b", "Beta")
        roundtrip()
        assert "wf-a" in global_workflows
        assert "wf-b" in global_workflows

    def test_empty_workflows_survive(self):
        roundtrip()
        assert global_workflows == {}


# ---------------------------------------------------------------------------
# Instance persistence
# ---------------------------------------------------------------------------

class TestInstancePersistence:
    def test_instance_uuid_and_workflow_uuid_survive(self):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        uuid = inst.uuid
        roundtrip()
        assert uuid in global_instances
        assert global_instances[uuid].workflow_uuid == "wf-1"

    def test_instance_state_survives(self):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        inst.state = RunStates.Paused
        uuid = inst.uuid
        roundtrip()
        assert global_instances[uuid].state == RunStates.Paused

    def test_instance_processing_step_survives(self):
        wf = make_workflow("wf-1")
        wf.procedures["other"] = []
        inst = wf.spawn_instance()
        inst.processing_step = ("other", 3)
        uuid = inst.uuid
        roundtrip()
        assert global_instances[uuid].processing_step == ("other", 3)

    def test_instance_variables_survive(self):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        inst.variables["counter"] = Integer(7)
        uuid = inst.uuid
        roundtrip()
        assert global_instances[uuid].variables["counter"].value == 7

    def test_instance_console_log_survives(self):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        inst.console_log = "line 1\nline 2\n"
        uuid = inst.uuid
        roundtrip()
        assert global_instances[uuid].console_log == "line 1\nline 2\n"

    def test_instance_next_processing_time_survives(self):
        wf = make_workflow("wf-1")
        inst = wf.spawn_instance()
        target = datetime(2030, 6, 15, 12, 0, 0)
        inst.next_processing_time = target
        uuid = inst.uuid
        roundtrip()
        assert global_instances[uuid].next_processing_time == target

    def test_multiple_instances_survive(self):
        wf = make_workflow("wf-1")
        a = wf.spawn_instance()
        b = wf.spawn_instance()
        roundtrip()
        assert a.uuid in global_instances
        assert b.uuid in global_instances


# ---------------------------------------------------------------------------
# Global variable persistence
# ---------------------------------------------------------------------------

class TestGlobalVariablePersistence:
    def test_global_variable_survives(self):
        global_variables["g"] = String("global_val")
        roundtrip()
        assert "g" in global_variables
        assert global_variables["g"].value == "global_val"

    def test_multiple_global_variables_survive(self):
        global_variables["a"] = Integer(1)
        global_variables["b"] = Float(2.5)
        roundtrip()
        assert global_variables["a"].value == 1
        assert global_variables["b"].value == 2.5

    def test_empty_globals_survive(self):
        roundtrip()
        assert global_variables == {}


# ---------------------------------------------------------------------------
# Secrets persistence
# ---------------------------------------------------------------------------

class TestSecretsPersistence:
    def test_secret_survives_roundtrip(self):
        global_secrets["api_key"] = String("secret123")
        state = save_secrets_state()
        global_secrets.clear()
        load_secrets_state(state)
        assert "api_key" in global_secrets
        assert global_secrets["api_key"].value == "secret123"

    def test_secrets_cleared_on_load(self):
        global_secrets["old"] = String("old_val")
        new_state = save_secrets_state()  # save with "old"
        global_secrets["extra"] = String("extra")
        load_secrets_state(new_state)  # reload — "extra" should be gone
        assert "extra" not in global_secrets
        assert "old" in global_secrets

    def test_empty_secrets_survive(self):
        state = save_secrets_state()
        load_secrets_state(state)
        assert global_secrets == {}


# ---------------------------------------------------------------------------
# Full pipeline state round-trip
# ---------------------------------------------------------------------------

class TestFullStateRoundtrip:
    def test_workflows_instances_and_globals_together(self):
        wf = make_workflow("wf-1", "Full Test")
        wf.constants["max"] = Integer(5)
        wf.procedures["start"] = [ProcessingStep("log", msg=String("hi"))]
        inst = wf.spawn_instance()
        inst.variables["x"] = String("value")
        global_variables["shared"] = Float(3.14)
        uuid = inst.uuid

        roundtrip()

        assert global_workflows["wf-1"].constants["max"].value == 5
        assert global_workflows["wf-1"].procedures["start"][0].command_name == "log"
        assert global_instances[uuid].variables["x"].value == "value"
        assert global_variables["shared"].value == 3.14

    def test_loaded_state_replaces_existing(self):
        make_workflow("wf-old", "Old")
        state = save_pipeline_global_state()
        # Add something after saving
        make_workflow("wf-new", "New")
        load_pipeline_global_state(state)
        assert "wf-old" in global_workflows
        assert "wf-new" not in global_workflows
