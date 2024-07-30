"""classes for AMPL types"""

import re
import typing as t


AMPL_TYPES = t.Literal["number", "string"]


class TypeBase:
    """abstract base class for AMPL types"""

    type_name: str
    regex: re.Pattern

    def __init__(self, value: str | t.Any) -> None:
        """initialize an object that represents one instance of an ampl datatype

        args:
            - `value (str | Any)`: ideally should be a str
        """
        self.value = value

    def __repr__(self) -> str:
        return f"<Ampl{self.__class__.__name__}({self.value})>"


class Primitive(TypeBase):
    """abstract base class for AMPL primitives"""

    type_name = "primitive"

    @classmethod
    def parse_type(cls, value: str) -> t.Self:
        """parses the type of the primitive

        args:
            - `value (str)`: the value of the primitive
        returns:
            - `t.Self`: an instance of the primitive, falls back to Primitive if the type is not recognized
        """

        classes = cls.__subclasses__()
        if not cls.__name__ == "Primitive":
            classes += list(cls.__bases__)
        for _sub in cls.__subclasses__():
            if _sub.regex.match(value):
                return _sub(value)
        return cls(value)


class Number(Primitive):
    """class for any number"""

    type_name = "number"
    regex = re.compile(r"\b([0-9]+(\.[0-9]+)?)")


class Symbolic(Primitive):
    """class for ampl strings;

    why is it called symbollic"""

    type_name = "symbollic"
    regex = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)")


# class Set(TypeBase):
#     """class for AMPL sets"""

#     type_name = "set"
#     regex = re.compile(r"^set ([a-z]\w+)")


class Argument(TypeBase):
    """class for AMPL arguments"""

    type_name = "argument"
    regex = re.compile(r"(?P<name>\w+): (?P<type>\w+)")


class Function(TypeBase):
    """class for AMPL functions"""

    type_name = "function"
    regex = re.compile(r"^function ([a-z]\w+)\(")


class Variable(TypeBase):
    """class for AMPL types"""

    type_name = "variable"
    regex = re.compile(
        r"^(arc|maximize|minimize|node|param|set|function|subj to|s\.t\.|subject\sto|var)\s(?![if|and|or])([a-zA-Z_][a-zA-Z0-9_]*)"
    )

    def __init__(
        self, name: str, declaration: str, type_: AMPL_TYPES, value: str
    ) -> None:
        """initialize an AMPLVariable object

        args:
            - `name (str)`: the name of the variable
            - `type_ (AMPL_TYPES)`: the type of the variable
        """
        super().__init__(value)
        self.name = name
        self.declaration = declaration
        self.type = type_
