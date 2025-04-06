from enum import Enum
from collections.abc import Callable
from typing import Any, Self
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
    value:Any|Self
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
        # Copy constructor or encapsulation type promotion
        # the subclasses implement their own inits to add in type information for easier linting when using the variables
        if type(value) == self.__class__:
            self.value = deepcopy(value.value)
        else:
            self.value = deepcopy(value)

    def is_valid(self)->bool:
        return False
    def normalize(self)->None:
        """
        Try to make the value of a variable fully sensible. eg convert a number to an int for Integer, or strip the whitespace off a string.
        """
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
        self.normalize()

    def coerce_into_type(self,new_type:type[Self])->Self|None:
        """Makes a copy of itself and attempt to coerce it into the new_type. Will return None if unsucsessful."""
        converted_var = deepcopy(self)
        converted_var.__class__ = new_type
        try:
            converted_var.normalize()
        except:
            return None
        if converted_var.is_valid():
            return converted_var
        return None

    def convert_to_python_type(self)->Any:
        """
        Converts recursivly the value of the WorkVaraible to be a base python type.
        Some types are simple and jsut need to return their value, but others like lists need to do some extra work.
        """
        if issubclass(self.value.__class__,WorkVariable):
            return self.value.convert_to_python_type()
        else:
            return deepcopy(self.value)

class String(WorkVariable):
    value:str
    def __init__(self, value: str | Self | None = None):
        if not value:
            value = ""
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
        if not value:
            value = 0
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
        if not value:
            value = 0.0
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
        if not value:
            value = ""
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
        if not value:
            value = []
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


class VariableList(WorkVariable):
    # A list of general other work variables. This lets you mix and match things if a programer so needs.
    value: list[WorkVariable]

    def __init__(self, value: list[WorkVariable] | Self | None = None):
        if not value:
            value = []
        super().__init__(value)

    def is_valid(self) -> bool:
        if type(self.value) != list:
            return False
        for x in self.value:
            if type(x) != WorkVariable:
                return False
        return True

    def normalize(self) -> None:
        if type(self.value) != list:
            raise ValueError(
                f"Needs to be a list to be a {self.__class__.__name__} value")
        for idx, val in enumerate(self.value):
            if not isinstance(val,WorkVariable):
                if type(val) == dict:
                    newval = WorkVariable()
                    newval.json_loadable(val)
                    newval.normalize()
                    self.value[idx] = newval
                else:
                    raise TypeError("The items in the VariableList are not dict and so cannot be converted to a WorkVariable.")

    def reset_to_default(self) -> None:
        self.value = []

    def json_savable(self) -> dict:
        simplified_value = []
        for value in self.value:
            simplified_value.append(value.json_savable())
        return {'value': simplified_value, 'typename': self.typename}

    def convert_to_python_type(self)->list[Any]:
        return [var.convert_to_python_type() for var in self.value]

# Specific type that is intended to say that it is refering to a different variable; either in an Instance or Workflow.
# Used for procedures to differentiate between variables and constants
class VariableName(WorkVariable):
    value:str
    def __init__(self, value: str | Self | None = None):
        if not value:
            value = ""
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
        if not value:
            value = []
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

# I have tried to get around needing a complete mapping type like this, but in the end, I just need
# to have a map of varname to WorkVariable for the spawning of an Instance.
# If I don't have this Dictionary that has WorkVariables as values, then to spawn an instance, you
# would need to save every value to a variable and then pass in VariableNameList which just so happens
# to have the indices line up which is a very weak mapping
class Dictionary(WorkVariable):
    value:dict[str,WorkVariable]
    def __init__(self, value: dict[str,WorkVariable] | Self | None = None):
        if not value:
            value = {}
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
        # Make sure all keys are strings
        for key in self.value:
            if type(key) != str:
                val = self.value[key]
                self.value[str(key).strip()] = val
                del self.value[key]
        # Make sure all values are work variables
        for key,val in self.value.items():
            if not isinstance(val,WorkVariable):
                if type(val) == dict:
                    newval = WorkVariable()
                    newval.json_loadable(val)
                    newval.normalize()
                    self.value[key] = newval
                else:
                    raise TypeError("Entries in the Dictionary are not dict and cannot be converted to a WorkVariable.")

    def reset_to_default(self) -> None:
        self.value = {}
    def json_savable(self) -> dict:
        simplified_value = {}
        for key,value in self.value.items():
            simplified_value[key] = value.json_savable()
        return {'value': simplified_value, 'typename': self.typename}

    def convert_to_python_type(self)->dict[str,Any]:
        return {name:var.convert_to_python_type() for name,var in self.value.items()}

global_variables: dict[str,WorkVariable] = {}
