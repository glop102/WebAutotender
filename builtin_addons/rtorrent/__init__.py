from pipeline_backend import *
from pipeline_backend.commands_builtin import *
from pipeline_backend.commands_builtin import yield_for_seconds

import xmlrpc.client
import urllib.request
from time import sleep

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

        return xmlrpc.client.Server(url_filled)

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
    
    def add_url_to_rtorrent(self,url:str|String)->"Torrent":
        """
        Add a torrent file or magnet link to rtorrent
        """
        if isinstance(url,WorkVariable):
            url = url.value
        orig_hashes:list[str] = self.connection.download_list()
        if(url.startswith("http")):
            #workaround for whatbox getting banned from downloading from nyaa.si
            #we download it on the current system and then send the actual file over to rtorrent
            torrentFile = urllib.request.urlopen(url).read()
            self.connection.load.raw_start("",torrentFile)
        else:
            #if it is just a magnet link, then rtorrent already knows how to deal with it
            self.connection.load.start("",url)
        
        while True:
            sleep(0.5)
            new_hashes:list[str] = [h for h in self.connection.download_list() if not h in orig_hashes]
            if len(new_hashes) > 1:
                raise Exception("Error: more than 1 new hash found when adding URL : {}\n{}".format(url, new_hashes))
            elif len(new_hashes) == 1:
                return Torrent(self,new_hashes[0])

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

@Commands.register_command
def rtorrent_add_torrent_to_server(instance:Instance,serverInfo:Dictionary,url:String,outputHashName:VariableName)->CommandReturnStatus:
    server = Server(instance,serverInfo)
    torrent = server.add_url_to_rtorrent(url)
    instance[outputHashName] = String(torrent.infohash)
    return CommandReturnStatus.Success

@Commands.register_command
def rtorrent_wait_until_complete(instance:Instance,serverInfo:Dictionary,infohash:String)->CommandReturnStatus:
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    if torrent.is_complete():
        return CommandReturnStatus.Success
    yield_for_seconds(instance,Integer(30))
    return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position

@Commands.register_command
def rtorrent_wait_until_ratio(instance:Instance,serverInfo:Dictionary,infohash:String,ratio:Float)->CommandReturnStatus:
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    if torrent.get_ratio() >= ratio.value:
        return CommandReturnStatus.Success
    yield_for_seconds(instance,Integer(30))
    return CommandReturnStatus.Yield|CommandReturnStatus.Keep_Position

@Commands.register_command
def rtorrent_set_torrent_label(instance:Instance,serverInfo:Dictionary,infohash:String,label:String)->CommandReturnStatus:
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    torrent.set_label(label.value)
    return CommandReturnStatus.Success

@Commands.register_command
def rtorrent_get_torrent_name(instance:Instance,serverInfo:Dictionary,infohash:String,varnameOut:VariableName)->CommandReturnStatus:
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    name = torrent.get_name()
    instance[varnameOut] = String(name)
    return CommandReturnStatus.Success

@Commands.register_command
def rtorrent_get_torrents_path(instance:Instance,serverInfo:Dictionary,infohash:String,varnameOut:VariableName)->CommandReturnStatus:
    server = Server(instance,serverInfo)
    torrent = Torrent(server,infohash.value)
    path = torrent.get_torrent_basepath()
    instance[varnameOut] = String(path)
    return CommandReturnStatus.Success

@Commands.register_command
def rtorrent_delete_torrent_but_not_files(instance:Instance,serverInfo:Dictionary,infohash:String)->CommandReturnStatus:
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