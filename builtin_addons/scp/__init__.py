from functools import partial

from pipeline_backend import *
from pipeline_backend.commands_builtin import *
import asyncssh
from datetime import datetime

"""
We assume that the account information that we need is passed in as a Dictionary.
This should have the following variables inside of it:
 - "URL" -> String
 - "username" -> String
 - "password" or "ssh key" of "ssh key filepath"-> String
    - password is a raw password, ssh key is the contents of a private key file (PEM format), and the filepath is a tring filepath to look read the key from
"""

async def open_ssh_pipe(instance: Instance, serverInfo: Dictionary)->None|asyncssh.SSHClientConnection:
    valid = True
    if "URL" not in serverInfo.value:
        instance.log_line("There is no 'URL' in the serverInfo")
        valid = False
    if "username" not in serverInfo.value:
        instance.log_line("There is no 'username' in the serverInfo")
        valid = False
    if "password" not in serverInfo.value and "ssh key" not in serverInfo.value and "ssh key filepath" not in serverInfo.value:
        instance.log_line("There is no 'password' or 'ssh key' or 'ssh key filepath' in the serverInfo")
        valid = False
    if not valid: return None

    # prioritize using an ssh key if both that and a password has been specified
    if "ssh key filepath" in serverInfo.value:
        return await asyncssh.connect(
            serverInfo.value["URL"].value,
            username=serverInfo.value["username"].value,
            client_keys=[serverInfo.value["ssh key filepath"].value]
        )
    elif "ssh key" in serverInfo.value:
        keyfile = parse_ssh_private_key(serverInfo.value["ssh key"].value)
        return await asyncssh.connect(
            serverInfo.value["URL"].value,
            username=serverInfo.value["username"].value,
            client_keys=[keyfile]
        )
    else:
        return await asyncssh.connect(
            serverInfo.value["URL"].value,
            username=serverInfo.value["username"].value,
            password=serverInfo.value["password"].value,
        )

def parse_ssh_private_key(key:str)->asyncssh.SSHKey:
    # Due to the nature of the web interface input, it strips all the newlines.
    # As such we need to pull the openssh header and footer out of the data stream before handing it asyncssh to parse
    # eg -----BEGIN OPENSSH PRIVATE KEY----- needs to be on a line by itself
    # key = key.replace(" ","")
    wrapper = "-----"
    header_end = key.find(wrapper,len(wrapper))+len(wrapper)
    footer_start = key.find(wrapper,header_end+len(wrapper))
    key = key[:footer_start] + "\n" + key[footer_start:]
    key = key[:header_end] + "\n" + key[header_end:]
    return asyncssh.import_private_key(key)

def human_readable_filesize(size:int)->str:
    suffixes = ["B","KB","MB","GB","TB","ExB"]
    divcount = 0
    while (size > 1000 and divcount < len(suffixes)):
        size /= 1000
        divcount += 1
    
    return f"{size:.2f} {suffixes[divcount]}"

def file_download_progress_callback(instance:Instance,print_thresholds:list[int],sourcepath:bytes,destpath:bytes,bytesdone:int,bytestotal:int):
    # print(f"\033[K\r{sourcepath.decode() } - {bytesdone}/{bytestotal}", end="\r", flush=True)
    if len(print_thresholds) == 0:
        return
    smallest = print_thresholds[0]
    if bytesdone > smallest:
        instance.log_line(f"    {(bytesdone/bytestotal)*100:3.1f}% : {human_readable_filesize(bytesdone)}")
        print_thresholds[:] = print_thresholds[1:]

@Commands.register_command
async def sftp_list_directory(instance: Instance, serverInfo: Dictionary, directory: String, outputVarname: VariableName) -> CommandReturnStatus:
    connection:asyncssh.SSHClientConnection = await open_ssh_pipe(instance,serverInfo)
    if not connection:
        return CommandReturnStatus.Error
    sftp:asyncssh.SFTPClient = await connection.start_sftp_client()
    entries = await sftp.listdir(directory.value)
    instance[outputVarname] = StringList(entries)

    return CommandReturnStatus.Success

@Commands.register_command
async def sftp_download_file(instance: Instance, serverInfo: Dictionary, remotepath: String, localpath: String) -> CommandReturnStatus:
    connection:asyncssh.SSHClientConnection = await open_ssh_pipe(instance,serverInfo)
    if not connection:
        return CommandReturnStatus.Error
    sftp:asyncssh.SFTPClient = await connection.start_sftp_client()
    if not await sftp.exists(remotepath.value):
        instance.log_line(f"Unable to find remote file '{remotepath.value}'")
        return CommandReturnStatus.Error
    filesize = await sftp.getsize(remotepath.value)
    print_thresholds = [x*(filesize//10) for x in range(1,10)]

    instance.log_line(f"Downloading '{remotepath.value}'\nto '{localpath.value}'")
    instance.log_line(f"    {human_readable_filesize(filesize)}")

    starting_time = datetime.now()
    await sftp.get(
        remotepath.value,
        localpath.value,
        recurse=False,
        progress_handler=partial(file_download_progress_callback,instance,print_thresholds),
    )
    ending_time = datetime.now()
    bytespersecond = filesize//(ending_time - starting_time).total_seconds()
    instance.log_line(f"    {human_readable_filesize(bytespersecond)}/s")

    return CommandReturnStatus.Success