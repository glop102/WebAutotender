from enum import Flag,auto
from types import UnionType
from typing import Callable,get_args
from inspect import signature
from .variables import *
from .instances import *

# This is the place that registers and validates commands that can be called in procedures.

class CommandReturnStatus(Flag): 
    # The instance will keep running
    Success = auto()
    # The instance will stop processing and wait until next_processing_time
    Yield = auto()
    # The instance will stop running and will not run again until manually restarted
    Error = auto()

    # Special case of telling the procedure runner to not modify the current proceesing step
    Keep_Position = auto()

class Commands:
    commands:dict[str,Callable] = {}
    @classmethod
    def get_command_input_variables(cls, command_name: str) -> list[tuple[str, type[WorkVariable]|tuple[type[WorkVariable]]]]:
        """Returns a in-order list of argument name and their type."""
        # Note to future me - do not change this from a list to a dict to reduce the type complexity. The list maintains order, the dict keys do not maintain order
        # This was used in the ProcedureRunner to build an args list to pass to the command function, which is order dependent
        if not command_name in cls.commands:
            raise NameError(f"Unable to find a command with the name {command_name}")
        sig = signature(cls.commands[command_name])
        argument_names = list(sig.parameters.keys())[1:] # sig.parameters nor its keys are directly iterable or slicable, so need to make it a list
        parms = []
        for arg_name in argument_names:
            match(sig.parameters[arg_name].annotation):
                case args_union if isinstance(args_union,UnionType):
                    parms.append(
                        (arg_name,get_args(args_union))
                    )
                case x if issubclass(x,WorkVariable):
                    parms.append(
                        (arg_name,x)
                    )
        return parms

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
                match(sig.parameters[arg_name].annotation):
                    case args_union if isinstance(args_union,UnionType):
                        for arg in get_args(args_union):
                            if not issubclass(arg,WorkVariable):
                                raise TypeError(f"Commands for processing must only accept WorkVariable subclasses. Instead of {arg}")
                    case x if issubclass(x,WorkVariable): pass
                    case _:
                        raise TypeError(f"Commands for processing must only accept WorkVariable classes. Instead of {sig.parameters[arg_name].annotation}")
                
        # Make sure that it returns a valid type for telling us if it succedded or failed or whatnot
        if not sig.return_annotation == CommandReturnStatus:
            raise TypeError("Commands for processing must return a CommandReturnStatus")
        
        cls.commands[item.__name__] = item
        # Let that function keep existing wherever it is. We were only wanting to get a reference to it.
        return item
    
    @classmethod
    def get_command_by_name(cls,command_name:str) -> Callable:
        if not command_name in cls.commands:
            raise KeyError(f"Unable to find {command_name} in the list of available commands")
        return cls.commands[command_name]

    @classmethod
    def get_command_doc_string(cls,command_name:str) -> str|None:
        if not command_name in cls.commands:
            raise KeyError(f"Unable to find {command_name} in the list of available commands")
        sig = signature(cls.commands[command_name])
        return sig.__doc__

    @classmethod
    def json_savable_all_commands_with_args(cls) -> dict:
        coms_with_args = {}
        for name in cls.commands:
            coms_with_args[name] = cls.json_savable_command_information(name)
        return coms_with_args
    
    @classmethod
    def json_savable_command_information(cls,command_name:str) -> dict:
        # TODO - Also pass back the doc string
        args = cls.get_command_input_variables(command_name)
        args_str = {}
        for arg in args:
            arg_name = arg[0]
            arg_types = arg[1]
            if type(arg_types) == tuple:
                args_str[arg_name] = [vt.__name__ for vt in arg_types]
            else:
                args_str[arg_name] = arg_types.__name__
        return {"arguments":args_str}

    @classmethod
    def json_savable_all_command_names(cls) -> list:
        return [name for name in cls.commands]
