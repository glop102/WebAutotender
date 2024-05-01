from copy import deepcopy
from uuid import uuid4
from enum import Enum
from .variables import *
from .procedures import *

# =====================================================================================
# Some Types
# =====================================================================================
class RunStates(Enum):
    Running = 0
    Paused = 1
    Error = 2

# =====================================================================================
# Main Classes
# =====================================================================================

class Instance:
    uuid:str
    workflow_name:str
    state: RunStates = RunStates.Running

    # Per Instance Variables - Initially populated with setup_variables and then runtime can mutate it
    variables: dict[str, WorkVariable] = {}

    #We always start with the procedure named "start" and at its 0th step
    processing_step:tuple[str,int] = ("start",0)
    # The next time we will want to be iterated on. This is not a precise time it will run, but a rough minimum before it gets run. Often gets set by the yield_* commands
    #next_processing_time:date_type_somewhere

    def __str__(self) -> str:
        return f"Instance {self.uuid} - Workflow: {self.workflow_name} - {self.state.name}"
    def __repr__(self) -> str:
        sss = self.__str__()
        sss += f"\n    {len(self.variables)} variables - {self.processing_step}"
        for varname in self.variables:
            sss+=f"\n    {varname} = {self.variables[varname]}"
        return sss


class Workflow:
    name: str
    constants: dict[str, WorkVariable] = {}
    # The values of these are the defaults when making a new instance for the workflow, and are copied to the instance
    setup_variables: dict[str, WorkVariable] = {}
    procedures: dict[str, Procedure] = {}

    # On startup and on set from the web UI, we will revalidate that everything looks correct
    # If something looks incorrect, we will mark it as invalid and skip processing
    state: RunStates = RunStates.Running

    # A free space for a user to leave notes for whatever reason. Probably a description of the workflow and reminder of how it works.
    user_notes: str = ""

    # Create a new Instance with some variables. The setup variables are optional, and if not everything is specified, will be filled with defaults as setup in the workflow.
    def spawn_instance(self, setup_var_non_defaults: dict[str, WorkVariable] = {}) -> Instance:
        if not hasattr(self,"name"):
            self.state = RunStates.Error
            raise ValueError("Workflow does not have a name and so cannot spawn an instance")
        #Note: Make sure Variables are a copy that we give to the instance, so the instance permuting does not change future workflow defaults
        new = Instance()
        new.uuid = str(uuid4())
        new.workflow_name = str(self.name)

        # Start with all defaults and then apply overrides - technically wastes making extra copies taht are thrown away, but we should not be copying all the much
        new.variables = deepcopy(self.setup_variables)
        for varname in setup_var_non_defaults:
            new.variables[varname] = deepcopy(setup_var_non_defaults[varname])
        return new
