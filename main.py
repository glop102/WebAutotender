#!/usr/bin/env python3

from pipeline_backend import *
from time import sleep

test_workflow = Workflow()
test_workflow.name = "Test Workflow"
global_workflows.append(test_workflow)

test_workflow.constants["Loop Iterations"] = Integer(6)
test_workflow.setup_variables["Debug Message Echo"] = String("This is a debug message.")
test_workflow.setup_variables["Loop Delay"] = Float(10.0)

test_instance = test_workflow.spawn_instance()

test_workflow.procedures["start"] = []
for _ in range(10):
    test_procstep = ProcessingStep()
    test_procstep.command_name = "log"
    test_procstep.variables["msg"] = VariableName("Debug Message Echo")
    test_workflow.procedures["start"].append(test_procstep)

test_procstep = ProcessingStep()
test_procstep.command_name = "delete_this_instance"
test_workflow.procedures["start"].append(test_procstep)

manager = PipelineManager()
manager.start()
sleep(1)
print(test_instance.console_log)
print()
manager.keep_running = False
manager.join()

# TODO
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



print("Displaying all global Workflows and Instances")
for w in global_workflows: print(w.__repr__())
for i in global_instances: print(i.__repr__())

# from fastapi import FastAPI
# import uvicorn
# app = FastAPI()
# uvicorn.run(app, port=6778)
#TODO - finally statement or something to have the pipeline manager stop running and save its state
