"""Full pipeline tests: complete workflows executed end-to-end through ProcedureRunner."""
import pytest
from pipeline_backend.procedure_runner import ProcedureRunner
from pipeline_backend.workflows import Workflow, RunStates, ProcessingStep, global_workflows
from pipeline_backend.variables import String, Integer, Float, VariablePath, Dictionary, VariableList, StringList
import builtin_addons.string_operations  # registers string commands
import builtin_addons.files              # registers file commands


class TestDotNotationWorkflowScenarioViaRunner:
    """Same scenario as TestDotNotationWorkflowScenario but built as a real workflow
    and executed through ProcedureRunner to verify state accumulation end-to-end."""

    def _make_workflow(self):
        wf = Workflow()
        wf.uuid = "dot-notation-runner-wf"
        wf.name = "Dot Notation Runner Scenario"
        wf.constants["strings_to_match"] = VariableList([
            String("abc 42 def 99"),
            String("hello 7 world 13"),
        ])
        wf.constants["dict"] = Dictionary({
            "matches1": StringList([]),
            "matches2": StringList([]),
        })
        wf.procedures["start"] = [
            ProcessingStep("list_pop_next",
                           list_varname=VariablePath("strings_to_match"),
                           item_varname=VariablePath("current"),
                           empty_procedure=String("done")),
            ProcessingStep("str_regex_matchAll",
                           regexPatern=String(r"\d+"),
                           inputString=VariablePath("current"),
                           outputVarname=VariablePath("dict.matches1")),
            ProcessingStep("list_pop_next",
                           list_varname=VariablePath("strings_to_match"),
                           item_varname=VariablePath("current"),
                           empty_procedure=String("done")),
            ProcessingStep("str_regex_matchAll",
                           regexPatern=String(r"\d+"),
                           inputString=VariablePath("current"),
                           outputVarname=VariablePath("dict.matches2")),
            ProcessingStep("pause_this_instance"),
        ]
        wf.procedures["done"] = [
            ProcessingStep("pause_this_instance"),
        ]
        global_workflows[wf.uuid] = wf
        return wf

    async def test_workflow_constants_unmodified_after_run(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert len(wf.constants["strings_to_match"].value) == 2
        assert wf.constants["dict"].value["matches1"].value == []
        assert wf.constants["dict"].value["matches2"].value == []

    async def test_instance_strings_list_fully_consumed(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert len(inst.variables["strings_to_match"].value) == 0

    async def test_instance_dict_has_both_match_results(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst["dict.matches1"].value == ["42", "99"]
        assert inst["dict.matches2"].value == ["7", "13"]

    async def test_instance_reaches_paused_state(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.state == RunStates.Paused


class TestBatchCounterWithBranching:
    """Workflow that iterates a VariableList of Integer scores, accumulates a
    running total, and counts how many scores exceed a threshold — exercising
    list_pop_next, goto_if_first_larger, math_add, and loop-back jumps."""

    # Scores: 10, 85, 40, 92, 5  — threshold 50
    # Above threshold: 85, 92  → above_count = 2
    # Total: 10+85+40+92+5 = 232

    def _make_workflow(self):
        wf = Workflow()
        wf.uuid = "batch-counter-wf"
        wf.name = "Batch Counter"
        wf.constants["scores"] = VariableList([
            Integer(10),
            Integer(85),
            Integer(40),
            Integer(92),
            Integer(5),
        ])
        wf.constants["threshold"] = Integer(50)
        wf.setup_variables["total"] = Integer(0)
        wf.setup_variables["above_count"] = Integer(0)

        # start: initialise accumulators then enter loop
        wf.procedures["start"] = [
            ProcessingStep("set_variable_value",
                           variable_name=VariablePath("total"),
                           value=Integer(0)),
            ProcessingStep("set_variable_value",
                           variable_name=VariablePath("above_count"),
                           value=Integer(0)),
            ProcessingStep("jump_to_procedure",
                           procedure_name=String("loop")),
        ]
        # loop: pop next score; if list empty → done
        wf.procedures["loop"] = [
            ProcessingStep("list_pop_next",
                           list_varname=VariablePath("scores"),
                           item_varname=VariablePath("current_score"),
                           empty_procedure=String("done")),
            ProcessingStep("math_add",
                           first=VariablePath("total"),
                           second=VariablePath("current_score"),
                           output_variable=VariablePath("total")),
            ProcessingStep("goto_if_first_larger",
                           procedure_name=String("increment_above"),
                           value1=VariablePath("current_score"),
                           value2=VariablePath("threshold")),
            ProcessingStep("jump_to_procedure",
                           procedure_name=String("loop")),
        ]
        # increment_above: bump the above-threshold counter then re-enter loop
        wf.procedures["increment_above"] = [
            ProcessingStep("math_add",
                           first=VariablePath("above_count"),
                           second=Integer(1),
                           output_variable=VariablePath("above_count")),
            ProcessingStep("jump_to_procedure",
                           procedure_name=String("loop")),
        ]
        wf.procedures["done"] = [
            ProcessingStep("pause_this_instance"),
        ]
        global_workflows[wf.uuid] = wf
        return wf

    async def test_total_is_correct(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst["total"].value == 232

    async def test_above_count_is_correct(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst["above_count"].value == 2

    async def test_scores_list_exhausted(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert len(inst["scores"].value) == 0

    async def test_workflow_constants_unmodified(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert len(wf.constants["scores"].value) == 5
        assert wf.constants["threshold"].value == 50

    async def test_instance_reaches_paused_state(self):
        wf = self._make_workflow()
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.state == RunStates.Paused


class TestFileOrganiserPipeline:
    """Workflow that loops over a StringList of filenames, extracts a department
    name via regex, builds destination paths with str_buildWithVars, creates the
    department sub-folder, and moves each file there — exercising list_pop_next,
    str_regex_firstMatch, str_buildWithVars, create_folder, and move_file."""

    # Filenames follow the pattern report_<date>_<department>.csv
    FILENAMES = [
        "report_2026-05_finance.csv",
        "report_2026-04_hr.csv",
        "report_2026-06_engineering.csv",
    ]
    # _\K[a-z]+(?=\.csv) uses \K to drop the underscore from the match,
    # leaving only the department name before the .csv extension.
    DEPT_PATTERN = r"_\K[a-z]+(?=\.csv)"

    def _make_workflow(self, staging_dir: str, dest_dir: str):
        wf = Workflow()
        wf.uuid = "file-organiser-wf"
        wf.name = "File Organiser"
        wf.constants["staging_dir"] = String(staging_dir)
        wf.constants["dest_dir"] = String(dest_dir)
        wf.constants["filenames"] = StringList(list(self.FILENAMES))

        wf.procedures["start"] = [
            ProcessingStep("jump_to_procedure",
                           procedure_name=String("loop")),
        ]
        wf.procedures["loop"] = [
            ProcessingStep("list_pop_next",
                           list_varname=VariablePath("filenames"),
                           item_varname=VariablePath("filename"),
                           empty_procedure=String("done")),
            ProcessingStep("str_regex_firstMatch",
                           regexPatern=String(self.DEPT_PATTERN),
                           inputString=VariablePath("filename"),
                           outputVarname=VariablePath("department")),
            ProcessingStep("str_buildWithVars",
                           inputString=String("{dest_dir}/{department}"),
                           outputVarname=VariablePath("dest_subdir_path")),
            ProcessingStep("create_folder",
                           path=VariablePath("dest_subdir_path")),
            ProcessingStep("str_buildWithVars",
                           inputString=String("{staging_dir}/{filename}"),
                           outputVarname=VariablePath("source_path")),
            ProcessingStep("str_buildWithVars",
                           inputString=String("{dest_subdir_path}/{filename}"),
                           outputVarname=VariablePath("final_dest_path")),
            ProcessingStep("move_file",
                           source=VariablePath("source_path"),
                           destination=VariablePath("final_dest_path")),
            ProcessingStep("jump_to_procedure",
                           procedure_name=String("loop")),
        ]
        wf.procedures["done"] = [
            ProcessingStep("pause_this_instance"),
        ]
        global_workflows[wf.uuid] = wf
        return wf

    async def test_files_moved_to_correct_subdirs(self, tmp_path):
        staging = tmp_path / "staging"
        dest = tmp_path / "dest"
        staging.mkdir()
        dest.mkdir()
        for f in self.FILENAMES:
            (staging / f).write_text("data")

        wf = self._make_workflow(str(staging), str(dest))
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert (dest / "finance" / "report_2026-05_finance.csv").is_file()
        assert (dest / "hr" / "report_2026-04_hr.csv").is_file()
        assert (dest / "engineering" / "report_2026-06_engineering.csv").is_file()

    async def test_source_files_no_longer_in_staging(self, tmp_path):
        staging = tmp_path / "staging"
        dest = tmp_path / "dest"
        staging.mkdir()
        dest.mkdir()
        for f in self.FILENAMES:
            (staging / f).write_text("data")

        wf = self._make_workflow(str(staging), str(dest))
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        for f in self.FILENAMES:
            assert not (staging / f).exists()

    async def test_filenames_list_exhausted(self, tmp_path):
        staging = tmp_path / "staging"
        dest = tmp_path / "dest"
        staging.mkdir()
        dest.mkdir()
        for f in self.FILENAMES:
            (staging / f).write_text("data")

        wf = self._make_workflow(str(staging), str(dest))
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert len(inst["filenames"].value) == 0

    async def test_workflow_constants_unmodified(self, tmp_path):
        staging = tmp_path / "staging"
        dest = tmp_path / "dest"
        staging.mkdir()
        dest.mkdir()
        for f in self.FILENAMES:
            (staging / f).write_text("data")

        wf = self._make_workflow(str(staging), str(dest))
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert wf.constants["filenames"].value == list(self.FILENAMES)

    async def test_instance_reaches_paused_state(self, tmp_path):
        staging = tmp_path / "staging"
        dest = tmp_path / "dest"
        staging.mkdir()
        dest.mkdir()
        for f in self.FILENAMES:
            (staging / f).write_text("data")

        wf = self._make_workflow(str(staging), str(dest))
        inst = wf.spawn_instance()
        await ProcedureRunner(inst).run_instance_until_yield()

        assert inst.state == RunStates.Paused
