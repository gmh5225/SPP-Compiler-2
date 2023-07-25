from __future__ import annotations

from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import ScopeHandler
from src.SyntacticAnalysis.Parser import ErrorFormatter


class TypeInference:
    @staticmethod
    def infer(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        TypeInference.infer_type_of_program(ast, s)
        s.switch_to_global_scope()

    @staticmethod
    def infer_type_of_program(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        for module_member in ast.module.body.members:
            match module_member:
                case Ast.FunctionPrototypeAst(): TypeInference.infer_type_of_function_prototype(module_member, s)
                case Ast.ClassPrototypeAst() | Ast.EnumPrototypeAst(): return
                case Ast.SupPrototypeNormalAst(): TypeInference.infer_type_of_sup_prototype(module_member, s)
                case Ast.SupPrototypeInheritanceAst(): TypeInference.infer_type_of_sup_prototype(module_member, s)

    @staticmethod
    def infer_type_of_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        s.next_scope()
        for statement in ast.body.statements:
            TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()

    @staticmethod
    def infer_type_of_statement(ast: Ast.StatementAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.TypedefStatementAst(): return
            case Ast.ReturnStatementAst(): return
            case Ast.LetStatementAst(): TypeInference.infer_type_of_let_statement(ast, s)
            case Ast.FunctionPrototypeAst(): TypeInference.infer_type_of_function_prototype(ast, s)
            case _: TypeInference.infer_type_of_expression(ast, s)

    @staticmethod
    def infer_type_of_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        if len(ast.variables) == 1:
            s.current_scope.get_symbol(ast.variables[0].identifier.identifier).type = ast.type_annotation or TypeInference.infer_type_of_expression(ast.value, s)
        else:
            inferred_type = TypeInference.infer_type_of_expression(ast.value, s)
            if not isinstance(inferred_type, Ast.TypeTupleAst):
                exception = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Expected a tuple type, but found {inferred_type}.")
                raise SystemExit(exception) from None
            if len(inferred_type.types) != len(ast.variables):
                exception = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Expected a tuple of length {len(ast.variables)}, but found {inferred_type}.")
                raise SystemExit(exception) from None
            for i in range(len(ast.variables)):
                s.current_scope.get_symbol(ast.variables[i].identifier.identifier).type = inferred_type.types[i]

    @staticmethod
    def infer_type_of_sup_prototype(ast: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, s: ScopeHandler) -> None:
        for statement in ast.body.members:
            TypeInference.infer_type_of_statement(statement, s)

    @staticmethod
    def infer_type_of_expression(ast: Ast.ExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst(): return TypeInference.infer_type_of_identifier(ast, s)
            case Ast.LambdaAst(): return TypeInference.infer_type_of_lambda(ast, s)
            case Ast.IfStatementAst(): return TypeInference.infer_type_of_if_statement(ast, s)
            case Ast.YieldStatementAst(): return
            case Ast.InnerScopeAst(): TypeInference.infer_type_of_inner_scope(ast, s)
            case Ast.WithStatementAst(): return TypeInference.infer_type_of_with_statement(ast, s)
            case Ast.TokenAst(): return
            case Ast.BinaryExpressionAst(): return TypeInference.infer_type_of_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): return TypeInference.infer_type_of_postfix_expression(ast, s)
            case Ast.AssignmentExpressionAst(): return TypeInference.infer_type_of_assignment_expression(ast, s)
            case Ast.PlaceholderAst():
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Placeholder found in an incorrect position.")
                raise SystemExit(error) from None
            case Ast.TypeSingleAst(): return TypeInference.infer_type_of_type_single(ast, s)
            case Ast.WhileStatementAst(): return TypeInference.infer_type_of_while_statement(ast, s)
            case Ast.BoolLiteralAst(): return CommonTypes.bool()
            case Ast.StringLiteralAst(): return CommonTypes.string()
            case Ast.CharLiteralAst(): return CommonTypes.char()
            case Ast.RegexLiteralAst(): return CommonTypes.regex()
            case Ast.TupleLiteralAst(): return TypeInference.infer_type_of_tuple_literal(ast, s)
            case Ast.NumberLiteralBase10Ast() | Ast.NumberLiteralBase16Ast() | Ast.NumberLiteralBase02Ast(): CommonTypes.num()
            case _:
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Expression {type(ast)} not yet supported.")
                raise SystemExit(error) from None


    @staticmethod
    def infer_type_of_tuple_literal(ast: Ast.TupleLiteralAst, s: ScopeHandler) -> Ast.TypeAst:
        return Ast.TypeTupleAst([TypeInference.infer_type_of_expression(e, s) for e in ast.values], -1)

    @staticmethod
    def infer_type_of_identifier(ast: Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        return s.current_scope.get_symbol(ast.identifier).type

    @staticmethod
    def infer_type_of_if_statement(ast: Ast.IfStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.void()
        for branch in ast.branches:
            t = TypeInference.infer_type_of_if_branch(branch, s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_if_branch(ast: Ast.PatternStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = TypeInference.infer_type_of_expression(ast.body, s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_inner_scope(ast: Ast.InnerScopeAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = TypeInference.infer_type_of_expression(ast.body[-1], s)
        s.prev_scope()

    @staticmethod
    def infer_type_of_with_statement(ast: Ast.WithStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        for statement in ast.body:
            TypeInference.infer_type_of_statement(statement, s)
        t = TypeInference.infer_type_of_expression(ast.body[-1], s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        return CommonTypes.unknown()

    @staticmethod
    def infer_type_of_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        return CommonTypes.unknown()

    @staticmethod
    def infer_type_of_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        return CommonTypes.unknown()

    @staticmethod
    def infer_type_of_type_single(ast: Ast.TypeSingleAst, s: ScopeHandler) -> Ast.TypeAst:
        return ast

    @staticmethod
    def infer_type_of_while_statement(ast: Ast.WhileStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        for statement in ast.body:
            TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()
        return CommonTypes.void()

    @staticmethod
    def infer_type_of_lambda(ast: Ast.LambdaAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.unknown()
        s.prev_scope()
        return t


class CommonTypes:
    @staticmethod
    def void() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Void", [], -1)], -1)
    
    @staticmethod
    def bool() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Bool", [], -1)], -1)
    
    @staticmethod
    def string() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Str", [], -1)], -1)
    
    @staticmethod
    def char() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Char", [], -1)], -1)
    
    @staticmethod
    def regex() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Rgx", [], -1)], -1)
    
    @staticmethod
    def num() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst("Num", [], -1)], -1)
    
    @staticmethod
    def unknown() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Unknown", [], -1)], -1)
