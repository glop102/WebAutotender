"""Integration tests: run complete workflows end-to-end through ProcedureRunner."""
import asyncio
import pytest
from pipeline_backend.procedure_runner import ProcedureRunner
from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep
from pipeline_backend.variables import String, Integer, Float, VariablePath, VariableNameList, Dictionary, VariableList, StringList
from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.commands_builtin import list_pop_next
from pipeline_backend.manager import PipelineManager
from builtin_addons.string_operations import str_regex_matchAll


@pytest.fixture
def loop_workflow(mgr):
    """Counts from 0 up to max_count (3), logging each iteration, then pauses."""
    wf = Workflow(mgr.ctx)
    wf.uuid = "loop-wf"
    wf.name = "Loop Test"
    wf.constants["max_count"] = Integer(3)
    wf.setup_variables["counter"] = Integer(0)

    wf.procedures["start"] = [
        ProcessingStep("set_variable_value",
                       variable_name=VariablePath("counter"),
                       value=Integer(0)),
        ProcessingStep("jump_to_procedure",
                       procedure_name=String("main_loop")),
    ]
    wf.procedures["main_loop"] = [
        ProcessingStep("goto_if_equal",
                       procedure_name=String("done"),
                       value1=VariablePath("counter"),
                       value2=VariablePath("max_count")),
        ProcessingStep("log",
                       msg=String("looping")),
        ProcessingStep("math_add",
                       first=VariablePath("counter"),
                       second=Integer(1),
                       output_variable=VariablePath("counter")),
        ProcessingStep("jump_to_procedure",
                       procedure_name=String("main_loop")),
    ]
    wf.procedures["done"] = [
        ProcessingStep("log",
                       msg=String("done")),
        ProcessingStep("pause_this_instance"),
    ]
    mgr.ctx.workflows[wf.uuid] = wf
    return wf


class TestLoopWorkflow:
    async def test_loop_runs_correct_number_of_iterations(self, loop_workflow):
        inst = loop_workflow.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.console_log.count("looping") == 3

    async def test_loop_counter_reaches_max(self, loop_workflow):
        inst = loop_workflow.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.variables["counter"].value == 3

    async def test_loop_reaches_done_procedure(self, loop_workflow):
        inst = loop_workflow.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert "done" in inst.console_log

    async def test_loop_ends_paused_not_error(self, loop_workflow):
        inst = loop_workflow.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.state == RunStates.Paused

    async def test_loop_instance_stays_in_global_instances(self, mgr, loop_workflow):
        inst = loop_workflow.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.uuid in mgr.ctx.instances

    async def test_loop_with_different_max(self, loop_workflow):
        loop_workflow.constants["max_count"] = Integer(5)
        inst = loop_workflow.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.variables["counter"].value == 5
        assert inst.console_log.count("looping") == 5


class TestMultipleYields:
    async def test_instance_resumes_correctly_across_multiple_yields(self, mgr):
        """run_instance_until_yield stops at each yield; successive calls
        advance the instance through each yield point in order."""
        wf = Workflow(mgr.ctx)
        wf.uuid = "multi-yield-wf"
        wf.name = "Multi Yield"
        wf.procedures["start"] = [
            ProcessingStep("log", msg=String("step1")),
            ProcessingStep("yield_for_seconds", num_seconds=Integer(0)),
            ProcessingStep("log", msg=String("step2")),
            ProcessingStep("yield_for_seconds", num_seconds=Integer(0)),
            ProcessingStep("log", msg=String("step3")),
            ProcessingStep("pause_this_instance"),
        ]
        mgr.ctx.workflows[wf.uuid] = wf
        inst = wf.spawn_instance()
        runner = ProcedureRunner(inst)

        await runner.run_instance_until_yield()
        assert "step1" in inst.console_log
        assert "step2" not in inst.console_log
        assert inst.processing_step == ("start", 2)

        await runner.run_instance_until_yield()
        assert "step2" in inst.console_log
        assert "step3" not in inst.console_log
        assert inst.processing_step == ("start", 4)

        await runner.run_instance_until_yield()
        assert "step3" in inst.console_log
        assert inst.state == RunStates.Paused


class TestSelfDeletingWorkflow:
    async def test_instance_deletes_itself_on_completion(self, mgr, loop_workflow):
        loop_workflow.procedures["done"] = [
            ProcessingStep("delete_this_instance"),
        ]
        inst = loop_workflow.spawn_instance()
        uuid = inst.uuid
        await ProcedureRunner(inst).run_instance_until_yield()

        assert uuid not in mgr.ctx.instances


class TestSpawnChainWorkflow:
    async def test_instance_spawns_child_instance(self, mgr):
        """A workflow that immediately spawns one instance of another workflow."""
        child_wf = Workflow(mgr.ctx)
        child_wf.uuid = "child-wf"
        child_wf.name = "Child"
        child_wf.procedures["start"] = []
        mgr.ctx.workflows[child_wf.uuid] = child_wf

        parent_wf = Workflow(mgr.ctx)
        parent_wf.uuid = "parent-wf"
        parent_wf.name = "Parent"
        parent_wf.procedures["start"] = [
            ProcessingStep("make_new_instance",
                           workflow_uuid=String("child-wf"),
                           setup_vars=Dictionary({}),
                           do_not_deref=VariableNameList([])),
            ProcessingStep("pause_this_instance"),
        ]
        mgr.ctx.workflows[parent_wf.uuid] = parent_wf

        parent_inst = parent_wf.spawn_instance()
        await ProcedureRunner(parent_inst).run_instance_until_yield()

        child_instances = [i for i in mgr.ctx.instances.values() if i.workflow_uuid == "child-wf"]
        assert len(child_instances) == 1


class TestDotNotationWorkflowScenario:
    """Exercises list_pop_next + dot-notation output paths in a realistic workflow scenario."""

    def _make_workflow(self, mgr):
        wf = Workflow(mgr.ctx)
        wf.uuid = "dot-notation-scenario-wf"
        wf.name = "Dot Notation Scenario"
        wf.constants["strings_to_match"] = VariableList([
            String("abc 42 def 99"),
            String("hello 7 world 13"),
        ])
        wf.constants["dict"] = Dictionary({
            "matches1": StringList([]),
            "matches2": StringList([]),
        })
        wf.procedures["start"] = []
        wf.procedures["done"] = []
        mgr.ctx.workflows[wf.uuid] = wf
        return wf

    def test_pop_modifies_instance_not_workflow(self, mgr):
        wf = self._make_workflow(mgr)
        inst = wf.spawn_instance()

        result = list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))

        assert result == CommandReturnStatus.Success
        assert inst.variables["current"].value == "abc 42 def 99"
        assert len(wf.constants["strings_to_match"].value) == 2
        assert len(inst.variables["strings_to_match"].value) == 1

    def test_regex_into_dot_path_modifies_instance_not_workflow(self, mgr):
        wf = self._make_workflow(mgr)
        inst = wf.spawn_instance()

        list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))
        result = asyncio.run(str_regex_matchAll(inst, String(r"\d+"), inst["current"], VariablePath("dict.matches1")))

        assert result == CommandReturnStatus.Success
        assert wf.constants["dict"].value["matches1"].value == []
        assert inst["dict.matches1"].value == ["42", "99"]

    def test_full_scenario_both_strings_processed(self, mgr):
        wf = self._make_workflow(mgr)
        inst = wf.spawn_instance()

        list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))
        asyncio.run(str_regex_matchAll(inst, String(r"\d+"), inst["current"], VariablePath("dict.matches1")))

        result = list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))
        assert result == CommandReturnStatus.Success
        assert inst.variables["current"].value == "hello 7 world 13"
        assert len(inst.variables["strings_to_match"].value) == 0

        asyncio.run(str_regex_matchAll(inst, String(r"\d+"), inst["current"], VariablePath("dict.matches2")))

        assert wf.constants["dict"].value["matches1"].value == []
        assert wf.constants["dict"].value["matches2"].value == []
        assert inst["dict.matches1"].value == ["42", "99"]
        assert inst["dict.matches2"].value == ["7", "13"]

    def test_list_exhausted_after_both_pops(self, mgr):
        wf = self._make_workflow(mgr)
        inst = wf.spawn_instance()

        list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))
        list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))
        result = list_pop_next(inst, VariablePath("strings_to_match"), VariablePath("current"), String("done"))

        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert inst.processing_step == ("done", 0)
