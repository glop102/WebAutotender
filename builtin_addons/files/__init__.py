import os
import shutil
from pipeline_backend import *
from pipeline_backend.variables import Boolean
from pipeline_backend.commands_builtin import jump_to_procedure


@Commands.register_command(category="Files")
def move_file(instance: Instance, source: String, destination: String) -> CommandReturnStatus:
    """Move or rename a file or directory. Works across filesystems.
  source: Path to the file or directory to move.
  destination: Destination path (including the new name if renaming)."""
    try:
        shutil.move(source.value, destination.value)
    except Exception as e:
        instance.log_line(f"Error: Unable to move '{source.value}' to '{destination.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def delete_file(instance: Instance, path: String) -> CommandReturnStatus:
    """Delete a single file. Errors if the path does not exist or is a directory.
  path: Path to the file to delete."""
    try:
        os.remove(path.value)
    except Exception as e:
        instance.log_line(f"Error: Unable to delete file '{path.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def delete_folder(instance: Instance, path: String) -> CommandReturnStatus:
    """Recursively delete a folder and all its contents. Errors if the path does not exist.
  path: Path to the folder to delete."""
    try:
        shutil.rmtree(path.value)
    except Exception as e:
        instance.log_line(f"Error: Unable to delete folder '{path.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def create_folder(instance: Instance, path: String) -> CommandReturnStatus:
    """Create a folder and any missing parent directories. Does nothing if the folder already exists.
  path: Path of the folder to create."""
    try:
        os.makedirs(path.value, exist_ok=True)
    except Exception as e:
        instance.log_line(f"Error: Unable to create folder '{path.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def file_exists(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    """Check whether a path exists (file or folder) and store the result as a Boolean.
  path: The path to check.
  output_varname: Name of the variable to store the Boolean result in."""
    instance[output_varname] = Boolean(os.path.exists(path.value))
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def is_file(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    """Check whether a path points to a regular file and store the result as a Boolean.
  path: The path to check.
  output_varname: Name of the variable to store the Boolean result in."""
    instance[output_varname] = Boolean(os.path.isfile(path.value))
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def is_folder(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    """Check whether a path points to a directory and store the result as a Boolean.
  path: The path to check.
  output_varname: Name of the variable to store the Boolean result in."""
    instance[output_varname] = Boolean(os.path.isdir(path.value))
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def goto_if_file(instance: Instance, procedure_name: String, path: String) -> CommandReturnStatus:
    """Jump to a procedure if the given path is a regular file. Continues to the next step otherwise.
  procedure_name: Name of the procedure to jump to when the file exists.
  path: The path to check."""
    if os.path.isfile(path.value):
        return jump_to_procedure(instance, procedure_name)
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def goto_if_folder(instance: Instance, procedure_name: String, path: String) -> CommandReturnStatus:
    """Jump to a procedure if the given path is a directory. Continues to the next step otherwise.
  procedure_name: Name of the procedure to jump to when the folder exists.
  path: The path to check."""
    if os.path.isdir(path.value):
        return jump_to_procedure(instance, procedure_name)
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def list_folder_contents(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    """List the names of entries in a folder and store them as a sorted StringList.
  path: Path to the folder to list.
  output_varname: Name of the variable to store the StringList of entry names in."""
    try:
        entries = sorted(os.listdir(path.value))
    except Exception as e:
        instance.log_line(f"Error: Unable to list folder '{path.value}': {e}")
        return CommandReturnStatus.Error
    instance[output_varname] = StringList(entries)
    return CommandReturnStatus.Success
