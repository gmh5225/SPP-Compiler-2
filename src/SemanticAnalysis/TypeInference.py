from typing import Any

from src.LexicalAnalysis.Tokens import TokenType
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolTableGeneration import ScopeManager


class TypeInference:
    # Entry function
    @staticmethod
    def infer_type_from_expression(ast: Ast.ExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        match ast:
            case Ast.BinaryExpressionAst(): return TypeInference.infer_type_from_binary_operator(ast, s)
            case Ast.UnaryExpressionAst(): return TypeInference.infer_type_from_unary_operator(ast, s)
            case Ast.PostfixExpressionAst(): return TypeInference.infer_type_from_postfix_operator(ast, s)
            case Ast.MultiAssignmentExpressionAst(): return TypeInference.infer_type_from_multi_assignment_operator(ast, s)
            case Ast.PrimaryExpressionAst(): return TypeInference.infer_type_from_primary_expression(ast, s)
            case _: raise NotImplementedError(f"Unknown expression type {ast.op.__class__.__name__}")

    @staticmethod
    def infer_type_from_binary_operator(ast: Ast.BinaryExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        function_identifier = mapping = {
            TokenType.TkPlus: "std::ops::Add::__add__",
            TokenType.TkPlusEquals: "std::ops::AddAssign::__add_assign__",
            TokenType.TkHyphen: "std::ops::Sub::__sub__",
            TokenType.TkHyphenEquals: "std::ops::SubAssign::__sub_assign__",
            TokenType.TkAsterisk: "std::ops::Mul::__mul__",
            TokenType.TkAsteriskEquals: "std::ops::MulAssign::__mul_assign__",
            TokenType.TkForwardSlash: "std::ops::Div::__div__",
            TokenType.TkForwardSlashEquals: "std::ops::DivAssign::__div_assign__",
            TokenType.TkPercent: "std::ops::Mod::__mod__",
            TokenType.TkPercentEquals: "std::ops::ModAssign::__mod_assign__",
            TokenType.TkDoubleForwardSlash: "std::ops::Flo::__flo__",
            TokenType.TkDoubleForwardSlashEquals: "std::ops::FloAssign::__flo_assign__",
            TokenType.TkDoubleAsterisk: "std::ops::Pow::__pow__",
            TokenType.TkDoubleAsteriskEquals: "std::ops::PowAssign::__pow_assign__",


            TokenType.TkDoubleAmpersand: "std::ops::And::__and__",
            TokenType.TkDoubleAmpersandEquals: "std::ops::AndAssign::__and_assign__",
            TokenType.TkDoublePipe: "std::ops::Or::__or__",
            TokenType.TkDoublePipeEquals: "std::ops::OrAssign::__or_assign__",
    

            TokenType.TkAmpersand: "std::ops::BitAnd::__bit_and__",
            TokenType.TkAmpersandEquals: "std::ops::BitAndAssign::__bit_and_assign__",
            TokenType.TkPipe: "std::ops::BitOr::__bit_or__",
            TokenType.TkPipeEquals: "std::ops::BitOrAssign::__bit_or_assign__",
            TokenType.TkCaret: "std::ops::BitXor::__bit_xor__",
            TokenType.TkCaretEquals: "std::ops::BitXorAssign::__bit_xor_assign__",
            TokenType.TkDoubleLeftAngleBracket: "std::ops::Shl::__shl__",
            TokenType.TkDoubleLeftAngleBracketEquals: "std::ops::ShlAssign::__shl_assign__",
            TokenType.TkDoubleRightAngleBracket: "std::ops::Shr::__shr__",
            TokenType.TkDoubleRightAngleBracketEquals: "std::ops::ShrAssign::__shr_assign__",
            TokenType.TkTripleLeftAngleBracket: "std::ops::Rol::__rol__",
            TokenType.TkTripleLeftAngleBracketEquals: "std::ops::RolAssign::__rol_assign__",
            TokenType.TkTripleRightAngleBracket: "std::ops::Ror::__ror__",
            TokenType.TkTripleRightAngleBracketEquals: "std::ops::RorAssign::__ror_assign__",
    
            TokenType.TkDoubleEquals: "std::ops::Eq::__eq__",
            TokenType.TkExclamationEquals: "std::ops::Ne::__ne__",
            TokenType.TkLeftAngleBracket: "std::ops::Lt::__lt__",
            TokenType.TkLeftAngleBracketEquals: "std::ops::Le::__le__",
            TokenType.TkRightAngleBracket: "std::ops::Gt::__gt__",
            TokenType.TkRightAngleBracketEquals: "std::ops::Ge::__ge__",
            TokenType.TkDoubleFatArrow: "std::ops::Cmp::__cmp__",
    
            TokenType.TkDoubleQuestionMark: "std::ops::Coalesce::__coa__",
            TokenType.TkDoubleQuestionMarkEquals: "std::ops::CoalesceAssign::__coa_assign__",
            TokenType.TkPipeArrow: "std::ops::Pipe::__pip__",
    
            TokenType.TkQuestionMark: "std::ops::Try::__try__",
        }[ast.op.primary.token_type] + "#" + TypeInference.infer_type_from_expression(ast.lhs, s).parts[-1].identifier
        arg_types = [TypeInference.infer_type_from_expression(ast.lhs, s), TypeInference.infer_type_from_expression(ast.rhs, s)]
        function = s.current_scope.function_registry.get_symbol(function_identifier, argument_types=arg_types)
        return function.return_type

    @staticmethod
    def infer_type_from_unary_operator(ast: Ast.UnaryExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        function_identifier = mapping = {
            TokenType.TkExclamation: "std::ops::Not::__not__",
            TokenType.TkTilde: "std::ops::BitNot::__bit_not__",
            TokenType.TkPlus: "std::ops::Abs::__ans__",
            TokenType.TkHyphen: "std::ops::Neg::__neg__",
        }[ast.op.primary.token_type] + "#" + TypeInference.infer_type_from_expression(ast.rhs, s).parts[-1].identifier
        arg_types = [TypeInference.infer_type_from_expression(ast.rhs, s)]
        function = s.current_scope.function_registry.get_symbol(function_identifier, argument_types=arg_types)
        return function.return_type

    @staticmethod
    def infer_type_from_postfix_operator(ast: Ast.PostfixExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        match ast:
            case Ast.PostfixFunctionCallAst(): return TypeInference.infer_type_from_postfix_function_call(ast, s)
            case Ast.PostfixIndexAccessAst(): return TypeInference.infer_type_from_postfix_index(ast, s)
            case Ast.PostfixMemberAccessAst(): return TypeInference.infer_type_from_postfix_member_access(ast, s)
            case Ast.PostfixStructInitializerAst(): return TypeInference.infer_type_from_postfix_struct_initializer(ast, s)
            case _: raise NotImplementedError(f"Type inference for postfix operator {ast} is not implemented")

    @staticmethod
    def infer_type_from_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        function_identifier = TypeInference.infer_type_from_expression(ast.lhs, s).parts[-1].identifier
        arg_types = [TypeInference.infer_type_from_expression(arg, s) for arg in ast.op.arguments]
        function = s.current_scope.function_registry.get_symbol(function_identifier, argument_types=arg_types)
        return function.return_type

    @staticmethod
    def infer_type_from_postfix_index(ast: Ast.PostfixExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        name = "IndexMut::__index_mut__" if ast.op.arguments[0].convention.modifier.token_type == TokenType.KwMut else "IndexRef::__index_ref__"
        function_identifier = name + "#" + TypeInference.infer_type_from_expression(ast.lhs, s).parts[-1].identifier
        arg_types = [TypeInference.infer_type_from_expression(arg, s) for arg in ast.op.arguments]
        function = s.current_scope.function_registry.get_symbol(function_identifier, argument_types=arg_types)
        return function.return_type

    @staticmethod
    def infer_type_from_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        class_type = TypeInference.infer_type_from_expression(ast.lhs, s)
        member_name = ast.op.identifier.identifier
        # todo - get member type from type-table? => or just read from ast as attribute types are known at compile time
        # todo - return the type of the member
        return None

    @staticmethod
    def infer_type_from_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        class_type = TypeInference.infer_type_from_expression(ast.lhs, s)
        return class_type

    @staticmethod
    def infer_type_from_multi_assignment_operator(ast: Ast.MultiAssignmentExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        ...
    
    @staticmethod
    def infer_type_from_primary_expression(ast: Ast.PrimaryExpressionAst, s: ScopeManager) -> Ast.TypeAst:
        match ast:
            case Ast.LiteralAst(): return TypeInference.infer_type_from_literal(ast, s)
            case Ast.IdentifierAst(): return TypeInference.infer_type_from_identifier(ast, s)
            case Ast.ParenthesizedExpressionAst(): return TypeInference.infer_type_from_parenthesized_expression(ast, s)
            case Ast.LambdaAst(): return TypeInference.infer_type_from_lambda(ast, s)
            case Ast.PlaceholderAst(): return TypeInference.infer_type_from_placeholder(ast, s)
            case Ast.IfStatementAst(): return TypeInference.infer_type_from_if_statement(ast, s)
            case Ast.MatchStatementAst(): return TypeInference.infer_type_from_match_statement(ast, s)
            case Ast.WhileStatementAst(): return TypeInference.infer_type_from_while_statement(ast, s)
            case Ast.ForStatementAst(): return TypeInference.infer_type_from_for_statement(ast, s)
            case Ast.DoWhileStatementAst(): return TypeInference.infer_type_from_do_while_statement(ast, s)
            case _: raise NotImplementedError(f"Unknown expression type {ast.op.__class__.__name__}")

    @staticmethod
    def infer_type_from_identifier(ast: Ast.IdentifierAst, s: ScopeManager) -> Ast.TypeAst:
        return s.current_scope.symbol_table.get_symbol(ast.identifier)

    @staticmethod
    def infer_type_from_if_statement(ast: Ast.IfStatementAst, s: ScopeManager) -> Ast.TypeAst:
        return TypeInference.infer_type_from_expression(ast.if_branch.body[-1], s)

    @staticmethod
    def infer_type_from_match_statement(ast: Ast.MatchStatementAst, s: ScopeManager) -> Ast.TypeAst:
        return TypeInference.infer_type_from_expression(ast.cases[0].body[-1], s)

    @staticmethod
    def infer_type_from_while_statement(ast: Ast.WhileStatementAst, s: ScopeManager) -> Ast.TypeAst:
        break_statement = [statement for statement in ast.body if isinstance(statement, Ast.BreakStatementAst)][0]
        return TypeInference.infer_type_from_expression(break_statement.returning_expression, s)

