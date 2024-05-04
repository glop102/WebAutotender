#!/usr/bin/env python3

# from fastapi import FastAPI

# app = FastAPI()

from pipeline_backend import *

#Test setup to think through the process and do an example tight yield loop
# Have 1 test workflow
# Have 2 instances of that workflow
# Make a few of the util functions to prove out the argument list setup
#  variable reading
#  variable setting
#  instance variables overshadowing workflow variables

# workflows : dict[str,Workflow] = {}
# instances : list[Instance] = []

test_workflow = Workflow()
test_workflow.name = "Test Workflow"
global_workflows.append(test_workflow)
test_var: WorkVariable

test_var = Integer()
test_var.value = 6
test_workflow.constants["Loop Iterations"] = test_var

test_var = String()
test_var.value = "This is a debug message."
test_workflow.setup_variables["Debug Message Echo"] = test_var

test_var = Float()
test_var.value = 10.0
test_workflow.setup_variables["Loop Delay"] = test_var


test_instance = test_workflow.spawn_instance()

@Commands.register_command
def test_command(inst: Instance, debug_msg: String) -> CommandReturnStatus:
    print(debug_msg)
    return CommandReturnStatus.Success
@Commands.register_command
def intentional_error_throw(inst: Instance) -> CommandReturnStatus:
    raise Exception()


test_workflow.procedures["start"] = []
for _ in range(10):
    test_procstep = ProcessingStep()
    test_procstep.command_name = "test_command"
    test_procstep.variables["debug_msg"] = VariableName()
    test_procstep.variables["debug_msg"].value = "Debug Message Echo"
    test_workflow.procedures["start"].append(test_procstep)

test_procstep = ProcessingStep()
test_procstep.command_name = "intentional_error_throw"
test_workflow.procedures["start"].append(test_procstep)

proc_runner = ProcedureRunner(test_instance)
if CommandReturnStatus.Error == proc_runner.run_single_step():
    print("Correctly detected incorrect number of variables in the processing step for the command given")
    print(test_workflow.__repr__())
    print(test_instance.__repr__())

if CommandReturnStatus.Error == proc_runner.run_instance_until_yield():
    print("Correctly did return an error status after the throw. Printing the instance console log now")

assert (test_instance.state == RunStates.Error)


# TODO
# persistence save/load functions
# Something that is the main background process
# - some setup of loading the persistent data
# - loading some addons by including all sub-folders with __init__.py files in builtin_addons and user_addons
# - mainloop() that makes a background thread or something and just starts processing away with appropriate long waits until the next due date
# fastapi
# - start the basic endpoints to read the workflows and instances, including all and by name/uuid
# - endpoint to add new workflows
# - endpoint to spawn new instances of a workflow
# - endpoints to modify workflows and instances
# web frontend : who knows


# Lets make the workflow go like this:
# start:
# - first make a loop counter variable with a value of 0
# - divert to the main loop step of the procedure to actually loop
# main loop:
# - print debug message - TODO Make a log utility so an instance can be debugged without putting status information into variables. Runtime only lifetime, so not serialized.
# - check if loop counter is equal to the loop iterations
#   - if equal, goto loop end
# - yield for loop delay time
# - divert to main_loop
# loop end:
# - print constant string of "Done Looping!"
# - delete this instance

# import json
# test_json = json.dumps(test_instance.json_savable(),indent=4)
# print(test_json)
# test_another_instance = Instance()
# test_another_instance.json_loadable(json.loads(test_json))
# print(test_another_instance.__repr__())

# print("\n\n")
# print(test_workflow.__repr__())
# test_json = json.dumps(test_workflow.json_savable(), indent=4)
# print(test_json)
# test_another_workflow = Workflow()
# test_another_workflow.json_loadable(json.loads(test_json))
# print(test_another_workflow.__repr__())

save_pipeline_global_state_to_file("test_data.json")
load_pipeline_global_state_from_file("test_data.json")

for w in global_workflows: print(w.__repr__())
for i in global_instances: print(i.__repr__())