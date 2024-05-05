from enum import Enum
from collections.abc import Callable
from typing import Self
from copy import deepcopy

# =====================================================================================
# Variables
# =====================================================================================
# Variables have a value and a type. types have a validation + normalization methods as
# well as a default value.
# The normalization methods should attempt to convert into a valid type, but are allowed to
# throw an exception. Make sure to double check that it is a valid type after attempting
# to normalize.
#
# As an addon or type author, simply inherit from the WorkVariable and implement the couple
# of methods we need [is_valid,normalize,reset_to_default]
# Do not do anything too fancy with your type. Keep it as flat and not dynamic as possible.
# You might want to also copy the init function of the specifict types so you can get type
# information added to the constructor
#
# Tech Explination Ramblings:
# Class.__subclasses__() is a dynamically created list of subclasses.
# All an addon would have to do is subclass the WorkVariable class and it will just magically get registered already!
# You can also just grab the human readable name with __name__ to then reference back and forth.
# And to round it off, you can *force* a class change with self.__class__ = OtherClass and if it is in the heritable tree, it will be cast!

class WorkVariable:
    value:None
    @property
    def typename(self)->str:
        return self.__class__.__name__

    @typename.setter
    def typename(self,typename:str)->None:
        for cls in WorkVariable.__subclasses__():
            if cls.__name__ == typename:
                self.__class__ = cls
                return
        raise TypeError(f"Unable to find a WorkVariable type to cast into with the name {typename}")

    def __init__(self, value: Self | None = None):
        # Copy constructor or encapsulation tpye promotion
        # the subclasses implement their own inits to add in type information for easier linting when using the variables
        if type(value) == self.__class__:
            self.value = deepcopy(value.value)
        else:
            self.value = deepcopy(value)

    def is_valid(self)->bool:
        return False
    def normalize(self)->None:
        pass
    def reset_to_default(self)->None:
        self.value = None

    def __str__(self)->str:
        return f"{self.__class__.__name__}({self.value})"
    
    def json_savable(self)->dict:
        return {'value':self.value,'typename':self.typename}
    def json_loadable(self,data:dict)->None:
        self.value = data['value']
        self.typename = data['typename']

class String(WorkVariable):
    value:str
    def __init__(self, value: str | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        return type(self.value) == str
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = str(self.value)
        self.value = self.value.strip()
    def reset_to_default(self) -> None:
        self.value = ""

class Integer(WorkVariable):
    value:int
    def __init__(self, value: int | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        return type(self.value) == int
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = int(self.value)
    def reset_to_default(self) -> None:
        self.value = 0

class Float(WorkVariable):
    value:float
    def __init__(self, value: float | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        return type(self.value) == float
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = float(self.value)
    def reset_to_default(self) -> None:
        self.value = 0.0

class URL(WorkVariable):
    value:str
    def __init__(self, value: str | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        return type(self.value) == str and "://" in self.value
    def normalize(self) -> None:
        if type(self.value) != str:
            self.value = str(self.value) .strip()
    def reset_to_default(self) -> None:
        self.value = ""

class StringList(WorkVariable):
    value:list[str]
    def __init__(self, value: list[str] | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        if type(self.value) != list: return False
        for x in self.value:
            if type(x) != str: return False
        return True
    def normalize(self) -> None:
        if type(self.value) != list:
            raise ValueError(f"Needs to be a list to be a {self.__class__.__name__} value")
        for idx,val in enumerate(self.value):
            self.value[idx] = str(val).strip()
    def reset_to_default(self) -> None:
        self.value = []

# Specific type that is intended to say that it is refering to a different variable; either in an Instance or Workflow.
# Used for procedures to differentiate between variables and constants
class VariableName(WorkVariable):
    value:str
    def __init__(self, value: str | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        return type(self.value) == str
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = str(self.value)
        self.value = self.value.strip()
    def reset_to_default(self) -> None:
        self.value = ""


class VariableNameList(WorkVariable):
    value:list[str]
    def __init__(self, value: list[str] | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        if type(self.value) != list: return False
        for x in self.value:
            if type(x) != str: return False
        return True
    def normalize(self) -> None:
        if type(self.value) != list:
            raise ValueError(f"Needs to be a list to be a {self.__class__.__name__} value")
        for idx,val in enumerate(self.value):
            self.value[idx] = str(val).strip()
    def reset_to_default(self) -> None:
        self.value = []

# I have tried to get around needing a comples mapping type like this, but in the end, I just need
# to have a map of varname to value for the spawning of a workflow instance command
class Dictionary(WorkVariable):
    value:dict[str,WorkVariable]
    def __init__(self, value: dict[str,WorkVariable] | Self | None = None):
        super().__init__(value)
    def is_valid(self) -> bool:
        if type(self.value) != dict: return False
        for key in self.value.keys():
            if type(key) != str: return False
        for val in self.value.values():
            if type(val) != WorkVariable and not WorkVariable.__subclasscheck__(type(val)):
                return False
        return True
    def normalize(self) -> None:
        if type(self.value) != dict:
            self.value = dict(self.value)
        for key in self.value:
            if type(key) != str:
                val = self.value[key]
                self.value[str(key).strip()] = val
    def reset_to_default(self) -> None:
        self.value = {}

global_variables: dict[str,WorkVariable] = {}
