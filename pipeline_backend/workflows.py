# To break the circular dependencies with Instance, we do this other import style along with the __future__ to allow delayed type checking so everything is imported before the checking happens
from __future__ import annotations
from enum import Enum
from copy import deepcopy,copy
from uuid import uuid4
import pipeline_backend.variables as variables
import pipeline_backend.instances as instances


class RunStates(Enum):
    Running = 0
    Paused = 1
    Error = 2

class ProcessingStep:
    command_name: str
    variables: dict[str, variables.WorkVariable]
    def __init__(self)->None:
        self.command_name = ""
        self.variables = {}
    def __str__(self) -> str:
        return f"ProcessingStep - {self.command_name} - {len(self.variables)} variables"
    def __repr__(self)->str:
        sss = self.__str__()
        for var_name in self.variables:
            sss += f"\n    {var_name} = {self.variables[var_name]}"
        return sss
    
    def json_savable(self) -> dict:
        data = {
            'command_name': copy(self.command_name),
            'variables': {}
        }
        for var_name in self.variables:
            data['variables'][var_name] = self.variables[var_name].json_savable()
        return data

    def json_loadable(self, data: dict) -> None:
        self.command_name = data['command_name']
        for var_name in data['variables']:
            var = variables.WorkVariable()
            var.json_loadable(data['variables'][var_name])
            self.variables[var_name] = var

class Workflow:
    name: str
    constants: dict[str, variables.WorkVariable]
    # The values of these are the defaults when making a new instance for the workflow, and are copied to the instance
    setup_variables: dict[str, variables.WorkVariable]
    procedures: dict[str, list[ProcessingStep]]

    # On startup and on set from the web UI, we will revalidate that everything looks correct
    # If something looks incorrect, we will mark it as invalid and skip processing
    state: RunStates

    # A free space for a user to leave notes for whatever reason. Probably a description of the workflow and reminder of how it works.
    user_notes: str

    def __init__(self) -> None:
        self.name = ""
        self.constants = {}
        self.setup_variables = {}
        self.procedures = {}
        self.state = RunStates.Running
        self.user_notes = ""

    def spawn_instance(self, setup_var_non_defaults: dict[str, variables.WorkVariable] = {}) -> instances.Instance:
        """Create a new Instance with some variables. The setup variables are optional, and if not everything is specified, will be filled with defaults as setup in the workflow. Can also be used to shadow values that are constants in the parent workflow."""
        #Note: Make sure Variables are a copy that we give to the instance, so the instance permuting does not change future workflow defaults
        new = instances.Instance()
        new.uuid = str(uuid4())
        new.workflow_name = str(self.name)

        # Start with all defaults and then apply overrides - technically wastes making extra copies that are thrown away, but we should not be copying all the much
        new.variables = deepcopy(self.setup_variables)
        for varname in setup_var_non_defaults:
            new.variables[varname] = deepcopy(setup_var_non_defaults[varname])

        if self in global_workflows:
            instances.global_instances.append(new)
        return new

    def __str__(self) -> str:
        return f"Workflow \"{self.name}\" - {self.state.name}"

    def __repr__(self) -> str:
        sss = self.__str__()
        sss += f"\n    {len(self.constants)} constants - {len(self.setup_variables)} setup_variables"
        for varname in self.constants:
            sss += f"\n    C:{varname} = {self.constants[varname]}"
        for varname in self.setup_variables:
            sss += f"\n    S:{varname} = {self.setup_variables[varname]}"
        for proc_name in self.procedures:
            sss += f"\n    Proc: {proc_name} - {len(self.procedures[proc_name])}"
        return sss
    
    def json_savable(self) -> dict:
        data = {
            'name': copy(self.name),
            'state': copy(self.state.name),
            'user_notes': copy(self.user_notes),
            'constants': {},
            'setup_variables': {},
            'procedures': {}
        }
        for var_name in self.constants:
            data['constants'][var_name] = self.constants[var_name].json_savable()
        for var_name in self.setup_variables:
            data['setup_variables'][var_name] = self.setup_variables[var_name].json_savable()
        for proc_name in self.procedures:
            data['procedures'][proc_name] = [proc_step.json_savable() for proc_step in self.procedures[proc_name] ]
        return data

    def json_loadable(self, data: dict) -> None:
        self.name = data['name']
        self.state = RunStates[data['state']]
        self.user_notes = data['user_notes']
        for var_name in data['constants']:
            var = variables.WorkVariable()
            var.json_loadable(data['constants'][var_name])
            self.constants[var_name] = var
        for var_name in data['setup_variables']:
            var = variables.WorkVariable()
            var.json_loadable(data['setup_variables'][var_name])
            self.setup_variables[var_name] = var
        for proc_name in data['procedures']:
            proc_steps:list[ProcessingStep] = []
            for step_data in data['procedures'][proc_name]:
                step = ProcessingStep()
                step.json_loadable(step_data)
                proc_steps.append(step)
            self.procedures[proc_name] = proc_steps
    
    @classmethod
    def get_by_name(cls,workflow_name:str)->Workflow:
        for w in global_workflows:
            if w.name == workflow_name:
                return w
        raise ValueError(
            f"Unable to find the associated workflow {workflow_name}")
    
# =====================================================================================
# Tracking available items
# =====================================================================================
# It is a little weird feeling to put these here, but Instances with their procedures will
# have commands that create or delete instances, so we need to track what is available
# internally to the module.

global_workflows:list[Workflow] = []
