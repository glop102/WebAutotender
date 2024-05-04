import traceback
from copy import deepcopy
from .commands import *
from .variables import *
from .instances import *
from .workflows import *

# =====================================================================================
# Processing Steps
# =====================================================================================
# A procedure is a series of steps that it will follow. Essentially a linear function.
# A processing step is something that addons can create that let us perform actions.
# There are some built in processings steps, such as yield_for and yield_until.
#
# Important Programmer Note : deepcopy variables that go into the funtion to prevent
# unintended sideeffects of changing the Constants of the ProcessingStep or values
# of the Instance variables when just naivly using the values in an addon
#
# Some built in commands that we will need to have
# yield_for(time)
# yield_until(time)
# delete_this_instance()
# make_new_instance(arg_list)
# goto_if_equal/notequal/greaterthan/lessthan(var1,var2,destination_precedure_name)
# set_variable(var_name,value_expression)
# error(message)
# regex(expression,value,destination_var)
# string_builder(stringlist_commands,destination_var) - takes in strings and combines it together with some operations on segments like leftpad() so we can get a complicated string built up


class ProcedureRunner:
    instance:Instance
    workflow:Workflow
    def __init__(self,instance:Instance):
        self.instance = instance
        self.workflow = instance.get_associated_workflow()
    
    def run_single_step(self) -> CommandReturnStatus:
        """Runs a single step of the procedure of the instance. Does most sanity checking and setup for calling a command. Wrap this in a try:except block """

        # get the command for the current step
        proc_name,step_idx = self.instance.processing_step
        try:
            procedure:list[ProcessingStep] = self.workflow.procedures[proc_name]
            proc_step = procedure[step_idx]
            # ProcessingStep has workvariables inside of it that are intended to be passed to the command, so we need to do some simple verification before handing it off to said command
        except KeyError as e:
            self.instance.state = RunStates.Error
            self.instance.log_line(f"Error: Unable to find the procedure {proc_name} in the workflow {self.workflow.name} when processing an Instance")
            self.instance.log_line(self.instance.__repr__())
            return CommandReturnStatus.Error
        except IndexError as e:
            self.instance.state = RunStates.Error
            self.instance.log_line(f"Error: Unable to get step {step_idx} of procedure {proc_name} in the workflow {self.workflow.name} when processing an Instance. Only {len(procedure)} steps are in that procedure")
            self.instance.log_line(self.instance.__repr__())
            return CommandReturnStatus.Error
        
        # get the variables for that command
        command:Callable = Commands.get_command_by_name(proc_step.command_name)
        req_vartypes = Commands.get_command_input_variables(proc_step.command_name)
        if len(req_vartypes) != len(proc_step.variables):
            self.instance.state = RunStates.Error
            self.workflow.state = RunStates.Error
            self.instance.log_line(f"Error: Inconsistent number of variables for the command {proc_step.command_name} - we have {len(proc_step.variables)} but the command expects {len(req_vartypes)}")
            self.instance.log_line(self.instance.__repr__())
            return CommandReturnStatus.Error
        
        # check the vars it needs and resolve references if it is asking for a more concrete type but given a variable name, or error if given an invalid type
        variables_for_command:list = [self.instance]
        for var_name,req_type in req_vartypes:
            if not var_name in proc_step.variables:
                self.instance.state = RunStates.Error
                self.workflow.state = RunStates.Error
                self.instance.log_line(f"Error: Unable to find the argument {var_name} given in the procedure step {self.workflow.name}/{proc_name}/{step_idx}")
                self.instance.log_line(self.instance.__repr__())
                return CommandReturnStatus.Error
            given_var = proc_step.variables[var_name]
            # Happy case
            if req_type == given_var.__class__:
                variables_for_command.append(deepcopy(given_var))
                continue
            # Common case of giving a variable name but really we are wanting to pass the value of a variable
            # TODO - Have it recursivly look up variable references until getting a concrete type
            if given_var.__class__ == VariableName:
                given_var = self.instance[given_var.value]
                # If it is the same type, then we are good, otherwise let it continue which will try to convert it
                if req_type == given_var.__class__:
                    variables_for_command.append(deepcopy(given_var))
                    continue
            # A Convenience case of type coercion - try to convert it to the requested type and pray that it works
            converted_var = deepcopy(given_var)
            converted_var.__class__ = req_type
            converted_var.normalize()
            if converted_var.is_valid():
                variables_for_command.append(converted_var)
            else:
                self.instance.state = RunStates.Error
                self.workflow.state = RunStates.Error
                self.instance.log_line(f"Error: Unable to convert argument {var_name} from a {given_var.__class__.__name__} to a {req_type.__name__} in the procedure step {self.workflow.name}/{proc_name}/{step_idx}")
                self.instance.log_line(self.instance.__repr__())
                return CommandReturnStatus.Error

        # run command
        try:
            command_finish_state:CommandReturnStatus = command(*variables_for_command)
        except Exception as e:
            self.instance.log_line(f"\nError: Exception thrown by the command {proc_step.command_name} in instance {self.workflow.name}/{self.instance.uuid}")
            self.instance.log_line(self.instance.__repr__())
            self.instance.log_line(traceback.format_exc())
            return CommandReturnStatus.Error

        # check return state
        if type(command_finish_state) != CommandReturnStatus:
            self.instance.state = RunStates.Error
            self.instance.log_line(f"Error: Command {proc_step.command_name} returned a value that is not a CommandReturnStatus but instead a {type(command_finish_state)}")
            self.instance.log_line(self.instance.__repr__())
            return CommandReturnStatus.Error
        match(command_finish_state):
            case CommandReturnStatus.Error:
                self.instance.state = RunStates.Error
            case CommandReturnStatus.Yield | CommandReturnStatus.Success:
                self.instance.processing_step = (proc_name,step_idx+1)

        return command_finish_state