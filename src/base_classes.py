from uuid import UUID
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

class Workflow:
    uuid: UUID
    constants: dict[str, WorkVariable] = {}
    setup_variables: dict[str, WorkVariable] = {} # The values of these are the defaults when making a new instance for the workflow, and are copied to the instance
    procedures: dict[str, Procedure] = {}

    # On startup and on set from the web UI, we will revalidate that everything looks correct
    # If something looks incorrect, we will mark it as invalid and skip processing
    valid_form : bool


class Instance:
    uuid:UUID
    workflow_uuid:UUID
    # It looks correct - eg variables are the right type, and so this is sane to try running
    valid_form:bool
    # In addition to being valid in its form, an instance interacts with the real world and so could encounter a processing error. We will want to skip processing it until that is resolved manually.
    valid_state:bool
    # Sometimes we want to actualy just pause something, but it is both valid and has never errored
    paused:bool = False

    #We always start with the procedure named "start" and at its 0th step
    processing_step:tuple[str,int] = ("start",0)
    # The next time we will want to be iterated on. This is not a precise time it will run, but a rough minimum before it gets run. Often gets set by the yield_* commands
    #next_processing_time:date_type_somewhere