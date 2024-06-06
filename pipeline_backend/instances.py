# To break the circular dependencies with Workflow, we do this other import style along with the __future__ to allow delayed type checking so everything is imported before the checking happens
from __future__ import annotations
from datetime import datetime
from copy import deepcopy,copy
import pipeline_backend.variables as variables
import pipeline_backend.workflows as workflows

class Instance:
    uuid: str
    workflow_name: str
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
        self.workflow_name = ""
        self.state = workflows.RunStates.Running
        self.variables = {}
        self.processing_step = ("start", 0)
        self.next_processing_time = datetime.now()
        self.console_log = ""

    def __str__(self) -> str:
        return f"Instance {self.uuid} - Workflow: {self.workflow_name} - {self.state.name}"

    def __repr__(self) -> str:
        sss = self.__str__()
        sss += f"\n    {len(self.variables)} variables - {self.processing_step}"
        for varname in self.variables:
            sss += f"\n    {varname} = {self.variables[varname]}"
        return sss

    def get_associated_workflow(self) -> workflows.Workflow:
        return workflows.Workflow.get_by_name(self.workflow_name)

    def log_line(self, line):
        """Will add a line to the log. This will add its own newline to the end of the line"""
        self.console_log += line+"\n"

    def __getitem__(self, var_name: str|variables.VariableName) -> variables.WorkVariable:
        """Get the value of the variable of the given name. Will throw a KeyError if it cannot find the variable. This handles the complication of searching the associated workflow as well."""
        if type(var_name) == variables.VariableName:
            var_name = var_name.value
        if var_name in self.variables:
            return deepcopy(self.variables[var_name])
        w:workflows.Workflow = self.get_associated_workflow()
        if var_name in w.constants:
            return deepcopy(w.constants[var_name])
        if var_name in w.setup_variables:
            return deepcopy(w.setup_variables[var_name])
        if var_name in variables.global_variables:
            return deepcopy(variables.global_variables[var_name])
        raise KeyError(f"Unable to find the variable named {var_name} - {self.workflow_name}/{self.uuid}")

    def __setitem__(self, var_name: str|variables.VariableName, value: variables.WorkVariable) -> None:
        if type(var_name) == variables.VariableName:
            var_name = var_name.value
        self.variables[var_name] = deepcopy(value)
    
    def __delitem__(self,var_name:str|variables.VariableName) -> None:
        if type(var_name) == variables.VariableName:
            var_name = var_name.value
        if not var_name in self.variables:
            raise KeyError(f"Unable to find the variable named {var_name} - {self.workflow_name}/{self.uuid}")
        del self.variables[var_name]

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
        except ValueError:
            return False
        return self.state == workflows.RunStates.Running and asoc_wf.state == workflows.RunStates.Running
    

    def json_savable(self) -> dict:
        data = {
            'uuid': copy(self.uuid),
            'workflow_name': copy(self.workflow_name),
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
        self.workflow_name = data['workflow_name']
        self.state = workflows.RunStates[data['state']]
        self.processing_step = tuple(data['processing_step'])
        self.next_processing_time = datetime.fromisoformat( data['next_processing_time'] )
        self.console_log = data['console_log']
        for var_name in data['variables']:
            var = variables.WorkVariable()
            var.json_loadable(data['variables'][var_name])
            self.variables[var_name] = var

    @classmethod
    def get_by_uuid(cls, instance_uuid: str) -> Instance:
        if instance_uuid in global_instances:
            return global_instances[instance_uuid]
        raise ValueError(
            f"Unable to find the instance {instance_uuid}")


global_instances: list[Instance] = {}
