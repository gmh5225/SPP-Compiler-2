from __future__ import annotations

from typing import Optional

from src.LexicalAnalysis.Tokens import Token, TokenType
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import ScopeHandler, convert_type_to_string
from src.SyntacticAnalysis.Parser import ErrorFormatter


BIN_FUNCTION_NAMES = {
    TokenType.TkAdd: "add",
    TokenType.TkSub: "sub",
    TokenType.TkMul: "mul",
    TokenType.TkDiv: "div",
    TokenType.TkRem: "mod",

    TokenType.TkDoubleAmpersand: "and",
    TokenType.TkDoublePipe: "or",
    TokenType.TkAmpersand: "bit_and",
    TokenType.TkPipe: "bit_or",
    TokenType.TkCaret: "bit_xor",

    TokenType.TkEq : "eq",
    TokenType.TkNe: "ne",
    TokenType.TkLt: "lt",
    TokenType.TkLe: "le",
    TokenType.TkGt: "gt",
    TokenType.TkGe: "ge",
    TokenType.TkSs : "cmp",
    TokenType.TkPipeArrowR: "rpip",
    TokenType.TkPipeArrowL: "lpip",
}


class TypeInference:
    @staticmethod
    def infer(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        TypeInference.infer_type_of_program(ast, s)
        s.switch_to_global_scope()

    @staticmethod
    def infer_type_of_program(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        for module_member in ast.module.body.members:
            match module_member:
                case Ast.FunctionPrototypeAst(): TypeInference.infer_type_of_function_prototype(module_member, s)
                case Ast.ClassPrototypeAst(): s.skip_scope()
                case Ast.EnumPrototypeAst(): s.skip_scope()
                case Ast.SupPrototypeNormalAst(): TypeInference.infer_type_of_sup_prototype(module_member, s)
                case Ast.SupPrototypeInheritanceAst(): TypeInference.infer_type_of_sup_prototype(module_member, s)
                # case _:
                #     error = Exception(
                #         ErrorFormatter.error(module_member._tok) +
                #         f"Unknown module member {module_member}.")
                #     raise SystemExit(error) from None

    @staticmethod
    def infer_type_of_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        s.next_scope()
        for parameter in ast.parameters:
            TypeInference.infer_type_of_type(parameter.type_annotation, s)
        t = CommonTypes.void()
        for statement in ast.body.statements:
            t = TypeInference.infer_type_of_statement(statement, s)
        if t != ast.return_type:
            error = Exception(
                ErrorFormatter.error(ast.body.statements[-1]._tok if ast.body.statements else ast.body._tok) +
                f"Expected return type {convert_type_to_string(ast.return_type)}, but found {convert_type_to_string(t or CommonTypes.void())}.")
            raise SystemExit(error) from None
        s.prev_scope()

    @staticmethod
    def infer_type_of_statement(ast: Ast.StatementAst, s: ScopeHandler) -> Optional[Ast.TypeAst]:
        match ast:
            case Ast.TypedefStatementAst(): return
            case Ast.ReturnStatementAst(): return TypeInference.infer_type_of_return_statement(ast, s)
            case Ast.LetStatementAst(): TypeInference.infer_type_of_let_statement(ast, s)
            case Ast.FunctionPrototypeAst(): TypeInference.infer_type_of_function_prototype(ast, s)
            case _: return TypeInference.infer_type_of_expression(ast, s)

    @staticmethod
    def infer_type_of_return_statement(ast: Ast.ReturnStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInference.infer_type_of_expression(ast.value, s)

    @staticmethod
    def infer_type_of_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        if len(ast.variables) == 1:
            inferred_type = ast.type_annotation or TypeInference.infer_type_of_expression(ast.value, s)
            s.current_scope.get_symbol(ast.variables[0].identifier.identifier).type = inferred_type
        else:
            inferred_type = TypeInference.infer_type_of_expression(ast.value, s)
            if not isinstance(inferred_type, Ast.TypeTupleAst):
                exception = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Expected a tuple type, but found {inferred_type}.")
                raise SystemExit(exception) from None
            if len(inferred_type.types) != len(ast.variables):
                exception = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Expected a tuple of length {len(ast.variables)}, but found {inferred_type}.")
                raise SystemExit(exception) from None
            for i in range(len(ast.variables)):
                s.current_scope.get_symbol(ast.variables[i].identifier.identifier).type = inferred_type.types[i]

    @staticmethod
    def infer_type_of_sup_prototype(ast: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, s: ScopeHandler) -> None:
        s.next_scope()
        for statement in ast.body.members:
            TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()

    @staticmethod
    def infer_type_of_expression(ast: Ast.ExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst(): return TypeInference.infer_type_of_identifier(ast, s)
            case Ast.LambdaAst(): return TypeInference.infer_type_of_lambda(ast, s)
            case Ast.IfStatementAst(): return TypeInference.infer_type_of_if_statement(ast, s)
            case Ast.YieldStatementAst(): return
            case Ast.InnerScopeAst(): TypeInference.infer_type_of_inner_scope(ast, s)
            case Ast.WithStatementAst(): return TypeInference.infer_type_of_with_statement(ast, s)
            case Ast.TokenAst(): return
            case Ast.BinaryExpressionAst(): return TypeInference.infer_type_of_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): return TypeInference.infer_type_of_postfix_expression(ast, s)
            case Ast.AssignmentExpressionAst(): return TypeInference.infer_type_of_assignment_expression(ast, s)
            case Ast.PlaceholderAst():
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Placeholder found in an incorrect position.")
                raise SystemExit(error) from None
            case Ast.TypeSingleAst(): return TypeInference.infer_type_of_type(ast, s)
            case Ast.WhileStatementAst(): return TypeInference.infer_type_of_while_statement(ast, s)
            case Ast.BoolLiteralAst(): return CommonTypes.bool()
            case Ast.StringLiteralAst(): return CommonTypes.string()
            case Ast.CharLiteralAst(): return CommonTypes.char()
            case Ast.RegexLiteralAst(): return CommonTypes.regex()
            case Ast.TupleLiteralAst(): return TypeInference.infer_type_of_tuple_literal(ast, s)
            case Ast.NumberLiteralBase10Ast() | Ast.NumberLiteralBase16Ast() | Ast.NumberLiteralBase02Ast(): return CommonTypes.num()
            case _:
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"{ast.__class__.__name__} is trying to be analysed as an expression: Report.")
                raise SystemExit(error) from None


    @staticmethod
    def infer_type_of_tuple_literal(ast: Ast.TupleLiteralAst, s: ScopeHandler) -> Ast.TypeAst:
        return Ast.TypeTupleAst([TypeInference.infer_type_of_expression(e, s) for e in ast.values], ast._tok)

    @staticmethod
    def infer_type_of_identifier(ast: Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        return s.current_scope.get_symbol(ast.identifier).type

    @staticmethod
    def infer_type_of_if_statement(ast: Ast.IfStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.void()
        for branch in ast.branches:
            t = TypeInference.infer_type_of_if_branch(branch, s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_if_branch(ast: Ast.PatternStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.void()
        for statement in ast.body:
            t = TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_inner_scope(ast: Ast.InnerScopeAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.void()
        for statement in ast.body:
            t = TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_with_statement(ast: Ast.WithStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.void()
        for statement in ast.body:
            t = TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()
        return t

    @staticmethod
    def infer_type_of_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # translate the operator to a function
        # a + b => a.add(b)
        # 1. get the correct function name for the operator
        # 2. form a member access expression
        # 3. form a function call expression
        # 4. find the function symbol
        # 5. get the return type of the function (first generic argument)
        # 6. return the type
        idx = ast.op._tok # todo : where to use "idx"
        function_name = Ast.IdentifierAst(BIN_FUNCTION_NAMES[ast.op.tok.token_type], idx)
        member_access = Ast.PostfixMemberAccessAst(Ast.TokenAst(Token(".", TokenType.TkDot), idx), function_name, idx)
        member_access = Ast.PostfixExpressionAst(ast.lhs, member_access, idx)
        function_call = Ast.PostfixFunctionCallAst([], [Ast.FunctionArgumentAst(None, ast.rhs, None, False, idx)], idx) # todo : convention
        function_call = Ast.PostfixExpressionAst(member_access, function_call, idx)
        return TypeInference.infer_type_of_expression(function_call, s)

    @staticmethod
    def infer_type_of_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast.op:
            case Ast.PostfixMemberAccessAst(): return TypeInference.infer_type_of_postfix_member_access(ast, s)
            case Ast.PostfixFunctionCallAst(): return TypeInference.infer_type_of_postfix_function_call(ast, s)
            case Ast.PostfixStructInitializerAst(): return TypeInference.infer_type_of_postfix_struct_initializer(ast, s)
            case _:
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Postfix expression {type(ast)} not yet supported.")
                raise SystemExit(error) from None

    @staticmethod
    def infer_type_of_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        class_symbol = TypeInference.infer_type_of_expression(ast.lhs, s)
        class_symbol = TypeInference.infer_type_of_type(class_symbol, s)
        restore_tuple = class_symbol
        if isinstance(class_symbol, Ast.TypeTupleAst):
            class_symbol = CommonTypes.tuple(class_symbol.types)

        class_scope = s.global_scope.get_child_scope_for_cls(class_symbol.parts[-1].identifier)
        if class_scope is None:
            error = Exception(
                ErrorFormatter.error(ast._tok) +
                f"Class {class_symbol.parts[-1].identifier} not found.")
            raise SystemExit(error) from None

        if isinstance(ast.op.identifier, Ast.NumberLiteralBase10Ast):
            if not isinstance(restore_tuple, Ast.TypeTupleAst):
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Class {class_symbol.parts[-1].identifier} is not a tuple.")
                raise SystemExit(error) from None
            if int(ast.op.identifier.integer) >= len(restore_tuple.types):
                error = Exception(
                    ErrorFormatter.error(ast._tok) +
                    f"Tuple index {ast.op.identifier} out of range.")
                raise SystemExit(error) from None
            return restore_tuple.types[int(ast.op.identifier.integer)]

        try:
            member_symbol = class_scope.get_symbol(ast.op.identifier.identifier)
        except:
            error = Exception(
                ErrorFormatter.error(ast.op.identifier._tok) +
                f"Member '{ast.op.identifier.identifier}' not found on class '{class_symbol.parts[-1].identifier}'.")
            raise SystemExit(error) from None
        return member_symbol.type


    @staticmethod
    def infer_type_of_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        lhs_type = TypeInference.infer_type_of_expression(ast.lhs, s)
        # lhs_type = s.current_scope.get_type(lhs_type.parts[-1].identifier).type
        lhs_type = lhs_type.parts[-1].generic_arguments[0].value
        return lhs_type

    @staticmethod
    def infer_type_of_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        given_fields = [f.identifier.identifier for f in ast.op.fields if isinstance(f.identifier, Ast.IdentifierAst)]
        for given_field in ast.op.fields:
            TypeInference.infer_type_of_expression(given_field.value, s)

        all_fields = any(isinstance(f.identifier, Ast.TokenAst) and f.identifier.tok.token_type == TokenType.KwElse for f in ast.op.fields)

        struct_type = TypeInference.infer_type_of_type(ast.lhs, s)
        actual_fields = s.global_scope.get_child_scope_for_cls(struct_type.parts[-1].identifier).all_exclusive_symbols()

        if len(given_fields) < len(actual_fields) and not all_fields:
            error = Exception(
                ErrorFormatter.error(ast._tok) +
                f"Struct initializer for {struct_type.parts[-1].identifier} is missing fields: {set(actual_fields) - set(given_fields)}.")
            raise SystemExit(error) from None

        if len(given_fields) > len(actual_fields):
            error = Exception(
                ErrorFormatter.error(ast._tok) +
                f"Struct initializer for {struct_type.parts[-1].identifier} given unknown fields: {set(given_fields) - set(actual_fields)}.")
            raise SystemExit(error) from None

        for given, actual in zip(sorted(given_fields), sorted(actual_fields)):
            given_value_type = TypeInference.infer_type_of_expression(ast.op.fields[given_fields.index(given)].value or s.current_scope.get_symbol(given).type, s)
            actual_value_type = s.global_scope.get_child_scope_for_cls(struct_type.parts[-1].identifier).get_symbol(actual).type
            if given_value_type != actual_value_type:
                error = Exception(
                    ErrorFormatter.error(ast.op.fields[given_fields.index(given)]._tok) +
                    f"Cannot assign {convert_type_to_string(given_value_type)} to {convert_type_to_string(actual_value_type)}.")
                raise SystemExit(error) from None

        return struct_type

    @staticmethod
    def infer_type_of_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # todo : test & compare to other tuple assignment methods
        lhs_types = [TypeInference.infer_type_of_expression(l, s) for l in ast.lhs]
        rhs_type = TypeInference.infer_type_of_expression(ast.rhs, s)
        if len(lhs_types) == 1 and lhs_types[0] != rhs_type:
            error = Exception(
                ErrorFormatter.error(ast.op._tok) +
                f"Cannot assign {convert_type_to_string(rhs_type)} to {convert_type_to_string(lhs_types[0])}.")
            raise SystemExit(error) from None
        elif len(lhs_types) == 1:
            return CommonTypes.void()
        else:
            if not isinstance(rhs_type, Ast.TypeTupleAst):
                error = Exception(
                    ErrorFormatter.error(ast.op._tok) +
                    f"Multi assignment required destructuring a tuple, not a {convert_type_to_string(rhs_type)}")
                raise SystemExit(error) from None

            if len(lhs_types) != len(rhs_type.types):
                error = Exception(
                    ErrorFormatter.error(ast.op._tok) +
                    f"Cannot unpack a {len(ast.rhs.values)}-tuple into {len(lhs_types)} variables.")
                raise SystemExit(error) from None

            for i in range(len(lhs_types)):
                if lhs_types[i] != rhs_type.types[i]:
                    error = Exception(
                        ErrorFormatter.error(ast.rhs.values[i]._tok) +
                        f"Cannot assign {convert_type_to_string(rhs_type.types[i])} to {convert_type_to_string(lhs_types[i])}.")
                    raise SystemExit(error) from None
        return CommonTypes.void()

    @staticmethod
    def infer_type_of_type(ast: Ast.TypeSingleAst | Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        if isinstance(ast, Ast.TypeTupleAst):
            for type in ast.types:
                TypeInference.infer_type_of_type(type, s)
            return ast

        if isinstance(ast.parts[0], Ast.SelfTypeAst):
            scope = s.current_scope
            while not scope.name.startswith("ClsPrototype"):
                scope = scope.parent
                if not scope:
                    error = Exception(
                        ErrorFormatter.error(ast._tok) +
                        f"Self in a non-class scope.")
                    raise SystemExit(error) from None
            ast.parts[0] = s.current_scope.get_type(scope.name).type

        identifier = convert_type_to_string(ast)
        if not s.current_scope.has_type(identifier):
            error = Exception(
                ErrorFormatter.error(ast._tok) +
                f"Type {identifier} not found.")
            raise SystemExit(error) from None
        return ast

    @staticmethod
    def infer_type_of_while_statement(ast: Ast.WhileStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        for statement in ast.body:
            TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()
        return CommonTypes.void()

    @staticmethod
    def infer_type_of_lambda(ast: Ast.LambdaAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.unknown()
        s.prev_scope()
        return t


class CommonTypes:
    @staticmethod
    def void() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Void", [], -1)], -1)
    
    @staticmethod
    def bool() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Bool", [], -1)], -1)
    
    @staticmethod
    def string() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Str", [], -1)], -1)
    
    @staticmethod
    def char() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Char", [], -1)], -1)
    
    @staticmethod
    def regex() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Rgx", [], -1)], -1)
    
    @staticmethod
    def num() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Num", [], -1)], -1)
    
    @staticmethod
    def unknown() -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Unknown", [], -1)], -1)

    @staticmethod
    def tuple(types: list[Ast.TypeAst]) -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Tup", types, -1)], -1)
