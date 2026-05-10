from .commands import *
from .variables import *
from .instances import *
from .workflows import *
from datetime import datetime,timedelta

# ====================================================================
# State control of instances
# ====================================================================

@Commands.register_command(category="Core")
def yield_for_seconds(instance:Instance,num_seconds:Integer|Float)->CommandReturnStatus:
    """Suspend this instance for a number of seconds before continuing.
  num_seconds: How long to wait, in seconds. Accepts Integer or Float."""
    instance.next_processing_time = datetime.now() + timedelta(seconds=num_seconds.value)
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def yield_for_minutes(instance:Instance,num_minutes:Integer|Float)->CommandReturnStatus:
    """Suspend this instance for a number of minutes before continuing.
  num_minutes: How long to wait, in minutes. Accepts Integer or Float."""
    instance.next_processing_time = datetime.now() + timedelta(minutes=num_minutes.value)
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def yield_until(instance: Instance, iso_datetime:String) -> CommandReturnStatus:
    """Suspend this instance until a specific date and time.
  iso_datetime: An ISO 8601 datetime string (e.g. 2026-05-08T14:00:00) indicating when to resume."""
    instance.next_processing_time = datetime.fromisoformat(iso_datetime.value)
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def delete_this_instance(instance: Instance) -> CommandReturnStatus:
    """Permanently remove this instance. Execution stops and the instance will not appear again."""
    if not instance.uuid in instance.ctx.instances:
        instance.log_line(f"Error: Unable to delete an instance that is not registered in the pipeline context.")
        return CommandReturnStatus.Error
    del instance.ctx.instances[instance.uuid]
    return CommandReturnStatus.Yield

@Commands.register_command(category="Core")
def make_new_instance(instance: Instance, workflow_uuid:String, setup_vars:Dictionary, do_not_deref:VariableNameList) -> CommandReturnStatus:
    """Spawn a new instance of another workflow, passing in initial variable values.
  workflow_uuid: UUID of the target workflow to spawn an instance of.
  setup_vars: Dictionary of setup variable names to values. VariablePath values are resolved from the caller's scope to match the destination's declared type.
  do_not_deref: List of keys in setup_vars whose VariablePath values should be passed through as-is without resolution."""
    if workflow_uuid.value not in instance.ctx.workflows:
        instance.log_line(f"Error: Unable to find a Workflow with the uuid {workflow_uuid.value} to spawn an instance of.")
        return CommandReturnStatus.Error

    workflow = instance.ctx.workflows[workflow_uuid.value]

    for key in setup_vars.value:
        if key not in workflow.setup_variables:
            instance.log_line(f"Error: '{key}' is not a declared setup variable of workflow '{workflow.name}'.")
            return CommandReturnStatus.Error

    for key in do_not_deref.value:
        if key not in setup_vars.value:
            instance.log_line(f"Error: '{key}' in do_not_deref is not present in setup_vars.")
            return CommandReturnStatus.Error

    resolved = {}
    for key, var in setup_vars.value.items():
        if key in do_not_deref.value:
            resolved[key] = var
            continue
        dest_type = type(workflow.setup_variables[key])
        current = var
        while True:
            if type(current) == dest_type:
                resolved[key] = current
                break
            if type(current) == VariablePath:
                try:
                    current = instance[current.value]
                except KeyError:
                    instance.log_line(f"Error: Dangling reference '{current.value}' when resolving setup var '{key}' for workflow '{workflow.name}'.")
                    return CommandReturnStatus.Error
            else:
                instance.log_line(f"Error: Cannot resolve setup var '{key}' to type {dest_type.__name__} for workflow '{workflow.name}' (got {type(current).__name__}).")
                return CommandReturnStatus.Error

    workflow.spawn_instance(resolved)
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def pause_this_instance(instance: Instance) -> CommandReturnStatus:
    """Pauses this instance. It will not run again until manually resumed or another instance resumes it."""
    instance.state = RunStates.Paused
    return CommandReturnStatus.Yield

# ====================================================================
# Logging and Messages
# ====================================================================

@Commands.register_command(category="Core")
def log(instance: Instance, msg: String) -> CommandReturnStatus:
    """Append a message to this instance's console log.
  msg: The text to log."""
    instance.log_line(msg.value)
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def error(instance: Instance, msg: String) -> CommandReturnStatus:
    """Log a message and put this instance into the Error state, halting execution.
  msg: The error message to log."""
    instance.log_line(msg.value)
    return CommandReturnStatus.Error

# ====================================================================
# conditionals and branches
# ====================================================================

@Commands.register_command(category="Core")
def jump_to_procedure(instance: Instance, procedure_name: String) -> CommandReturnStatus:
    """Unconditionally jump to the start of another procedure in this workflow.
  procedure_name: Name of the procedure to jump to."""
    workflow = instance.get_associated_workflow()
    if not procedure_name.value in workflow.procedures:
        instance.log_line(f"Error: Cannot jump to the procedure {procedure_name} because it does not exist in the workflow {instance.workflow_uuid}")
        return CommandReturnStatus.Error
    instance.processing_step = (procedure_name.value,0)
    return CommandReturnStatus.Success | CommandReturnStatus.Keep_Position

@Commands.register_command(category="Core")
def goto_if(instance: Instance, procedure_name: String, condition: Boolean) -> CommandReturnStatus:
    """Jump to a procedure if a Boolean condition is true. Continues to the next step if false.
  procedure_name: Name of the procedure to jump to when condition is true.
  condition: The Boolean value to test."""
    if condition.value:
        return jump_to_procedure(instance, procedure_name)
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def goto_if_equal(instance: Instance, procedure_name: String, value1:WorkVariable, value2:WorkVariable) -> CommandReturnStatus:
    """Jump to a procedure if two values are equal. Compares by type then by string representation.
  procedure_name: Name of the procedure to jump to when values are equal.
  value1: First value to compare. VariablePaths are dereferenced automatically.
  value2: Second value to compare. VariablePaths are dereferenced automatically."""
    while type(value1) == VariablePath:
        value1 = instance[value1.value]
    while type(value2) == VariablePath:
        value2 = instance[value2.value]

    if type(value1) == type(value2) and value1.value == value2.value:
        return jump_to_procedure(instance,procedure_name)
    if str(value1.value) == str(value2.value):
        return jump_to_procedure(instance, procedure_name)

    # Nothing was equal so continue without jumping
    return CommandReturnStatus.Success


@Commands.register_command(category="Core")
def goto_if_not_equal(instance: Instance, procedure_name: String, value1: WorkVariable, value2: WorkVariable) -> CommandReturnStatus:
    """Jump to a procedure if two values are not equal. Compares by type then by string representation.
  procedure_name: Name of the procedure to jump to when values are not equal.
  value1: First value to compare. VariablePaths are dereferenced automatically.
  value2: Second value to compare. VariablePaths are dereferenced automatically."""
    while type(value1) == VariablePath:
        value1 = instance[value1.value]
    while type(value2) == VariablePath:
        value2 = instance[value2.value]

    if type(value1) == type(value2) and value1.value != value2.value:
        return jump_to_procedure(instance, procedure_name)
    if str(value1.value) != str(value2.value):
        return jump_to_procedure(instance, procedure_name)

    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def goto_if_first_larger(instance: Instance, procedure_name: String, value1: Integer|Float, value2: Integer|Float) -> CommandReturnStatus:
    """Jump to a procedure if value1 is strictly greater than value2.
  procedure_name: Name of the procedure to jump to.
  value1: The value to test as larger.
  value2: The value to test against."""
    if value1.value > value2.value:
        return jump_to_procedure(instance, procedure_name)

    return CommandReturnStatus.Success

# ====================================================================
# Basic Math
# ====================================================================

@Commands.register_command(category="Math")
def math_add(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariablePath) -> CommandReturnStatus:
    """Add two numbers and store the result.
  first: The base value to add to.
  second: The value to add.
  output_variable: Name of the variable to store the result in."""
    first.value += second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command(category="Math")
def math_subtract(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariablePath) -> CommandReturnStatus:
    """Subtract second from first and store the result.
  first: The value to subtract from.
  second: The value to subtract.
  output_variable: Name of the variable to store the result in."""
    first.value -= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command(category="Math")
def math_multiply(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariablePath) -> CommandReturnStatus:
    """Multiply two numbers and store the result.
  first: The first factor.
  second: The second factor.
  output_variable: Name of the variable to store the result in."""
    first.value *= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

@Commands.register_command(category="Math")
def math_divide(instance: Instance, first: Integer|Float, second: Integer|Float, output_variable: VariablePath) -> CommandReturnStatus:
    """Divide first by second and store the result.
  first: The dividend.
  second: The divisor.
  output_variable: Name of the variable to store the result in."""
    first.value /= second.value
    instance[output_variable] = first
    return CommandReturnStatus.Success

# ====================================================================
# Utilities
# ====================================================================


@Commands.register_command(category="Core")
def list_pop_next(instance: Instance, list_varname: VariablePath, item_varname: VariablePath, empty_procedure: String) -> CommandReturnStatus:
    """Pop the first item from a StringList or VariableList into a variable. Jumps to empty_procedure when the list is already empty on entry, so the last item is always processed before the jump.
  list_varname: Name of the StringList or VariableList variable to pop from.
  item_varname: Name of the variable to store the popped item in.
  empty_procedure: Procedure to jump to when the list is empty on entry."""
    the_list = instance[list_varname.value]
    if not isinstance(the_list, (StringList, VariableList)):
        instance.log_line(f"Error: '{list_varname.value}' is not a StringList or VariableList.")
        return CommandReturnStatus.Error
    if len(the_list.value) == 0:
        return jump_to_procedure(instance, empty_procedure)
    item = the_list.value.pop(0)
    if isinstance(the_list, StringList):
        # StringList stores raw Python strings internally, so wrap in String before storing
        item = String(item)
    instance[item_varname] = item
    instance[list_varname] = the_list
    return CommandReturnStatus.Success


@Commands.register_command(category="Core")
def set_variable_value(instance: Instance, variable_name: VariablePath, value:WorkVariable) -> CommandReturnStatus:
    """Set a variable on this instance to the given value.
  variable_name: Name of the variable to set.
  value: The value to assign."""
    instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def set_variable_value_in_another_instance(instance: Instance, instance_uuid:String, variable_name: VariablePath, value: WorkVariable) -> CommandReturnStatus:
    """Set a variable on a different instance by its UUID.
  instance_uuid: UUID of the target instance to modify.
  variable_name: Name of the variable to set on the target instance.
  value: The value to assign."""
    if not instance_uuid.value in instance.ctx.instances:
        instance.log_line(f"Unable to find an instance with the UUID {instance_uuid.value} to set a variable in")
        return CommandReturnStatus.Error
    other_instance = instance.ctx.instances[instance_uuid.value]
    other_instance[variable_name.value] = value
    return CommandReturnStatus.Success

@Commands.register_command(category="Core")
def save_uuid_to_variables(instance: Instance) -> CommandReturnStatus:
    """Store this instance's UUID into a variable named 'uuid' for use in subsequent steps."""
    instance["uuid"] = String(instance.uuid)
    return CommandReturnStatus.Success
