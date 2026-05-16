from io import BytesIO

from builtin_addons.http import http_download_file
from pipeline_backend.commands import CommandReturnStatus
from pipeline_backend.instances import Instance
from pipeline_backend.manager import PipelineManager
from pipeline_backend.variables import Dictionary, String


class FakeResponse:
    status = 200

    def __init__(self, data: bytes):
        self._data = BytesIO(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self._data.read(size)


def make_instance():
    return Instance(PipelineManager().ctx)


async def test_http_download_file_writes_response_and_sends_cookie(monkeypatch, tmp_path):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse(b"downloaded data")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    localpath = tmp_path / "download.bin"

    result = await http_download_file(
        make_instance(),
        Dictionary({"cookie": String("_UserID=1; _SessionID=abc"), "referer": String("https://rtorrent.example/")}),
        String("https://rtorrent.example/download/files/file.mkv"),
        String(str(localpath)),
    )

    assert result == CommandReturnStatus.Success
    assert localpath.read_bytes() == b"downloaded data"
    assert captured["timeout"] == 30
    assert captured["request"].get_header("Cookie") == "_UserID=1; _SessionID=abc"
    assert captured["request"].get_header("Referer") == "https://rtorrent.example/"
