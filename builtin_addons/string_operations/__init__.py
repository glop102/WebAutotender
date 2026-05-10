from pipeline_backend import *
from pipeline_backend.commands_builtin import *
try:
    import regex as re
except:
    # Personally I really like having the \K flag available so lets just force it to be available
    raise Exception("Unable to import regex module. This is an expanded regex support module for python. The package may be simply called python-regex in your package manager.")

@Commands.register_command(category="Strings")
async def str_regex_firstMatch(instance: Instance, regexPatern:String, inputString:String, outputVarname: VariablePath) -> CommandReturnStatus:
    """Find the first regex match in a string using extended regex syntax (supports \\K and other extras). Errors if no match is found.
  regexPatern: The regex pattern to search with.
  inputString: The string to search in.
  outputVarname: Name of the variable to store the matched text in."""
    match:re.Match|None = re.search(regexPatern.value,inputString.value)
    if match is None:
        instance.log_line(f"Unable to find any match of {regexPatern.value} in the string {inputString.value}")
        return CommandReturnStatus.Error
    instance[outputVarname] = String(match.group(0))
    return CommandReturnStatus.Success

@Commands.register_command(category="Strings")
async def str_regex_matchAll(instance: Instance, regexPatern: String, inputString: String, outputVarname: VariablePath) -> CommandReturnStatus:
    """Find all regex matches in a string using extended regex syntax (supports \\K and other extras). Stores an empty list if there are no matches.
  regexPatern: The regex pattern to search with.
  inputString: The string to search in.
  outputVarname: Name of the variable to store the StringList of matched strings in."""
    matches = re.findall(regexPatern.value, inputString.value)
    instance[outputVarname] = StringList(matches)
    return CommandReturnStatus.Success

@Commands.register_command(category="Strings")
async def str_buildWithVars(instance: Instance, inputString:String, outputVarname: VariablePath) -> CommandReturnStatus:
    """Build a string using Python-style {variable_name} placeholders filled from instance variables.
  inputString: A format string with {variable_name} placeholders referencing instance or global variables.
  outputVarname: Name of the variable to store the resulting string in."""
    vars = {name:var.convert_to_python_type() for name,var in instance.variables.items()}
    for name,var in instance.get_associated_workflow().constants.items():
        if not name in vars:
            vars[name] = var.convert_to_python_type()
    for name,var in instance.ctx.variables.items():
        if not name in vars:
            vars[name] = var.convert_to_python_type()
    # TODO : Errors on list types so we need to recusivly convert values down if they are WorkVariables and their value is iterable
    outputString = inputString.value.format_map(vars)
    instance[outputVarname] = String(outputString)
    return CommandReturnStatus.Success

