import pipeline_backend.commands_builtin
from .procedure_runner import *
from .persistence import *
from .manager import *

"""
Generally the hierarchy so far
ProcedureRunner
Workflow
Instance
WorkVariables and Commands

Workflow and Instances are what should be saved to disk and restored to continue state.
The Variables will be underneith (composition) of the instances and workflows.
The commands are registered at startup.

ProcedureRunner is just a runtime manager.
"""
