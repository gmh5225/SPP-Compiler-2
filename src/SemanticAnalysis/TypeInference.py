from __future__ import annotations
from src.SyntacticAnalysis import Ast
from src.LexicalAnalysis.Tokens import TokenType

class SemanticUnknownSymbolError(Exception):
    pass


BINARY_FUNC_MAP = {
    # Mathematical operations
    TokenType.TkAdd: "std::ops::Add::__add__",
    TokenType.TkAddEq: "std::ops::AddAssign::__add_assign__",
    TokenType.TkSub: "std::ops::Sub::__sub__",
    TokenType.TkSubEq: "std::ops::SubAssign::__sub_assign__",
    TokenType.TkMul: "std::ops::Mul::__mul__",
    TokenType.TkMulEq: "std::ops::MulAssign::__mul_assign__",
    TokenType.TkDiv: "std::ops::Div::__div__",
    TokenType.TkDivEq: "std::ops::DivAssign::__div_assign__",
    TokenType.TkRem: "std::ops::Mod::__mod__",
    TokenType.TkRemEq: "std::ops::ModAssign::__mod_assign__",

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

    # Comparison operations
    TokenType.TkEq: "std::ops::Eq::__eq__",
    TokenType.TkNe: "std::ops::Ne::__ne__",
    TokenType.TkLt: "std::ops::Lt::__lt__",
    TokenType.TkLe: "std::ops::Le::__le__",
    TokenType.TkGt: "std::ops::Gt::__gt__",
    TokenType.TkGe: "std::ops::Ge::__ge__",
    TokenType.TkSs: "std::ops::Cmp::__cmp__",

    # Miscellaneous operations
    TokenType.TkPipeArrowR: "std::ops::Pipe::__pip__",
}


class TypeInference:
    @staticmethod
    def infer_type(*args) -> Ast.TypeAst:
        return TypeInference._infer_type_from_expression(*args)

    @staticmethod
    def _infer_type_from_expression(ast: Ast.ExpressionAst, s) -> Ast.TypeAst:
        match ast:
            case Ast.BinaryExpressionAst(): return TypeInference._infer_type_from_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): return TypeInference._infer_type_from_postfix_expression(ast, s)
            case _:
                if type(ast) in Ast.PrimaryExpressionAst.__args__: return TypeInference._infer_type_from_primary_expression(ast, s)
                raise NotImplementedError(f"Type inference for {type(ast)} is not implemented")

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
        from .SymbolTable import SymbolName
        method = SymbolName(Ast.IdentifierAst(method), None)
        method = s.lookup_symbol(method)
        return method.return_type

    @staticmethod
    def _infer_type_from_postfix_expression(ast: Ast.PostfixExpressionAst, s) -> Ast.TypeAst:
        match ast.op:
            case Ast.PostfixFunctionCallAst(): return TypeInference._infer_type_from_function_call(ast, s)
            case Ast.PostfixMemberAccessAst(): return TypeInference._infer_type_from_member_access(ast, s)
            case Ast.PostfixStructInitializerAst(): return TypeInference._infer_type_from_struct_initializer(ast, s)
            case _: raise NotImplementedError(f"Type inference for {type(ast)} is not implemented")

    @staticmethod
    def _infer_type_from_function_call(ast: Ast.PostfixExpressionAst, s) -> Ast.TypeAst:
        # Set of operations to perform:
        #   - Find all functions that match the identifier.
        #   - Filter by the number of arguments (allowing for optional and variadics).
        #   - Fill in the generic type identifiers, explicit and implicit.
        #   - For each parameter, check if every "constraint" it met -- for parameters with 1 type, this just means check that this type is implemented on the actual argument type.
        #   - If there are multiple functions that match, pick the most constrained ones.
        #   - If there are still multiple functions that match, pick the first one (value guard are irrelevant as all have same return type).
        from .SymbolTable import SymbolName
        function = TypeInference._infer_type_from_expression(ast.lhs, s)
        matching_functions = s.lookup_symbols(SymbolName("::".join([p.identifier for p in function.parts])))
        print(ast.lhs)
        print("Found functions:", matching_functions)

        return Ast.TypeSingleAst([])

    @staticmethod
    def _infer_type_from_member_access(ast: Ast.PostfixExpressionAst, s) -> Ast.TypeAst:
        # The type of an attribute is accessed by inspecting the attribute type of the class that the attribute belongs
        # to. When this function is called, the struct may not have ben analysed yet, so to resolve this, this function
        # is only called from a lambda (from the caller in the SymbolBuilder class). All lambda type-inference functions
        # are called after the entire symbol table is built, so that all types are known.
        from .SymbolTable import SymbolName
        lhs_type = TypeInference._infer_type_from_expression(ast.lhs, s)
        lhs_type = SymbolName(Ast.IdentifierAst(lhs_type.parts[-1].identifier))
        t = s.lookup_type(lhs_type)._scope
        stored_type_scope = [c for c in t._child_scopes if c._name == lhs_type][0]

        rhs_identifier = ast.op.identifier
        rhs_identifier = SymbolName(Ast.IdentifierAst(rhs_identifier.identifier))
        rhs_identifier = s.lookup_symbol(rhs_identifier)
        return rhs_identifier.type.type


    @staticmethod
    def _infer_type_from_struct_initializer(ast: Ast.PostfixExpressionAst, s) -> Ast.TypeAst:
        # The type from a struct initializer is the type of the struct being initialized itself -- so for std::Num{},
        # the type is std::Num. The LHS must be a type, but this check will happen later in the "type checking". This is
        # because this stage is purely inferring what the type will be, not performing any checks.
        return ast.lhs

    @staticmethod
    def _infer_type_from_primary_expression(ast: Ast.PrimaryExpressionAst, s) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst(): return TypeInference._infer_type_from_identifier(ast, s)
            case Ast.GenericIdentifierAst(): return TypeInference._infer_type_from_generic_identifier(ast, s)
            case Ast.LambdaAst(): return TypeInference._infer_type_from_lambda(ast, s)
            case Ast.PlaceholderAst(): return TypeInference._infer_type_from_placeholder(ast, s)
            case Ast.TypeSingleAst(): return TypeInference._infer_type_from_type_single(ast, s)
            case Ast.IfStatementAst(): return TypeInference._infer_type_from_if_statement(ast, s)
            case Ast.MatchStatementAst(): return TypeInference._infer_type_from_match_statement(ast, s)
            case Ast.WhileStatementAst() | Ast.ForStatementAst() | Ast.DoWhileStatementAst(): return TypeInference._infer_type_from_looping_statement(ast, s)
            case _:
                if type(ast) in Ast.LiteralAst.__args__: return TypeInference._infer_type_from_literal(ast, s)
                raise NotImplementedError(f"Type inference for {type(ast)} is not implemented")

    @staticmethod
    def _infer_type_from_literal(ast: Ast.LiteralAst, s) -> Ast.TypeAst:
        match ast:
            case Ast.StringLiteralAst(): return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Str", [])])
            case Ast.CharLiteralAst(): return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Char", [])])
            case Ast.BoolLiteralAst(): return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Bool", [])])
            case Ast.RegexLiteralAst(): return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Reg", [])])
            case Ast.TupleLiteralAst(): return Ast.TypeTupleAst([TypeInference._infer_type_from_expression(e, s) for e in ast.values])
            case _:
                if type(ast) in Ast.NumberLiteralAst.__args__: return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Num", [])])
                raise NotImplementedError(f"Type inference for {type(ast)} is not implemented")

    @staticmethod
    def _infer_type_from_identifier(ast: Ast.IdentifierAst, s) -> Ast.TypeAst:
        # The type of an identifier is the type of the variable that it refers to. This is stored in the symbol table
        # under the variable's name.
        from .SymbolTable import SymbolName
        try:
            return s.lookup_symbol(SymbolName(ast)).type.type
        except AttributeError:
            raise SemanticUnknownSymbolError(f"Unknown symbol {ast.identifier}")

    @staticmethod
    def _infer_type_from_generic_identifier(ast: Ast.GenericIdentifierAst, s) -> Ast.TypeAst:
        identified_type = TypeInference._infer_type_from_identifier(Ast.IdentifierAst(ast.identifier), s)
        # todo => send in generics
        return identified_type

    @staticmethod
    def _infer_type_from_lambda(ast: Ast.LambdaAst, s) -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Non-Inferrable (for now)", [])])
        # raise NotImplementedError(f"Type inference for {type(ast)} is not implemented")

    @staticmethod
    def _infer_type_from_placeholder(ast: Ast.PlaceholderAst, s) -> Ast.TypeAst:
        raise Exception("Placeholders should not be present in the AST at this stage")

    @staticmethod
    def _infer_type_from_type_single(ast: Ast.TypeSingleAst, s) -> Ast.TypeAst:
        return ast

    @staticmethod
    def _infer_type_from_if_statement(ast: Ast.IfStatementAst, s) -> Ast.TypeAst:
        # The return type from an if statement is the return type of the final expression in the branches' statements
        expression = ast.branches[0].body[-1]
        try: return TypeInference._infer_type_from_expression(expression, s)
        except NotImplementedError: Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Void", [])])

    @staticmethod
    def _infer_type_from_match_statement(ast: Ast.MatchStatementAst, s) -> Ast.TypeAst:
        # The return type from a match statement is the return type of the final expression in the branches' statements
        expression = ast.cases[0].body[-1]
        try: return TypeInference._infer_type_from_expression(expression, s)
        except NotImplementedError: Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Void", [])])

    @staticmethod
    def _infer_type_from_looping_statement(ast: Ast.WhileStatementAst | Ast.ForStatementAst | Ast.DoWhileStatementAst, s) -> Ast.TypeAst:
        # The return type from a while statement is the return type of the break statement's expression
        break_expressions = [statement for statement in ast.body if isinstance(statement, Ast.BreakStatementAst)]
        if len(break_expressions) == 0:
            raise Exception("While statement does not contain a break statement")
        else:
            expression = break_expressions[0].returning_expression
            try: return TypeInference._infer_type_from_expression(expression, s)
            except NotImplementedError: Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Void", [])])



