"""
Type inference:
- Binary operator => map to correct function, check for function existing, get return type
- Unary operator => map to correct function, check for function existing, get return type
- Postfix operator => map to correct function, check for function existing, get return type
- Parenthesized expression => get type of expression inside parentheses
- Function call => model as callable object, call the object, get return type
- Attribute => check attribute exists, get type of attribute
- Literal => get type of literal
- Identifier => check identifier exists, get type of identifier
"""


from __future__ import annotations
from src.LexicalAnalysis.Tokens import TokenType
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis import Exceptions
from src.SemanticAnalysis.SymbolTable import Scope

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
}

UNARY_FUNC_MAP = {
    TokenType.TkExclamation: "std::ops::Not::__not__",
    TokenType.TkTilde: "std::ops::BitNot::__bit_not__",
    TokenType.TkPlus: "std::ops::Abs::__ans__",
    TokenType.TkHyphen: "std::ops::Neg::__neg__",
}

FUNCTION_FUNC_MAP = {
    (TokenType.TkAmpersand, False): "std::ops::Fn::__call__",
    (TokenType.TkAmpersand, True): "std::ops::FnMut::__call__",
    None: "std::ops::FnOnce::__call__",
}


class TypeInference:
    def __infer_type_expression(self, expression: Ast.ExpressionAst, scope: Scope) -> Ast.TypeAst:
        match expression:
            case Ast.BinaryExpressionAst: return self.__infer_type_binary_expression(expression, scope)
            case Ast.UnaryExpressionAst: return self.__infer_type_unary_expression(expression, scope)
            case Ast.PostfixExpressionAst: return self.__infer_type_postfix_expression(expression, scope)

        if type(expression) in Ast.PrimaryExpressionAst.__args__: return self.__infer_type_primary_expression(expression, scope)
        raise NotImplementedError(f"Type inference for expression {expression} is not implemented")

    def __infer_type_binary_expression(self, binary_expression: Ast.BinaryExpressionAst, scope: Scope) -> Ast.TypeAst:
        # Get the operation from the BinaryExpression AST object, and inspect its token, to get the correct class and
        # function that the LHS needs to have implemented. This just acts as a wrapper to a regular function call.
        binary_operation = binary_expression.op.primary.token_type
        binary_function = BINARY_FUNC_MAP[binary_operation]

        # The LHS of a binary expression must be a primary expression that is not a lambda, statement-expression, type,
        # or placeholder. The RHS can be any expression, so no checks are needed.
        match binary_expression.lhs:
            case Ast.LambdaAst | Ast.StatementAst | Ast.TypeAst | Ast.PlaceholderAst: raise Exceptions.IllegalBinaryLhsExpressionError(binary_expression.lhs)
            case _: pass

        # Once the binary function has been determined, ie "std::ops::Add::__add__", then the LHS needs to be checked to
        # see if it has implemented the correct function, with compatible generic constraints and function-parameter
        # types. If the operation is 1 + 2, then the function needed to be found is "std::Num::__add__" via
        # "std::ops::Add::__add__", so look for "std::ops::Add::__add__(&std::Num, ...)" in the global scope.
        function_argument_types = [self.__infer_type_expression(binary_expression.lhs, scope), self.__infer_type_expression(binary_expression.rhs, scope)]
        function_type_arguments = []
        function = scope.lookup_function(binary_function, function_argument_types, function_type_arguments)

        # If the function is not found, then the LHS does not implement the correct function, so raise an exception.
        if function is None:
            raise Exceptions.UnknownFunctionError(binary_function, function_argument_types, function_type_arguments)

        # If the function is found, then the parameters match, so get the return-type of the function, and return it.
        # Return it as a TypeAst object, so that the type can be used in the rest of the program.
        return function.return_type


    def __infer_type_unary_expression(self, unary_expression: Ast.UnaryExpressionAst, scope: Scope) -> Ast.TypeAst:
        # Get the operation from the UnaryExpression AST object, and inspect its token, to get the correct class and
        # function that the rhs needs to have implemented. This just acts as a wrapper to a regular function call.
        unary_operation = unary_expression.op.primary.token_type
        unary_function = UNARY_FUNC_MAP[unary_operation]

        # The RHS of a unary expression can be any expression (as long as the return-type of it super-imposes the
        # correct class, so no extra check is required here, same as for the RHS of a binary expression.
        function_argument_types = [self.__infer_type_expression(unary_expression.rhs)]
        function_type_arguments = []
        function = scope.lookup_function(unary_function, function_argument_types, function_type_arguments)

        # If the function is not found, then the RHS does not implement the correct function, so raise an exception.
        if function is None:
            raise Exceptions.UnknownFunctionError(unary_function, function_argument_types, function_type_arguments)

        return function.return_type


    def __infer_type_postfix_expression(self, postfix_expression: Ast.PostfixExpressionAst, scope: Scope) -> Ast.TypeAst:
        match postfix_expression.op:
            case Ast.PostfixFunctionCallAst: return self.__infer_type_function_call(postfix_expression, scope)
            case Ast.PostfixIndexAccessAst: return self.__infer_type_index(postfix_expression, scope)
            case Ast.PostfixStructInitializerAst: return self.__infer_type_struct_initializer(postfix_expression, scope)
            case Ast.PostfixMemberAccessAst: return self.__infer_type_member_access(postfix_expression, scope)
            case Ast.TokenAst: return self.__infer_type_early_return(postfix_expression, scope)
            case _: raise NotImplementedError(f"Unknown postfix expression type {postfix_expression.op}")

    def __infer_type_function_call(self, function_call: Ast.PostfixExpressionAst, scope: Scope) -> Ast.TypeAst:
        # Now call either std::Fn::__call__, std::FnMut::__call_mut__, or std::FnOnce::__call_once__ depending on the
        # type of the function, and return the return-type of the function.
        try:
            function_call_function = FUNCTION_FUNC_MAP[(function_call.op.arguments[-1].calling_convention.primary.token_type, function_call.op.arguments[-1].calling_convention.modifier)]
        except AttributeError:
            function_call_function = FUNCTION_FUNC_MAP[None]

        # Functions are just objects in the global scope, whose type is either std::Fn, std::FnMut, or std::FnOnce. The
        # standard function creation syntax ie `fn a() -> R` is just syntactic sugar to wrap the construction. Find the
        # function in the global namespace, constrain the correct signature against the parameter types, type generic
        # constraints and number of parameters.
        function_argument_types = [self.__infer_type_expression(argument) for argument in function_call.op.arguments]
        function_type = self.__infer_type_expression(function_call.lhs)
        function_type_arguments = function_type.parts[-1].generics
        function = scope.get_function(function_type, function_argument_types, function_type_arguments)

        # If the function is not found, then the function does not exist, so raise an exception.
        if function is None:
            raise Exceptions.UnknownFunctionError(function_type, function_argument_types, function_type_arguments)

        return function.return_type

    def __infer_type_index(self, index: Ast.PostfixExpressionAst, scope: Scope) -> Ast.TypeAst:
        # TODO : decide between __index__ or __index_mut__ (how?)
        function_argument_type = self.__infer_type_expression(index.op.arguments[0])
        function_type = self.__infer_type_expression(index.lhs)
        function_type_arguments = function_type.parts[-1].generics
        function = scope.get_function(function_type, [function_argument_type], function_type_arguments)

        # If the function is not found, then the function does not exist, so raise an exception.
        if function is None:
            raise Exceptions.UnknownFunctionError(function_type, [function_argument_type], function_type_arguments)

        return function.return_type

    def __infer_type_struct_initializer(self, struct_initializer: Ast.PostfixExpressionAst, scope: Scope) -> Ast.TypeAst:
        # The type of a struct initializer is the type of the struct itself, so just return the type of the struct.
        # Ie std::Vec{} will return an std::Vec always (the struct-initializer ALWAYS returns the type of class being created).
        return self.__infer_type_expression(struct_initializer.lhs)

    def __infer_type_member_access(self, member_access: Ast.PostfixExpressionAst, scope: Scope) -> Ast.TypeAst:
        # Look at the attribute types for the type being accessed, and return the type of the attribute being accessed.
        # If the attribute does not exist, then raise an exception.
        attribute_name = member_access.op.identifier
        enclosing_type = self.__infer_type_expression(member_access.lhs)
        attribute_type = scope.get_type(enclosing_type).get_attribute(attribute_name).type
        return attribute_type
