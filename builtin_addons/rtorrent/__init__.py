from pipeline_backend import *
from pipeline_backend.commands_builtin import *
from pipeline_backend.commands_builtin import yield_for_seconds

import xmlrpc.client
import urllib.request
from time import sleep

class Torrent:
    server:xmlrpc.client.Server
    infohash:str
    def __init__(self,server:xmlrpc.client.Server,infohash:str):
        self.server = server
        self.infohash = infohash
    def is_complete(self)->bool:
        """
        Query if the torrent is finished downloading. (seed ratios and limits on the server do not prevent it from completing)
        """
        return True if self.server.d.complete(self.infohash) == 1 else False
    def is_multifile(self)->bool:
        """
        Torrents can be either single file or multifile which determines if the files are put in a subfolder.
        A lot of torrents are lsited as multifile even though it contains only a single one though, which is why sometimes they make a folder with the one file inside of it.
        """
        res = int(self.server.d.is_multi_file(self.infohash))
        if res == 1: return True
        return False
    def set_label(self,label:str):
        self.server.d.custom1.set(self.infohash,label)
    def get_name(self)->str:
        return self.server.d.name(self.infohash)
    def get_ratio(self)->float:
        raw_ratio = self.server.d.ratio(self.infohash)
        #docs say it is an int of the ratio multiplied by a thousand, so i need to divide by a thousand to get the real ratio
        return float( raw_ratio ) / 1000.0
    def get_filecount(self)->int:
        return self.server.d.size_files(self.infohash)
    def get_filepaths_absolute(self)->list[str]:
        # filename_glob - glob based filename filtering
        paths = self.server.f.multicall(
            self.infohash,
            "", # filename_glob - just passing in nothing now to get everything
            [ "f.frozen_path=" ]
        )
        return [path[0] for path in paths]
    def get_filepaths_relative(self)->list[str]:
        # filename_glob - glob based filename filtering
        paths = self.server.f.multicall(
            self.infohash,
            "", # filename_glob - just passing in nothing now to get everything
            [ "f.path=" ]
        )
        return [path[0] for path in paths]
    def get_torrent_basepath(self)->str:
        """
        The base path of the torrent is where all files are saved relative too
        """
        path = self.server.d.base_path(self.infohash)
        if path == "":
            print("ERROR : Empty path reported from server : "+self.infohash)
        return path
    def delete_torrent(self):
        """
        Will remove the torrent from rtorrent but leave the files on the server.
        Recomended to either get the list of files or the base path and then delete the files right after deleting the torrent.
        """
        self.server.d.delete_tied(self.infohash)
        self.server.d.erase(self.infohash)

def connect_to_server_basic(url:str,username:str,password:str) -> xmlrpc.client.Server:
    # Unfortunantly, the username:pasword needs to be added to the URL to have xmlrpc auto-login
    # So lets parse out the protocol of the url and insert the credentials in
    proto_idx = url.index("://")+3
    url_filled = url[:proto_idx] + f"{username}:{password}@" + url[proto_idx:]

    return xmlrpc.client.Server(url_filled)

def connect_to_server(instance: Instance, serverInfo: Dictionary)->xmlrpc.client.Server:
    valid = True
    if "URL" not in serverInfo.value:
        instance.log_line("There is no 'URL' in the serverInfo")
        valid = False
    else:
        url = serverInfo.value['URL'].value
    if "username" not in serverInfo.value:
        instance.log_line("There is no 'username' in the serverInfo")
        valid = False
    else:
        username = serverInfo.value['username'].value
    if "password" not in serverInfo.value:
        instance.log_line("There is no 'password' in the serverInfo")
        valid = False
    else:
        password = serverInfo.value['password'].value
    if not valid:
        raise Exception("Insufficent information to log in to rtorrent")

    return connect_to_server_basic(url,username,password)

def get_total_torrents_list(server:xmlrpc.client.Server)->list[Torrent]:
    infohashes = server.download_list()
    return [Torrent(server,infohash) for infohash in infohashes]

def add_url_to_rtorrent(server:xmlrpc.client.Server,url:str)->Torrent:
    """
    Add a torrent file or magnet link to rtorrent
    """
    orig_hashes:list[str] = server.download_list()
    if(url.startswith("http")):
        #workaround for whatbox getting banned from downloading from nyaa.si
        #we download it on the current system and then send the actual file over to rtorrent
        torrentFile = urllib.request.urlopen(url).read()
        server.load.raw_start("",torrentFile)
    else:
        #if it is just a magnet link, then rtorrent already knows how to deal with it
        server.load.start("",url)
    
    while True:
        sleep(0.5)
        new_hashes:list[str] = [h for h in server.download_list() if not h in orig_hashes]
        if len(new_hashes) > 1:
            raise Exception("Error: more than 1 new hash found when adding URL : {}\n{}".format(url, new_hashes))
        elif len(new_hashes) == 1:
            return Torrent(server,new_hashes[0])

@Commands.register_command
def rtorrent_add_torrent_to_server(instance:Instance,serverInfo:Dictionary,url:String,outputHashName:VariableName)->CommandReturnStatus:
    server = connect_to_server(instance,serverInfo)
    torrent = add_url_to_rtorrent(server,url)
    instance[outputHashName] = String(torrent.infohash)
    return CommandReturnStatus.Success

@Commands.register_command
def rtorrent_wait_until_complete(instance:Instance,serverInfo:Dictionary,infohash:String)->CommandReturnStatus:
    server = connect_to_server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    if torrent.is_complete():
        return CommandReturnStatus.Success
    yield_for_seconds(instance,Integer(30))
    return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position

if __name__ == "__main__":
    server = connect_to_server_basic("https://rtorrent.merryfox.box.ca/xmlrpc","username","password")
    print(server.download_list())