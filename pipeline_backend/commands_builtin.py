from .commands import *
from .variables import *
from .instances import *
from .workflows import *
from datetime import datetime,timedelta
import re

# Some built in commands that we will need to have
# goto_if_equal/notequal/greaterthan/lessthan(var1,var2,destination_precedure_name)
# string_builder(stringlist_commands,destination_var) - takes in strings and combines it together with some operations on segments like leftpad() so we can get a complicated string built up

# TODO! Have a doc string with all of these commands and then also have the commands registry have a function to pull those doc strings to serve as hints or instructions that get sent to the UI
# This way even addons can provide information for registered commands.

# ====================================================================
# State control of instances
# ====================================================================

@Commands.register_command
def yield_for_minutes(instance:Instance,num_minutes:Integer)->CommandReturnStatus:
    instance.next_processing_time = datetime.now() + timedelta(minutes=num_minutes.value)
    return CommandReturnStatus.Yield

@Commands.register_command
def yield_until(instance: Instance, iso_datetime:String) -> CommandReturnStatus:
    instance.next_processing_time = datetime.fromisoformat(iso_datetime.value)
    return CommandReturnStatus.Yield

@Commands.register_command
def delete_this_instance(instance: Instance) -> CommandReturnStatus:
    if not instance in global_instances:
        instance.log_line(f"Error: Unable to delete an instance that is not in the global_instances array. The pipeline lib only supports a single global pipeline state for many operations.")
        return CommandReturnStatus.Error
    global_instances.remove(instance)
    return CommandReturnStatus.Yield

@Commands.register_command
def make_new_instance(instance: Instance, workflow_name:String, setup_vars:Dictionary) -> CommandReturnStatus:
    try:
        workflow = Workflow.get_by_name(workflow_name.value)
    except:
        instance.log_line(f"Error: Unable to find a Workflow with the name {workflow_name} to spawn an instance of.")
        return CommandReturnStatus.Error
    workflow.spawn_instance(setup_vars.value)
    return CommandReturnStatus.Success

# ====================================================================
# Logging and Messages
# ====================================================================

@Commands.register_command
def log(instance: Instance, msg: String) -> CommandReturnStatus:
    instance.log_line(msg.value)
    return CommandReturnStatus.Success

@Commands.register_command
def error(instance: Instance, msg: String) -> CommandReturnStatus:
    instance.log_line(msg.value)
    return CommandReturnStatus.Error

# TODO - Have string formatting versions so it can print variables and whatnot inbetween
# Maybe have it follow the python formatting style and then somehow have python give the contents of the replacment groups for me to then safely implement string formatting?

# ====================================================================
# conditionals and branches
# ====================================================================

@Commands.register_command
def jump_to_procedure(instance: Instance, procedure_name: String) -> CommandReturnStatus:
    workflow = instance.get_associated_workflow()
    if not procedure_name in workflow.procedures:
        instance.log_line(f"Error: Cannot jump to the procedure {procedure_name} because it does not exist in the workflow {instance.workflow_name}")
        return CommandReturnStatus.Error
    instance.processing_step = (procedure_name.value,0)
    return CommandReturnStatus.Success

# ====================================================================
# Utilities
# ====================================================================

@Commands.register_command
def regex_first_match(instance: Instance, format_string: String, input_string: String, output_variable:VariableName) -> CommandReturnStatus:
    matcher = re.compile(format_string.value)
    first_match = matcher.search(input_string.value)
    if not first_match:
        instance.log_line(f"Error: Unable to find a match of {format_string} on the input {input_string}")
        return CommandReturnStatus.Error

    instance[output_variable.value] = String(first_match.group())
    return CommandReturnStatus.Success

@Commands.register_command
def regex_match_all(instance: Instance, format_string: String, input_string: String, output_variable: VariableName) -> CommandReturnStatus:
    matcher = re.compile(format_string.value)
    matches = matcher.findall(input_string.value)
    # I think we can trust prople handling when the list of matches is 0 length. It is still a list after all.
    # if len(matches) == 0:
    #     instance.log_line(
    #         f"Error: Unable to find a match of {format_string} on the input {input_string}")
    #     return CommandReturnStatus.Error

    instance[output_variable.value] = StringList(matches)
    return CommandReturnStatus.Success

@Commands.register_command
def set_variable_value(instance: Instance, variable_name: VariableName, value:WorkVariable) -> CommandReturnStatus:
    instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command
def set_variable_value_in_another_instance(instance: Instance, instance_uuid:String, variable_name: VariableName, value: WorkVariable) -> CommandReturnStatus:
    other_instance = Instance.get_by_uuid(instance_uuid.value)
    other_instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command
def save_uuid_to_variables(instance: Instance) -> CommandReturnStatus:
    instance["uuid"] = String(instance.uuid)
    return CommandReturnStatus.Success