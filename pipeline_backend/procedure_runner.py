from .variables import *
from .commands import *
from .workflows import *

# =====================================================================================
# Processing Steps
# =====================================================================================
# A procedure is a series of steps that it will follow. Essentially a linear function.
# A processing step is something that addons can create that let us perform actions.
# There are some built in processings steps, such as yield_for and yield_until.
#
# An important two things to make this fully capable and probably turing complete is
# to have branches and jumps. 
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


# Commands will get registered with a function decorator or something
# Either they specify their arguments to the decorator specifically, or we do reflection
# to grab their arguments.
# In any case, we will have a name to type mapping that we can serve back to the UI for
# user friendliness of what each argument in the list is.

# Possible conventions for the command that will be called
# - command(instance:Instance,variables:dict[str,WorkVariable])
# - command(instance:Instance, var1:WorkVariable)


class ProcedureRunner:
    def __init__(self,instance:Instance):
        self.instance = instance
    
    def run_single_step(self):
        """Runs a single step of the procedure of the instance"""
        # skip checking if an instance is valid - we are a runner, not a checker
        # get the current step
        # get the command for that step
        # get the variables for that command
        # check the vars it needs and resolve references if it is asking for a more concrete type
        # run command
        # check return state
        # update instance (we need to think about branches and who increments the step)
        pass