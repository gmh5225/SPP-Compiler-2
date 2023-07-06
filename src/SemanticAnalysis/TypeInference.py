"""
Type-inference:
-- Type inference in "let" statements => only place where type-inference is used.
-- Work through the RHS expression and get the type for each operation / attribute, etc.

Operations:
-- Map to their respective operator classes (std::ops::...).
-- Check operator classes are implemented on the item being operated on.
-- Read the function signature to get the return type.

Attributes:
-- Check attribute exists on the item being operated on (read the symbol table)
-- Get the type the attribute is declared with.

Function calls:
-- Check function exists in the current scope (read the scopes function registry).
-- List the correct method signatures that match the type-constraints, parameter types, and number of arguments
-- Get the function's return type (multiple signatures => only difference is value-guard, so return types are the same)
"""

from src.LexicalAnalysis.Tokens import TokenType
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolTables import Scope


class TypeInference:
    def infer_type_binary_expression(self, binary_expression: Ast.BinaryExpressionAst):
        cls, fn = get_operator_class(binary_expression.op.primary.token_type, Ast.BinaryExpressionAst)

    def infer_type_unary_expression(self, unary_expression: Ast.UnaryExpressionAst):
        pass

    def infer_type_postfix_expression(self, postfix_expression: Ast.PostfixExpressionAst):
        pass

    def infer_type_parenthesized_expression(self, parenthesized_expression: Ast.ParenthesizedExpressionAst):
        pass

    def infer_type_expression(self, expression: Ast.ExpressionAst):
        match expression:
            case Ast.BinaryExpressionAst(binary_expression): self.infer_type_binary_expression(binary_expression)
            case Ast.UnaryExpressionAst(unary_expression): self.infer_type_unary_expression(unary_expression)
            case Ast.PostfixExpressionAst(postfix_expression): self.infer_type_postfix_expression(postfix_expression)
            case Ast.ParenthesizedExpressionAst(parenthesized_expression): self.infer_type_parenthesized_expression(parenthesized_expression)
            case _: raise Exception("Unknown expression type")


def get_operator_class(operator: TokenType, ast: type):
    match ast, operator:
        case Ast.BinaryExpressionAst, TokenType.TkPlus: return "std::ops::Add", "__add__"
        case Ast.BinaryExpressionAst, TokenType.TkPlusEquals: return "std::ops::AddAssign", "__add_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkHyphen: return "std::ops::Sub", "__sub__"
        case Ast.BinaryExpressionAst, TokenType.TkHyphenEquals: return "std::ops::SubAssign", "__sub_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkAsterisk: return "std::ops::Mul", "__mul__"
        case Ast.BinaryExpressionAst, TokenType.TkAsteriskEquals: return "std::ops::MulAssign", "__mul_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkForwardSlash: return "std::ops::Div", "__div__"
        case Ast.BinaryExpressionAst, TokenType.TkForwardSlashEquals: return "std::ops::DivAssign", "__div_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkPercent: return "std::ops::Mod", "__mod__"
        case Ast.BinaryExpressionAst, TokenType.TkPercentEquals: return "std::ops::ModAssign", "__mod_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleForwardSlash: return "std::ops::Flo", "__flo__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleForwardSlashEquals: return "std::ops::FloAssign", "__flo_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleAsterisk: return "std::ops::Pow", "__pow__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleAsteriskEquals: return "std::ops::PowAssign", "__pow_assign__"

        case Ast.UnaryExpressionAst, TokenType.TkExclamation: return "std::ops::Not", "__not__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleAmpersand: return "std::ops::And", "__and__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleAmpersandEquals: return "std::ops::AndAssign", "__and_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkDoublePipe: return "std::ops::Or", "__or__"
        case Ast.BinaryExpressionAst, TokenType.TkDoublePipeEquals: return "std::ops::OrAssign", "__or_assign__"

        case Ast.UnaryExpressionAst, TokenType.TkTilde: return "std::ops::BitNot", "__bit_not__"
        case Ast.BinaryExpressionAst, TokenType.TkAmpersand: return "std::ops::BitAnd", "__bit_and__"
        case Ast.BinaryExpressionAst, TokenType.TkAmpersandEquals: return "std::ops::BitAndAssign", "__bit_and_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkPipeArrow: return "std::ops::BitOr", "__bit_or__"
        case Ast.BinaryExpressionAst, TokenType.TkPipeEquals: return "std::ops::BitOrAssign", "__bit_or_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkCaret: return "std::ops::BitXor", "__bit_xor__"
        case Ast.BinaryExpressionAst, TokenType.TkCaretEquals: return "std::ops::BitXorAssign", "__bit_xor_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleLeftAngleBracket: return "std::ops::Shl", "__shl__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleLeftAngleBracketEquals: return "std::ops::ShlAssign", "__shl_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleRightAngleBracket: return "std::ops::Shr", "__shr__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleRightAngleBracketEquals: return "std::ops::ShrAssign", "__shr_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkTripleLeftAngleBracket: return "std::ops::Rol", "__rol__"
        case Ast.BinaryExpressionAst, TokenType.TkTripleLeftAngleBracketEquals: return "std::ops::RolAssign", "__rol_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkTripleRightAngleBracket: return "std::ops::Ror", "__ror__"
        case Ast.BinaryExpressionAst, TokenType.TkTripleRightAngleBracketEquals: return "std::ops::RorAssign", "__ror_assign__"

        case Ast.BinaryExpressionAst, TokenType.TkDoubleEquals: return "std::ops::Eq", "__eq__"
        case Ast.BinaryExpressionAst, TokenType.TkExclamationEquals: return "std::ops::Ne", "__ne__"
        case Ast.BinaryExpressionAst, TokenType.TkLeftAngleBracket: return "std::ops::Lt", "__lt__"
        case Ast.BinaryExpressionAst, TokenType.TkLeftAngleBracketEquals: return "std::ops::Le", "__le__"
        case Ast.BinaryExpressionAst, TokenType.TkRightAngleBracket: return "std::ops::Gt", "__gt__"
        case Ast.BinaryExpressionAst, TokenType.TkRightAngleBracketEquals: return "std::ops::Ge", "__ge__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleFatArrow: return "std::ops::Cmp", "__cmp__"

        case Ast.BinaryExpressionAst, TokenType.TkDoubleQuestionMark: return "std::ops::Coalesce", "__coa__"
        case Ast.BinaryExpressionAst, TokenType.TkDoubleQuestionMarkEquals: return "std::ops::CoalesceAssign", "__coa_assign__"
        case Ast.BinaryExpressionAst, TokenType.TkPipeArrow: return "std::ops::Pipe", "__pip__"

        case Ast.UnaryExpressionAst, TokenType.TkPlus: return "std::ops::Abs", "__ans__"
        case Ast.UnaryExpressionAst, TokenType.TkHyphen: return "std::ops::Neg", "__neg__"

        case Ast.PostfixExpressionAst, TokenType.TkQuestionMark: return "std::ops::Try", "__try__"
        # todo : other postfix operators


