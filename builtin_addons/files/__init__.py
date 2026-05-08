import os
import shutil
from pipeline_backend import *
from pipeline_backend.variables import Boolean
from pipeline_backend.commands_builtin import jump_to_procedure


@Commands.register_command(category="Files")
def move_file(instance: Instance, source: String, destination: String) -> CommandReturnStatus:
    try:
        shutil.move(source.value, destination.value)
    except Exception as e:
        instance.log_line(f"Error: Unable to move '{source.value}' to '{destination.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def delete_file(instance: Instance, path: String) -> CommandReturnStatus:
    try:
        os.remove(path.value)
    except Exception as e:
        instance.log_line(f"Error: Unable to delete file '{path.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def delete_folder(instance: Instance, path: String) -> CommandReturnStatus:
    try:
        shutil.rmtree(path.value)
    except Exception as e:
        instance.log_line(f"Error: Unable to delete folder '{path.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def create_folder(instance: Instance, path: String) -> CommandReturnStatus:
    try:
        os.makedirs(path.value, exist_ok=True)
    except Exception as e:
        instance.log_line(f"Error: Unable to create folder '{path.value}': {e}")
        return CommandReturnStatus.Error
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def file_exists(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    instance[output_varname] = Boolean(os.path.exists(path.value))
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def is_file(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    instance[output_varname] = Boolean(os.path.isfile(path.value))
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def is_folder(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    instance[output_varname] = Boolean(os.path.isdir(path.value))
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def goto_if_file(instance: Instance, procedure_name: String, path: String) -> CommandReturnStatus:
    if os.path.isfile(path.value):
        return jump_to_procedure(instance, procedure_name)
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def goto_if_folder(instance: Instance, procedure_name: String, path: String) -> CommandReturnStatus:
    if os.path.isdir(path.value):
        return jump_to_procedure(instance, procedure_name)
    return CommandReturnStatus.Success


@Commands.register_command(category="Files")
def list_folder_contents(instance: Instance, path: String, output_varname: VariableName) -> CommandReturnStatus:
    try:
        entries = sorted(os.listdir(path.value))
    except Exception as e:
        instance.log_line(f"Error: Unable to list folder '{path.value}': {e}")
        return CommandReturnStatus.Error
    instance[output_varname] = StringList(entries)
    return CommandReturnStatus.Success
