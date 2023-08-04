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
    def string() -> Ast.TypeAst:
        # String type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Str", [], -1)], -1)

    @staticmethod
    def char() -> Ast.TypeAst:
        # Character type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Char", [], -1)], -1)

    @staticmethod
    def regex() -> Ast.TypeAst:
        # Regular expression type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Rgx", [], -1)], -1)

    @staticmethod
    def num() -> Ast.TypeAst:
        # Number type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Num", [], -1)], -1)

    @staticmethod
    def tuple(types: list[Ast.TypeAst]) -> Ast.TypeAst:
        # Tuple type - add the types of the tuple as the generic arguments
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Tup", types, -1)], -1)
