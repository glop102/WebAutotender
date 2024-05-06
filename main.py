#!/usr/bin/env python3

from pipeline_backend import *
from time import sleep

test_workflow = Workflow()
test_workflow.name = "Test Workflow - Simple Loop and print"
global_workflows.append(test_workflow)

test_workflow.constants["Loop Iterations"] = Integer(6)
test_workflow.setup_variables["Loop Delay"] = Float(5.0)

test_instance = test_workflow.spawn_instance()

test_workflow.procedures["start"] = []
test_workflow.procedures["start"].append(ProcessingStep(
    "set_variable_value",
    variable_name=VariableName("Loop Counter"),
    value=Integer(0)
    ))
test_workflow.procedures["start"].append(ProcessingStep(
    "jump_to_procedure",
    procedure_name=String("main loop")
    ))

test_workflow.procedures["main loop"] = []
test_workflow.procedures["main loop"].append(ProcessingStep(
    "goto_if_equal",
    procedure_name=String("cleanup"),
    value1=VariableName("Loop Counter"),
    value2=VariableName("Loop Iterations")
    ))
test_workflow.procedures["main loop"].append(ProcessingStep(
    "log",
    msg=String("Looping...")
    ))
test_workflow.procedures["main loop"].append(ProcessingStep(
    "math_add",
    output_variable=VariableName("Loop Counter"),
    first=VariableName("Loop Counter"),
    second=Integer(1)
    ))
test_workflow.procedures["main loop"].append(ProcessingStep(
    "yield_for_seconds",
    num_seconds=VariableName("Loop Delay")
    ))
test_workflow.procedures["main loop"].append(ProcessingStep(
    "jump_to_procedure",
    procedure_name=String("main loop")
    ))

test_workflow.procedures["cleanup"] = []
test_workflow.procedures["cleanup"].append(ProcessingStep(
    "log",
    msg=String("Loop Done!")
    ))
test_workflow.procedures["cleanup"].append(ProcessingStep(
    "pause_this_instance"
    ))
test_workflow.procedures["cleanup"].append(ProcessingStep(
    "delete_this_instance"
    ))

manager = PipelineManager()
manager.start()
while test_instance.state == RunStates.Running:
    sleep(1.0)
print(test_instance.console_log)
sleep(1.0)
test_instance.state = RunStates.Running
manager.notify_of_something_happening()
while test_instance in global_instances:
    sleep(0.1)
manager.stop()
manager.join()
print(test_instance.console_log)

# TODO
# the test workflow and any other basic commands I can think of
# module importing of addons for things like the torrent commands
# fastapi
# - shutdown event triggers the background process to save
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
# - print debug message
# - check if loop counter is equal to the loop iterations
#   - if equal, goto loop end
# - yield for loop delay time
# - divert to main_loop
# loop end:
# - print constant string of "Done Looping!"
# - delete this instance



print("\nDisplaying all global Workflows and Instances")
for w in global_workflows: print(w.__repr__())
for i in global_instances: print(i.__repr__())

# from fastapi import FastAPI
# import uvicorn
# app = FastAPI()
# uvicorn.run(app, port=6778)
#TODO - finally statement or something to have the pipeline manager stop running and save its state
