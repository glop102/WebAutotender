from pipeline_backend import *
from pipeline_backend.commands_builtin import *
try:
    import regex as re
except:
    # Personally I really like having the \K flag available so lets just force it to be available
    raise Exception("Unable to import regex module. This is an expanded regex support module for python. The package may be simply called python-regex in your package manager.")

@Commands.register_command
async def str_regex_firstMatch(instance: Instance, regexPatern:String, inputString:String, outputVarname: VariableName) -> CommandReturnStatus:
    match:re.Match|None = re.search(regexPatern.value,inputString.value)
    instance.log_line(f"Unable to find any match of {regexPatern.value} in the string {inputString.value}")
    if match is None:
        return CommandReturnStatus.Error
    instance[outputVarname] = String(match.group(0))
    return CommandReturnStatus.Success

@Commands.register_command
async def str_buildWithVars(instance: Instance, inputString:String, outputVarname: VariableName) -> CommandReturnStatus:
    """
    This is a bit of an odder one since we want to emulate the way python formatted strings work and implicitly pull in the variables that are in the formatted string but using the instance as a source.
    This is why we are not having a variable list as an input source in addition since the variable names will be required in the {} and then we will rtequire the types to match up to have the builtin python formatting rules work.
    https://docs.python.org/3.8/library/string.html#string.Formatter
    """
    vars = {name:var.convert_to_python_type() for name,var in instance.variables.items()}
    for name,var in instance.get_associated_workflow().constants.items():
        if not name in vars:
            vars[name] = var.convert_to_python_type()
    for name,var in global_variables.items():
        if not name in vars:
            vars[name] = var.convert_to_python_type()
    # TODO : Errors on list types so we need to recusivly convert values down if they are WorkVariables and their value is iterable
    outputString = inputString.value.format_map(vars)
    instance[outputVarname] = String(outputString)
    return CommandReturnStatus.Success

