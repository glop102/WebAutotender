from enum import Enum
from typing import Callable
from inspect import signature
from .variables import *
from .instances import *

# This is the place that registers and validates commands that can be called in procedures.

class CommandReturnStatus(Enum): 
    Success = 1
    Yield = 2
    Error = 3

class Commands:
    commands:dict[str,Callable] = {}
    @classmethod
    def get_command_input_variables(cls,command_name:str) -> list[tuple[str,type[WorkVariable]]]:
        """Returns a in-order list of argument name and their type"""
        if not command_name in cls.commands:
            raise NameError(f"Unable to find a command with the name {command_name}")
        sig = signature(cls.commands[command_name])
        parms = sig.parameters
        return [ (arg_name,parms[arg_name].annotation) for arg_name in list(parms.keys())[1:]]

    @classmethod
    def register_command(cls,item:Callable) -> Callable:
        sig = signature(item)
        function_arguments = list(sig.parameters.keys())
        if len(function_arguments) == 0:
            raise TypeError("Commands for processing must at least take one variable of the Instance they are processing for")
        if sig.parameters[function_arguments[0]].annotation != Instance:
            raise TypeError("Commands for processing must have their first argument be the Instance they are processing for")
        # Make sure they are only ever asking for types that are WorkVariable types
        if len(function_arguments) > 1:
            for arg_name in function_arguments[1:]:
                if not sig.parameters[arg_name].annotation in WorkVariable.__subclasses__() and not sig.parameters[arg_name].annotation == WorkVariable:
                    raise TypeError(f"Commands for processing must only accept WorkVariable classes. Instead of {sig.parameters[arg_name].annotation}")
                
        # Make sure that it returns a valid type for telling us if it succedded or failed or whatnot
        if not sig.return_annotation == CommandReturnStatus:
            raise TypeError("Commands for processing must return a CommandReturnStatus")
        
        cls.commands[item.__name__] = item
        # Let that function keep existing wherever it is. We were only wanting to get a reference to it.
        return item
    
    @classmethod
    def get_command_by_name(cls,command_name) -> Callable:
        if not command_name in cls.commands:
            raise KeyError(f"Unable to find {command_name} in the list of available commands")
        return cls.commands[command_name]
