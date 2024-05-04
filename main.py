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

print()

@Commands.register_command
def test_command(inst: Instance, debug_msg: String) -> CommandReturnStatus:
    print(type(debug_msg))
    print(debug_msg)
    return CommandReturnStatus.Success
@Commands.register_command
def intentional_error_throw(inst: Instance) -> CommandReturnStatus:
    raise Exception()

print("Lets actually run a procedure now.")
# First Procedure with a single command which is our debug message printing test_command
test_procstep = ProcessingStep()
test_workflow.procedures["start"] = [test_procstep]
test_procstep.command_name = "test_command"

proc_runner = ProcedureRunner(test_instance)
if CommandReturnStatus.Error == proc_runner.run_single_step():
    print("Correctly detected incorrect number of variables in the processing step for the command given")
    print(test_workflow.__repr__())
    print(test_instance.__repr__())
assert(test_instance.state == RunStates.Error)

test_instance.state = RunStates.Running #reset

print("\nWonderful! Corectly failed when not having the arguments, so this time we added in an argument.")
test_procstep.variables["debug_msg"] = VariableName()
test_procstep.variables["debug_msg"].value = "Debug Message Echo"

proc_runner.run_single_step()
print(test_instance.__repr__())

if CommandReturnStatus.Error == proc_runner.run_single_step():
    print("Correctly detected running out of items in the procedure to be used as commands")
    print(test_instance.__repr__())

print("\n\nPrinting the console log")
print(test_instance.console_log)

print("\n\n Lets clear the log, add a new processing step, and then double check it handles a command throwing an error.")
test_instance.console_log = ""
test_procstep = ProcessingStep()
test_workflow.procedures["start"].append(test_procstep)
test_procstep.command_name = "intentional_error_throw"
if CommandReturnStatus.Error == proc_runner.run_single_step():
    print("Correctly did return an error status after the throw. Printing the instance console log now")
    print(test_instance.console_log)