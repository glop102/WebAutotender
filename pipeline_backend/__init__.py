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


# test_workflow = Workflow()
# test_workflow.name = "Test Workflow - Simple Loop and print"
# global_workflows.append(test_workflow)

# test_workflow.constants["Loop Iterations"] = Integer(6)
# test_workflow.setup_variables["Loop Delay"] = Float(5.0)

# test_instance = test_workflow.spawn_instance()

# test_workflow.procedures["start"] = []
# test_workflow.procedures["start"].append(ProcessingStep(
#     "set_variable_value",
#     variable_name=VariableName("Loop Counter"),
#     value=Integer(0)
#     ))
# test_workflow.procedures["start"].append(ProcessingStep(
#     "jump_to_procedure",
#     procedure_name=String("main loop")
#     ))

# test_workflow.procedures["main loop"] = []
# test_workflow.procedures["main loop"].append(ProcessingStep(
#     "goto_if_equal",
#     procedure_name=String("cleanup"),
#     value1=VariableName("Loop Counter"),
#     value2=VariableName("Loop Iterations")
#     ))
# test_workflow.procedures["main loop"].append(ProcessingStep(
#     "log",
#     msg=String("Looping...")
#     ))
# test_workflow.procedures["main loop"].append(ProcessingStep(
#     "math_add",
#     output_variable=VariableName("Loop Counter"),
#     first=VariableName("Loop Counter"),
#     second=Integer(1)
#     ))
# test_workflow.procedures["main loop"].append(ProcessingStep(
#     "yield_for_seconds",
#     num_seconds=VariableName("Loop Delay")
#     ))
# test_workflow.procedures["main loop"].append(ProcessingStep(
#     "jump_to_procedure",
#     procedure_name=String("main loop")
#     ))

# test_workflow.procedures["cleanup"] = []
# test_workflow.procedures["cleanup"].append(ProcessingStep(
#     "log",
#     msg=String("Loop Done!")
#     ))
# test_workflow.procedures["cleanup"].append(ProcessingStep(
#     "pause_this_instance"
#     ))
# test_workflow.procedures["cleanup"].append(ProcessingStep(
#     "delete_this_instance"
#     ))
