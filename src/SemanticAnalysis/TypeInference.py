from __future__ import annotations

import re
from typing import Optional
import difflib

from src.LexicalAnalysis.Tokens import Token, TokenType
from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import ScopeHandler, convert_type_to_string, convert_multi_identifier_to_string, convert_convention_to_string, function_identifier_strip_signature
from src.SyntacticAnalysis.Parser import ErrFmt


# todo : document that overloading cannot be done my mutability of parameters

# todo : a string in a pattern errors?
# todo : where block (requires generics)
# todo : optional and variadic parameters
# todo : check module identifier is correct (matches file name & path/directory)
# todo : type inference for lambdas
# todo : all things "type generics"
# todo : mutability checks
#   - calling mutable functions on immutable references
# todo : visibility checks
# todo : memory checks
#   - enforce the law of exclusivity for member-access-attributes (locals done)
#       - partial moves
#   - consuming self (will require function selection)
#   - fix "self" being &Self but passing to a &mut Self method etc
#   - convention matching issues => if a variable is a reference, then the "&" isn't required in the function call
#       - or just make is so that it is?
# todo : symbol initialization for tuple types
# todo : all things lambdas => maybe convert into a function prototype?
# todo : exhaustion or default for "if comparisons" that are for assignment => add optional param to "check-if"...
# todo : fold expressions
# todo : partial functions with underscore placeholder -> make a new type, also memory rules
# todo : some errors say "identifier ... not found", should say "attribute ... not found"
# todo : assignment needs to allow assigning a more derived class onto a base class type
# todo : all things "yielding"
# todo : FnRef vs FnMut vs FnOne

# todo : unify behaviour for "let", "=" and func-call()
#   - change "let x = 3" to "let x: Num", "x=3"
#   - change "x = 3" to x.assign(3)
#   - so "let x = 3" becomes "let x: Num; x.assign(3)"


# todo : pure/impure functions
# todo : tail-call recursion

# todo : where block
#   - add the inline constraints from the type generics to the where block
#   - check every type being constrained exists (even as generic params)
#   - check every type it is being constrained to exists



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
        for decorator in ast.module.decorators:
            TypeInference.infer_type_of_decorator(ast, decorator, s)

        for module_member in ast.module.body.members:
            match module_member:
                case Ast.FunctionPrototypeAst(): TypeInference.infer_type_of_function_prototype(module_member, s)
                case Ast.ClassPrototypeAst(): TypeInference.infer_type_of_class_prototype(module_member, s)
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
        # Handle all the decorators
        for decorator in ast.decorators:
            TypeInference.infer_type_of_decorator(ast, decorator, s)

        s.next_scope()
        # Run semantic checks for each parameter in the function prototype. This will handle type-checking and default
        # expression checking.
        for parameter in ast.parameters:
            TypeInference.infer_type_of_parameter(parameter, s)

        # Make sure all the type generic parameters are inferrable
        for type_generic in ast.generic_parameters:
            if type_generic.identifier.identifier not in [convert_type_to_string(p.type_annotation) for p in ast.parameters]:
                raise SystemExit(ErrFmt.err(type_generic._tok) + f"Type generic '{type_generic.identifier.identifier}' cannot be inferred.")

        # Run a type-infer on the return type so the Self type can be inferred prior to any return statement's type
        # check
        TypeInference.infer_type_of_type(ast.return_type, s)

        # Default the discovered returning type of the function to the Void type. For each statement inferred, get the
        # type of the statement and set the returning type to that type. The final statement's type will be the
        # returning type of the function.
        discovered_ret_type = CommonTypes.void()
        for statement in ast.body.statements:
            discovered_ret_type = TypeInference.infer_type_of_statement(statement, s)

        # Check that the final statement's inferred type matches the return type of the function. If not, throw an
        # error. If there are no statements in the body, then the token position is just the "{" scope opening token.
        if discovered_ret_type != ast.return_type:
            final_statement_ast = ast.body.statements[-1] if ast.body.statements else ast.body
            raise SystemExit(ErrFmt.err(final_statement_ast._tok) + f"Expected return type {convert_type_to_string(ast.return_type)}, but found {convert_type_to_string(discovered_ret_type or CommonTypes.void())}.")
        s.prev_scope()

    @staticmethod
    def infer_type_of_decorator(enclosing, ast: Ast.DecoratorAst, s: ScopeHandler) -> None:
        match convert_multi_identifier_to_string(ast.identifier):
            case "private":
                ...
            case "public":
                ...
            case "protected":
                ...
            case "virtualmethod":
                if not isinstance(enclosing, Ast.FunctionPrototypeAst):
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Decorator '@virtualmethod' can only be used on functions.")
                symbol = s.current_scope.get_symbol(enclosing.identifier.identifier)
                symbol.meta["virtual"] = True
            case "abstractmethod":
                if not isinstance(enclosing, Ast.FunctionPrototypeAst):
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Decorator '@abstractmethod' can only be used on functions.")
                symbol = s.current_scope.get_symbol(enclosing.identifier.identifier)
                symbol.meta["abstract"] = True
            case "staticmethod":
                if not isinstance(enclosing, Ast.FunctionPrototypeAst):
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Decorator '@staticmethod' can only be used on functions.")
                symbol = s.current_scope.get_symbol(enclosing.identifier.identifier)
                symbol.meta["static"] = True
            case _:
                ...

    @staticmethod
    def infer_type_of_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeHandler) -> None:
        for decorator in ast.decorators:
            TypeInference.infer_type_of_decorator(ast, decorator, s)

        s.next_scope()
        for member in ast.body.members:
            TypeInference.infer_type_of_class_attribute(member, s)
        s.prev_scope()

    @staticmethod
    def infer_type_of_class_attribute(ast: Ast.ClassAttributeAst, s: ScopeHandler) -> None:
        for decorator in ast.decorators:
            TypeInference.infer_type_of_decorator(ast, decorator, s)

        TypeInference.infer_type_of_type(ast.type_annotation, s)

    @staticmethod
    def infer_type_of_parameter(ast: Ast.FunctionParameterAst, s: ScopeHandler) -> None:
        # Check the type of parameter exists, and if the parameter has a default value, check the expression. This
        # expression will actually be evaluated per call at runtime, so only type info is needed here.
        TypeInference.infer_type_of_type(ast.type_annotation, s)
        TypeInference.infer_type_of_expression(ast.default_value, s) if ast.default_value else None
        MemoryEnforcer.set_variable_initialized([ast.identifier], s, True)
        s.current_scope.get_symbol(ast.identifier.identifier).defined = True

    @staticmethod
    def infer_type_of_statement(ast: Ast.StatementAst, s: ScopeHandler) -> Optional[Ast.TypeAst]:
        match ast:
            case Ast.TypedefStatementAst(): TypeInference.infer_type_of_typedef(ast, s)
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

        if isinstance(ast, Ast.SupPrototypeInheritanceAst):
            TypeInference.infer_type_of_type(ast.super_class, s)

        for member in ast.body.members:
            match member:
                case Ast.SupMethodPrototypeAst(): TypeInference.infer_type_of_sup_method_prototype(member, ast, s)
                case Ast.SupTypedefAst(): TypeInference.infer_type_of_sup_typedef(member, s)
        s.prev_scope()

    @staticmethod
    def infer_type_of_sup_method_prototype(ast: Ast.SupMethodPrototypeAst, sup_block: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, s: ScopeHandler) -> None:
        # Some extra checks for inheritance -- the method must exist in the super class, and the method must be
        # decorated as virtual or abstract. If not, then throw an error.
        if isinstance(sup_block, Ast.SupPrototypeInheritanceAst):
            super_class_scope = s.global_scope.get_child_scope_for_cls(convert_type_to_string(sup_block.super_class))

            # Check that the super class being super-imposed onto this class contains the member being overridden.
            # Simple symbol table lookup to check if the symbol exists.
            if not super_class_scope.has_symbol(ast.identifier.identifier):
                bad_function_identifier = function_identifier_strip_signature(ast.identifier.identifier, string_ref=True)
                raise SystemExit(ErrFmt.err(ast.identifier._tok) + f"Method '{bad_function_identifier}' not found in super class '{convert_type_to_string(sup_block.super_class)}'.")

            # Check that the super class member being overridden is decorated as virtual or abstract. If not, then
            # throw an error.
            function_symbol = super_class_scope.get_symbol(ast.identifier.identifier)
            if not function_symbol.meta.get("virtual") and not function_symbol.meta.get("abstract"):
                bad_function_identifier = function_identifier_strip_signature(ast.identifier.identifier, string_ref=True)
                raise SystemExit(ErrFmt.err(ast.identifier._tok) + f"Method '{bad_function_identifier}' in super class '{convert_type_to_string(sup_block.super_class)}' is not virtual or abstract.")


        TypeInference.infer_type_of_function_prototype(ast, s)

    @staticmethod
    def infer_type_of_sup_typedef(ast: Ast.SupTypedefAst, s: ScopeHandler) -> None:
        for decorator in ast.decorators:
            TypeInference.infer_type_of_decorator(ast, decorator, s)
        TypeInference.infer_type_of_typedef(ast, s)

    @staticmethod
    def infer_type_of_typedef(ast: Ast.TypedefStatementAst, s: ScopeHandler) -> None:
        TypeInference.infer_type_of_type(ast.old_type, s)

    @staticmethod
    def infer_type_of_expression(ast: Ast.ExpressionAst, s: ScopeHandler, call: bool = False) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst(): return TypeInference.infer_type_of_identifier(ast, s, call)
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
    def infer_type_of_identifier(ast: Ast.IdentifierAst, s: ScopeHandler, call: bool = False) -> Ast.TypeAst:
        # For an identifier to be valid, it must exist in the current scope, or a parent scope, and must also be
        # "defined" -- this means that if it's found in a scope, it must be before the current line. If it's not, then
        # whilst the symbol technically exists, it's not valid to use it, as it hasn't been assigned a value yet. If
        # it's in the global scope, then the order doesn't matter - these are the functions, classes, enums etc.
        if (not s.current_scope.has_symbol(ast.identifier) or not s.current_scope.get_symbol(ast.identifier).defined) and not s.global_scope.has_symbol(ast.identifier):
            identifier = ast.identifier

            # todo : not sure this is picking ip attributes
            candidate_symbols = [sym for sym in s.current_scope.all_symbols() if s.current_scope.get_symbol(sym).defined or s.global_scope.has_symbol(sym)]
            most_likely = (-1.0, "")

            # Check each candidate symbol
            for candidate in candidate_symbols:
                if not call and "#" in candidate:
                    continue
                ratio = difflib.SequenceMatcher(None, identifier, candidate).ratio()

                # If a more likely match is found, based on string comparison, then update the most likely match. This
                # is calculated by comparing comparison ratios. If the ratio is greater than the current most likely
                # match, then it is more likely, and is therefore the new most likely match.
                if ratio > most_likely[0]:
                    most_likely = (ratio, candidate)

                # If the ratio is equal to the current most likely match, then choose the option that is closest to the
                # length of the identifier. This is done by comparing the absolute difference between the lengths of the
                # identifier and the candidate. If the difference is less than the difference between the identifier
                # and the current most likely match, then the candidate is more likely.
                elif ratio == most_likely[0]:
                    if abs(len(identifier) - len(candidate)) < abs(len(identifier) - len(most_likely[1])):
                        most_likely = (ratio, candidate)

            # Raise the unknown symbol error, and suggest the most likely match. This is when a non-function type is
            # being called.
            if not call:
                if most_likely[1]:
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Identifier '{ast.identifier}' not defined. Did you mean '{most_likely[1]}'?")
                else:
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Identifier '{ast.identifier}' not defined.")

            # For functions, change the output slightly -- firstly, offer alternative signature suggestions, and
            # secondly, offset alternative function names.
            else:
                # Get all functions in the scope that have the same identifier as the one being called, but keep
                # searching the entire scope so that every overload is discovered.
                matching_functions_dif_signatures = [s for s in s.current_scope.all_symbols() if "#" in s and s.split("#")[0] == ast.identifier.split("#")[0]]

                # If there are any matching function names, then multiple overloads have been provided -- convert them
                # into strings for the error message.
                if matching_functions_dif_signatures:
                    bad_function_identifier = function_identifier_strip_signature(ast.identifier, string_ref=True)
                    string = f"Matching signature for '{bad_function_identifier}' not defined. Available signatures:\n"
                    for f in matching_functions_dif_signatures:
                        f = function_identifier_strip_signature(f, string_ref=True)
                        string += f"    - {f}\n"
                    raise SystemExit(ErrFmt.err(ast._tok) + string)

                # If there are no matching function names, then the symbol doesn't exist -- offer the most likely
                # alternative match.
                most_likely = function_identifier_strip_signature(most_likely[1])
                bad_function_identifier = function_identifier_strip_signature(ast.identifier, string_ref=True)
                if most_likely != ")":
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Function '{bad_function_identifier}' not defined. Did you mean '{most_likely}'?")
                else:
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Function '{bad_function_identifier}' not defined.")


        # Return the type of the symbol, which is found in the current scope, or a parent scope. This symbol must exist,
        # as prior checks have guaranteed this.
        return s.current_scope.get_symbol(ast.identifier).type

    @staticmethod
    def infer_type_of_if_statement(ast: Ast.IfStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()
        t = CommonTypes.void()
        ts = []
        for branch in ast.branches:
            t = TypeInference.infer_type_of_if_branch(ast, branch, s)
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
    def infer_type_of_if_branch(if_ast: Ast.IfStatementAst, ast: Ast.PatternStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        s.next_scope()

        # If the "if" statement contains the comparison operator, then the branch can't contain the comparison operator.
        # Check both the "if" condition and the branch condition to ensure they don't both contain the comparison
        # operator.
        if if_ast.comparison_op and ast.comparison_op:
            raise SystemExit(ErrFmt.err(ast._tok) + f"Branch cannot contain a comparison operator.")

        # Check the comparison function exists on the type's being compared.
        comparison_pattern = if_ast.comparison_op or ast.comparison_op
        binary_comp = Ast.BinaryExpressionAst(if_ast.condition, comparison_pattern, ast.patterns[0].value, comparison_pattern._tok)
        TypeInference.infer_type_of_expression(binary_comp, s)

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

        if ast.alias:
            s.current_scope.get_symbol(ast.alias.identifier.identifier).type = TypeInference.infer_type_of_expression(ast.value, s)
            s.current_scope.get_symbol(ast.alias.identifier.identifier).defined = True
            MemoryEnforcer.set_variable_initialized([ast.alias], s, True)

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
        function_call = Ast.PostfixFunctionCallAst([], [Ast.FunctionArgumentAst(None, ast.rhs, Ast.ParameterPassingConventionReferenceAst(False, idx), False, idx)], idx) # todo : convention
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
        # todo : errors come up on the RHS before the LHS - try switch this

        # Infer the type of the LHS of the member access expression. This will be the type of the class that the member
        # is being accessed on. Because things like (x + 1).function().attr is valid, it needs to recursively infer the
        # type of the LHS until it is an IdentifierAst, so that it's type can be retrieved from the symbol table.
        lhs = TypeInference.infer_type_of_expression(ast.lhs, s)
        lhs_type = TypeInference.infer_type_of_type(lhs, s)

        # If the LHS type is a TypeTupleAst node, then save this node. This is because the LHS type will be converted
        # into the language Tup type, for super-imposition etc. Convert the LHS into the Tup[...] type.
        restore_tuple = lhs_type
        if isinstance(lhs_type, Ast.TypeTupleAst):
            lhs_type = CommonTypes.tuple(lhs_type.types)

        # Get the scope that contains the symbol of the class definition, so that the attribute can be checked.
        class_scope = s.global_scope.get_child_scope_for_cls(lhs_type.parts[-1].identifier)

        # If the class scope doesn't exist, then the type of the variable being operated on is not a class, so throw
        # an error. todo : would this stage ever be reached? Type inference for LHS member should catch this?
        if class_scope is None:
            raise SystemExit(ErrFmt.err(ast._tok) + f"Class {lhs_type.parts[-1].identifier} not found.")

        # If the member access is a number, then perform some additional checks to ensure the LHS conforms to certain
        # type constraints, specifically regarding tuples.
        if isinstance(ast.op.identifier, Ast.NumberLiteralBase10Ast):

            # If the originally inferred type of the LHS was a not TypeTupleAst, then throw an error, as the member
            # access is trying to access a tuple index on a non-tuple type.
            if not isinstance(restore_tuple, Ast.TypeTupleAst):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Class {lhs_type.parts[-1].identifier} is not a tuple.")

            # If the tuple index is out of range, then throw an error, as the member access is trying to access a tuple
            # index that doesn't exist.
            # todo : is the negative check required?
            if int(ast.op.identifier.integer) >= len(restore_tuple.types) or int(ast.op.identifier.integer) < 0:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Tuple index {ast.op.identifier} out of range.")

            # If the tuple index is valid, then return the type of the tuple index.
            # todo : partial moves for a tuple created here
            return restore_tuple.types[int(ast.op.identifier.integer)]

        # Otherwise, the access is attribute, not index, based, so try to get the attribute from the class definition's
        # symbol table.
        try:
            return class_scope.get_symbol(ast.op.identifier.identifier).type

        # If there was an error, then the symbol, and therefore the attribute, doesn't exist.
        except:
            # It is known that the attribute doesn't exist, so simulate an IdentifierAst access on the class's scope, as
            # it will force the same errors to be thrown.
            # todo : scope is correct but error not so much
            restore_scope = s.current_scope
            s.current_scope = class_scope
            TypeInference.infer_type_of_identifier(ast.op.identifier, s, "#" in ast.op.identifier.identifier)
            s.current_scope = restore_scope

    @staticmethod
    def infer_type_of_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        ref_args = set()
        mut_args = set()
        arg_types = []

        for i, a in enumerate(ast.op.arguments):
            arg_types.append(TypeInference.infer_type_of_expression(a.value, s))

            """
            if isinstance(a.value, Ast.IdentifierAst):
                symbol = s.current_scope.get_symbol(a.value.identifier)
            else:
                lhs_type = TypeInference.infer_type_of_expression(ast.lhs, s, call=True)
                scope = s.global_scope.get_child_scope_for_cls(lhs_type.parts[-1].identifier)
                symbol = scope.get_symbol(a.value.identifier)
            """

            # todo -> double use of an identifier => moved/uninit so won't work
            # todo -> double use of attribute
            #   - check not moving from borrowed context (from borrowed object)
            #   - check not using a partialy-moved value (from owned object)

            # Prevent moving from a borrowed context by checking if there is no calling convention, and that the
            # expression is an attribute access from a symbol currently being borrowed.
            v = a.value
            if isinstance(v, Ast.PostfixExpressionAst) and isinstance(v.op, Ast.PostfixMemberAccessAst) and not a.calling_convention:
                r = v
                while isinstance(v, Ast.PostfixExpressionAst) and isinstance(v.op, Ast.PostfixMemberAccessAst):
                    r, v = v, v.lhs
                symbol = s.current_scope.get_symbol(v.identifier)
                if isinstance(v, Ast.IdentifierAst) and (symbol.borrowed_ref or symbol.borrowed_mut):
                    raise SystemExit(ErrFmt.err(r.op.identifier._tok) + f"Cannot move from a borrowed context.")

            # Check that the value to be moved is initialized, and if so, mark it as uninitialized, as it is being
            # moved into the function call.
            if isinstance(a.value, Ast.IdentifierAst) and not MemoryEnforcer.get_variable_initialized(a.value, s):
                raise SystemExit(ErrFmt.err(a.value._tok) + f"Argument '{a.value.identifier}' is not initialized or has been moved.")

            if isinstance(a.value, Ast.IdentifierAst) and a.calling_convention and a.calling_convention.is_mutable:
                symbol = s.current_scope.get_symbol(a.value.identifier)
                if not symbol.mutable:
                    raise SystemExit(ErrFmt.err(a.value._tok) + f"Cannot take a mutable reference to an immutable value.")
                if symbol.borrowed_ref:
                    raise SystemExit(ErrFmt.err(a.value._tok) + f"Cannot take a mutable reference to an immutable reference.")

                if a.value in ref_args:
                    raise SystemExit(ErrFmt.err(a.value._tok) + f"Cannot hold a mutable an immutable reference to the same value at once.")
                if a.value in mut_args:
                    raise SystemExit(ErrFmt.err(a.value._tok) + f"Cannot hold > 1 mutable references to the same value at once.")
                mut_args |= {a.value}

            elif isinstance(a.value, Ast.IdentifierAst) and a.calling_convention:
                if a.value in mut_args:
                    raise SystemExit(ErrFmt.err(a.value._tok) + f"Cannot hold a mutable an immutable reference to the same value at once.")
                ref_args |= {a.value}

            # Any argument that isn't being passed by reference is being moved, so mark the symbol (on the caller side)
            # as uninitialized, so that it can't be used again, unless it is re-initialized.
            if isinstance(a.value, Ast.IdentifierAst) and not a.calling_convention:
                MemoryEnforcer.set_variable_initialized([a.value], s, False)

        # Get to the innermost IdentifierAst (if there is one), and add the types after a "#", so the correct overload
        # of the function is called.
        # todo : other Ast types that need to be inspected in order to modify the underlying fn-call name?
        lhs = ast.lhs
        arg_conventions = [arg.calling_convention for arg in ast.op.arguments]
        while isinstance(lhs, Ast.PostfixExpressionAst) and isinstance(lhs.op, Ast.PostfixMemberAccessAst):
            self_type = TypeInference.infer_type_of_expression(lhs.lhs, s)
            lhs = lhs.op
            if isinstance(lhs.identifier, Ast.IdentifierAst):
                lhs = lhs.identifier
                lhs.identifier += f"#{','.join([convert_convention_to_string(conv) + '|' + convert_type_to_string(arg_type) for conv, arg_type in zip(arg_conventions, arg_types)])}"

                # todo : this allows an &Self to be used for &mut Self, and other memory violations
                # todo : also allows things like &Self to be used as Self - obviously wrong
                if not lhs.identifier.split("#")[1]:
                    lhs.identifier += f"???|{convert_type_to_string(self_type)}"
                else:
                    lhs.identifier = lhs.identifier.split("#")[0] + f"#???|{convert_type_to_string(self_type)}," + lhs.identifier.split("#")[1]
                break
        else:
            if isinstance(lhs, Ast.IdentifierAst):
                lhs.identifier += f"#{','.join([convert_convention_to_string(conv) + '|' + convert_type_to_string(arg_type) for conv, arg_type in zip(arg_conventions, arg_types)])}"
            else:
                print("???")

        # fn_symbol = s.current_scope.get_symbol(lhs.identifier)
        # fn_ast = fn_symbol.value
        # print("F", fn_ast)
        # fn_param_types = [p.type_annotation for p in fn_ast.parameters]
        # for g in fn_ast.generic_parameters:
        #     if g not in fn_param_types:
        #         raise SystemExit(ErrFmt.err(ast._tok) + f"Generic parameter '{g}' not cannot be inferred.")

        # Get the function type from the symbol table, and return the return type of the function, from the generic type
        # of the function ie FnRef[Output, (Args)]. The return type is the first generic argument.
        lhs_type = TypeInference.infer_type_of_expression(ast.lhs, s, call=True)
        lhs.identifier = lhs.identifier.split("#")[0]
        lhs_type = lhs_type.parts[-1].generic_arguments[0].value
        return lhs_type


    @staticmethod
    def infer_type_of_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # todo : base class field with sup=(...)

        # Check that the type of struct being initialized exists. As all types are Objects, there is no requirement to
        # check that the type is a struct type, as all types are structs.
        struct_type = TypeInference.infer_type_of_type(ast.lhs, s)

        # Get the fields that were given to the initializer, and ensure that their values are valid. The value is either
        # the provided value for the field, or the variable with an equivalent identifier to the field.
        given_fields = [f.identifier.identifier for f in ast.op.fields if isinstance(f.identifier, Ast.IdentifierAst)]
        for given_field in ast.op.fields:
            given_field = given_field.value or given_field.identifier
            TypeInference.infer_type_of_expression(given_field, s)

            # Check that the value to be moved is initialized, and if so, mark it as uninitialized, as it is being
            # moved into the function call.
            if isinstance(given_field, Ast.IdentifierAst) and not MemoryEnforcer.get_variable_initialized(given_field, s):
                raise SystemExit(ErrFmt.err(given_field._tok) + f"Argument '{given_field.identifier}' is not initialized or has been moved.")
            else:
                MemoryEnforcer.set_variable_initialized([given_field], s, False)

        # The "default_obj_given" field is a special field that is used to provide a default value for all fields not
        # given explicitly. If this field is present, then all fields not given explicitly are moved from the default
        # object to the current one. The "default_obj_given" field is given by the "else=..." syntax.
        default_obj_given = any(isinstance(f.identifier, Ast.TokenAst) and f.identifier.tok.token_type == TokenType.KwElse for f in ast.op.fields)

        # Get a list of all the fields on a struct, so that the "given_fields" can be checked against the
        # "actual_fields" to make sure all fields are given, and that no unknown fields are given.
        actual_fields = s.global_scope.get_child_scope_for_cls(struct_type.parts[-1].identifier).all_exclusive_symbols()

        # If the number of given fields is less than the number of actual fields, then not all fields have been given,
        # so display the different in sets of fields.
        if len(given_fields) < len(actual_fields) and not default_obj_given:
            raise SystemExit(ErrFmt.err(ast._tok) + f"Struct initializer for {struct_type.parts[-1].identifier} is missing fields: {set(actual_fields) - set(given_fields)}.")

        # Now it is guaranteed that the number of given fields is greater than or equal to the number of actual fields,
        # so check that all given fields are actual fields.
        if unknown_fields := set(given_fields) - set(actual_fields):
            unknown_field = unknown_fields.pop()
            unknown_field_ast = ast.op.fields[given_fields.index(unknown_field)]
            raise SystemExit(ErrFmt.err(unknown_field_ast._tok) + f"Struct initializer for '{struct_type.parts[-1].identifier}' given unknown field: '{unknown_field}'.")

        if default_obj_given:
            all_fields_value = ast.op.fields[[isinstance(f.identifier, Ast.TokenAst) and f.identifier.tok.token_type == TokenType.KwElse for f in ast.op.fields].index(True)].value
            all_fields_value_type = TypeInference.infer_type_of_expression(all_fields_value, s)
            if all_fields_value_type != struct_type:
                error = SemanticError(
                    ErrFmt.err(all_fields_value._tok) +
                    f"Struct initializer default for {struct_type.parts[-1].identifier} given a value of type {convert_type_to_string(all_fields_value_type)}.")
                raise SystemExit(error) from None

        for given, actual in zip(sorted(given_fields), sorted(actual_fields)):
            # todo : incorrect type -> should "^" sit under the "=" or the value (value not always given)
            given_value_type = TypeInference.infer_type_of_expression(ast.op.fields[given_fields.index(given)].value or s.current_scope.get_symbol(given).type, s)
            actual_value_type = s.global_scope.get_child_scope_for_cls(struct_type.parts[-1].identifier).get_symbol(actual).type
            wrong_type_value = ast.op.fields[given_fields.index(given)].value if ast.op.fields[given_fields.index(given)].value else ast.op.fields[given_fields.index(given)]
            if given_value_type != actual_value_type:
                raise SystemExit(ErrFmt.err(wrong_type_value._tok) + f"Cannot assign {convert_type_to_string(given_value_type)} to {convert_type_to_string(actual_value_type)}.")

        return struct_type

    @staticmethod
    def infer_type_of_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        # If only a type annotation is provided, and not a value, then the variable is not initialized. Mark the symbol
        # as non-initialized so that it can be checked later.
        if not ast.value:
            # The only type a variable cannot be is the void type, so check that the provided type annotation is not the
            # Void type. todo : same for class attribute types
            if ast.type_annotation == CommonTypes.void():
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot annotate a variable as Void.")

            MemoryEnforcer.set_variable_initialized(ast.variables, s, False)
            return CommonTypes.void()

        # If the variable is provided a value, but the result of the value expression is a Void type, then throw an
        # error, as the variables inferred type would be Void, but Void is the only invalid type for a variable.
        rhs_type = TypeInference.infer_type_of_expression(ast.value, s)
        if rhs_type == CommonTypes.void():
            raise SystemExit(ErrFmt.err(ast.value._tok) + f"Cannot assign Void to a variable.")

        # Prevent moving from a borrowed context
        v = ast.value
        if isinstance(v, Ast.PostfixExpressionAst) and isinstance(v.op, Ast.PostfixMemberAccessAst):
            r = v
            while isinstance(v, Ast.PostfixExpressionAst) and isinstance(v.op, Ast.PostfixMemberAccessAst):
                r, v = v, v.lhs
            symbol = s.current_scope.get_symbol(v.identifier)
            if isinstance(v, Ast.IdentifierAst) and (symbol.borrowed_ref or symbol.borrowed_mut):
                raise SystemExit(ErrFmt.err(r.op.identifier._tok) + f"Cannot move from a borrowed context.")

        # If this step is reached, then a value has been provided, as providing a type annotation or a value is mutually
        # exclusive. As a value has been provided, the variable is initialized. Mark the symbol as initialized. Mark the
        # RHS identifiers as uninitialized, as they are "moved" into the LHS identifiers.
        MemoryEnforcer.set_variable_initialized(ast.variables, s, True)

        # If the value expression being assigned to variables isn't initialized, or has been moved into another
        # variable, then is a violation of linear types - a value can only be used exactly once.
        # todo : differentiate between uninitialized and moved -- and for moved show where it was moved by using 2
        #  ErrorFormatting.error() calls concatenated
        if isinstance(ast.value, Ast.IdentifierAst) and not MemoryEnforcer.get_variable_initialized(ast.value, s):
            raise SystemExit(ErrFmt.err(ast.value._tok) + f"Variable '{ast.value.identifier}' is not initialized or has been moved.")

        MemoryEnforcer.set_variable_initialized([ast.value], s, False)

        # For a single variable being defined, set its type by inferring the expression value being assigned to it.
        if len(ast.variables) == 1:
            rhs_type = ast.type_annotation or rhs_type
            s.current_scope.get_symbol(ast.variables[0].identifier.identifier).defined = True
            s.current_scope.get_symbol(ast.variables[0].identifier.identifier).type = rhs_type

        # Otherwise, destructure a tuple into the variables being defined. The tuple type will be inferred, but is
        # subject to a number of checks / constraints to ensure type-safety.
        else:
            # Firstly ensure that the inferred type is a tuple type, as a tuple is being destructured. This is done by
            # checking the AST type.
            if not isinstance(rhs_type, Ast.TypeTupleAst):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Expected a tuple type to destructure, but found {rhs_type}.")

            # Secondly, ensure that the length of the tuple type matches the number of variables being defined. This is
            # done by checking the length of the tuple AST node. This ensures that all variables are handled.
            if len(rhs_type.types) != len(ast.variables):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot unpack a {len(rhs_type.types)}-tuple into {len(ast.variables)} variables.")

            # Finally, ensure that the type of each variable matches the type of the corresponding tuple element. This
            # is done by checking the type of each variable against the type of the corresponding tuple element.
            for i in range(len(ast.variables)):
                s.current_scope.get_symbol(ast.variables[i].identifier.identifier).defined = True
                s.current_scope.get_symbol(ast.variables[i].identifier.identifier).type = rhs_type.types[i]

        # Handle the "else" clause for the let statement. If the "else" clause is present, then the type of the "else"
        # clause must match the type of the variable being assigned to.
        if ast.if_null:
            t = TypeInference.infer_type_of_inner_scope(ast.if_null, s)

            # The returning expression from the "else" clause must be the same type as the variable being assigned to.
            # This is done by checking the type of the returning expression against the type of the variable.
            if t != rhs_type:
                raise SystemExit(ErrFmt.err(ast.if_null._tok) + f"Cannot assign {convert_type_to_string(t)} to {convert_type_to_string(rhs_type)}.")

        return CommonTypes.void()

    @staticmethod
    def infer_type_of_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        for lhs in ast.lhs:
            symbol = None
            if isinstance(lhs, Ast.IdentifierAst):
                symbol = s.current_scope.get_symbol(lhs.identifier)
            else:
                # Get the LHS but not the innermost member access, because the innermost member access is the actual
                # variable being assigned to, and the outer member accesses are just for accessing the variable.
                lhs_type = TypeInference.infer_type_of_expression(lhs.lhs, s)
                lhs_type_scope = s.global_scope.get_child_scope_for_cls(lhs_type.parts[-1].identifier)
                symbol = lhs_type_scope.get_symbol(lhs.op.identifier.identifier)
            if not symbol.mutable:
                raise SystemExit(ErrFmt.err(ast.op._tok) + f"Cannot assign to immutable variable.")

        rhs_type = TypeInference.infer_type_of_expression(ast.rhs, s)
        if rhs_type == CommonTypes.void():
            raise SystemExit(ErrFmt.err(ast.rhs._tok) + f"Cannot assign Void to a variable.")

        # Prevent moving from a borrowed context
        v = ast.rhs
        if isinstance(v, Ast.PostfixExpressionAst) and isinstance(v.op, Ast.PostfixMemberAccessAst):
            r = v
            while isinstance(v, Ast.PostfixExpressionAst) and isinstance(v.op, Ast.PostfixMemberAccessAst):
                r, v = v, v.lhs
            symbol = s.current_scope.get_symbol(v.identifier)
            if isinstance(v, Ast.IdentifierAst) and (symbol.borrowed_ref or symbol.borrowed_mut):
                raise SystemExit(ErrFmt.err(r.op.identifier._tok) + f"Cannot move from a borrowed context.")

        # Any variables on the left hand side of the assignment are now initialized. Mark them as such, so that they can
        # be checked later.
        MemoryEnforcer.set_variable_initialized(ast.lhs, s, True)

        if isinstance(ast.rhs, Ast.IdentifierAst) and not MemoryEnforcer.get_variable_initialized(ast.rhs, s):
            raise SystemExit(ErrFmt.err(ast.rhs._tok) + f"Variable '{ast.rhs.identifier}' is not initialized or has been moved.")

        MemoryEnforcer.set_variable_initialized([ast.rhs], s, False)

        # Check the LHS and RHS types are the same -- for single types, just do a simple comparison. For tuples, check
        # that the number of elements in the tuple matches the number of variables on the LHS, and that the type of
        # each element matches the type of the corresponding variable on the LHS.
        lhs_types = [TypeInference.infer_type_of_expression(l, s) for l in ast.lhs]
        if len(lhs_types) == 1 and lhs_types[0] != rhs_type:
            raise SystemExit(ErrFmt.err(ast.op._tok) + f"Cannot assign {convert_type_to_string(rhs_type)} to {convert_type_to_string(lhs_types[0])}.")

        # If there was only 1 variable and the type was valid, return Void, as assignment expression don't return
        # anything, to ensure ownership safety.
        elif len(lhs_types) == 1:
            return CommonTypes.void()

        # Otherwise, there are more than 1 variable being assigned to. Check that the RHS type is a tuple type, and that
        # the number of elements in the tuple matches the number of variables on the LHS, and that the type of each
        # element matches the type of the corresponding variable on the LHS.
        else:
            if not isinstance(rhs_type, Ast.TypeTupleAst):
                raise SystemExit(ErrFmt.err(ast.op._tok) + f"Expected a tuple type to destructure, but found {rhs_type}.")

            if len(lhs_types) != len(rhs_type.types):
                raise SystemExit(ErrFmt.err(ast.op._tok) + f"Cannot unpack a {len(rhs_type.types)}-tuple into {len(lhs_types)} variables.")

            for i in range(len(lhs_types)):
                if lhs_types[i] != rhs_type.types[i]:
                    raise SystemExit(ErrFmt.err(ast.op._tok) + f"Cannot assign {convert_type_to_string(rhs_type.types[i])} to {convert_type_to_string(lhs_types[i])}.")

        return CommonTypes.void()

    @staticmethod
    def infer_type_of_type(ast: Ast.TypeSingleAst | Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        # Check if the type exists, by checking the string representation of the type against the types in the current
        # scope (and its parent scopes). If the type doesn't exist, throw an error.
        identifier = convert_type_to_string(ast)
        if isinstance(ast, Ast.TypeTupleAst):
            for t in ast.types:
                TypeInference.infer_type_of_type(t, s)

        elif not s.current_scope.has_type(identifier) and not s.current_scope.has_type(identifier + "?"):
            raise SystemExit(ErrFmt.err(ast._tok) + f"Type '{identifier}' not found.")

        # If the type exists, return the type.
        return ast

    @staticmethod
    def infer_type_of_while_statement(ast: Ast.WhileStatementAst, s: ScopeHandler) -> Ast.TypeAst:
        # A "while" statement always returns the Void type, because it doesn't return anything. There are no "break"
        # statements, meaning that the loop will always run until the condition is false.
        s.next_scope()
        for statement in ast.body:
            TypeInference.infer_type_of_statement(statement, s)
        s.prev_scope()
        return CommonTypes.void()

    @staticmethod
    def infer_type_of_lambda(ast: Ast.LambdaAst, s: ScopeHandler) -> Ast.TypeAst:
        # todo

        TypeInference.infer_type_of_expression(ast.body, s)

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

class MemoryEnforcer:
    @staticmethod
    def set_variable_initialized(asts, s: ScopeHandler, initialized: bool) -> None:
        for ast in asts:
            if isinstance(ast, Ast.IdentifierAst):
                s.current_scope.get_symbol(ast.identifier).initialized = initialized
            elif isinstance(ast, Ast.LocalVariableAst):
                s.current_scope.get_symbol(ast.identifier.identifier).initialized = initialized
            elif isinstance(ast, Ast.TupleLiteralAst):
                for item in ast.values:
                    MemoryEnforcer.set_variable_initialized([item], s, initialized)

    @staticmethod
    def get_variable_initialized(ast, s: ScopeHandler) -> bool:
        if isinstance(ast, Ast.IdentifierAst):
            return s.current_scope.get_symbol(ast.identifier).initialized
        elif isinstance(ast, Ast.LocalVariableAst):
            return s.current_scope.get_symbol(ast.identifier.identifier).initialized
        elif isinstance(ast, Ast.TupleLiteralAst):
            # todo : check this tuple one
            for item in ast.values:
                if not MemoryEnforcer.get_variable_initialized(item, s):
                    return False
            return True
        else:
            raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot check if {ast} is initialized.")


class CompiletimeDecorators:
    ...
