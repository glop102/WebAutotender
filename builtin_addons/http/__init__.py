from base64 import b64encode
from datetime import datetime
import asyncio
import urllib.error
import urllib.request

from pipeline_backend import *


def _human_readable_filesize(size: int) -> str:
    suffixes = ["B", "KB", "MB", "GB", "TB", "ExB"]
    divcount = 0
    size_float = float(size)
    while size_float > 1000 and divcount < len(suffixes) - 1:
        size_float /= 1000
        divcount += 1
    return f"{size_float:.2f} {suffixes[divcount]}"


def _request_headers(request_info: Dictionary) -> dict[str, str]:
    headers = {
        "Accept-Encoding": "identity",
        "User-Agent": "WebAutotender/1.0",
    }
    if "headers" in request_info.value:
        raw_headers = request_info.value["headers"]
        if isinstance(raw_headers, Dictionary):
            for key, value in raw_headers.value.items():
                headers[str(key)] = str(value.value if isinstance(value, WorkVariable) else value)
    if "cookie" in request_info.value:
        headers["Cookie"] = request_info.value["cookie"].value
    if "Cookie" in request_info.value:
        headers["Cookie"] = request_info.value["Cookie"].value
    if "referer" in request_info.value:
        headers["Referer"] = request_info.value["referer"].value
    if "Referer" in request_info.value:
        headers["Referer"] = request_info.value["Referer"].value
    if "username" in request_info.value and "password" in request_info.value:
        credentials = f"{request_info.value['username'].value}:{request_info.value['password'].value}"
        headers["Authorization"] = "Basic " + b64encode(credentials.encode()).decode()
    return headers


def _download_file(instance: Instance, request_info: Dictionary, url: str, localpath: str) -> CommandReturnStatus:
    request = urllib.request.Request(url, headers=_request_headers(request_info))
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                instance.log_line(f"Error: HTTP download returned status {status} for '{url}'")
                return CommandReturnStatus.Error

            filesize = int(response.headers.get("Content-Length", "0") or 0)
            instance.log_line(f"Downloading '{url}'\nto '{localpath}'")
            if filesize:
                instance.log_line(f"    {_human_readable_filesize(filesize)}")

            starting_time = datetime.now()
            bytesdone = 0
            next_progress = 0.1
            last_time = starting_time
            last_bytes = 0
            with open(localpath, "wb") as outfile:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    outfile.write(chunk)
                    bytesdone += len(chunk)
                    if filesize and bytesdone / filesize >= next_progress:
                        now = datetime.now()
                        elapsed = (now - last_time).total_seconds()
                        bytespersecond = int((bytesdone - last_bytes) / elapsed) if elapsed > 0 else 0
                        instance.log_line(
                            f"    {bytesdone / filesize * 100:3.1f}% : "
                            f"{_human_readable_filesize(bytesdone)} @ {_human_readable_filesize(bytespersecond)}/s"
                        )
                        next_progress = (int(bytesdone / filesize * 10) + 1) / 10.0
                        last_time = now
                        last_bytes = bytesdone

            ending_time = datetime.now()
            elapsed = (ending_time - starting_time).total_seconds()
            bytespersecond = int(bytesdone / elapsed) if elapsed > 0 else 0
            instance.log_line(f"    {_human_readable_filesize(bytespersecond)}/s")
    except urllib.error.HTTPError as e:
        instance.log_line(f"Error: HTTP download returned status {e.code} for '{url}': {e.reason}")
        return CommandReturnStatus.Error
    except Exception as e:
        instance.log_line(f"Error: Unable to download '{url}' to '{localpath}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="HTTP")
async def http_download_file(instance: Instance, requestInfo: Dictionary, url: String, localpath: String) -> CommandReturnStatus:
    """Download a single file from an HTTP/HTTPS URL, following redirects and logging progress.
  requestInfo: Dictionary with optional cookie/Cookie, referer/Referer, username/password, or headers Dictionary.
  url: HTTP/HTTPS URL to download.
  localpath: Local path where the file will be saved."""
    return await asyncio.to_thread(_download_file, instance, requestInfo, url.value, localpath.value)
