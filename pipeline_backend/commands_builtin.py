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

@Commands.register_command(category="Core")
def yield_for_seconds(instance:Instance,num_seconds:Integer|Float)->CommandReturnStatus:
    instance.next_processing_time = datetime.now() + timedelta(seconds=num_seconds.value)
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def yield_for_minutes(instance:Instance,num_minutes:Integer|Float)->CommandReturnStatus:
    instance.next_processing_time = datetime.now() + timedelta(minutes=num_minutes.value)
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def yield_until(instance: Instance, iso_datetime:String) -> CommandReturnStatus:
    instance.next_processing_time = datetime.fromisoformat(iso_datetime.value)
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def delete_this_instance(instance: Instance) -> CommandReturnStatus:
    if not instance.uuid in global_instances:
        instance.log_line(f"Error: Unable to delete an instance that is not in the global_instances dictionary. The pipeline lib only supports a single global pipeline state for many operations.")
        return CommandReturnStatus.Error
    del global_instances[instance.uuid]
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def make_new_instance(instance: Instance, workflow_uuid:String, setup_vars:Dictionary) -> CommandReturnStatus:
    if not workflow_uuid.value in global_workflows:
        instance.log_line(f"Error: Unable to find a Workflow with the uuid {workflow_uuid.value} to spawn an instance of.")
        return CommandReturnStatus.Error
    #TODO VariableName values inside setup_vars are ambiguous in intent. There are three valid cases:
    #  1. Dereference from the calling instance (e.g. pass the current value of "num_to_spawn" into the new instance)
    #  2. Pass-through for the destination (the new workflow already has a variable by that name, let it resolve itself)
    #  3. Global reference (valid in any context, no source instance needed)
    # Cases 2 and 3 are currently fine as-is. Case 1 is broken — the new instance gets a VariableName that has no
    # parent value to read. The problem is that VariableName encodes *what* to look up but not *where*, so any
    # automatic resolution rule would silently break one of the other valid cases.
    workflow = global_workflows[workflow_uuid.value]
    workflow.spawn_instance(setup_vars.value)
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def pause_this_instance(instance: Instance) -> CommandReturnStatus:
    instance.state = RunStates.Paused
    return CommandReturnStatus.Yield

# ====================================================================
# Logging and Messages
# ====================================================================

@Commands.register_command(category="Core")
def log(instance: Instance, msg: String) -> CommandReturnStatus:
    instance.log_line(msg.value)
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def error(instance: Instance, msg: String) -> CommandReturnStatus:
    instance.log_line(msg.value)
    return CommandReturnStatus.Error

# TODO - Have string formatting versions so it can print variables and whatnot inbetween
# Maybe have it follow the python formatting style and then somehow have python give the contents of the replacment groups for me to then safely implement string formatting?

# ====================================================================
# conditionals and branches
# ====================================================================

@Commands.register_command(category="Core")
def jump_to_procedure(instance: Instance, procedure_name: String) -> CommandReturnStatus:
    workflow = instance.get_associated_workflow()
    if not procedure_name.value in workflow.procedures:
        instance.log_line(f"Error: Cannot jump to the procedure {procedure_name} because it does not exist in the workflow {instance.workflow_uuid}")
        return CommandReturnStatus.Error
    instance.processing_step = (procedure_name.value,0)
    return CommandReturnStatus.Success | CommandReturnStatus.Keep_Position

@Commands.register_command(category="Core")
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


@Commands.register_command(category="Core")
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

@Commands.register_command(category="Core")
def goto_if_first_larger(instance: Instance, procedure_name: String, value1: Integer|Float, value2: Integer|Float) -> CommandReturnStatus:
    if value1.value > value2.value:
        return jump_to_procedure(instance, procedure_name)

    return CommandReturnStatus.Success

# ====================================================================
# Basic Math
# ====================================================================

@Commands.register_command(category="Math")
def math_add(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value += second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command(category="Math")
def math_subtract(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value -= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command(category="Math")
def math_multiply(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value *= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command(category="Math")
def math_divide(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariableName) -> CommandReturnStatus:
    first.value /= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

# ====================================================================
# Utilities
# ====================================================================

@Commands.register_command(category="Strings")
def regex_first_match(instance: Instance, format_string: String, input_string: String, output_variable:VariableName) -> CommandReturnStatus:
    matcher = re.compile(format_string.value)
    first_match = matcher.search(input_string.value)
    if not first_match:
        instance.log_line(f"Error: Unable to find a match of {format_string} on the input {input_string}")
        return CommandReturnStatus.Error

    instance[output_variable.value] = String(first_match.group())
    return CommandReturnStatus.Success

@Commands.register_command(category="Strings")
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

@Commands.register_command(category="Core")
def set_variable_value(instance: Instance, variable_name: VariableName, value:WorkVariable) -> CommandReturnStatus:
    instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def set_variable_value_in_another_instance(instance: Instance, instance_uuid:String, variable_name: VariableName, value: WorkVariable) -> CommandReturnStatus:
    if not instance_uuid.value in global_instances:
        instance.log_line(f"Unable to find an instance with the UUID {instance_uuid.value} to set a variable in")
        return CommandReturnStatus.Error
    other_instance = global_instances[instance_uuid.value]
    other_instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def save_uuid_to_variables(instance: Instance) -> CommandReturnStatus:
    instance["uuid"] = String(instance.uuid)
    return CommandReturnStatus.Success
