from enum import Enum
from typing import Callable
from inspect import signature
import src.variables as variables
import src.workflows as workflows

# This is the place that registers and validates commands that can be called in procedures.

class CommandReturnStatus(Enum): 
    Success = 1
    Yield = 2
    Error = 3

class Commands:
    commands:dict[str,Callable] = {}
    @classmethod

    @classmethod
    def register_command(cls,item:Callable):
        sig = signature(item)
        function_arguments = list(sig.parameters.keys())
        if len(function_arguments) == 0:
            raise TypeError("Commands for processing must at least take one variable of the Instance they are processing for")
        if sig.parameters[function_arguments[0]].annotation != workflows.Instance:
            raise TypeError("Commands for processing must have their first argument be the Instance they are processing for")
        # Make sure they are only ever asking for types that are WorkVariable types
        if len(function_arguments) > 1:
            for arg_name in function_arguments[1:]:
                if not sig.parameters[arg_name].annotation in variables.WorkVariable.__subclasses__():
                    raise TypeError("Commands for processing must only accept WorkVariable classes")
                
        # Make sure that it returns a valid type for telling us if it succedded or failed or whatnot
        if not sig.return_annotation == CommandReturnStatus:
            raise TypeError("Commands for processing must return a CommandReturnStatus")
        
        cls.commands[item.__name__] = item
