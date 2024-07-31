"""classes for AMPL types"""

import re

import typing as t


class TypeBase:
    """abstract base class for AMPL types"""

    type_name: str
    regex: re.Pattern
    iterable: bool = False

    def __init__(self, value: str | t.Any = None) -> None:
        """initialize an object that represents one instance of an ampl primitive

        args:
            - `value (str | Any)`: ideally should be a str
        """
        self.value = value

    def __repr__(self) -> str:
        return f"<Ampl{self.__class__.__name__}({self.value})>"

    @property
    def display_name(self) -> str:
        """name displayed to the user"""
        if self.__class__.__subclasses__():
            return "Any"
        if self.iterable:
            return f"{self.type_name}[]"
        return self.type_name

    @classmethod
    def parse_type(cls, value: str) -> t.Self:
        """parses the type of the primitive

        args:
            - `value (str)`: the value of the primitive
        returns:
            - `t.Self`: an instance of the primitive, falls back to Primitive
        """

        classes = cls.__subclasses__()
        if parents := [c for c in cls.__bases__ if c is not object]:
            classes += [b for a in parents for b in a.__subclasses__()]
        for _sub in cls.__subclasses__():
            if _sub.regex.match(value):
                return _sub(value)
        return cls(value)


class Primitive(TypeBase):
    """abstract base class for AMPL primitives"""

    type_name: str = "primitive"


class Number(Primitive):
    """class for any number"""

    type_name: str = "number"
    regex: re.Pattern = re.compile(r"\b([0-9]+(\.[0-9]+)?)")


class Symbolic(Primitive):
    """class for ampl strings;

    why is it called symbolic"""

    type_name: str = "symbolic"
    regex: re.Pattern = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)")


class DeclaredType(TypeBase):
    """class for declared types"""

    type_name: str = "declared_type"
    identifier: str

    def __init__(self, value: str, subtype: t.Type[Primitive] = None) -> None:
        """initialize an AMPLSet object

        args:
            - `value (str)`: the value of the set
        """
        super().__init__(value)
        self.subtype: str = subtype

    def __repr__(self) -> str:
        return f"<Ampl{__class__.__name__}({self.subtype.__class__.__name__}"


class Set(DeclaredType):
    """set of array in AMPL"""

    type_name: str = "set"
    identifier: str = "set"
    iterable: bool = True


class Objective(DeclaredType):
    """the object of the model, can be maximized or minimized"""


class Constraint(DeclaredType):
    """a constraint in the model"""


# class Variable:
#     """class for AMPL variables"""

#     regex: re.Pattern = re.compile(
#         r"^(arc|maximize|minimize|node|param|set|function|subj to|s\.t\.|subject\sto|var)\s(?![if|and|or])([a-zA-Z_][a-zA-Z0-9_]*)"
#     )

#     def __init__(self, raw: str) -> None:
#         """initialize an AMPLVariable object

#         args:
#             - `raw (str)`: the raw string from the AMPL file
#         """
#         _match = self.regex.match(raw)
#         value = self.regex.match(raw).group(2)
#         self.name = name
#         self.declaration = declaration
#         self.type = type_


# class DeclaredType(Primitive):
#     """class for declared types"""


#     type_name: str = "set"
#     identifier: str = "set"
#     iterable: bool = False

#     def __init__(self, value: str, subtype: t.Type[Primitive] = None) -> None:
#         """initialize an AMPLSet object

#         args:
#             - `value (str)`: the value of the set
#         """
#         super().__init__(value)
#         self.subtype: str = subtype

#     def __repr__(self) -> str:
#         return f"<Ampl{__class__.__name__}({self.subtype.__class__.__name__}[])>"


# class Set(Primitive):
#     """a class representing a set or array in AMPL"""

#     type_name: str = "set"
#     identifier = "set"
#     regex: re.Pattern = re.compile(r"^set ([a-z]\w+)")
#     iterable = True

#     def __init__(self, value: str, subtype: t.Type[Symbolic | Number] = None) -> None:
#         """initialize an AMPLSet object

#         args:
#             - `value (str)`: the value of the set
#         """
#         super().__init__(value)
#         self.subtype: str = subtype

#     def __repr__(self) -> str:
#         return f"<Ampl{__class__.__name__}({self.subtype.__class__.__name__}[])>"


# class Set(TypeBase):
#     """class for AMPL sets"""

#     type_name: str = "set"
#     regex: re.Pattern = re.compile(r"^set ([a-z]\w+)")


class Argument(TypeBase):
    """class for AMPL arguments"""

    type_name: str = "argument"
    regex: re.Pattern = re.compile(r"(?P<name>\w+): (?P<type>\w+)")


class Function(TypeBase):
    """class for AMPL functions"""

    type_name: str = "function"
    regex: re.Pattern = re.compile(r"^function ([a-z]\w+)\(")
