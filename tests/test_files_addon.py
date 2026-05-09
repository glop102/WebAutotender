import pytest
import os
from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.commands_builtin import list_pop_next
from pipeline_backend.workflows import Workflow, RunStates, global_workflows
from pipeline_backend.instances import Instance, global_instances
from pipeline_backend.variables import String, StringList, VariableName, Boolean

import builtin_addons.files
from builtin_addons.files import (
    move_file, delete_file, delete_folder, create_folder,
    file_exists, is_file, is_folder,
    goto_if_file, goto_if_folder,
    list_folder_contents,
)


@pytest.fixture
def workflow():
    wf = Workflow()
    wf.uuid = "wf-files-test"
    wf.name = "Files Test"
    wf.procedures["target"] = []
    global_workflows[wf.uuid] = wf
    return wf


@pytest.fixture
def instance(workflow):
    return workflow.spawn_instance()


# ============================================================
# move_file
# ============================================================

class TestMoveFile:
    def test_moves_file_to_new_path(self, instance, tmp_path):
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_text("hello")
        result = move_file(instance, String(str(src)), String(str(dst)))
        assert result == CommandReturnStatus.Success
        assert not src.exists()
        assert dst.read_text() == "hello"

    def test_moves_file_into_existing_folder(self, instance, tmp_path):
        src = tmp_path / "a.txt"
        src.write_text("data")
        dst_dir = tmp_path / "subdir"
        dst_dir.mkdir()
        result = move_file(instance, String(str(src)), String(str(dst_dir)))
        assert result == CommandReturnStatus.Success
        assert (dst_dir / "a.txt").exists()

    def test_nonexistent_source_returns_error(self, instance, tmp_path):
        result = move_file(instance, String(str(tmp_path / "no.txt")), String(str(tmp_path / "dst.txt")))
        assert result == CommandReturnStatus.Error


# ============================================================
# delete_file
# ============================================================

class TestDeleteFile:
    def test_deletes_existing_file(self, instance, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x")
        result = delete_file(instance, String(str(f)))
        assert result == CommandReturnStatus.Success
        assert not f.exists()

    def test_nonexistent_file_returns_error(self, instance, tmp_path):
        result = delete_file(instance, String(str(tmp_path / "missing.txt")))
        assert result == CommandReturnStatus.Error


# ============================================================
# delete_folder
# ============================================================

class TestDeleteFolder:
    def test_deletes_directory_tree(self, instance, tmp_path):
        d = tmp_path / "tree"
        d.mkdir()
        (d / "child.txt").write_text("y")
        result = delete_folder(instance, String(str(d)))
        assert result == CommandReturnStatus.Success
        assert not d.exists()

    def test_nonexistent_folder_returns_error(self, instance, tmp_path):
        result = delete_folder(instance, String(str(tmp_path / "nope")))
        assert result == CommandReturnStatus.Error


# ============================================================
# create_folder
# ============================================================

class TestCreateFolder:
    def test_creates_directory(self, instance, tmp_path):
        d = tmp_path / "new"
        result = create_folder(instance, String(str(d)))
        assert result == CommandReturnStatus.Success
        assert d.is_dir()

    def test_creates_nested_directories(self, instance, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        result = create_folder(instance, String(str(d)))
        assert result == CommandReturnStatus.Success
        assert d.is_dir()

    def test_existing_directory_is_idempotent(self, instance, tmp_path):
        result = create_folder(instance, String(str(tmp_path)))
        assert result == CommandReturnStatus.Success


# ============================================================
# file_exists / is_file / is_folder
# ============================================================

class TestPathChecks:
    def test_file_exists_true_for_file(self, instance, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("")
        file_exists(instance, String(str(f)), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is True

    def test_file_exists_false_for_missing(self, instance, tmp_path):
        file_exists(instance, String(str(tmp_path / "nope")), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is False

    def test_file_exists_true_for_directory(self, instance, tmp_path):
        file_exists(instance, String(str(tmp_path)), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is True

    def test_is_file_true_for_file(self, instance, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("")
        is_file(instance, String(str(f)), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is True

    def test_is_file_false_for_directory(self, instance, tmp_path):
        is_file(instance, String(str(tmp_path)), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is False

    def test_is_file_false_for_missing(self, instance, tmp_path):
        is_file(instance, String(str(tmp_path / "nope")), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is False

    def test_is_folder_true_for_directory(self, instance, tmp_path):
        is_folder(instance, String(str(tmp_path)), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is True

    def test_is_folder_false_for_file(self, instance, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("")
        is_folder(instance, String(str(f)), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is False

    def test_is_folder_false_for_missing(self, instance, tmp_path):
        is_folder(instance, String(str(tmp_path / "nope")), VariableName("result"))
        assert type(instance.variables["result"]) == Boolean and instance.variables["result"].value is False


# ============================================================
# goto_if_file / goto_if_folder
# ============================================================

class TestGotoBranches:
    def test_goto_if_file_jumps_for_file(self, workflow, instance, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("")
        result = goto_if_file(instance, String("target"), String(str(f)))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert instance.processing_step == ("target", 0)

    def test_goto_if_file_continues_for_directory(self, workflow, instance, tmp_path):
        result = goto_if_file(instance, String("target"), String(str(tmp_path)))
        assert result == CommandReturnStatus.Success
        assert instance.processing_step == ("start", 0)

    def test_goto_if_file_continues_for_missing(self, workflow, instance, tmp_path):
        result = goto_if_file(instance, String("target"), String(str(tmp_path / "nope")))
        assert result == CommandReturnStatus.Success

    def test_goto_if_folder_jumps_for_directory(self, workflow, instance, tmp_path):
        result = goto_if_folder(instance, String("target"), String(str(tmp_path)))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert instance.processing_step == ("target", 0)

    def test_goto_if_folder_continues_for_file(self, workflow, instance, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("")
        result = goto_if_folder(instance, String("target"), String(str(f)))
        assert result == CommandReturnStatus.Success

    def test_goto_if_folder_continues_for_missing(self, workflow, instance, tmp_path):
        result = goto_if_folder(instance, String("target"), String(str(tmp_path / "nope")))
        assert result == CommandReturnStatus.Success


# ============================================================
# list_folder_contents
# ============================================================

class TestListFolderContents:
    def test_lists_files_sorted(self, instance, tmp_path):
        (tmp_path / "c.txt").write_text("")
        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b.txt").write_text("")
        result = list_folder_contents(instance, String(str(tmp_path)), VariableName("entries"))
        assert result == CommandReturnStatus.Success
        assert instance.variables["entries"].value == ["a.txt", "b.txt", "c.txt"]

    def test_includes_subdirectories(self, instance, tmp_path):
        (tmp_path / "file.txt").write_text("")
        (tmp_path / "subdir").mkdir()
        list_folder_contents(instance, String(str(tmp_path)), VariableName("entries"))
        assert "file.txt" in instance.variables["entries"].value
        assert "subdir" in instance.variables["entries"].value

    def test_empty_folder_returns_empty_list(self, instance, tmp_path):
        result = list_folder_contents(instance, String(str(tmp_path)), VariableName("entries"))
        assert result == CommandReturnStatus.Success
        assert instance.variables["entries"].value == []

    def test_nonexistent_folder_returns_error(self, instance, tmp_path):
        result = list_folder_contents(instance, String(str(tmp_path / "nope")), VariableName("entries"))
        assert result == CommandReturnStatus.Error


# ============================================================
# list_pop_next (Core)
# ============================================================

class TestStringlistPopNext:
    def test_pops_first_item_into_variable(self, workflow, instance):
        instance.variables["items"] = StringList(["a", "b", "c"])
        result = list_pop_next(instance, VariableName("items"), VariableName("current"), String("target"))
        assert result == CommandReturnStatus.Success
        assert instance.variables["current"].value == "a"
        assert instance.variables["items"].value == ["b", "c"]

    def test_pops_last_item_and_continues(self, workflow, instance):
        # Last item should be popped and returned normally — caller loops back and hits the empty check next time
        instance.variables["items"] = StringList(["only"])
        result = list_pop_next(instance, VariableName("items"), VariableName("current"), String("target"))
        assert result == CommandReturnStatus.Success
        assert instance.variables["current"].value == "only"
        assert instance.variables["items"].value == []

    def test_jumps_to_procedure_when_list_is_empty(self, workflow, instance):
        # Empty list on entry → jump immediately, item_varname not touched
        instance.variables["items"] = StringList([])
        result = list_pop_next(instance, VariableName("items"), VariableName("current"), String("target"))
        assert result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position
        assert instance.processing_step == ("target", 0)

    def test_drain_loop_visits_all_items(self, workflow, instance):
        # Simulate the full drain: call repeatedly until we get the jump
        instance.variables["items"] = StringList(["x", "y", "z"])
        seen = []
        for _ in range(10):
            result = list_pop_next(instance, VariableName("items"), VariableName("current"), String("target"))
            if result == CommandReturnStatus.Success | CommandReturnStatus.Keep_Position:
                break
            seen.append(instance.variables["current"].value)
        assert seen == ["x", "y", "z"]
        assert instance.processing_step == ("target", 0)

    def test_non_stringlist_returns_error(self, workflow, instance):
        from pipeline_backend.variables import Integer
        instance.variables["items"] = Integer(5)
        result = list_pop_next(instance, VariableName("items"), VariableName("current"), String("target"))
        assert result == CommandReturnStatus.Error
