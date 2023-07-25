from __future__ import annotations

from src.SyntacticAnalysis import Ast


class TypeInference:
    @staticmethod
    def infer_type_of_expression(ast: Ast.ExpressionAst) -> Ast.TypeAst:
        """
        PrimaryExpressionAst = LiteralAst | IdentifierAst | LambdaAst | PlaceholderAst | TypeSingleAst | IfStatementAst | YieldStatementAst | InnerScopeAst | WithStatementAst | TokenAst
        ExpressionAst = BinaryExpressionAst | PostfixExpressionAst | AssignmentExpressionAst | PrimaryExpressionAst | TokenAst
        """
        match ast:
            case Ast.IdentifierAst: return TypeInference.infer_type_of_identifier(ast)
            case Ast.LambdaAst: return TypeInference.infer_type_of_lambda(ast)
            case Ast.IfStatementAst: return TypeInference.infer_type_of_if_statement(ast)
            case Ast.YieldStatementAst: return
            case Ast.InnerScopeAst: TypeInference.infer_type_of_inner_scope(ast)
            case Ast.WithStatementAst: return TypeInference.infer_type_of_with_statement(ast)



