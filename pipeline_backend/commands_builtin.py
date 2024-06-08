from .commands import *
from .variables import *
from .instances import *
from .workflows import *
from datetime import datetime,timedelta
import re

# Some built in commands that we will need to have
# string_builder(stringlist_commands,destination_var) - takes in strings and combines it together with some operations on segments like leftpad() so we can get a complicated string built up

# TODO! Have a doc string with all of these commands and then also have the commands registry have a function to pull those doc strings to serve as hints or instructions that get sent to the UI
# This way even addons can provide information for registered commands.

# ====================================================================
# State control of instances
# ====================================================================

@Commands.register_command
def yield_for_seconds(instance:Instance,num_seconds:Integer|Float)->CommandReturnStatus:
    instance.next_processing_time = datetime.now() + timedelta(seconds=num_seconds.value)
    return CommandReturnStatus.Yield

@Commands.register_command
def yield_for_minutes(instance:Instance,num_minutes:Integer|Float)->CommandReturnStatus:
    instance.next_processing_time = datetime.now() + timedelta(minutes=num_minutes.value)
    return CommandReturnStatus.Yield

@Commands.register_command
def yield_until(instance: Instance, iso_datetime:String) -> CommandReturnStatus:
    instance.next_processing_time = datetime.fromisoformat(iso_datetime.value)
    return CommandReturnStatus.Yield

@Commands.register_command
def delete_this_instance(instance: Instance) -> CommandReturnStatus:
    if not instance.uuid in global_instances:
        instance.log_line(f"Error: Unable to delete an instance that is not in the global_instances dictionary. The pipeline lib only supports a single global pipeline state for many operations.")
        return CommandReturnStatus.Error
    del global_instances[instance.uuid]
    return CommandReturnStatus.Yield

@Commands.register_command
def make_new_instance(instance: Instance, workflow_uuid:String, setup_vars:Dictionary) -> CommandReturnStatus:
    if not workflow_uuid.value in global_workflows:
        instance.log_line(f"Error: Unable to find a Workflow with the uuid {workflow_uuid.value} to spawn an instance of.")
        return CommandReturnStatus.Error
    #TODO Uhhhh... what do we do to pull values *out* of the source workflow? And VariableReference in the Dictionary will only point at the new workflow, so pulling values from the source instance/workflow like a show title will not work.
    #Maybe it would be easiest to follow the workflow thought of having constants and references. The references get added to the constants before handing it to the workflow we are spawning. Obviously dereference the references.
    workflow = global_workflows[workflow_uuid.value]
    workflow.spawn_instance(setup_vars.value)
    return CommandReturnStatus.Success

@Commands.register_command
def pause_this_instance(instance: Instance) -> CommandReturnStatus:
    instance.state = RunStates.Paused
    return CommandReturnStatus.Yield

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
    if not procedure_name.value in workflow.procedures:
        instance.log_line(f"Error: Cannot jump to the procedure {procedure_name} because it does not exist in the workflow {instance.workflow_uuid}")
        return CommandReturnStatus.Error
    instance.processing_step = (procedure_name.value,0)
    return CommandReturnStatus.Success | CommandReturnStatus.Keep_Position

@Commands.register_command
def goto_if_equal(instance: Instance, procedure_name: String, value1:WorkVariable, value2:WorkVariable) -> CommandReturnStatus:
    while type(value1) == VariableName:
        value1 = instance[value1.value]
    while type(value2) == VariableName:
        value2 = instance[value2.value]
    
    if type(value1) == type(value2) and value1.value == value2.value:
        return jump_to_procedure(instance,procedure_name)
    if str(value1.value) == str(value2.value):
        return jump_to_procedure(instance, procedure_name)

    # Nothing was equal so continue without jumping
    return CommandReturnStatus.Success


@Commands.register_command
def goto_if_not_equal(instance: Instance, procedure_name: String, value1: WorkVariable, value2: WorkVariable) -> CommandReturnStatus:
    while type(value1) == VariableName:
        value1 = instance[value1.value]
    while type(value2) == VariableName:
        value2 = instance[value2.value]

    if type(value1) == type(value2) and value1.value != value2.value:
        return jump_to_procedure(instance, procedure_name)
    if str(value1.value) != str(value2.value):
        return jump_to_procedure(instance, procedure_name)

    return CommandReturnStatus.Success

@Commands.register_command
def goto_if_first_larger(instance: Instance, procedure_name: String, value1: Integer|Float, value2: Integer|Float) -> CommandReturnStatus:
    if value1.value > value2.value:
        return jump_to_procedure(instance, procedure_name)

    return CommandReturnStatus.Success

# ====================================================================
# Basic Math
# ====================================================================

@Commands.register_command
def math_add(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value += second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command
def math_subtract(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value -= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command
def math_multiply(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value *= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command
def math_divide(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value /= second.value
    instance[output_variable] = first
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
    if not instance_uuid.value in global_instances:
        instance.log_line(f"Unable to find an instance with the UUID {instance_uuid.value} to set a variable in")
        return CommandReturnStatus.Error
    other_instance = global_instances[instance_uuid.value]
    other_instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command
def save_uuid_to_variables(instance: Instance) -> CommandReturnStatus:
    instance["uuid"] = String(instance.uuid)
    return CommandReturnStatus.Success
