from __future__ import annotations

from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import ScopeHandler


class TypeInference:
    @staticmethod
    def infer_type_of_expression(ast: Ast.ExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst: return TypeInference.infer_type_of_identifier(ast, s)
            case Ast.LambdaAst: return TypeInference.infer_type_of_lambda(ast, s)
            case Ast.IfStatementAst: return TypeInference.infer_type_of_if_statement(ast, s)
            case Ast.YieldStatementAst: return
            case Ast.InnerScopeAst: TypeInference.infer_type_of_inner_scope(ast, s)
            case Ast.WithStatementAst: return TypeInference.infer_type_of_with_statement(ast, s)
            case Ast.TokenAst: return
            case Ast.BinaryExpressionAst: return TypeInference.infer_type_of_binary_expression(ast, s)
            case Ast.PostfixExpressionAst: return TypeInference.infer_type_of_postfix_expression(ast, s)
            case Ast.AssignmentExpressionAst: return TypeInference.infer_type_of_assignment_expression(ast, s)
            case Ast.PlaceholderAst: return TypeInference.infer_type_of_placeholder(ast, s)
            case Ast.TypeSingleAst: return TypeInference.infer_type_of_type_single(ast, s)
            case Ast.WhileStatementAst: return TypeInference.infer_type_of_while_statement(ast, s)

    @staticmethod
    def infer_type_of_identifier(ast: Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        return s.current_scope.get_symbol(ast.identifier).type

    @staticmethod
    def infer_type_of_if_statement(ast: Ast.IfStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInference.infer_type_of_expression(ast.branches[0].body, s)

    @staticmethod
    def infer_type_of_inner_scope(ast: Ast.InnerScopeAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInference.infer_type_of_expression(ast.body[-1], s)

    @staticmethod
    def infer_type_of_with_statement(ast: Ast.WithStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInference.infer_type_of_expression(ast.body[-1], s)

    @staticmethod
    def infer_type_of_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        mapped_function = BIN_FUNCTIONS[ast.op.tok.token_type]

