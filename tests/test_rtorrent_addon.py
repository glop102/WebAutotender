import asyncio
import threading
import time
import xmlrpc.client

from builtin_addons import rtorrent
from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.instances import Instance
from pipeline_backend.manager import PipelineManager
from pipeline_backend.variables import Dictionary, Float, String, VariablePath


class FakeConnection:
    def __init__(self, ratio=0, delay=0.0, tracker=None, filepaths=None, require_list_multicall=False):
        self.d = FakeDownloadMethods(ratio, delay, tracker)
        self.f = FakeFileMethods(filepaths or [], require_list_multicall)


class FakeDownloadMethods:
    def __init__(self, ratio, delay, tracker):
        self.ratio_value = ratio
        self.delay = delay
        self.tracker = tracker

    def ratio(self, infohash):
        if self.tracker is not None:
            with self.tracker["lock"]:
                self.tracker["active"] += 1
                self.tracker["max_active"] = max(self.tracker["max_active"], self.tracker["active"])
        try:
            time.sleep(self.delay)
            return self.ratio_value
        finally:
            if self.tracker is not None:
                with self.tracker["lock"]:
                    self.tracker["active"] -= 1


class FakeFileMethods:
    def __init__(self, filepaths, require_list_multicall=False):
        self.filepaths = filepaths
        self.require_list_multicall = require_list_multicall

    def multicall(self, infohash, filename_glob, *fields):
        if self.require_list_multicall and not isinstance(fields[0], list):
            raise xmlrpc.client.Fault(-500, "Wrong object type: expected: array actual: string")
        return [[path] for path in self.filepaths]


def make_server_info(url="https://example.invalid/xmlrpc"):
    return Dictionary({
        "URL": String(url),
        "username": String("user"),
        "password": String("password"),
    })


def make_instance():
    return Instance(PipelineManager().ctx)


def patch_connection(monkeypatch, connection):
    monkeypatch.setattr(
        rtorrent.Server,
        "_Server__connect_to_server_basic",
        lambda self, url, username, password: connection,
    )


async def test_wait_until_ratio_does_not_block_event_loop(monkeypatch):
    patch_connection(monkeypatch, FakeConnection(ratio=0, delay=0.05))

    task = asyncio.create_task(rtorrent.rtorrent_wait_until_ratio(
        make_instance(),
        make_server_info("https://event-loop-test.invalid/xmlrpc"),
        String("hash"),
        Float(5.0),
    ))

    await asyncio.sleep(0.01)

    assert not task.done()
    assert await task == CommandReturnStatus.Yield | CommandReturnStatus.Keep_Position


async def test_wait_until_ratio_serializes_calls_per_server(monkeypatch):
    tracker = {"active": 0, "max_active": 0, "lock": threading.Lock()}
    patch_connection(monkeypatch, FakeConnection(ratio=0, delay=0.02, tracker=tracker))
    server_info = make_server_info("https://serialized-test.invalid/xmlrpc")

    results = await asyncio.gather(
        rtorrent.rtorrent_wait_until_ratio(make_instance(), server_info, String("hash-1"), Float(5.0)),
        rtorrent.rtorrent_wait_until_ratio(make_instance(), server_info, String("hash-2"), Float(5.0)),
    )

    assert results == [
        CommandReturnStatus.Yield | CommandReturnStatus.Keep_Position,
        CommandReturnStatus.Yield | CommandReturnStatus.Keep_Position,
    ]
    assert tracker["max_active"] == 1


async def test_get_torrent_download_url_encodes_relative_file_path(monkeypatch):
    patch_connection(monkeypatch, FakeConnection(filepaths=["[SubsPlease] Jigokuraku - 23 (1080p) [B7561A67].mkv"]))
    instance = make_instance()

    result = await rtorrent.rtorrent_get_torrent_download_url(
        instance,
        make_server_info("https://download-url-test.invalid/xmlrpc"),
        String("hash"),
        String("https://rtorrent.example/download/files/"),
        VariablePath("download_url"),
    )

    assert result == CommandReturnStatus.Success
    assert instance.variables["download_url"].value == (
        "https://rtorrent.example/download/files/"
        "%5BSubsPlease%5D%20Jigokuraku%20-%2023%20%281080p%29%20%5BB7561A67%5D.mkv"
    )


async def test_get_torrent_download_url_errors_for_multifile_torrent(monkeypatch):
    patch_connection(monkeypatch, FakeConnection(filepaths=["folder/a.mkv", "folder/b.mkv"]))

    result = await rtorrent.rtorrent_get_torrent_download_url(
        make_instance(),
        make_server_info("https://multifile-test.invalid/xmlrpc"),
        String("hash"),
        String("https://rtorrent.example/download/files"),
        VariablePath("download_url"),
    )

    assert result == CommandReturnStatus.Error


async def test_get_torrent_download_url_falls_back_to_list_multicall(monkeypatch):
    patch_connection(monkeypatch, FakeConnection(
        filepaths=["single.mkv"],
        require_list_multicall=True,
    ))
    instance = make_instance()

    result = await rtorrent.rtorrent_get_torrent_download_url(
        instance,
        make_server_info("https://list-multicall-test.invalid/xmlrpc"),
        String("hash"),
        String("https://rtorrent.example/download/files"),
        VariablePath("download_url"),
    )

    assert result == CommandReturnStatus.Success
    assert instance.variables["download_url"].value == "https://rtorrent.example/download/files/single.mkv"
