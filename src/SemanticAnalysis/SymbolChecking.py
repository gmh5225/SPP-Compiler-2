from __future__ import annotations

from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import ScopeHandler
from src.SyntacticAnalysis.Parser import ErrorFormatter

import difflib


class SymbolChecker:
    @staticmethod
    def check(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        SymbolChecker.check_program_symbols(ast, s)
        s.switch_to_global_scope()

    @staticmethod
    def check_program_symbols(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        for module_member in ast.module.body.members:
            match module_member:
                case Ast.FunctionPrototypeAst(): SymbolChecker.check_function_prototype_symbols(module_member, s)
                case Ast.ClassPrototypeAst() | Ast.EnumPrototypeAst(): s.skip_scope()
                case Ast.SupPrototypeNormalAst(): SymbolChecker.check_sup_prototype_symbols(module_member, s)
                case Ast.SupPrototypeInheritanceAst(): SymbolChecker.check_sup_prototype_symbols(module_member, s)

    @staticmethod
    def check_function_prototype_symbols(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        s.next_scope()
        for statement in ast.body.statements:
            SymbolChecker.check_statement_symbols(statement, s)
        s.prev_scope()

    @staticmethod
    def check_statement_symbols(ast: Ast.StatementAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.TypedefStatementAst(): return
            case Ast.ReturnStatementAst(): SymbolChecker.check_return_statement_symbols(ast, s)
            case Ast.LetStatementAst(): SymbolChecker.check_let_statement_symbols(ast, s)
            case Ast.FunctionPrototypeAst(): SymbolChecker.check_function_prototype_symbols(ast, s)
            case _: SymbolChecker.check_expression_symbols(ast, s)

    @staticmethod
    def check_let_statement_symbols(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.value, s)

    @staticmethod
    def check_expression_symbols(ast: Ast.ExpressionAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.BinaryExpressionAst(): SymbolChecker.check_binary_expression_symbols(ast, s)
            case Ast.PostfixExpressionAst(): SymbolChecker.check_postfix_expression_symbols(ast, s)
            case Ast.AssignmentExpressionAst(): SymbolChecker.check_assignment_expression_symbols(ast, s)
            case Ast.IdentifierAst(): SymbolChecker.check_identifier_symbols(ast, s)
            case Ast.LambdaAst(): SymbolChecker.check_lambda_symbols(ast, s)
            case Ast.PlaceholderAst(): return
            case Ast.TypeSingleAst(): return
            case Ast.IfStatementAst(): SymbolChecker.check_if_statement_symbols(ast, s)
            case Ast.WhileStatementAst(): SymbolChecker.check_while_statement_symbols(ast, s)
            case Ast.YieldStatementAst(): SymbolChecker.check_yield_statement_symbols(ast, s)
            case Ast.InnerScopeAst(): SymbolChecker.check_inner_scope_symbols(ast, s)
            case Ast.WithStatementAst(): SymbolChecker.check_with_statement_symbols(ast, s)
            case Ast.TokenAst(): return
            case _ :
                if type(ast) in Ast.LiteralAst.__args__: return
                if type(ast) in Ast.NumberLiteralAst.__args__: return
                raise NotImplementedError(f"ExpressionAst {ast} not implemented")

    @staticmethod
    def check_binary_expression_symbols(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.lhs, s)
        SymbolChecker.check_expression_symbols(ast.rhs, s)

    @staticmethod
    def check_postfix_expression_symbols(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.lhs, s)
        match ast.op:
            case Ast.PostfixFunctionCallAst(): SymbolChecker.check_postfix_function_call_symbols(ast.op, s)
            case Ast.PostfixMemberAccessAst(): return  # MemberAccess => do in the type-checking phase?
            case Ast.PostfixStructInitializerAst(): SymbolChecker.check_postfix_struct_initializer_symbols(ast.op, s)

    @staticmethod
    def check_postfix_function_call_symbols(ast: Ast.PostfixFunctionCallAst, s: ScopeHandler) -> None:
        for argument in ast.arguments:
            SymbolChecker.check_expression_symbols(argument.value, s)

    @staticmethod
    def check_postfix_struct_initializer_symbols(ast: Ast.PostfixStructInitializerAst, s: ScopeHandler) -> None:
        for argument in ast.fields:
            # check identifiers exist: type-checking phase?
            SymbolChecker.check_expression_symbols(argument.value or argument.identifier, s)

    @staticmethod
    def check_assignment_expression_symbols(ast: Ast.AssignmentExpressionAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.lhs, s)
        SymbolChecker.check_expression_symbols(ast.rhs, s)

    @staticmethod
    def check_identifier_symbols(ast: Ast.IdentifierAst, s: ScopeHandler) -> None:
        if not s.current_scope.has_symbol(ast.identifier):
            looking_for = ast.identifier
            possible = s.current_scope.all_symbols()
            most_likely = (-1, "")
            for p in possible:
                ratio = difflib.SequenceMatcher(None, looking_for, p).ratio()
                if ratio > most_likely[0]:
                    most_likely = (ratio, p)
                elif ratio == most_likely[0]:
                    # Choose the option closest to the length of the identifier
                    if abs(len(looking_for) - len(p)) < abs(len(looking_for) - len(most_likely[1])):
                        most_likely = (ratio, p)

            error = Exception(
                ErrorFormatter.error(ast._tok) +
                f"Identifier '{ast.identifier}' not found in scope. Did you mean '{most_likely[1]}'?")
            raise SystemExit(error) from None

    @staticmethod
    def check_return_statement_symbols(ast: Ast.ReturnStatementAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.value, s)

    @staticmethod
    def check_yield_statement_symbols(ast: Ast.YieldStatementAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.value, s)

    @staticmethod
    def check_lambda_symbols(ast: Ast.LambdaAst, s: ScopeHandler) -> None:
        s.next_scope()
        SymbolChecker.check_expression_symbols(ast.body, s)
        s.prev_scope()

    @staticmethod
    def check_if_statement_symbols(ast: Ast.IfStatementAst, s: ScopeHandler) -> None:
        s.next_scope()
        SymbolChecker.check_expression_symbols(ast.condition, s)
        for branch in ast.branches:
            SymbolChecker.check_if_branch_symbols(branch, s)
        s.prev_scope()

    @staticmethod
    def check_if_branch_symbols(ast: Ast.PatternStatementAst, s: ScopeHandler) -> None:
        s.next_scope()
        for pattern in ast.patterns:
            SymbolChecker.check_patterns_symbols(pattern, s)
        for statement in ast.body:
            SymbolChecker.check_statement_symbols(statement, s)
        s.prev_scope()

    @staticmethod
    def check_patterns_symbols(ast: Ast.PatternAst, s: ScopeHandler) -> None:
        SymbolChecker.check_expression_symbols(ast.value, s)

    @staticmethod
    def check_while_statement_symbols(ast: Ast.WhileStatementAst, s: ScopeHandler) -> None:
        s.next_scope()
        SymbolChecker.check_expression_symbols(ast.condition, s)
        for statement in ast.body:
            SymbolChecker.check_statement_symbols(statement, s)
        s.prev_scope()

    @staticmethod
    def check_inner_scope_symbols(ast: Ast.InnerScopeAst, s: ScopeHandler) -> None:
        s.next_scope()
        for statement in ast.body:
            SymbolChecker.check_statement_symbols(statement, s)
        s.prev_scope()

    @staticmethod
    def check_with_statement_symbols(ast: Ast.WithStatementAst, s: ScopeHandler) -> None:
        s.next_scope()
        SymbolChecker.check_expression_symbols(ast.value, s)
        for statement in ast.body:
            SymbolChecker.check_statement_symbols(statement, s)
        s.prev_scope()

    @staticmethod
    def check_sup_prototype_symbols(ast: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, s: ScopeHandler) -> None:
        for method in filter(lambda member: isinstance(member, Ast.SupMethodPrototypeAst), ast.body.members):
            SymbolChecker.check_function_prototype_symbols(method, s)
