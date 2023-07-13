from enum import Enum

class __SemanticError(Exception):
    pass

class UnknownFunctionError(__SemanticError):
    def __init__(self, function: str, argument_types: list[str], type_arguments: list[str]):
        Exception.__init__(self, f"[0001] Could not find function {function} with argument types {argument_types} and type arguments {type_arguments}")

class IllegalBinaryLhsExpressionError(__SemanticError):
    def __init__(self, lhs_type: str):
        Exception.__init__(self, f"[0002] Binary expression left hand side must not be a literal, identifier or a parenthesized expression, not a {lhs_type}")

