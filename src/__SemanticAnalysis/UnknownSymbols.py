"""
Scan the AST with the SymbolTables and check for unknown symbols
- Check variable exists in the current scope
- Check function exists in the current scope
- Check attribute exists on the type of the item being operated on (read the symbol table)

No "type" checking -> just checking symbols exist for use in expressions
"""


from __future__ import annotations
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolTables import SymbolTableManager


class UnknownSymbols:
    @staticmethod
    def check_expression(expression: Ast.ExpressionAst, symbol_table: SymbolTableManager):
        match expression:
            case Ast.BinaryExpressionAst(): UnknownSymbols.check_binary_expression(expression, symbol_table)
            case Ast.UnaryExpressionAst(): UnknownSymbols.check_unary_expression(expression, symbol_table)
            case Ast.PostfixExpressionAst(): UnknownSymbols.check_postfix_expression(expression, symbol_table)
            case Ast.PrimaryExpressionAst(): UnknownSymbols.check_primary_expression(expression, symbol_table)
            case _: raise Exception(f"Unknown expression type {expression.op.__class__.__name__}")

    @staticmethod
    def check_binary_expression(binary_expression: Ast.BinaryExpressionAst, symbol_table: SymbolTableManager):
        UnknownSymbols.check_expression(binary_expression.lhs, symbol_table)
        UnknownSymbols.check_expression(binary_expression.rhs, symbol_table)

    @staticmethod
    def check_unary_expression(unary_expression: Ast.UnaryExpressionAst, symbol_table: SymbolTableManager):
        UnknownSymbols.check_expression(unary_expression.rhs, symbol_table)

    @staticmethod
    def check_postfix_expression(postfix_expression: Ast.PostfixExpressionAst, symbol_table: SymbolTableManager):
        match postfix_expression.op:
            case Ast.PostfixFunctionCallAst(): UnknownSymbols.check_postfix_function_call(postfix_expression, symbol_table)
            case Ast.PostfixIndexAccessAst(): UnknownSymbols.check_postfix_index_access(postfix_expression, symbol_table)
            case Ast.PostfixSliceAccessAst(): UnknownSymbols.check_postfix_slice_access(postfix_expression, symbol_table)
            case Ast.PostfixMemberAccessAst(): UnknownSymbols.check_postfix_member_access(postfix_expression, symbol_table)
            case Ast.PostfixStructInitializerAst(): UnknownSymbols.check_postfix_struct_initializer(postfix_expression, symbol_table)
            case _: raise Exception(f"Unknown postfix expression type {postfix_expression.op.__class__.__name__}")

    @staticmethod
    def check_primary_expression(primary_expression: Ast.PrimaryExpressionAst, symbol_table: SymbolTableManager):
        match primary_expression:
            case Ast.IdentifierAst(): UnknownSymbols.check_identifier(primary_expression, symbol_table)
            case Ast.LiteralAst(): UnknownSymbols.check_literal(primary_expression, symbol_table)
            case Ast.TypeAst(): UnknownSymbols.check_type(primary_expression, symbol_table)
            case Ast.LambdaAst(): UnknownSymbols.check_lambda(primary_expression, symbol_table)
            case Ast.IfStatementAst(): UnknownSymbols.check_if_statement(primary_expression, symbol_table)
            case Ast.MatchStatementAst(): UnknownSymbols.check_match_statement(primary_expression, symbol_table)
            case Ast.ForStatementAst(): UnknownSymbols.check_for_statement(primary_expression, symbol_table)
            case Ast.WhileStatementAst(): UnknownSymbols.check_while_statement(primary_expression, symbol_table)
            case Ast.DoWhileStatementAst(): UnknownSymbols.check_do_while_statement(primary_expression, symbol_table)

    @staticmethod
    def check_postfix_function_call(postfix_expression: Ast.PostfixExpressionAst, symbol_table: SymbolTableManager):
        for argument in postfix_expression.arguments:
            UnknownSymbols.check_expression(argument, symbol_table)
