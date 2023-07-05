from src.SyntacticAnalysis import Ast

"""
Register the signature of functions, and provide the infrastructure to request the correct function based on the
type-constraints, parameter types, and number of arguments.
"""


class FunctionRegister:
    REGISTRY: dict[Ast.IdentifierAst, list[Ast.FunctionPrototypeAst]] = dict()

    @staticmethod
    def register_function(function_prototype: Ast.FunctionPrototypeAst):
        fn_name = function_prototype.identifier
        FunctionRegister.REGISTRY[fn_name] = FunctionRegister.REGISTRY.get(fn_name, []) + [function_prototype]
