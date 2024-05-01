#!/usr/bin/env python3

# from fastapi import FastAPI

# app = FastAPI()

from src import *

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
# Note: make sure to have it gracefully handle going to a step that does not exist and then simply pausing the instance.
# Might want to make it delete itself by default? But could be nice to have it pause and wait for reading logs to debug if it is going somewhere weird.

test_instance = test_workflow.spawn_instance()
print(test_instance.__repr__())