# To break the circular dependencies with Instance, we do this other import style along with the __future__ to allow delayed type checking so everything is imported before the checking happens
from __future__ import annotations
from enum import Enum
from copy import deepcopy
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
        """Create a new Instance with some variables. The setup variables are optional, and if not everything is specified, will be filled with defaults as setup in the workflow. This will add the Instance to the global_instances array."""
        #Note: Make sure Variables are a copy that we give to the instance, so the instance permuting does not change future workflow defaults
        new = instances.Instance()
        new.uuid = str(uuid4())
        new.workflow_name = str(self.name)

        # Start with all defaults and then apply overrides - technically wastes making extra copies taht are thrown away, but we should not be copying all the much
        new.variables = deepcopy(self.setup_variables)
        for varname in setup_var_non_defaults:
            new.variables[varname] = deepcopy(setup_var_non_defaults[varname])
        return new

    def __str__(self) -> str:
        return f"Workflow {self.name} - {self.state.name}"

    def __repr__(self) -> str:
        sss = self.__str__()
        sss += f"\n    {len(self.constants)} constants - {len(self.setup_variables)} setup_variables"
        for varname in self.constants:
            sss += f"\n    C:{varname} = {self.constants[varname]}"
        for varname in self.setup_variables:
            sss += f"\n    S:{varname} = {self.setup_variables[varname]}"
        return sss
    
# =====================================================================================
# Tracking available items
# =====================================================================================
# It is a little weird feeling to put these here, but Instances with their procedures will
# have commands that create or delete instances, so we need to track what is available
# internally to the module.

global_workflows:list[Workflow] = []