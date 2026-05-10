# To break the circular dependencies with Workflow, we do this other import style along with the __future__ to allow delayed type checking so everything is imported before the checking happens
from __future__ import annotations
from datetime import datetime
from copy import deepcopy,copy
import pipeline_backend.variables as variables
import pipeline_backend.workflows as workflows

class Instance:
    uuid: str
    workflow_uuid: str
    state: workflows.RunStates

    # Per Instance Variables - Initially populated with setup_variables and then runtime can mutate it
    variables: dict[str, variables.WorkVariable]

    # We always start with the procedure named "start" and at its 0th step
    processing_step: tuple[str, int]
    # The next time we will want to be iterated on. This is not a precise time it will run, but a rough minimum before it gets run. Often gets set by the yield_* commands
    next_processing_time:datetime

    # It is handy to debug things when there is actually feedback to the user
    console_log: str

    def __init__(self) -> None:
        self.uuid = ""
        self.workflow_uuid = ""
        self.state = workflows.RunStates.Running
        self.variables = {}
        self.processing_step = ("start", 0)
        self.next_processing_time = datetime.now()
        self.console_log = ""

    def __str__(self) -> str:
        return f"Instance {self.uuid} - Workflow: {self.workflow_uuid} - {self.state.name}"

    def __repr__(self) -> str:
        sss = self.__str__()
        sss += f"\n    {len(self.variables)} variables - {self.processing_step}"
        for varname in self.variables:
            sss += f"\n    {varname} = {self.variables[varname]}"
        return sss

    def get_associated_workflow(self) -> workflows.Workflow:
        return workflows.global_workflows[self.workflow_uuid]

    def log_line(self, line):
        """Will add a line to the log. This will add its own newline to the end of the line"""
        self.console_log += line+"\n"

    def __getitem__(self, var_name: str|variables.VariablePath) -> variables.WorkVariable:
        """Get the value of the variable at the given name or dot-notation path (e.g. 'entry.link').
        Searches instance variables, workflow constants/setup_variables, then globals.
        Will throw a KeyError if the variable or any path segment cannot be found."""
        if type(var_name) == variables.VariablePath:
            var_name = var_name.value

        parts = var_name.split('.')
        first = parts[0]

        w: workflows.Workflow = self.get_associated_workflow()
        for scope in (self.variables, w.constants, w.setup_variables,
                      variables.global_variables, variables.global_secrets):
            if first in scope:
                result = deepcopy(scope[first])
                break
        else:
            raise KeyError(f"Unable to find the variable named {first} - {self.workflow_uuid}/{self.uuid}")

        for part in parts[1:]:
            match result:
                case variables.Dictionary():
                    if part not in result.value:
                        raise KeyError(f"Key '{part}' not found in Dictionary")
                    result = deepcopy(result.value[part])
                case variables.VariableList():
                    result = deepcopy(result.value[int(part)])
                case variables.StringList():
                    result = variables.String(result.value[int(part)])
                case variables.VariableNameList():
                    result = variables.VariablePath(result.value[int(part)])
                case _:
                    raise KeyError(f"Cannot index into {type(result).__name__} with '{part}'")

        return result

    def __setitem__(self, var_name: str|variables.VariablePath, value: variables.WorkVariable) -> None:
        if type(var_name) == variables.VariablePath:
            var_name = var_name.value
        if not issubclass(type(value), variables.WorkVariable):
            raise TypeError(f"Cannot save a variable of type {type(value)} to an instance. Please wrap it in a WorkVariable type. (value={value})")

        parts = var_name.split('.')

        if len(parts) == 1:
            self.variables[var_name] = deepcopy(value)
            return

        # Get or create the top-level container
        top_key = parts[0]
        if top_key in self.variables:
            top = deepcopy(self.variables[top_key])
        else:
            top = variables.Dictionary()

        # Navigate down, creating intermediate Dictionaries as needed
        current = top
        for part in parts[1:-1]:
            if not isinstance(current, variables.Dictionary):
                raise TypeError(f"Cannot set into {type(current).__name__} with key '{part}' — only Dictionary supports auto-creation")
            if part not in current.value:
                current.value[part] = variables.Dictionary()
            current = current.value[part]

        if not isinstance(current, variables.Dictionary):
            raise TypeError(f"Cannot set key '{parts[-1]}' into {type(current).__name__}")
        current.value[parts[-1]] = deepcopy(value)
        self.variables[top_key] = top

    def __delitem__(self, var_name: str|variables.VariablePath) -> None:
        if type(var_name) == variables.VariablePath:
            var_name = var_name.value
        if not var_name in self.variables:
            raise KeyError(f"Unable to find the variable named {var_name} - {self.workflow_uuid}/{self.uuid}")
        del self.variables[var_name]

    def __contains__(self, var_name: str|variables.VariablePath) -> bool:
        try:
            self.__getitem__(var_name)
            return True
        except KeyError:
            return False

    def past_time_to_run(self,current_time:datetime=None) -> bool:
        if not self.next_processing_time:
            self.state = workflows.RunStates.Error
            return False
        if not current_time:
            current_time = datetime.now()
        return current_time > self.next_processing_time

    def is_allowed_to_run(self):
        #TODO have a lock check in here for the UI doing an edit
        try:
            asoc_wf = self.get_associated_workflow()
        except:
            return False
        return self.state == workflows.RunStates.Running and asoc_wf.state == workflows.RunStates.Running
    

    def json_savable(self) -> dict:
        data = {
            'uuid': copy(self.uuid),
            'workflow_uuid': copy(self.workflow_uuid),
            'state': copy(self.state.name),
            'processing_step': copy(self.processing_step),
            'next_processing_time': self.next_processing_time.isoformat(),
            'console_log': copy(self.console_log),
            'variables': {}
            }
        for var_name in self.variables:
            data['variables'][var_name] = self.variables[var_name].json_savable()
        return data

    def json_loadable(self, data: dict) -> None:
        self.uuid = data['uuid']
        self.workflow_uuid = data['workflow_uuid']
        self.state = workflows.RunStates[data['state']]
        self.processing_step = tuple(data['processing_step'])
        self.next_processing_time = datetime.fromisoformat( data['next_processing_time'] )
        self.console_log = data['console_log']
        for var_name in data['variables']:
            var = variables.WorkVariable()
            var.json_loadable(data['variables'][var_name])
            self.variables[var_name] = var


global_instances: dict[str, Instance] = {}
