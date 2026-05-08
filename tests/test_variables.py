import pytest
from pipeline_backend.variables import (
    WorkVariable, String, Integer, Float, URL,
    Boolean, StringList, VariableList, VariableName, VariableNameList, Dictionary,
)


class TestString:
    def test_default(self):
        assert String().value == ""

    def test_valid(self):
        assert String("hello").is_valid()

    def test_normalize_strips_whitespace(self):
        s = String("  hello  ")
        s.normalize()
        assert s.value == "hello"

    def test_reset(self):
        s = String("hello")
        s.reset_to_default()
        assert s.value == ""

    def test_json_roundtrip(self):
        s = String("test value")
        data = s.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, String)
        assert restored.value == "test value"


class TestInteger:
    def test_default(self):
        assert Integer().value == 0

    def test_valid(self):
        assert Integer(42).is_valid()

    def test_normalize_from_string(self):
        i = Integer()
        i.value = "7"
        i.normalize()
        assert i.value == 7

    def test_reset(self):
        i = Integer(5)
        i.reset_to_default()
        assert i.value == 0

    def test_json_roundtrip(self):
        i = Integer(99)
        data = i.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, Integer)
        assert restored.value == 99


class TestBoolean:
    def test_default_is_false(self):
        assert Boolean().value == False

    def test_valid_true(self):
        assert Boolean(True).is_valid()

    def test_valid_false(self):
        assert Boolean(False).is_valid()

    def test_normalize_from_string_true(self):
        b = Boolean()
        b.value = "true"
        b.normalize()
        assert b.value is True

    def test_normalize_from_string_false(self):
        b = Boolean()
        b.value = "false"
        b.normalize()
        assert b.value is False

    def test_normalize_from_string_case_insensitive(self):
        b = Boolean()
        b.value = "True"
        b.normalize()
        assert b.value is True

    def test_normalize_from_int_one(self):
        b = Boolean()
        b.value = 1
        b.normalize()
        assert b.value is True

    def test_normalize_from_int_zero(self):
        b = Boolean()
        b.value = 0
        b.normalize()
        assert b.value is False

    def test_reset(self):
        b = Boolean(True)
        b.reset_to_default()
        assert b.value is False

    def test_json_roundtrip_true(self):
        b = Boolean(True)
        data = b.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, Boolean)
        assert restored.value is True

    def test_json_roundtrip_false(self):
        b = Boolean(False)
        data = b.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, Boolean)
        assert restored.value is False


class TestFloat:
    def test_default(self):
        assert Float().value == 0.0

    def test_valid(self):
        assert Float(3.14).is_valid()

    def test_normalize_from_int(self):
        f = Float()
        f.value = 5
        f.normalize()
        assert isinstance(f.value, float)
        assert f.value == 5.0

    def test_json_roundtrip(self):
        f = Float(2.5)
        data = f.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, Float)
        assert restored.value == 2.5


class TestURL:
    def test_valid(self):
        assert URL("https://example.com").is_valid()

    def test_valid_non_https(self):
        assert URL("ftp://files.example.com").is_valid()

    def test_invalid_no_scheme(self):
        assert not URL("example.com").is_valid()

    def test_default_invalid(self):
        assert not URL().is_valid()


class TestStringList:
    def test_default(self):
        assert StringList().value == []

    def test_valid(self):
        assert StringList(["a", "b"]).is_valid()

    def test_invalid_non_list(self):
        sl = StringList()
        sl.value = "not a list"
        assert not sl.is_valid()

    def test_normalize_strips_elements(self):
        sl = StringList(["  a  ", " b"])
        sl.normalize()
        assert sl.value == ["a", "b"]

    def test_json_roundtrip(self):
        sl = StringList(["x", "y", "z"])
        data = sl.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, StringList)
        assert restored.value == ["x", "y", "z"]


class TestDictionary:
    def test_default(self):
        assert Dictionary().value == {}

    def test_valid(self):
        d = Dictionary({"key": String("val")})
        assert d.is_valid()

    def test_invalid_non_workvar_value(self):
        d = Dictionary()
        d.value = {"key": "not a workvar"}
        assert not d.is_valid()

    def test_invalid_non_string_key(self):
        d = Dictionary()
        d.value = {1: String("val")}
        assert not d.is_valid()

    def test_json_roundtrip(self):
        d = Dictionary({"name": String("alice"), "age": Integer(30)})
        data = d.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, Dictionary)
        assert restored.value["name"].value == "alice"
        assert restored.value["age"].value == 30

    def test_nested_dictionary_roundtrip(self):
        inner = Dictionary({"x": Integer(1)})
        outer = Dictionary({"inner": inner})
        data = outer.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, Dictionary)
        assert isinstance(restored.value["inner"], Dictionary)
        assert restored.value["inner"].value["x"].value == 1


class TestVariableName:
    def test_valid(self):
        assert VariableName("my_var").is_valid()

    def test_default(self):
        assert VariableName().value == ""

    def test_normalize_strips(self):
        v = VariableName("  my_var  ")
        v.normalize()
        assert v.value == "my_var"


class TestVariableList:
    def test_default(self):
        assert VariableList().value == []

    def test_valid(self):
        vl = VariableList([String("a"), Integer(1)])
        assert vl.is_valid()

    def test_invalid_non_list(self):
        vl = VariableList()
        vl.value = "not a list"
        assert not vl.is_valid()

    def test_invalid_contains_non_workvar(self):
        vl = VariableList()
        vl.value = ["raw string"]
        assert not vl.is_valid()

    def test_normalize_converts_dict_entries(self):
        vl = VariableList()
        vl.value = [{"value": "hello", "typename": "String"}]
        vl.normalize()
        assert isinstance(vl.value[0], String)
        assert vl.value[0].value == "hello"

    def test_normalize_raises_on_non_dict_non_workvar(self):
        vl = VariableList()
        vl.value = [42]  # neither WorkVariable nor dict
        with pytest.raises(TypeError):
            vl.normalize()

    def test_json_roundtrip(self):
        vl = VariableList([String("x"), Integer(7)])
        data = vl.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, VariableList)
        assert restored.value[0].value == "x"
        assert restored.value[1].value == 7

    def test_convert_to_python_type(self):
        vl = VariableList([String("a"), Integer(2)])
        assert vl.convert_to_python_type() == ["a", 2]


class TestVariableNameList:
    def test_default(self):
        assert VariableNameList().value == []

    def test_valid(self):
        assert VariableNameList(["foo", "bar"]).is_valid()

    def test_invalid_non_list(self):
        vnl = VariableNameList()
        vnl.value = "not a list"
        assert not vnl.is_valid()

    def test_invalid_contains_non_string(self):
        vnl = VariableNameList()
        vnl.value = [123]
        assert not vnl.is_valid()

    def test_normalize_strips_elements(self):
        vnl = VariableNameList(["  foo  ", " bar"])
        vnl.normalize()
        assert vnl.value == ["foo", "bar"]

    def test_normalize_raises_on_non_list(self):
        vnl = VariableNameList()
        vnl.value = "not a list"
        with pytest.raises(ValueError):
            vnl.normalize()

    def test_json_roundtrip(self):
        vnl = VariableNameList(["a", "b", "c"])
        data = vnl.json_savable()
        restored = WorkVariable()
        restored.json_loadable(data)
        assert isinstance(restored, VariableNameList)
        assert restored.value == ["a", "b", "c"]


class TestURLNormalize:
    def test_str_value_left_unchanged(self):
        u = URL("https://example.com")
        u.normalize()
        assert u.value == "https://example.com"

    def test_non_str_value_converted_to_str(self):
        u = URL.__new__(URL)
        u.value = 12345
        u.normalize()
        assert isinstance(u.value, str)


class TestDictionaryNormalize:
    def test_non_string_keys_converted_to_string(self):
        d = Dictionary()
        d.value = {1: String("val")}
        d.normalize()
        assert "1" in d.value
        assert 1 not in d.value

    def test_dict_values_loaded_from_raw_dicts(self):
        d = Dictionary()
        d.value = {"k": {"value": "hello", "typename": "String"}}
        d.normalize()
        assert isinstance(d.value["k"], String)
        assert d.value["k"].value == "hello"

    def test_non_dict_non_workvar_value_raises(self):
        d = Dictionary()
        d.value = {"k": 42}
        with pytest.raises(TypeError):
            d.normalize()


class TestCoercion:
    def test_integer_to_float(self):
        result = Integer(5).coerce_into_type(Float)
        assert result is not None
        assert isinstance(result, Float)
        assert result.value == 5.0

    def test_float_to_integer(self):
        result = Float(3.0).coerce_into_type(Integer)
        assert result is not None
        assert isinstance(result, Integer)

    def test_string_to_integer_valid(self):
        result = String("42").coerce_into_type(Integer)
        assert result is not None
        assert result.value == 42

    def test_string_to_integer_invalid(self):
        result = String("not_a_number").coerce_into_type(Integer)
        assert result is None

    def test_coerce_returns_copy_not_original(self):
        s = String("hello")
        result = s.coerce_into_type(String)
        assert result is not None
        assert result is not s
        assert result.value == "hello"

    def test_invalid_coercion_returns_none(self):
        s = String("abc")
        result = s.coerce_into_type(Float)
        assert result is None

    def test_normalize_exception_returns_none_not_raises(self):
        # StringList.normalize() raises ValueError if value is not a list.
        # coerce_into_type must catch that and return None rather than propagating.
        result = String("hello").coerce_into_type(StringList)
        assert result is None


class TestConvertToPythonType:
    def test_string(self):
        assert String("hello").convert_to_python_type() == "hello"

    def test_integer(self):
        assert Integer(7).convert_to_python_type() == 7

    def test_string_list(self):
        assert StringList(["a", "b"]).convert_to_python_type() == ["a", "b"]

    def test_dictionary(self):
        d = Dictionary({"k": Integer(1)})
        result = d.convert_to_python_type()
        assert result == {"k": 1}
