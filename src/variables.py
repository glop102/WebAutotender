from enum import Enum
from collections.abc import Callable

# =====================================================================================
# Variables
# =====================================================================================
# Variables have a value and a type. types have a validation + normalization methods as
# well as a default value.
# The normalization methods should attempt to return a valid type, but are allowed to
# throw an exception.
#
# As an addon or type author, simply inherit from the WorkVariable.
# Do not do anything too fancy with your type. Keep it as flat and not dynamic as possible.
#
# Tech Explination Ramblings:
# Class.__subclasses__() is a dynamically created list of subclasses.
# All an addon would have to do is subclass the WorkVariable class and it will just magically get registered already!
# You can also just grab the human readable name with __name__ to then reference back and forth.
# And to round it off, you can *force* a class change with self.__class__ = OtherClass and if it is in the heritable tree, it will be cast!

class WorkVariable:
    value = None
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

    def is_valid(self)->bool:
        return False
    def normalize(self)->None:
        pass
    def reset_to_default(self)->None:
        self.value = None

class String(WorkVariable):
    value:str
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
    def is_valid(self) -> bool:
        return type(self.value) == int
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = int(self.value)
    def reset_to_default(self) -> None:
        self.value = 0

class Float(WorkVariable):
    value:float
    def is_valid(self) -> bool:
        return type(self.value) == float
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = float(self.value)
    def reset_to_default(self) -> None:
        self.value = 0.0

class URL(WorkVariable):
    value:str
    def is_valid(self) -> bool:
        return type(self.value) == str and "://" in self.value
    def normalize(self) -> None:
        if type(self.value) != str:
            self.value = str(self.value) .strip()
    def reset_to_default(self) -> None:
        self.value = ""

class StringList(WorkVariable):
    value:list[str]
    def is_valid(self) -> bool:
        if type(self.value) != list: return False
        for x in self.value:
            if type(x) != str: return False
        return True
    def normalize(self) -> None:
        if type(self.value) != list:
            return
        for idx,val in enumerate(self.value):
            self.value[idx] = val.strip()
    def reset_to_default(self) -> None:
        self.value = []

# Specific type that is intended to say that it is refering to a different variable; either in an Instance or Workflow.
# Used for procedures to differentiate between variables and constants
class VariableName(WorkVariable):
    value:str
    def is_valid(self) -> bool:
        return type(self.value) == str
    def normalize(self) -> None:
        if not self.is_valid():
            self.value = str(self.value)
        self.value = self.value.strip()
    def reset_to_default(self) -> None:
        self.value = ""

if __name__ == "__main__":
    test = WorkVariable()
    test.value = "ABCD"
    print(test.typename)
    print(test.value)
    test.typename = "String"
    print(test.typename)
    print(test.value)
    test.value = "EFGH"
    print(test.value)
