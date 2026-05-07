import pytest
from datetime import datetime, timedelta
from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.commands_builtin import (
    log, error,
    set_variable_value, set_variable_value_in_another_instance, save_uuid_to_variables,
    math_add, math_subtract, math_multiply, math_divide,
    jump_to_procedure, goto_if_equal, goto_if_not_equal, goto_if_first_larger,
    yield_for_seconds, yield_for_minutes,
    pause_this_instance, delete_this_instance, make_new_instance,
    regex_first_match, regex_match_all,
)
from pipeline_backend.workflows import Workflow, RunStates, global_workflows
from pipeline_backend.instances import Instance, global_instances
from pipeline_backend.variables import String, Integer, Float, VariableName, StringList, Dictionary


@pytest.fixture
def workflow():
    wf = Workflow()
    wf.uuid = "wf-cmd-test"
    wf.name = "Command Test"
    global_workflows[wf.uuid] = wf
    return wf


@pytest.fixture
def instance(workflow):
    return workflow.spawn_instance()


class TestLog:
    def test_returns_success(self, instance):
        assert log(instance, String("hello")) == CommandReturnStatus.Success

    def test_appends_to_console_log(self, instance):
        log(instance, String("test message"))
        assert "test message" in instance.console_log

    def test_multiple_calls_accumulate(self, instance):
        log(instance, String("line 1"))
        log(instance, String("line 2"))
        assert "line 1" in instance.console_log
        assert "line 2" in instance.console_log


class TestError:
    def test_returns_error_status(self, instance):
        assert error(instance, String("bad")) == CommandReturnStatus.Error

    def test_appends_to_console_log(self, instance):
        error(instance, String("something went wrong"))
        assert "something went wrong" in instance.console_log


class TestSetVariableValue:
    def test_sets_instance_variable(self, instance):
        result = set_variable_value(instance, VariableName("x"), Integer(42))
        assert result == CommandReturnStatus.Success
        assert instance.variables["x"].value == 42

    def test_overwrites_existing_variable(self, instance):
        instance.variables["x"] = String("old")
        set_variable_value(instance, VariableName("x"), String("new"))
        assert instance.variables["x"].value == "new"

    def test_set_in_another_instance(self, workflow, instance):
        other = workflow.spawn_instance()
        result = set_variable_value_in_another_instance(
            instance, String(other.uuid), VariableName("shared"), Integer(99)
        )
        assert result == CommandReturnStatus.Success
        assert other.variables["shared"].value == 99

    def test_set_in_nonexistent_instance_errors(self, instance):
        result = set_variable_value_in_another_instance(
            instance, String("no-such-uuid"), VariableName("x"), Integer(1)
        )
        assert result == CommandReturnStatus.Error

    def test_save_uuid_stores_uuid_string(self, instance):
        result = save_uuid_to_variables(instance)
        assert result == CommandReturnStatus.Success
        assert instance.variables["uuid"].value == instance.uuid


class TestMath:
    def test_add_integers(self, instance):
        instance.variables["r"] = Integer(0)
        math_add(instance, Integer(3), Integer(4), VariableName("r"))
        assert instance.variables["r"].value == 7

    def test_subtract_integers(self, instance):
        instance.variables["r"] = Integer(0)
        math_subtract(instance, Integer(10), Integer(4), VariableName("r"))
        assert instance.variables["r"].value == 6

    def test_multiply_integers(self, instance):
        instance.variables["r"] = Integer(0)
        math_multiply(instance, Integer(3), Integer(4), VariableName("r"))
        assert instance.variables["r"].value == 12

    def test_divide_floats(self, instance):
        instance.variables["r"] = Float(0.0)
        math_divide(instance, Float(10.0), Float(4.0), VariableName("r"))
        assert instance.variables["r"].value == 2.5

    def test_add_floats(self, instance):
        instance.variables["r"] = Float(0.0)
        math_add(instance, Float(1.5), Float(2.5), VariableName("r"))
        assert instance.variables["r"].value == 4.0

    def test_all_math_return_success(self, instance):
        instance.variables["r"] = Integer(0)
        assert math_add(instance, Integer(1), Integer(1), VariableName("r")) == CommandReturnStatus.Success
        assert math_subtract(instance, Integer(1), Integer(1), VariableName("r")) == CommandReturnStatus.Success
        assert math_multiply(instance, Integer(1), Integer(1), VariableName("r")) == CommandReturnStatus.Success
        assert math_divide(instance, Float(1.0), Float(1.0), VariableName("r")) == CommandReturnStatus.Success


class TestControlFlow:
    def test_jump_to_procedure_changes_processing_step(self, workflow, instance):
        workflow.procedures["other"] = []
        result = jump_to_procedure(instance, String("other"))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert instance.processing_step == ("other", 0)

    def test_jump_to_nonexistent_procedure_errors(self, instance):
        result = jump_to_procedure(instance, String("nonexistent"))
        assert result == CommandReturnStatus.Error

    def test_goto_if_equal_jumps_when_equal(self, workflow, instance):
        workflow.procedures["target"] = []
        result = goto_if_equal(instance, String("target"), Integer(5), Integer(5))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert instance.processing_step == ("target", 0)

    def test_goto_if_equal_continues_when_not_equal(self, instance):
        result = goto_if_equal(instance, String("target"), Integer(5), Integer(6))
        assert result == CommandReturnStatus.Success
        assert instance.processing_step == ("start", 0)

    def test_goto_if_equal_string_comparison(self, workflow, instance):
        workflow.procedures["target"] = []
        result = goto_if_equal(instance, String("target"), String("abc"), String("abc"))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position

    def test_goto_if_equal_deref_variable_name(self, workflow, instance):
        workflow.procedures["target"] = []
        instance.variables["val"] = Integer(7)
        goto_if_equal(instance, String("target"), VariableName("val"), Integer(7))
        assert instance.processing_step == ("target", 0)

    def test_goto_if_not_equal_jumps_when_not_equal(self, workflow, instance):
        workflow.procedures["target"] = []
        result = goto_if_not_equal(instance, String("target"), Integer(3), Integer(5))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position

    def test_goto_if_not_equal_continues_when_equal(self, instance):
        result = goto_if_not_equal(instance, String("target"), Integer(5), Integer(5))
        assert result == CommandReturnStatus.Success
        assert instance.processing_step == ("start", 0)

    def test_goto_if_first_larger_jumps_when_larger(self, workflow, instance):
        workflow.procedures["target"] = []
        result = goto_if_first_larger(instance, String("target"), Integer(10), Integer(5))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert instance.processing_step == ("target", 0)

    def test_goto_if_first_larger_continues_when_smaller(self, instance):
        result = goto_if_first_larger(instance, String("target"), Integer(3), Integer(5))
        assert result == CommandReturnStatus.Success
        assert instance.processing_step == ("start", 0)

    def test_goto_if_first_larger_continues_when_equal(self, instance):
        result = goto_if_first_larger(instance, String("target"), Integer(5), Integer(5))
        assert result == CommandReturnStatus.Success


class TestYield:
    def test_yield_for_seconds_returns_yield(self, instance):
        before = datetime.now()
        result = yield_for_seconds(instance, Integer(30))
        assert result == CommandReturnStatus.Yield
        assert instance.next_processing_time > before + timedelta(seconds=29)

    def test_yield_for_minutes_returns_yield(self, instance):
        before = datetime.now()
        result = yield_for_minutes(instance, Integer(5))
        assert result == CommandReturnStatus.Yield
        assert instance.next_processing_time > before + timedelta(minutes=4)

    def test_yield_for_seconds_accepts_float(self, instance):
        result = yield_for_seconds(instance, Float(1.5))
        assert result == CommandReturnStatus.Yield


class TestInstanceLifecycle:
    def test_pause_sets_paused_state(self, instance):
        result = pause_this_instance(instance)
        assert result == CommandReturnStatus.Yield
        assert instance.state == RunStates.Paused

    def test_delete_removes_from_global_instances(self, instance):
        uuid = instance.uuid
        assert uuid in global_instances
        result = delete_this_instance(instance)
        assert result == CommandReturnStatus.Yield
        assert uuid not in global_instances

    def test_delete_orphan_not_in_global_returns_error(self):
        inst = Instance()
        inst.uuid = "orphan-not-registered"
        result = delete_this_instance(inst)
        assert result == CommandReturnStatus.Error


class TestMakeNewInstance:
    def test_spawns_instance_in_target_workflow(self, workflow, instance):
        target = Workflow()
        target.uuid = "target-wf"
        target.name = "Target"
        global_workflows[target.uuid] = target

        result = make_new_instance(instance, String("target-wf"), Dictionary({}))
        assert result == CommandReturnStatus.Success
        spawned = [i for i in global_instances.values() if i.workflow_uuid == "target-wf"]
        assert len(spawned) == 1

    def test_passes_setup_vars_to_new_instance(self, workflow, instance):
        target = Workflow()
        target.uuid = "target-wf2"
        target.name = "Target"
        target.setup_variables["name"] = String("default")
        global_workflows[target.uuid] = target

        make_new_instance(instance, String("target-wf2"), Dictionary({"name": String("custom")}))
        spawned = [i for i in global_instances.values() if i.workflow_uuid == "target-wf2"]
        assert len(spawned) == 1
        assert spawned[0].variables["name"].value == "custom"

    def test_nonexistent_workflow_uuid_returns_error(self, instance):
        result = make_new_instance(instance, String("no-such-uuid"), Dictionary({}))
        assert result == CommandReturnStatus.Error


class TestRegex:
    def test_first_match_returns_success(self, instance):
        result = regex_first_match(instance, String(r"\d+"), String("abc 123 def"), VariableName("out"))
        assert result == CommandReturnStatus.Success
        assert instance.variables["out"].value == "123"

    def test_first_match_no_match_returns_error(self, instance):
        result = regex_first_match(instance, String(r"\d+"), String("no digits here"), VariableName("out"))
        assert result == CommandReturnStatus.Error

    def test_match_all_returns_list(self, instance):
        result = regex_match_all(instance, String(r"\d+"), String("1 and 2 and 3"), VariableName("out"))
        assert result == CommandReturnStatus.Success
        assert isinstance(instance.variables["out"], StringList)
        assert instance.variables["out"].value == ["1", "2", "3"]

    def test_match_all_no_matches_returns_empty_list(self, instance):
        result = regex_match_all(instance, String(r"\d+"), String("no digits"), VariableName("out"))
        assert result == CommandReturnStatus.Success
        assert instance.variables["out"].value == []
