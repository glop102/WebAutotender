from pipeline_backend import *
from pipeline_backend.commands_builtin import *
from pipeline_backend.commands_builtin import yield_for_seconds

import asyncio
import hashlib
import http.client
import urllib.parse
import xmlrpc.client
import urllib.request

class _TimeoutTransport(xmlrpc.client.SafeTransport):
    def __init__(self, timeout:int, **kwargs):
        super().__init__(**kwargs)
        self._timeout = timeout
    def make_connection(self, host):
        conn = super().make_connection(host)
        conn.timeout = self._timeout
        return conn

def _bencode_find_end(data: bytes, start: int) -> int:
    """Return the index just past the end of the bencoded value starting at data[start]."""
    c = data[start:start+1]
    if c == b'i':
        return data.index(b'e', start + 1) + 1
    elif c in (b'd', b'l'):
        pos = start + 1
        while data[pos:pos+1] != b'e':
            pos = _bencode_find_end(data, pos)
        return pos + 1
    elif c.isdigit():
        colon = data.index(b':', start)
        length = int(data[start:colon])
        return colon + 1 + length
    raise ValueError(f"Invalid bencode byte {c!r} at position {start}")

def _infohash_from_torrent_bytes(data: bytes) -> str:
    """Compute the infohash of a .torrent file from its raw bytes."""
    info_key = b"4:info"
    idx = data.find(info_key)
    if idx == -1:
        raise ValueError("No 'info' key found — not a valid .torrent file")
    info_start = idx + len(info_key)
    info_end = _bencode_find_end(data, info_start)
    return hashlib.sha1(data[info_start:info_end]).hexdigest().upper()

def _infohash_from_magnet(magnet: str) -> str:
    """Extract the infohash from a magnet URI."""
    import base64
    params = urllib.parse.parse_qs(urllib.parse.urlparse(magnet).query)
    xt = params.get('xt', [''])[0]
    if not xt.startswith('urn:btih:'):
        raise ValueError(f"Cannot extract infohash from magnet: {magnet}")
    h = xt[9:]
    if len(h) == 32:  # base32-encoded
        return base64.b32decode(h.upper()).hex().upper()
    return h.upper()


class Server:
    instance:Instance
    serverInfo:Dictionary
    connection:xmlrpc.client
    def __init__(self, instance:Instance, serverInfo:Dictionary):
        self.instance = instance # Mostly just need the instance for logging
        self.serverInfo = serverInfo
        self.connection = self.__connect_to_server()
    
    def __connect_to_server_basic(self, url:str,username:str,password:str) -> xmlrpc.client.Server:
        # Unfortunantly, the username:pasword needs to be added to the URL to have xmlrpc auto-login
        # So lets parse out the protocol of the url and insert the credentials in
        proto_idx = url.index("://")+3
        url_filled = url[:proto_idx] + f"{username}:{password}@" + url[proto_idx:]

        transport = _TimeoutTransport(timeout=10)
        return xmlrpc.client.Server(url_filled, transport=transport)

    def __connect_to_server(self)->xmlrpc.client.Server:
        valid = True
        if "URL" not in self.serverInfo.value:
            self.instance.log_line("There is no 'URL' in the serverInfo")
            valid = False
        else:
            url = self.serverInfo.value['URL'].value
        if "username" not in self.serverInfo.value:
            self.instance.log_line("There is no 'username' in the serverInfo")
            valid = False
        else:
            username =self.serverInfo.value['username'].value
        if "password" not in self.serverInfo.value:
            self.instance.log_line("There is no 'password' in the serverInfo")
            valid = False
        else:
            password = self.serverInfo.value['password'].value
        if not valid:
            raise Exception("Insufficent information to log in to rtorrent")

        return self.__connect_to_server_basic(url,username,password)
    
    def get_total_torrents_list(self)->list["Torrent"]:
        infohashes = self.connection.download_list()
        return [Torrent(self,infohash) for infohash in infohashes]
    
    async def add_url_to_rtorrent(self, url: str|String) -> "Torrent":
        """Add a torrent file URL or magnet link to rtorrent.
        The infohash is computed locally from the torrent bytes (or extracted from the
        magnet URI) before submission, then we poll until rtorrent registers it."""
        if isinstance(url, WorkVariable):
            url = url.value
        if url.startswith("magnet:"):
            infohash = _infohash_from_magnet(url)
            self.connection.load.start("", url)
        else:
            # workaround for whatbox getting banned from downloading from nyaa.si:
            # download the torrent file here and push the raw bytes to rtorrent
            torrent_bytes = urllib.request.urlopen(url).read()
            infohash = _infohash_from_torrent_bytes(torrent_bytes)
            self.connection.load.raw_start("", torrent_bytes)
        while infohash not in self.connection.download_list():
            await asyncio.sleep(0.1)
        return Torrent(self, infohash)

class Torrent:
    server:Server
    infohash:str
    def __init__(self,server:Server,infohash:str):
        self.server = server
        self.infohash = infohash
    def is_complete(self)->bool:
        """
        Query if the torrent is finished downloading. (seed ratios and limits on the server do not prevent it from completing)
        """
        return True if self.server.connection.d.complete(self.infohash) == 1 else False
    def is_multifile(self)->bool:
        """
        Torrents can be either single file or multifile which determines if the files are put in a subfolder.
        A lot of torrents are lsited as multifile even though it contains only a single one though, which is why sometimes they make a folder with the one file inside of it.
        """
        res = int(self.server.connection.d.is_multi_file(self.infohash))
        if res == 1: return True
        return False
    def set_label(self,label:str):
        self.server.connection.d.custom1.set(self.infohash,label)
    def get_name(self)->str:
        return self.server.connection.d.name(self.infohash)
    def get_ratio(self)->float:
        raw_ratio = self.server.connection.d.ratio(self.infohash)
        #docs say it is an int of the ratio multiplied by a thousand, so i need to divide by a thousand to get the real ratio
        return float( raw_ratio ) / 1000.0
    def get_filecount(self)->int:
        return self.server.connection.d.size_files(self.infohash)
    def get_filepaths_absolute(self)->list[str]:
        # filename_glob - glob based filename filtering
        paths = self.server.connection.f.multicall(
            self.infohash,
            "", # filename_glob - just passing in nothing now to get everything
            [ "f.frozen_path=" ]
        )
        return [path[0] for path in paths]
    def get_filepaths_relative(self)->list[str]:
        # filename_glob - glob based filename filtering
        paths = self.server.connection.f.multicall(
            self.infohash,
            "", # filename_glob - just passing in nothing now to get everything
            [ "f.path=" ]
        )
        return [path[0] for path in paths]
    def get_torrent_basepath(self)->str:
        """
        The base path of the torrent is where all files are saved relative too
        """
        path = self.server.connection.d.base_path(self.infohash)
        if path == "":
            print("ERROR : Empty path reported from server : "+self.infohash)
        return path
    def delete_torrent(self):
        """
        Will remove the torrent from rtorrent but leave the files on the server.
        Recomended to either get the list of files or the base path and then delete the files right after deleting the torrent.
        """
        self.server.connection.d.delete_tied(self.infohash)
        self.server.connection.d.erase(self.infohash)

@Commands.register_command(category="rTorrent")
async def rtorrent_add_torrent_to_server(instance:Instance,serverInfo:Dictionary,url:String,outputHashName:VariablePath)->CommandReturnStatus:
    """Add a torrent URL or magnet link to an rTorrent server and store the resulting infohash.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  url: HTTP/HTTPS URL to a .torrent file, or a magnet link.
  outputHashName: Name of the variable to store the torrent infohash string in."""
    server = Server(instance,serverInfo)
    torrent = await server.add_url_to_rtorrent(url)
    instance[outputHashName] = String(torrent.infohash)
    return CommandReturnStatus.Success

@Commands.register_command(category="rTorrent")
def rtorrent_wait_until_complete(instance:Instance,serverInfo:Dictionary,infohash:String)->CommandReturnStatus:
    """Yield and re-check every 30 seconds until a torrent finishes downloading.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  infohash: The infohash string of the torrent to wait on."""
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    try:
        complete = torrent.is_complete()
    except OSError as e:
        instance.log_line(f"Connection error checking torrent completion, will retry: {e}")
        yield_for_seconds(instance,Integer(30))
        return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position
    if complete:
        return CommandReturnStatus.Success
    yield_for_seconds(instance,Integer(30))
    return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position

@Commands.register_command(category="rTorrent")
def rtorrent_wait_until_ratio(instance:Instance,serverInfo:Dictionary,infohash:String,ratio:Float)->CommandReturnStatus:
    """Yield and re-check every 30 seconds until a torrent's seed ratio reaches the target.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  infohash: The infohash string of the torrent to wait on.
  ratio: The minimum seed ratio to wait for (e.g. 1.0 for 1:1)."""
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    try:
        current_ratio = torrent.get_ratio()
    except OSError as e:
        instance.log_line(f"Connection error checking torrent ratio, will retry: {e}")
        yield_for_seconds(instance,Integer(30))
        return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position
    if current_ratio >= ratio.value:
        return CommandReturnStatus.Success
    yield_for_seconds(instance,Integer(300))
    return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position

@Commands.register_command(category="rTorrent")
def rtorrent_set_torrent_label(instance:Instance,serverInfo:Dictionary,infohash:String,label:String)->CommandReturnStatus:
    """Set the custom label (custom1) on a torrent in rTorrent.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  infohash: The infohash string of the torrent to label.
  label: The label string to assign."""
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    torrent.set_label(label.value)
    return CommandReturnStatus.Success

@Commands.register_command(category="rTorrent")
def rtorrent_get_torrent_name(instance:Instance,serverInfo:Dictionary,infohash:String,varnameOut:VariablePath)->CommandReturnStatus:
    """Retrieve the display name of a torrent and store it in a variable.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  infohash: The infohash string of the torrent.
  varnameOut: Name of the variable to store the torrent name string in."""
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    name = torrent.get_name()
    instance[varnameOut] = String(name)
    return CommandReturnStatus.Success

@Commands.register_command(category="rTorrent")
def rtorrent_get_torrents_path(instance:Instance,serverInfo:Dictionary,infohash:String,varnameOut:VariablePath)->CommandReturnStatus:
    """Retrieve the base download path of a torrent (where its files are saved) and store it in a variable.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  infohash: The infohash string of the torrent.
  varnameOut: Name of the variable to store the base path string in."""
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    path = torrent.get_torrent_basepath()
    instance[varnameOut] = String(path)
    return CommandReturnStatus.Success

@Commands.register_command(category="rTorrent")
def rtorrent_delete_torrent_but_not_files(instance:Instance,serverInfo:Dictionary,infohash:String)->CommandReturnStatus:
    """Remove a torrent from rTorrent without deleting the downloaded files on the server.
  serverInfo: Dictionary with keys URL, username, and password for the rTorrent XMLRPC endpoint.
  infohash: The infohash string of the torrent to remove."""
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    torrent.delete_torrent()
    return CommandReturnStatus.Success

if __name__ == "__main__":
    serverInfo = Dictionary(
        {
            "URL": String("https://rtorrent.merryfox.box.ca/xmlrpc"),
            "username": String("username"),
            "password": String("password"),
        }
    )
    server = Server(None,serverInfo)
    print(server.download_list())