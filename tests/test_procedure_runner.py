import pytest
from pipeline_backend.procedure_runner import ProcedureRunner
from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep, global_workflows
from pipeline_backend.instances import Instance
from pipeline_backend.variables import String, Integer, Float, VariablePath


@pytest.fixture
def workflow():
    wf = Workflow()
    wf.uuid = "wf-runner-test"
    wf.name = "Runner Test"
    global_workflows[wf.uuid] = wf
    return wf


class TestStepAdvancement:
    async def test_success_advances_step(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("log", msg=String("first")),
            ProcessingStep("log", msg=String("second")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result == CommandReturnStatus.Success
        assert inst.processing_step == ("start", 1)

    async def test_yield_stops_loop(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("yield_for_seconds", num_seconds=Integer(60)),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state != RunStates.Error  # stopped for yield, not error
        assert inst.processing_step == ("start", 1)

    async def test_keep_position_does_not_advance_step(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("jump_to_procedure", procedure_name=String("start")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result == CommandReturnStatus.Success
        assert inst.processing_step == ("start", 0)

    async def test_jump_to_other_procedure_changes_proc_and_step(self, workflow):
        workflow.procedures["other"] = []
        workflow.procedures["start"] = [
            ProcessingStep("jump_to_procedure", procedure_name=String("other")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        await runner.run_single_step()
        assert inst.processing_step == ("other", 0)


class TestErrorConditions:
    # Note: run_single_step returns (command_finish_state & Success), so errors
    # produce != Success rather than == Error. Instance state carries the Error.

    async def test_missing_procedure_marks_error(self, workflow):
        inst = workflow.spawn_instance()
        inst.processing_step = ("nonexistent_proc", 0)
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_out_of_bounds_step_marks_error(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("log", msg=String("only step")),
        ]
        inst = workflow.spawn_instance()
        inst.processing_step = ("start", 99)
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_unknown_command_marks_error(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("no_such_command_exists"),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_empty_command_name_marks_error(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep(),  # command_name defaults to ""
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_wrong_arg_count_marks_error(self, workflow):
        # log expects one arg (msg), passing none
        workflow.procedures["start"] = [
            ProcessingStep("log"),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_orphan_instance_marks_error(self):
        inst = Instance()
        inst.uuid = "orphan"
        inst.workflow_uuid = "workflow-that-does-not-exist"
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_error_command_marks_instance_error(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("error", msg=String("deliberate error")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error


class TestMathEdgeCases:
    async def test_division_by_zero_marks_error(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("math_divide",
                           first=Float(1.0),
                           second=Float(0.0),
                           output_variable=VariablePath("r")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_string_arg_to_math_add_marks_error(self, workflow):
        # String cannot be coerced to Integer|Float, runner should reject it
        workflow.procedures["start"] = [
            ProcessingStep("math_add",
                           first=String("a"),
                           second=String("b"),
                           output_variable=VariablePath("r")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error


class TestVariableResolution:
    async def test_variablename_dereferenced_from_instance(self, workflow):
        workflow.procedures["start"] = [
            ProcessingStep("log", msg=VariablePath("my_msg")),
        ]
        inst = workflow.spawn_instance()
        inst.variables["my_msg"] = String("dereffed message")
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result == CommandReturnStatus.Success
        assert "dereffed message" in inst.console_log

    async def test_variablename_derefs_from_workflow_constant(self, workflow):
        workflow.constants["greeting"] = String("hello from constant")
        workflow.procedures["start"] = [
            ProcessingStep("log", msg=VariablePath("greeting")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result == CommandReturnStatus.Success
        assert "hello from constant" in inst.console_log

    async def test_integer_passes_as_integer_or_float(self, workflow):
        # yield_for_seconds accepts Integer|Float — Integer should pass directly
        workflow.procedures["start"] = [
            ProcessingStep("yield_for_seconds", num_seconds=Integer(1)),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        await runner.run_single_step()
        assert inst.state != RunStates.Error

    async def test_successful_coercion_passes_arg_to_command(self, workflow):
        # log expects String; Integer(42) should coerce to String("42") and succeed
        workflow.procedures["start"] = [
            ProcessingStep("log", msg=Integer(42)),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result == CommandReturnStatus.Success
        assert "42" in inst.console_log

    async def test_incompatible_type_marks_error(self, workflow):
        # yield_for_seconds needs Integer|Float; String("abc") cannot be coerced
        workflow.procedures["start"] = [
            ProcessingStep("yield_for_seconds", num_seconds=String("not a number")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error

    async def test_missing_variable_name_marks_error(self, workflow):
        # VariablePath pointing to a var that doesn't exist anywhere
        workflow.procedures["start"] = [
            ProcessingStep("log", msg=VariablePath("does_not_exist")),
        ]
        inst = workflow.spawn_instance()
        runner = ProcedureRunner(inst)
        result = await runner.run_single_step()
        assert result != CommandReturnStatus.Success
        assert inst.state == RunStates.Error
