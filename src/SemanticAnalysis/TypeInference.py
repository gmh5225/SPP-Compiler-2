from __future__ import annotations
from src.SyntacticAnalysis import Ast
from src.LexicalAnalysis.Tokens import TokenType

BINARY_FUNC_MAP = {
    # Mathematical operations
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

    # Logical operations
    TokenType.TkDoubleAmpersand: "std::ops::And::__and__",
    TokenType.TkDoubleAmpersandEquals: "std::ops::AndAssign::__and_assign__",
    TokenType.TkDoublePipe: "std::ops::Or::__or__",
    TokenType.TkDoublePipeEquals: "std::ops::OrAssign::__or_assign__",

    # Bitwise operations
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

    # Comparison operations
    TokenType.TkDoubleEquals: "std::ops::Eq::__eq__",
    TokenType.TkExclamationEquals: "std::ops::Ne::__ne__",
    TokenType.TkLeftAngleBracket: "std::ops::Lt::__lt__",
    TokenType.TkLeftAngleBracketEquals: "std::ops::Le::__le__",
    TokenType.TkRightAngleBracket: "std::ops::Gt::__gt__",
    TokenType.TkRightAngleBracketEquals: "std::ops::Ge::__ge__",
    TokenType.TkDoubleFatArrow: "std::ops::Cmp::__cmp__",

    # Miscellaneous operations
    TokenType.TkDoubleQuestionMark: "std::ops::Coalesce::__coa__",
    TokenType.TkDoubleQuestionMarkEquals: "std::ops::CoalesceAssign::__coa_assign__",
    TokenType.TkPipeArrow: "std::ops::Pipe::__pip__",
}

UNARY_FUNC_MAP = {
    TokenType.TkExclamation: "std::ops::Not::__not__",
    TokenType.TkTilde: "std::ops::BitNot::__bit_not__",
    TokenType.TkPlus: "std::ops::Abs::__ans__",
    TokenType.TkHyphen: "std::ops::Neg::__neg__",
}


class TypeInference:
    @staticmethod
    def infer_type(*args) -> Ast.TypeAst:
        return [Ast.TypeSingleAst([Ast.GenericIdentifierAst("", [])])] * 20

    @staticmethod
    def _infer_type_from_expression(ast: Ast.ExpressionAst, s) -> Ast.TypeAst:
        match ast:
            case Ast.BinaryExpressionAst: return TypeInference._infer_type_from_binary_expression(ast, s)
            case Ast.UnaryExpressionAst: return TypeInference._infer_type_from_unary_expression(ast, s)
            case Ast.PostfixExpressionAst: return TypeInference._infer_type_from_postfix_expression(ast, s)
            case True if type(ast) in Ast.PrimaryExpressionAst.__args__: return TypeInference._infer_type_from_primary_expression(ast, s)
            case _: raise NotImplementedError(f"Type inference for {type(ast)} is not implemented")

    @staticmethod
    def _infer_type_from_binary_expression(ast: Ast.BinaryExpressionAst, s) -> Ast.TypeAst:
        # Get the type of the LHS and RHS operators, and find the class that the operator belongs to, and the name of
        # the method that the operator maps to. For example, 1 + 2 maps to std::ops::Add::__add__(std::Num, std::Num).
        lhs_type = TypeInference._infer_type_from_expression(ast.lhs, s)
        rhs_type = TypeInference._infer_type_from_expression(ast.rhs, s)
        operator_class, method = BINARY_FUNC_MAP[ast.op.tok.token_type].rsplit("::", 1)

        # Locate the function in the scope, and get the return type of the function. There might be > 1 matching
        # function signatures in the scope, so we need to find the one that matches the LHS and RHS types and any
        # generic constraints.


