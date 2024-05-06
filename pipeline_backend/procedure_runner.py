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
            return self.__mark_error(f"Error: Unable to find the procedure {proc_name} in the workflow {self.workflow.name} when processing an Instance")
        except IndexError as e:
            return self.__mark_error(f"Error: Unable to get step {step_idx} of procedure {proc_name} in the workflow {self.workflow.name} when processing an Instance. Only {len(procedure)} steps are in that procedure")
        
        # Find the command - also guarentees we can find the var to go with it to build the variable list
        try:
            command:Callable = Commands.get_command_by_name(proc_step.command_name)
        except:
            return self.__mark_error(f"\nError: Unable to find the command {proc_step.command_name}",True)

        # check the vars it needs and resolve references if it is asking for a more concrete type but given a variable name, or error if given an invalid type
        variables_for_command:list|None = self.build_variables_list_for_command(proc_step)
        if not variables_for_command:
            return CommandReturnStatus.Error

        # run command
        try:
            command_finish_state:CommandReturnStatus = command(*variables_for_command)
        except Exception as e:
            return self.__mark_error(f"{traceback.format_exc()}\nError: Exception thrown by the command {proc_step.command_name} in instance:")

        # check return state
        if type(command_finish_state) != CommandReturnStatus:
            return self.__mark_error(f"Error: Command {proc_step.command_name} returned a value that is not a CommandReturnStatus but instead a {type(command_finish_state)}")
        match(command_finish_state):
            case CommandReturnStatus.Error:
                self.instance.state = RunStates.Error
            case CommandReturnStatus.Yield | CommandReturnStatus.Success:
                if not CommandReturnStatus.Keep_Position in command_finish_state:
                    self.instance.processing_step = (proc_name,step_idx+1)
            case _:
                return self.__mark_error(f"Error: Unknown return state from the command {proc_step.command_name} - {command_finish_state} {type(command_finish_state)}")

        return command_finish_state & CommandReturnStatus.Success
    
    def run_instance_until_yield(self):
        while self.run_single_step() == CommandReturnStatus.Success:
            pass


    def __mark_error(self,message:str="",also_mark_workflow:bool=False)->CommandReturnStatus:
        self.instance.state = RunStates.Error
        if also_mark_workflow:
            self.workflow.state = RunStates.Error
        self.instance.log_line(message)
        self.instance.log_line(self.instance.__repr__())
        return CommandReturnStatus.Error
    
    def __check_deref_coerce_variable(self,given_var:WorkVariable,req_type:type[WorkVariable]|tuple[type[WorkVariable]])->WorkVariable|None:
        # Happy case - already as expected or the function will take anything
        if type(req_type) == tuple:
            if type(given_var) in req_type:
                return deepcopy(given_var)
        else:
            if req_type == given_var.__class__ or req_type == WorkVariable:
                return deepcopy(given_var)

        # Common case of giving a variable name but really we are wanting to pass the value of a variable
        if given_var.__class__ == VariableName:
            try:
                retrieved_var = self.instance[given_var.value]
                return self.__check_deref_coerce_variable(retrieved_var, req_type)
            except Exception as e:
                self.__mark_error(f"Error: Unable to do variable lookup to convert a type in the procedure. \n{traceback.format_exc()}")
                return None

        # A Convenience case of type coercion - try to convert it to the requested type and pray that it works
        if type(req_type) == tuple:
            converted_var = None
            for req_type2 in req_type:
                converted_var = given_var.coerce_into_type(req_type2)
                if converted_var: break
        else:
            converted_var = given_var.coerce_into_type(req_type)
        if converted_var:
            return converted_var
        else:
            self.__mark_error(f"Error: Unable to convert argument from a {given_var.__class__.__name__} to a {req_type.__name__} in the procedure step", True)
            return None

    def build_variables_list_for_command(self,proc_step:ProcessingStep) -> list|None:
        req_vartypes = Commands.get_command_input_variables(proc_step.command_name)
        if len(req_vartypes) != len(proc_step.variables):
            self.__mark_error(f"Error: Inconsistent number of variables for the command {proc_step.command_name} - we have {len(proc_step.variables)} but the command expects {len(req_vartypes)}", True)
            return None

        variables_for_command: list = [self.instance]
        for var_name, req_type in req_vartypes:
            if not var_name in proc_step.variables:
                self.__mark_error(f"Error: Unable to find the argument {var_name} given in the procedure step", True)
                return None
            given_var = proc_step.variables[var_name]
            conv_var = self.__check_deref_coerce_variable(given_var,req_type)
            if not conv_var:
                return None
            else:
                variables_for_command.append(conv_var)

        return variables_for_command
