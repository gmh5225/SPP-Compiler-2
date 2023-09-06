"""
Common types are used by the compiler for either literals getting their correct type, or for checking an expression
evaluates to a certain type. For example, the "Void" type is used for checking that a function doesn't return a value,
and while/if-pattern condition expressions must evaluate to a boolean.
"""


from src.SyntacticAnalysis import Ast


class CommonTypes:
    @staticmethod
    def void() -> Ast.TypeAst:
        # Void type for a "no-value" return
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Void", [], -1)], -1)

    @staticmethod
    def bool() -> Ast.TypeAst:
        # Boolean type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Bool", [], -1)], -1)

    @staticmethod
    def str() -> Ast.TypeAst:
        # String type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Str", [], -1)], -1)

    @staticmethod
    def arr(element_type: Ast.TypeAst) -> Ast.TypeAst:
        # Character type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Arr", [element_type], -1)], -1)

    @staticmethod
    def reg() -> Ast.TypeAst:
        # Regular expression type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Rgx", [], -1)], -1)

    @staticmethod
    def num() -> Ast.TypeAst:
        # Number type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Num", [], -1)], -1)

    @staticmethod
    def tup(element_types: list[Ast.TypeAst]) -> Ast.TypeAst:
        # Tuple type - add the types of the tuple as the generic arguments
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Tup", element_types, -1)], -1)
