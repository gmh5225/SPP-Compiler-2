from __future__ import annotations

from src.SemanticAnalysis.SymbolGeneration import ScopeHandler
from src.SyntacticAnalysis import Ast

"""
TypeChecker:
-- Check RHS matches LHS.
-- Check argument matches parameter.
-- Check function return/yield expression types.
"""


class TypeChecker:
    @staticmethod
    def check(s: ScopeHandler) -> None:
        TypeChecker.check_program(s)

    @staticmethod
    def check_program(s: ScopeHandler) -> None:
        for module_member in s.current_scope().members:
            match module_member:
                case Ast.FunctionPrototypeAst(): TypeChecker.check_function_prototype(module_member, s)
                case Ast.ClassPrototypeAst() | Ast.EnumPrototypeAst(): s.skip_scope()
                case Ast.SupPrototypeNormalAst(): TypeChecker.check_sup_prototype(module_member, s)
                case Ast.SupPrototypeInheritanceAst(): TypeChecker.check_sup_prototype(module_member, s)

    @staticmethod
    def check_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        for statement in ast.body.statements:
            TypeChecker.check_statement(statement, s)

    @staticmethod
    def check_statement(ast: Ast.StatementAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.TypedefStatementAst(): return
            case Ast.ReturnStatementAst(): TypeChecker.check_return_statement(ast, s)
            case Ast.LetStatementAst(): TypeChecker.check_let_statement(ast, s)
            case Ast.FunctionPrototypeAst(): TypeChecker.check_function_prototype(ast, s)
            case _: TypeChecker.check_expression(ast, s)

    @staticmethod
    def check_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        if ast.value:
            TypeChecker.check_expression(ast.value, s)

    @staticmethod
    def check_expression(ast: Ast.ExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast:
            case Ast.BinaryExpressionAst(): TypeChecker.check_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): TypeChecker.check_postfix_expression(ast, s)
            case Ast.AssignmentExpressionAst(): TypeChecker.check_assignment_expression(ast, s)
            case Ast.IdentifierAst(): return
            case Ast.LambdaAst(): TypeChecker.check_lambda(ast, s)
            case Ast.PlaceholderAst(): return
            case Ast.TypeSingleAst(): return
            case Ast.IfStatementAst(): TypeChecker.check_if_statement(ast, s)
            case Ast.WhileStatementAst(): TypeChecker.check_while_statement(ast, s)
            case Ast.YieldStatementAst(): TypeChecker.check_yield_statement(ast, s)
            case Ast.InnerScopeAst(): TypeChecker.check_inner_scope(ast, s)
            case Ast.WithStatementAst(): TypeChecker.check_with_statement(ast, s)

    @staticmethod
    def check_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        ...

    @staticmethod
    def check_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast.op:
            case Ast.PostfixMemberAccessAst(): return
            case Ast.PostfixFunctionCallAst(): TypeChecker.check_function_call(ast, s)
            case Ast.PostfixStructInitializerAst(): TypeChecker.check_struct_initializer(ast, s)

    @staticmethod
    def check_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler) -> None:
        TypeChecker.check_expression(ast.lhs, s)
        TypeChecker.check_expression(ast.rhs, s)
