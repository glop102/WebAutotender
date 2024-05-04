# To break the circular dependencies with Workflow, we do this other import style along with the __future__ to allow delayed type checking so everything is imported before the checking happens
from __future__ import annotations
from datetime import datetime
from copy import deepcopy
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
        for w in workflows.global_workflows:
            if w.name == self.workflow_name:
                return w
        raise ValueError(
            f"Unable to find the associated workflow {self.workflow_name} for Instance {self.uuid}")

    def log_line(self, line):
        """Will add a line to the log. This will add its own newline to the end of the line"""
        self.console_log += line+"\n"

    def __getitem__(self, var_name: str) -> variables.WorkVariable:
        """Get the value of the variable of the given name. Will throw a KeyError if it cannot find the variable. This handles the complication of searching the associated workflow as well."""
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

    def __setitem__(self, var_name: str, value: variables.WorkVariable) -> None:
        self.variables[var_name] = deepcopy(value)
    
    def __delitem__(self,var_name:str) -> None:
        if not var_name in self.variables:
            raise KeyError(f"Unable to find the variable named {var_name} - {self.workflow_name}/{self.uuid}")
        del self.variables[var_name]

    def past_time_to_run(self) -> bool:
        if not self.next_processing_time:
            self.state = workflows.RunStates.Error
            return False
        return datetime.now() > self.next_processing_time


global_instances: list[Instance] = []
