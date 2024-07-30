"""classes for AMPL types"""

import re


class AMPLTypeBase:
    """base class for AMPL types"""

    name: str
    regex: re.Pattern


class AMPLArgument(AMPLTypeBase):
    """class for AMPL arguments"""

    name = "argument"
    regex = re.compile(r"(?P<name>\w+): (?P<type>\w+)")


class AMPLFunction(AMPLTypeBase):
    """class for AMPL functions"""

    name = "function"
    regex = re.compile(r"^function ([a-z]\w+)\(")


class AMPLType(AMPLTypeBase):
    """class for AMPL types"""

    name = "type"
    regex = re.compile(r"^type ([A-Z]\w+)\(")
