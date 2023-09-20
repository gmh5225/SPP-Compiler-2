"""
Common types are used by the compiler for either literals getting their correct type, or for checking an expression
evaluates to a certain type. For example, the "Void" type is used for checking that a function doesn't return a value,
and while/if-pattern condition expressions must evaluate to a boolean.
"""
from src.SemanticAnalysis2.NsSubstitution import NsSubstitution
from src.SyntacticAnalysis import Ast


class CommonTypes:
    @staticmethod
    def void(s) -> Ast.TypeAst:
        # Void type for a "no-value" return
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Void", [], -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def bool(s) -> Ast.TypeAst:
        # Boolean type
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Bool", [], -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def str(s) -> Ast.TypeAst:
        # String type
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Str", [], -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def arr(element_type: Ast.TypeAst, s) -> Ast.TypeAst:
        # Character type
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Arr", [element_type], -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def rgx(s) -> Ast.TypeAst:
        # Regular expression type
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Rgx", [], -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def num(s) -> Ast.TypeAst:
        # Number type
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Num", [], -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def tup(element_types: list[Ast.TypeAst], s) -> Ast.TypeAst:
        # Tuple type - add the types of the tuple as the generic arguments
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Tup", element_types, -1)], -1)
        NsSubstitution.do_substitution(t, s)
        return t

    @staticmethod
    def self() -> Ast.TypeAst:
        # Self type
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Self", [], -1)], -1)

    @staticmethod
    def is_function_type(ast: Ast.TypeSingleAst) -> Ast.TypeAst:
        c1 = ast.parts_as_strings() == ["std", "FnRef"]
        c2 = ast.parts_as_strings() == ["std", "FnMut"]
        c3 = ast.parts_as_strings() == ["std", "FnOne"]
        return c1 or c2 or c3
