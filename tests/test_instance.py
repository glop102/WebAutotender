import pytest
from pipeline_backend.instances import Instance, global_instances
from pipeline_backend.workflows import Workflow, global_workflows
from pipeline_backend.variables import String, Integer, Float, VariablePath, StringList, VariableList, VariableNameList, Dictionary, global_variables, global_secrets


@pytest.fixture
def workflow():
    wf = Workflow()
    wf.uuid = "wf-instance-test"
    wf.name = "Instance Test"
    global_workflows[wf.uuid] = wf
    return wf


class TestVariableLookupChain:
    def test_instance_variable_found(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("instance_val")
        assert inst["x"].value == "instance_val"

    def test_instance_variable_shadows_constant(self, workflow):
        workflow.constants["x"] = String("constant_val")
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("instance_val")
        assert inst["x"].value == "instance_val"

    def test_falls_through_to_constant(self, workflow):
        workflow.constants["x"] = String("constant_val")
        inst = workflow.spawn_instance()
        assert inst["x"].value == "constant_val"

    def test_constant_shadows_setup_variable(self, workflow):
        # Constant takes priority over setup_variables added after spawn
        workflow.constants["x"] = String("constant_val")
        inst = workflow.spawn_instance()
        workflow.setup_variables["x"] = String("setup_val")
        assert inst["x"].value == "constant_val"

    def test_falls_through_to_setup_variable_added_after_spawn(self, workflow):
        # setup_variables added after spawn are not in inst.variables but still reachable
        inst = workflow.spawn_instance()
        workflow.setup_variables["late_var"] = String("setup_val")
        assert inst["late_var"].value == "setup_val"

    def test_setup_variables_copied_to_instance_at_spawn(self, workflow):
        workflow.setup_variables["x"] = String("default")
        inst = workflow.spawn_instance()
        assert "x" in inst.variables
        assert inst["x"].value == "default"

    def test_spawn_override_replaces_setup_default(self, workflow):
        workflow.setup_variables["x"] = String("default")
        inst = workflow.spawn_instance({"x": String("override")})
        assert inst["x"].value == "override"

    def test_falls_through_to_global_variable(self, workflow):
        global_variables["g"] = Integer(42)
        inst = workflow.spawn_instance()
        assert inst["g"].value == 42

    def test_falls_through_to_global_secret(self, workflow):
        global_secrets["s"] = String("secret_val")
        inst = workflow.spawn_instance()
        assert inst["s"].value == "secret_val"

    def test_not_found_raises_keyerror(self, workflow):
        inst = workflow.spawn_instance()
        with pytest.raises(KeyError):
            _ = inst["nonexistent"]

    def test_lookup_returns_copy_not_reference(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("original")
        got = inst["x"]
        got.value = "mutated"
        assert inst["x"].value == "original"


class TestContains:
    def test_contains_true_for_instance_var(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["k"] = String("v")
        assert "k" in inst

    def test_contains_true_for_constant(self, workflow):
        workflow.constants["k"] = String("v")
        inst = workflow.spawn_instance()
        assert "k" in inst

    def test_contains_true_for_global(self, workflow):
        global_variables["g"] = Integer(1)
        inst = workflow.spawn_instance()
        assert "g" in inst

    def test_contains_false_for_missing(self, workflow):
        inst = workflow.spawn_instance()
        assert "missing" not in inst


class TestSetItem:
    def test_stores_value(self, workflow):
        inst = workflow.spawn_instance()
        inst["x"] = String("hello")
        assert inst.variables["x"].value == "hello"

    def test_accepts_variable_name_key(self, workflow):
        inst = workflow.spawn_instance()
        inst[VariablePath("x")] = Integer(5)
        assert inst.variables["x"].value == 5

    def test_stores_copy_not_reference(self, workflow):
        inst = workflow.spawn_instance()
        val = String("original")
        inst["x"] = val
        val.value = "mutated"
        assert inst.variables["x"].value == "original"

    def test_rejects_non_workvar(self, workflow):
        inst = workflow.spawn_instance()
        with pytest.raises(TypeError):
            inst["x"] = "not a workvar"

    def test_overwrites_existing(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("old")
        inst["x"] = String("new")
        assert inst.variables["x"].value == "new"


class TestDelItem:
    def test_deletes_instance_variable(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("val")
        del inst["x"]
        assert "x" not in inst.variables

    def test_delete_missing_raises_keyerror(self, workflow):
        inst = workflow.spawn_instance()
        with pytest.raises(KeyError):
            del inst["nonexistent"]


class TestSpawnInstance:
    def test_registers_in_global_instances(self, workflow):
        inst = workflow.spawn_instance()
        assert inst.uuid in global_instances

    def test_unregistered_workflow_not_added_to_global(self):
        wf = Workflow()
        wf.uuid = "unregistered"
        wf.name = "Unregistered"
        # Not added to global_workflows
        inst = wf.spawn_instance()
        assert inst.uuid not in global_instances

    def test_sets_workflow_uuid(self, workflow):
        inst = workflow.spawn_instance()
        assert inst.workflow_uuid == workflow.uuid

    def test_initial_processing_step_is_start(self, workflow):
        inst = workflow.spawn_instance()
        assert inst.processing_step == ("start", 0)

    def test_multiple_spawns_have_unique_uuids(self, workflow):
        a = workflow.spawn_instance()
        b = workflow.spawn_instance()
        assert a.uuid != b.uuid


class TestDotNotationGet:
    def test_single_level_dict_key(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["entry"] = Dictionary({"link": String("http://example.com")})
        assert inst["entry.link"].value == "http://example.com"

    def test_multi_level_nested_dicts(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["a"] = Dictionary({"b": Dictionary({"c": String("deep")})})
        assert inst["a.b.c"].value == "deep"

    def test_integer_index_into_variablelist(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["items"] = VariableList([String("first"), String("second")])
        assert inst["items.0"].value == "first"
        assert inst["items.1"].value == "second"

    def test_integer_index_into_stringlist(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["words"] = StringList(["hello", "world"])
        result = inst["words.0"]
        assert isinstance(result, String)
        assert result.value == "hello"

    def test_integer_index_into_variablenamelist(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["names"] = VariableNameList(["foo", "bar"])
        result = inst["names.1"]
        assert isinstance(result, VariablePath)
        assert result.value == "bar"

    def test_missing_dict_key_raises_keyerror(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["d"] = Dictionary({"a": String("x")})
        with pytest.raises(KeyError):
            _ = inst["d.missing"]

    def test_indexing_into_non_container_raises_keyerror(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("flat")
        with pytest.raises(KeyError):
            _ = inst["x.sub"]

    def test_missing_first_segment_raises_keyerror(self, workflow):
        inst = workflow.spawn_instance()
        with pytest.raises(KeyError):
            _ = inst["nonexistent.key"]

    def test_variablepath_key_accepted(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["d"] = Dictionary({"v": Integer(7)})
        assert inst[VariablePath("d.v")].value == 7


class TestDotNotationSet:
    def test_single_level_unchanged(self, workflow):
        inst = workflow.spawn_instance()
        inst["x"] = String("flat")
        assert inst.variables["x"].value == "flat"

    def test_creates_dict_and_sets_key(self, workflow):
        inst = workflow.spawn_instance()
        inst["entry.link"] = String("http://example.com")
        assert isinstance(inst.variables["entry"], Dictionary)
        assert inst.variables["entry"].value["link"].value == "http://example.com"

    def test_sets_key_in_existing_dict(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["entry"] = Dictionary({"title": String("old")})
        inst["entry.title"] = String("new")
        assert inst.variables["entry"].value["title"].value == "new"

    def test_creates_intermediate_dicts(self, workflow):
        inst = workflow.spawn_instance()
        inst["a.b.c"] = Integer(99)
        assert inst.variables["a"].value["b"].value["c"].value == 99

    def test_setting_into_non_dict_intermediate_raises(self, workflow):
        inst = workflow.spawn_instance()
        inst.variables["x"] = String("flat")
        with pytest.raises(TypeError):
            inst["x.key"] = String("val")
