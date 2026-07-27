"""Tests for addon discovery and importing - search path order, shadowing, module naming."""
import os
import pathlib
import sys
import pytest

from pipeline_backend import manager as manager_module
from pipeline_backend.manager import ADDON_NAMESPACE, addon_search_paths


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_addon(folder: pathlib.Path, name: str, body: str = "") -> pathlib.Path:
    """Create an addon folder containing an __init__.py.

    The bodies here deliberately never register commands, so importing a test addon
    cannot leak into the process wide Commands registry.
    """
    addon = folder / name
    addon.mkdir(parents=True, exist_ok=True)
    (addon / "__init__.py").write_text(body or f"NAME = {name!r}\n")
    return addon


@pytest.fixture(autouse=True)
def isolate_addon_environment(monkeypatch):
    """Keep the ambient environment out of the tests, and unregister anything a test imported."""
    monkeypatch.delenv("WEBAUTOTENDER_ADDON_PATH", raising=False)
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        if name == ADDON_NAMESPACE or name.startswith(ADDON_NAMESPACE + "."):
            del sys.modules[name]


@pytest.fixture
def search_path(monkeypatch):
    """Returns a callable that pins the addon search path to an explicit list of folders."""
    def use(*folders):
        monkeypatch.setattr(manager_module, "addon_search_paths", lambda: list(folders))
    return use


# ---------------------------------------------------------------------------
# addon_search_paths
# ---------------------------------------------------------------------------

class TestAddonSearchPaths:
    def test_builtin_addons_come_last(self):
        assert addon_search_paths()[-1].name == "builtin_addons"

    def test_builtin_addons_do_not_depend_on_the_working_directory(self, monkeypatch, tmp_path):
        # This is what lets the nix wrapper stop cd'ing into the store before starting
        monkeypatch.chdir(tmp_path)
        builtin = addon_search_paths()[-1]
        assert builtin.is_absolute()
        assert (builtin / "html" / "__init__.py").is_file()

    def test_env_var_entries_come_first_and_keep_their_order(self, monkeypatch, tmp_path):
        first, second = tmp_path / "first", tmp_path / "second"
        monkeypatch.setenv("WEBAUTOTENDER_ADDON_PATH", f"{first}{os.pathsep}{second}")
        paths = addon_search_paths()
        assert paths[0] == first
        assert paths[1] == second

    def test_env_var_prepends_rather_than_replacing(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEBAUTOTENDER_ADDON_PATH", str(tmp_path))
        # Setting the variable must not be able to hide the builtins
        assert addon_search_paths()[-1].name == "builtin_addons"

    def test_blank_env_var_entries_are_ignored(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WEBAUTOTENDER_ADDON_PATH", f"{os.pathsep}  {os.pathsep}{tmp_path}")
        paths = addon_search_paths()
        assert paths[0] == tmp_path

    def test_unset_env_var_adds_nothing(self):
        assert not any(p == pathlib.Path("") for p in addon_search_paths())

    def test_xdg_data_home_is_honoured(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        assert tmp_path / "webautotender" / "addons" in addon_search_paths()

    def test_home_is_used_when_xdg_is_unset(self, monkeypatch, tmp_path):
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        expected = tmp_path / ".local" / "share" / "webautotender" / "addons"
        assert expected in addon_search_paths()

    def test_no_home_at_all_does_not_raise(self, monkeypatch):
        # A bare service environment may have neither set - pathlib.Path.home() would throw
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)
        paths = addon_search_paths()
        assert not any(p.as_posix().endswith(".local/share/webautotender/addons") for p in paths)
        assert paths[-1].name == "builtin_addons"


# ---------------------------------------------------------------------------
# discover_addons
# ---------------------------------------------------------------------------

class TestDiscoverAddons:
    def test_finds_addons_in_a_search_folder(self, mgr, tmp_path, search_path):
        make_addon(tmp_path, "alpha")
        make_addon(tmp_path, "beta")
        search_path(tmp_path)
        assert sorted(mgr.discover_addons()) == ["alpha", "beta"]

    def test_maps_the_name_to_its_folder(self, mgr, tmp_path, search_path):
        addon = make_addon(tmp_path, "alpha")
        search_path(tmp_path)
        assert mgr.discover_addons()["alpha"] == addon

    def test_ignores_loose_files(self, mgr, tmp_path, search_path):
        make_addon(tmp_path, "alpha")
        (tmp_path / "addons_go_here.txt").write_text("not an addon\n")
        search_path(tmp_path)
        assert sorted(mgr.discover_addons()) == ["alpha"]

    def test_ignores_folders_without_an_init(self, mgr, tmp_path, search_path):
        make_addon(tmp_path, "alpha")
        (tmp_path / "__pycache__").mkdir()
        search_path(tmp_path)
        assert sorted(mgr.discover_addons()) == ["alpha"]

    def test_skips_search_paths_that_do_not_exist(self, mgr, tmp_path, search_path):
        make_addon(tmp_path / "present", "alpha")
        search_path(tmp_path / "missing", tmp_path / "present")
        assert sorted(mgr.discover_addons()) == ["alpha"]

    def test_first_match_wins(self, mgr, tmp_path, search_path):
        high = make_addon(tmp_path / "high", "dup")
        make_addon(tmp_path / "low", "dup")
        search_path(tmp_path / "high", tmp_path / "low")
        assert mgr.discover_addons()["dup"] == high

    def test_shadowing_does_not_hide_the_rest_of_the_lower_folder(self, mgr, tmp_path, search_path):
        make_addon(tmp_path / "high", "dup")
        make_addon(tmp_path / "low", "dup")
        make_addon(tmp_path / "low", "only_low")
        search_path(tmp_path / "high", tmp_path / "low")
        found = mgr.discover_addons()
        assert found["dup"] == tmp_path / "high" / "dup"
        assert found["only_low"] == tmp_path / "low" / "only_low"

    def test_the_real_search_path_finds_the_builtins(self, mgr):
        found = mgr.discover_addons()
        for name in ("html", "files", "rtorrent", "ssh", "http", "rssfeed", "string_operations"):
            assert name in found


# ---------------------------------------------------------------------------
# import_addon
# ---------------------------------------------------------------------------

class TestImportAddon:
    def test_module_is_named_after_its_folder(self, mgr, tmp_path):
        module = mgr.import_addon(make_addon(tmp_path, "demo"))
        assert module is not None
        assert module.__name__ == f"{ADDON_NAMESPACE}.demo"

    def test_module_is_registered_in_sys_modules(self, mgr, tmp_path):
        module = mgr.import_addon(make_addon(tmp_path, "demo"))
        assert sys.modules[f"{ADDON_NAMESPACE}.demo"] is module

    def test_two_addons_do_not_share_a_module_name(self, mgr, tmp_path):
        alpha = mgr.import_addon(make_addon(tmp_path, "alpha"))
        beta = mgr.import_addon(make_addon(tmp_path, "beta"))
        assert alpha.__name__ != beta.__name__
        assert (alpha.NAME, beta.NAME) == ("alpha", "beta")

    def test_an_addon_can_import_its_own_helper_files(self, mgr, tmp_path):
        addon = make_addon(tmp_path, "multi", body="from . import helper\nVALUE = helper.VALUE\n")
        (addon / "helper.py").write_text("VALUE = 'from helper'\n")
        module = mgr.import_addon(addon)
        assert module is not None, "relative imports inside an addon should resolve"
        assert module.VALUE == "from helper"

    def test_a_raising_addon_returns_none(self, mgr, tmp_path):
        addon = make_addon(tmp_path, "broken", body="raise RuntimeError('boom')\n")
        assert mgr.import_addon(addon) is None

    def test_a_raising_addon_leaves_nothing_registered(self, mgr, tmp_path):
        mgr.import_addon(make_addon(tmp_path, "broken", body="raise RuntimeError('boom')\n"))
        assert f"{ADDON_NAMESPACE}.broken" not in sys.modules

    def test_a_folder_without_an_init_returns_none(self, mgr, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert mgr.import_addon(empty) is None


# ---------------------------------------------------------------------------
# import_addons
# ---------------------------------------------------------------------------

class TestImportAddons:
    def test_imports_everything_found(self, mgr, tmp_path, search_path):
        make_addon(tmp_path, "alpha")
        make_addon(tmp_path, "beta")
        search_path(tmp_path)
        assert sorted(m.NAME for m in mgr.import_addons()) == ["alpha", "beta"]

    def test_only_the_shadowing_copy_is_imported(self, mgr, tmp_path, search_path):
        make_addon(tmp_path / "high", "dup", body="NAME = 'high'\n")
        make_addon(tmp_path / "low", "dup", body="NAME = 'low'\n")
        search_path(tmp_path / "high", tmp_path / "low")
        assert [m.NAME for m in mgr.import_addons()] == ["high"]

    def test_a_broken_addon_does_not_stop_the_others(self, mgr, tmp_path, search_path):
        make_addon(tmp_path, "good")
        make_addon(tmp_path, "bad", body="raise RuntimeError('boom')\n")
        search_path(tmp_path)
        assert [m.NAME for m in mgr.import_addons()] == ["good"]
