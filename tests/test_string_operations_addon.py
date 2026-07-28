import pytest

from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.workflows import Workflow
from pipeline_backend.variables import String, VariablePath

import builtin_addons.string_operations
from builtin_addons.string_operations import str_regex_matchAll


@pytest.fixture
def workflow(mgr):
    wf = Workflow(mgr.ctx)
    wf.uuid = "wf-strings-test"
    wf.name = "Strings Test"
    mgr.ctx.workflows[wf.uuid] = wf
    return wf


class TestRegexMatchAll:
    async def test_no_capture_group_returns_whole_matches(self, workflow):
        inst = workflow.spawn_instance()
        result = await str_regex_matchAll(inst, String(r"\d+"), String("a1b22c333"), VariablePath("out"))
        assert result == CommandReturnStatus.Success
        assert inst["out"].value == ["1", "22", "333"]

    async def test_one_capture_group_returns_that_group(self, workflow):
        inst = workflow.spawn_instance()
        result = await str_regex_matchAll(inst, String(r"id=(\d+)"), String("id=12 id=34"), VariablePath("out"))
        assert result == CommandReturnStatus.Success
        assert inst["out"].value == ["12", "34"]

    async def test_K_escape_still_works(self, workflow):
        # \K is the reason this addon depends on the regex module rather than re, and it
        # needs no capture group at all - the guard must not get in its way
        inst = workflow.spawn_instance()
        result = await str_regex_matchAll(inst, String(r"id=\K\d+"), String("id=12 id=34"), VariablePath("out"))
        assert result == CommandReturnStatus.Success
        assert inst["out"].value == ["12", "34"]

    async def test_non_capturing_groups_do_not_count(self, workflow):
        inst = workflow.spawn_instance()
        result = await str_regex_matchAll(inst, String(r"(?:id|ref)=(\d+)"), String("id=12 ref=34"), VariablePath("out"))
        assert result == CommandReturnStatus.Success
        assert inst["out"].value == ["12", "34"]

    async def test_no_matches_stores_an_empty_list(self, workflow):
        inst = workflow.spawn_instance()
        result = await str_regex_matchAll(inst, String(r"\d+"), String("no digits here"), VariablePath("out"))
        assert result == CommandReturnStatus.Success
        assert inst["out"].value == []

    async def test_several_capture_groups_is_an_error(self, workflow):
        inst = workflow.spawn_instance()
        result = await str_regex_matchAll(inst, String(r"(\w)=(\d)"), String("a=1 b=2"), VariablePath("out"))
        assert result == CommandReturnStatus.Error

    async def test_several_capture_groups_does_not_store_anything(self, workflow):
        # The failure mode being guarded against is a StringList quietly holding tuples
        inst = workflow.spawn_instance()
        await str_regex_matchAll(inst, String(r"(\w)=(\d)"), String("a=1 b=2"), VariablePath("out"))
        assert "out" not in inst

    async def test_several_capture_groups_explains_itself(self, workflow):
        inst = workflow.spawn_instance()
        await str_regex_matchAll(inst, String(r"(\w)=(\d)"), String("a=1 b=2"), VariablePath("out"))
        assert "2 capture groups" in inst.console_log
