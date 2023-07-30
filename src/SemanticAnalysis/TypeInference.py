from __future__ import annotations

from typing import Optional

from src.LexicalAnalysis.Tokens import Token, TokenType
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import ScopeHandler, convert_type_to_string
from src.SyntacticAnalysis.Parser import ErrFmt

# todo : function selection (via signature)
# todo : base class auto upcast? maybe make it explicit
# todo : type inference for lambdas
# todo : all things "type generics"
# todo : mutability checks
# todo : visibility checks
# todo : builtin decorators
# todo : memory checks
#   - moves
#   - mutable references from mutable variables (required mutability)
#   - enforce the law of exclusivity
# todo : "partial moves"
# todo : symbol initialization for tuple types
# todo : merge most of "let" and "assignment" checks
#   - do this by converting "let x = 123" to "let x: Num" and "x = 123"


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


class SemanticError(Exception):
    # def throw(self):
    #     raise SystemExit(self) from None
    ...


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
                case _:
                    error = SemanticError(
                        ErrFmt.err(module_member._tok) +
                        f"Unknown module member {module_member}. Report this bug.")
                    raise SystemExit(error) from None

    @staticmethod
    def infer_type_of_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        s.next_scope()

        # Run semantic checks for each parameter in the function prototype. This will handle type-checking and default
        # expression checking.
        for parameter in ast.parameters:
            TypeInference.infer_type_of_parameter(parameter, s)

        # Default the discovered returning type of the function to the Void type. For each statement inferred, get the
        # type of the statement and set the returning type to that type. The final statement's type will be the
        # returning type of the function.
        discovered_ret_type = CommonTypes.void()
        for statement in ast.body.statements:
            discovered_ret_type = TypeInference.infer_type_of_statement(statement, s)

        # Check that the final statement's inferred type matches the return type of the function. If not, throw an
        # error.
        if discovered_ret_type != ast.return_type:
            error = SemanticError(
                ErrFmt.err(ast.body.statements[-1]._tok if ast.body.statements else ast.body._tok) +
                f"Expected return type {convert_type_to_string(ast.return_type)}, but found {convert_type_to_string(discovered_ret_type or CommonTypes.void())}.")
            raise SystemExit(error) from None
        s.prev_scope()

    @staticmethod
    def infer_type_of_parameter(ast: Ast.FunctionParameterAst, s: ScopeHandler) -> None:
        # Check the type of parameter exists, and if the parameter has a default value, check the expression. This
        # expression will actually be evaluated per call at runtime, so only type info is needed here.
        TypeInference.infer_type_of_type(ast.type_annotation, s)
        TypeInference.infer_type_of_expression(ast.default_value, s) if ast.default_value else None

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
                error = SemanticError(
                    ErrFmt.err(ast._tok) +
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
                error = SemanticError(
                    ErrFmt.err(ast._tok) +
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
        ts = []
        for branch in ast.branches:
            t = TypeInference.infer_type_of_if_branch(branch, s)
            ts.append(t)
        s.prev_scope()

        if len(ts) >= 1:
            branch_ret_type = ts[0]
            branch_type_0 = convert_type_to_string(branch_ret_type)
            for i in range(1, len(ts)):
                branch_type_i = convert_type_to_string(ts[i])
                if ts[i] != branch_ret_type:
                    error = SemanticError(
                        ErrFmt.err(ast.branches[i].body[-1]._tok) +
                        f"Branch {i} has a different type ({branch_type_i}) than the first branch ({branch_type_0}).")
                    raise SystemExit(error) from None

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
                error = SemanticError(
                    ErrFmt.err(ast._tok) +
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
            error = SemanticError(
                ErrFmt.err(ast._tok) +
                f"Class {class_symbol.parts[-1].identifier} not found.")
            raise SystemExit(error) from None

        if isinstance(ast.op.identifier, Ast.NumberLiteralBase10Ast):
            if not isinstance(restore_tuple, Ast.TypeTupleAst):
                error = SemanticError(
                    ErrFmt.err(ast._tok) +
                    f"Class {class_symbol.parts[-1].identifier} is not a tuple.")
                raise SystemExit(error) from None
            if int(ast.op.identifier.integer) >= len(restore_tuple.types):
                error = SemanticError(
                    ErrFmt.err(ast._tok) +
                    f"Tuple index {ast.op.identifier} out of range.")
                raise SystemExit(error) from None
            return restore_tuple.types[int(ast.op.identifier.integer)]

        try:
            member_symbol = class_scope.get_symbol(ast.op.identifier.identifier)
        except:
            error = SemanticError(
                ErrFmt.err(ast.op.identifier._tok) +
                f"Member '{ast.op.identifier.identifier}' not found on class '{class_symbol.parts[-1].identifier}'.")
            raise SystemExit(error) from None
        return member_symbol.type

    @staticmethod
    def infer_type_of_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        for a in ast.op.arguments:
            # todo : check
            TypeInference.infer_type_of_expression(a.value, s)
            if isinstance(a.value, Ast.IdentifierAst):
                s.current_scope.get_symbol(a.value.identifier).initialized = False

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
            error = SemanticError(
                ErrFmt.err(ast._tok) +
                f"Struct initializer for {struct_type.parts[-1].identifier} is missing fields: {set(actual_fields) - set(given_fields)}.")
            raise SystemExit(error) from None

        if len(given_fields) > len(actual_fields):
            error = SemanticError(
                ErrFmt.err(ast._tok) +
                f"Struct initializer for {struct_type.parts[-1].identifier} given unknown fields: {set(given_fields) - set(actual_fields)}.")
            raise SystemExit(error) from None

        if all_fields:
            all_fields_value = ast.op.fields[[isinstance(f.identifier, Ast.TokenAst) and f.identifier.tok.token_type == TokenType.KwElse for f in ast.op.fields].index(True)].value
            all_fields_value_type = TypeInference.infer_type_of_expression(all_fields_value, s)
            if all_fields_value_type != struct_type:
                error = SemanticError(
                    ErrFmt.err(all_fields_value._tok) +
                    f"Struct initializer default for {struct_type.parts[-1].identifier} given a value of type {convert_type_to_string(all_fields_value_type)}.")
                raise SystemExit(error) from None

        for given, actual in zip(sorted(given_fields), sorted(actual_fields)):
            given_value_type = TypeInference.infer_type_of_expression(ast.op.fields[given_fields.index(given)].value or s.current_scope.get_symbol(given).type, s)
            actual_value_type = s.global_scope.get_child_scope_for_cls(struct_type.parts[-1].identifier).get_symbol(actual).type
            if given_value_type != actual_value_type:
                error = SemanticError(
                    ErrFmt.err(ast.op.fields[given_fields.index(given)]._tok) +
                    f"Cannot assign {convert_type_to_string(given_value_type)} to {convert_type_to_string(actual_value_type)}.")
                raise SystemExit(error) from None

        return struct_type

    @staticmethod
    def infer_type_of_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        # If only a type annotation is provided, and not a value, then the variable is not initialized. Mark the symbol
        # as non-initialized so that it can be checked later.
        if not ast.value:
            # The only type a variable cannot be is the void type, so check that the provided type annotation is not the
            # Void type. todo : same for class attribute types
            if ast.type_annotation == CommonTypes.void():
                error = SemanticError(ErrFmt.err(ast._tok) + f"Cannot annotate a variable as Void.")
                raise SystemExit(error) from None

            s.current_scope.get_symbol(ast.variables[0].identifier.identifier).initialized = False
            return

        # If this step is reached, then a value has been provided, as providing a type annotation or a value is mutually
        # exclusive. As a value has been provided, the variable is initialized. Mark the symbol as initialized.
        s.current_scope.get_symbol(ast.variables[0].identifier.identifier).initialized = True

        # If the variable is provided a value, but the result of the value expression is a Void type, then throw an
        # error, as the variables inferred type would be Void, but Void is the only invalid type for a variable.
        if TypeInference.infer_type_of_expression(ast.value, s) == CommonTypes.void():
            error = SemanticError(
                ErrFmt.err(ast.value._tok) +
                f"Cannot assign Void to a variable.")
            raise SystemExit(error) from None

        # If the value expression being assigned to variables isn't initialized, or has been moved into another
        # variable, then is a violation of linear types - a value can only be used exactly once.
        # todo : differentiate between uninitialized and moved -- and for moved show where it was moved by using 2
        #  ErrorFormatting.error() calls concatenated
        if isinstance(ast.value, Ast.IdentifierAst) and not s.current_scope.get_symbol(ast.value.identifier).initialized:
            error = SemanticError(
                ErrFmt.err(ast.value._tok) +
                f"Variable '{ast.value.identifier}' is not initialized or has been moved.")
            raise SystemExit(error) from None

        # As assignment is a destructive move, so mark the variable as moved, by clearing its "initialized" flag. For
        # tuples, mark each item in the tuple as moved, recursively.
        # todo : create a function to uninitialize symbols - allow recursive for tuples
        if isinstance(ast.value, Ast.IdentifierAst):
            s.current_scope.get_symbol(ast.value.identifier).initialized = False
        elif isinstance(ast.value, Ast.TupleLiteralAst):
            # todo (recursive)
            ...

        # For a single variable being defined, set its type by inferring the expression value being assigned to it.
        if len(ast.variables) == 1:
            inferred_type = ast.type_annotation or TypeInference.infer_type_of_expression(ast.value, s)
            s.current_scope.get_symbol(ast.variables[0].identifier.identifier).type = inferred_type

        # Otherwise, destructure a tuple into the variables being defined. The tuple type will be inferred, but is
        # subject to a number of checks / constraints to ensure type-safety.
        else:
            # Infer the tuple type from the expression value being assigned to the variables.
            inferred_type = TypeInference.infer_type_of_expression(ast.value, s)

            # Firstly ensure that the inferred type is a tuple type, as a tuple is being destructured. This is done by
            # checking the AST type.
            if not isinstance(inferred_type, Ast.TypeTupleAst):
                exception = SemanticError(
                    ErrFmt.err(ast._tok) +
                    f"Expected a tuple type, but found {inferred_type}.")
                raise SystemExit(exception) from None

            # Secondly, ensure that the length of the tuple type matches the number of variables being defined. This is
            # done by checking the length of the tuple AST node. This ensures that all variables are handled.
            if len(inferred_type.types) != len(ast.variables):
                exception = SemanticError(
                    ErrFmt.err(ast._tok) +
                    f"Expected a tuple of length {len(ast.variables)}, but found {inferred_type}.")
                raise SystemExit(exception) from None

            # Finally, ensure that the type of each variable matches the type of the corresponding tuple element. This
            # is done by checking the type of each variable against the type of the corresponding tuple element.
            for i in range(len(ast.variables)):
                s.current_scope.get_symbol(ast.variables[i].identifier.identifier).type = inferred_type.types[i]

    @staticmethod
    def infer_type_of_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        if TypeInference.infer_type_of_expression(ast.rhs, s) == CommonTypes.void():
            error = SemanticError(
                ErrFmt.err(ast.rhs.value._tok) +
                f"Cannot assign Void to a variable.")
            raise SystemExit(error) from None

        # Any variables on the left hand side of the assignment are now initialized. Mark them as such, so that they can
        # be checked later.
        for l in [l for l in ast.lhs if isinstance(l, Ast.IdentifierAst)]:
            s.current_scope.get_symbol(l.identifier).initialized = True

        # todo : test & compare to other tuple assignment methods
        lhs_types = [TypeInference.infer_type_of_expression(l, s) for l in ast.lhs]
        rhs_type = TypeInference.infer_type_of_expression(ast.rhs, s)
        if len(lhs_types) == 1 and lhs_types[0] != rhs_type:
            error = SemanticError(
                ErrFmt.err(ast.op._tok) +
                f"Cannot assign {convert_type_to_string(rhs_type)} to {convert_type_to_string(lhs_types[0])}.")
            raise SystemExit(error) from None
        elif len(lhs_types) == 1:
            return CommonTypes.void()
        else:
            # TODO : DUP
            if not isinstance(rhs_type, Ast.TypeTupleAst):
                error = SemanticError(
                    ErrFmt.err(ast.op._tok) +
                    f"Multi assignment required destructuring a tuple, not a {convert_type_to_string(rhs_type)}")
                raise SystemExit(error) from None

            if len(lhs_types) != len(rhs_type.types):
                error = SemanticError(
                    ErrFmt.err(ast.op._tok) +
                    f"Cannot unpack a {len(ast.rhs.values)}-tuple into {len(lhs_types)} variables.")
                raise SystemExit(error) from None
            # TODO : DUP

            for i in range(len(lhs_types)):
                if lhs_types[i] != rhs_type.types[i]:
                    error = SemanticError(
                        ErrFmt.err(ast.rhs.values[i]._tok) +
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
                    error = SemanticError(
                        ErrFmt.err(ast._tok) +
                        f"Self in a non-class scope.")
                    raise SystemExit(error) from None
            ast.parts[0] = s.current_scope.get_type(scope.name).type

        identifier = convert_type_to_string(ast)
        if not s.current_scope.has_type(identifier):
            error = SemanticError(
                ErrFmt.err(ast._tok) +
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
