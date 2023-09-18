import copy
import pprint
from difflib import SequenceMatcher
from typing import Generator, Optional, Any
import inspect

from src.LexicalAnalysis.Tokens import TokenType
from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes, VariableSymbolMemoryStatus
from src.SemanticAnalysis2.CommonTypes import CommonTypes


def enumerable_any(args: list) -> tuple[int, bool]:
    for i, arg in enumerate(args):
        if arg:
            return i, True
    return -1, False


class TypeInfer:
    @staticmethod
    def infer_expression(ast: Ast.ExpressionAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        # Match the AST node by its type, and call the appropriate function to infer the type. For example, if the AST
        # node is an identifier, call infer_identifier() to infer the type of the identifier. Literals will always
        # return the same type, so there is no need for their own special functions.

        match ast:
            case Ast.IdentifierAst():
                # Reroute to appropriate function.
                return TypeInfer.infer_identifier(ast, s)

            case Ast.LambdaAst():
                # Lambda analysis is not implemented yet.
                raise NotImplementedError("Lambda expressions are not implemented yet.")

            case Ast.IfStatementAst():
                # The return type of an "if statement" is the final statement per branch's block.
                return TypeInfer.infer_if_statement(ast, s)

            case Ast.WhileStatementAst():
                # Cannot return from a while statement, so return the std.Void type.
                return CommonTypes.void()

            case Ast.YieldStatementAst():
                # Yield statement analysis is not implemented yet.
                raise NotImplementedError("Yield expressions are not implemented yet.")

            case Ast.WithStatementAst():
                # The return type of a "with statement" is the final statement in the block.
                return TypeInfer.infer_statement(ast.body[-1], s)

            case Ast.InnerScopeAst():
                # The return type of an "inner scope" is the final statement in the block.
                return TypeInfer.infer_statement(ast.body[-1], s)

            case Ast.BinaryExpressionAst():
                # There is a complex set of operations for inferring a binary expression, so call a specific function.
                return TypeInfer.infer_binary_expression(ast, s)

            case Ast.PostfixExpressionAst():
                # There is a complex set of operations for inferring a postfix expression, so call a specific function.
                return TypeInfer.infer_postfix_expression(ast, s, **kwargs)

            case Ast.AssignmentExpressionAst():
                # Assignment always returns the std.Void type.
                return CommonTypes.void()

            case Ast.PlaceholderAst():
                # Placeholder analysis is not implemented yet.
                raise NotImplementedError("Placeholder expressions are not implemented yet.")

            case Ast.TypeSingleAst():
                # A type is already a type and doesn't need analysing, so return the type.
                return ast

            case Ast.BoolLiteralAst():
                # A boolean literal always returns the std.Bool type.
                return CommonTypes.bool()

            case Ast.StringLiteralAst():
                # A string literal always returns the std.Str type.
                return CommonTypes.str()

            case Ast.ArrayLiteralAst():
                # An array literal always returns the std.Arr type, inferring the generic type from the first element.
                return CommonTypes.arr(TypeInfer.infer_expression(ast.values[0], s))

            case Ast.RegexLiteralAst():
                # A regex literal always returns the std.Rgx type.
                return CommonTypes.rgx()

            case Ast.TupleLiteralAst():
                # A tuple literal always returns the std.Tup type, inferring the generic types from the elements.
                return CommonTypes.tup([TypeInfer.infer_expression(e, s) for e in ast.values])

            case Ast.NumberLiteralBase02Ast():
                # A binary number literal always returns the std.Num type.
                return CommonTypes.num()

            case Ast.NumberLiteralBase10Ast():
                # A decimal number literal always returns the std.Num type.
                return CommonTypes.num()

            case Ast.NumberLiteralBase16Ast():
                # A hexadecimal number literal always returns the std.Num type.
                return CommonTypes.num()

            case Ast.TokenAst() if ast.tok.token_type == TokenType.KwSelf:
                # A "self" token always returns the "Self" type (has own function as symbol discovery is required).
                return TypeInfer.infer_self(ast, s)

            case _:
                # If the AST node is not matched, then it is an unknown expression, so raise an error.
                raise SystemExit(
                    "An incorrect AST is being attempted to be type-inferred as an expression. Report as bug." +
                    ErrFmt.err(ast._tok) + f"{type(ast).__name__} is being inferred an an expression here.")

    @staticmethod
    def infer_self(ast: Ast.TokenAst, s: ScopeHandler) -> Ast.TypeAst:
        # For the "self" keyword, get the "Self" type that is created in scope when a class or super-imposition's block
        # is created in the symbol generation stage of semantic analysis.
        mock_identifier = Ast.IdentifierAst("Self", ast._tok)
        self_type_symbol = s.current_scope.get_symbol(mock_identifier, SymbolTypes.TypeSymbol)
        return self_type_symbol.type

    @staticmethod
    def infer_if_statement(ast: Ast.StatementAst, s: ScopeHandler) -> Ast.TypeAst:
        # If the if statement has branches, and the first branch has a body, then the return type will be the type of
        # the final statement in the first branch's body. There will have already been some analysis performed to ensure
        # that the return type of each branch is the same, given the if statement is being used for assignment.
        if ast.branches and ast.branches[0].body:
            return TypeInfer.infer_statement(ast.branches[0].body[-1], s)

        # Otherwise, either the if statement has no branches, or the branches return the std.Void type, so return that.
        return CommonTypes.void()

    @staticmethod
    def infer_statement(ast: Ast.StatementAst, s: ScopeHandler) -> Ast.TypeAst:
        # Match the AST node by its type, and call the appropriate function to infer the type. For example, if the AST
        # node is a return statement, call infer_return_statement() to infer the type of the return statement.

        match ast:
            case Ast.TypedefStatementAst():
                # Typedef statements don't manage variables, so the return type will always be the std.Void type.
                return CommonTypes.void()

            case Ast.ReturnStatementAst():
                # The type of a return statement is the type of the expression being returned, or std.Void.
                return TypeInfer.infer_expression(ast.value, s) if ast.value else CommonTypes.void()

            case Ast.LetStatementAst():
                # The type of a let statement is std.Void.
                return CommonTypes.void()

            case Ast.FunctionPrototypeAst():
                # todo : surely this should be the function prototype type ie std.FnRef[...] ?
                return CommonTypes.void()

    @staticmethod
    def infer_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # todo : this is currently a duplicate of SemanticAnalysis.analyse_binary_expression()

        # Remodel the binary expression into a function call, then analyse the function call. Start with constructing a
        # postfix call to the correct method name. For example, for "x + y", begin with constructing "x.add".
        pos = ast._tok
        fn = Ast.IdentifierAst(Ast.BIN_FN[ast.op.tok.token_type], pos)
        fn = Ast.PostfixMemberAccessAst(fn, pos)
        fn = Ast.PostfixExpressionAst(ast.lhs, fn, pos)

        # Next, convert the right-hand side into a function argument, and construct the function call. The function call
        # creates the "(y)" that is the postfix expression for "x.add", creating "x.add(y)". This is then analysed.
        rhs = Ast.FunctionArgumentAst(None, ast.rhs, None, False, pos)
        fn_call = Ast.PostfixFunctionCallAst([], [rhs], pos)
        fn_call = Ast.PostfixExpressionAst(fn, fn_call, pos)

        return TypeInfer.infer_expression(fn_call, s)

    @staticmethod
    def infer_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        # Match the AST node by its type, and call the appropriate function to infer the type. For example, if the AST
        # node is a member access, call infer_postfix_member_access() to infer the type of the member access.

        match ast.op:
            case Ast.PostfixMemberAccessAst():
                # Reroute to appropriate function.
                return TypeInfer.infer_postfix_member_access(ast, s, **kwargs)

            case Ast.PostfixFunctionCallAst():
                # Reroute to appropriate function.
                return TypeInfer.infer_postfix_function_call(ast, s)[1]

            case Ast.PostfixStructInitializerAst():
                # Reroute to appropriate function.
                return TypeInfer.infer_postfix_struct_initializer(ast, s)

            case _:
                # If the AST node is not matched, then it is an unknown postfix expression, so raise an error.
                raise SystemExit(
                    "An incorrect AST is being attempted to be type-inferred as a postfix expression. Report as bug." +
                    ErrFmt.err(ast._tok) + f"{type(ast).__name__} is being inferred an an postfix expression here.")

    @staticmethod
    def infer_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        # Get the type of the expression on the left of the right-most-dot (this could recursively call this method),
        # and then get the class scope for this type in the symbol table.
        ty = TypeInfer.infer_expression(ast.lhs, s)
        type_scope = s.global_scope.get_child_scope(ty)

        # If the rhs of the right-most-dot is an identifier, then enter the first branch, which handles attribute access
        # into a type.
        if isinstance(ast.op.identifier, Ast.IdentifierAst):
            attribute_symbol = type_scope.get_symbol_exclusive(ast.op.identifier, SymbolTypes.VariableSymbol)
            return attribute_symbol.type

        # Otherwise, the rhs of the right-most-dot is a number, which means a tuple's generics are being indexed for
        # some nth type.
        elif isinstance(ast.op.identifier, Ast.NumberLiteralBase10Ast):
            index = int(ast.op.identifier.integer)
            return ty.parts[-1].generic_arguments[index]

        else:
            raise SystemExit(
                "An incorrect AST is being attempted to be type-inferred as a postfix member access. Report as bug." +
                ErrFmt.err(ast._tok) + f"{type(ast).__name__} is being inferred an an postfix member access here.")

    @staticmethod
    def infer_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> tuple[Optional[SymbolTypes.VariableSymbol], Ast.TypeAst]:
        if type(ast.lhs) in Ast.TypeAst.__args__:
            raise SystemExit(
                "Cannot call a type. Try using the struct initializer syntax instead." +
                ErrFmt.err(ast._tok) + f"Type '{ast.lhs}' is being called here.")


        # A special method is a "__" prefixed method. It requires special behaviour in certain circumstances as seen
        # later on in this method.
        is_special_function = isinstance(ast.lhs, Ast.IdentifierAst) and ast.lhs.identifier in ["__set__", "__assign__"]

        # The "__set__" special method is used for the "let statement", to allow mock analysis for modelling it as a
        # function, but as this function doesn't actually exist, no analysis needs to be performed. Instead, return a
        # None symbol and the std.Void type.
        if isinstance(ast.lhs, Ast.IdentifierAst) and ast.lhs.identifier == "__set__":
            return None, CommonTypes.void()

        # The "__assign__" special method is used for the "assignment expression", to allow mock analysis for modelling
        # it as a function. Create the mock function prototype.
        if isinstance(ast.lhs, Ast.IdentifierAst) and ast.lhs.identifier == "__assign__":
            fn_proto = Ast.FunctionPrototypeAst([], False, Ast.IdentifierAst("__assign__", -1), [], [
                Ast.FunctionParameterAst(True, False, Ast.IdentifierAst("self", -1), Ast.ParameterPassingConventionReferenceAst(True, -1), TypeInfer.infer_expression(ast.op.arguments[0].value, s), None, False, -1),
                Ast.FunctionParameterRequiredAst(False, Ast.IdentifierAst("value", -1), None, TypeInfer.infer_expression(ast.op.arguments[0].value, s), -1)
            ], CommonTypes.void(), None, Ast.FunctionImplementationAst([], -1), -1)
            function_prototypes = [fn_proto]
            default_generic_map = {}

        # Otherwise, perform a number of operations to obtain the existing function prototypes, and handle some generic
        # operations too.
        else:
            # Infer the lhs of the function call, getting the object that has the overloads on. For example, a() would
            # get the __MOCK_a type. Get the symbol for the __MOCK_a class. Get all the "call_[ref|mut|one]" functions
            # on the overload manager. Store the corresponding function prototype ASTs in a list.
            overload_manager_ty = TypeInfer.infer_expression(ast.lhs, s, all=True)
            overload_manager_scope = s.global_scope.get_child_scope(overload_manager_ty)
            overload_symbols = [x for x in overload_manager_scope.all_symbols_exclusive(SymbolTypes.VariableSymbol) if x.name.identifier in ["call_ref", "call_mut", "call_one"]]
            function_prototypes = [f.meta_data["fn_proto"] for f in overload_symbols]

            # Construct the default generic map. Pull in proceeding postfix expressions' generic maps for fallthrough,
            # so that generic types on owner classes etc can be used etc. ie Vec[Str].new() can pull [T -> Str].
            current_lhs = ast.lhs
            default_generic_map = {}
            while type(current_lhs) == Ast.PostfixExpressionAst: # and type(current_lhs.op) == Ast.PostfixMemberAccessAst:
                default_generic_map |= {g: h for g, h in current_lhs.op.generic_map.items() if h}
                current_lhs = current_lhs.lhs

        # Get all the argument types, and the argument calling conventions. The types are inferred from the value of the
        # arguments, and the calling conventions are members of the argument ASTs.
        argument_tys = [TypeInfer.infer_expression(arg.value, s) for arg in ast.op.arguments]
        argument_ccs = [arg.calling_convention for arg in ast.op.arguments]

        # Create some lists to store function signatures and errors to display later if there's an error.
        sigs = []
        errs = []

        # Create copies of the original call arguments, argument types, and argument calling conventions. These are
        # used later on to reset the function call's arguments, types, and calling conventions, so that the next
        # function prototype can be checked.
        original_call_arguments = ast.op.arguments.copy()
        original_args_tys = argument_tys.copy()
        original_args_ccs = argument_ccs.copy()

        # Create a list to store all valid overloads in -- this is so that the list can be scanned and ordered based on
        # how constraining the parameters are, in order to select the most constraining overload.
        valid_overloads = []

        # Check each overload in the function prototypes list.
        for i, fn_type in enumerate(function_prototypes):

            # Create local copies of the generic map, call arguments, argument types, and argument calling conventions.
            # These are used to check the current function prototype, and are reset after each check.
            ast.op.generic_map = default_generic_map.copy()
            ast.op.arguments = original_call_arguments.copy()
            argument_tys = original_args_tys.copy()
            argument_ccs = original_args_ccs.copy()

            # Get the parameter names, types, and calling conventions from the function prototype. These are required,
            # to be checked against their argument counterparts.
            param_names = [param.identifier.identifier for param in fn_type.parameters]
            param_tys = [param.type_annotation for param in fn_type.parameters]
            param_ccs = [param.calling_convention for param in fn_type.parameters]

            num_required_parameters = len([p for p in fn_type.parameters if p.is_required()])

            # Stringify the function prototype, and add it to the list of function signatures to display later if there
            # is an error.
            str_fn_type = str(fn_type)
            str_fn_type_substring_index = [i for i, char in enumerate(str_fn_type) if char in ["[", "("]][0]
            str_fn_type = str(ast.lhs) + str_fn_type[str_fn_type_substring_index:].strip()
            sigs.append(str_fn_type)

            # Check function generics
            all_generic_parameters = fn_type.generic_parameters
            given_generic_arguments = ast.op.type_arguments
            required_generic_parameters = TypeInfer.required_generic_parameters_for_fun(fn_type, s)
            missing_generic_parameters = required_generic_parameters[len(given_generic_arguments):]
            unpack = all_generic_parameters and all_generic_parameters[-1].is_variadic

            if len(given_generic_arguments) > len(all_generic_parameters) and not unpack:
                errs.append(f"Too many generic arguments given to function '{fn_type}'.")
                continue

            if len(given_generic_arguments) < len(required_generic_parameters):
                errs.append(f"Not enough generic arguments given to function '{fn_type}'. Missing {[str(t) for t in missing_generic_parameters]}.")
                continue

            # Add the generic parameters of the function to the generic map (as None)
            for g in all_generic_parameters:
                ast.op.generic_map[g.identifier] = None

            # Add the explicit generic arguments to the generic map. This means that for "func[T](...)", calling
            # "func[Str](...)" will map add {"T": "Str"} in the generic map.
            for j, g in enumerate(all_generic_parameters[:len(given_generic_arguments)]):
                explicit_generic_argument = given_generic_arguments[j]
                ast.op.generic_map[g.identifier] = explicit_generic_argument.value

            # Skip first argument type for non-static functions - todo?
            if not is_special_function:
                if overload_symbols[i].meta_data.get("is_method", False) and overload_symbols[i].meta_data.get("fn_proto").parameters and overload_symbols[i].meta_data.get("fn_proto").parameters[0].is_self:
                    argument_tys.insert(0, TypeInfer.infer_expression(ast.lhs.lhs, s))
                    argument_ccs.insert(0, copy.deepcopy(param_ccs[0]))
                    ast.op.arguments.insert(0, Ast.FunctionArgumentAst(None, ast.lhs.lhs, copy.deepcopy(param_ccs[0]), False, -1))

                # Check if the function is callable with the number of given arguments.
                if len(argument_tys) != num_required_parameters:
                    errs.append(f"Expected {len(param_tys)} arguments, but got {len(argument_tys)}.")
                    continue

            # Check if the function is callable with the given argument types.
            checks = [TypeInfer.types_equal_account_for_generic(param_ty, arg_ty, ast.op.generic_map, s) for i, (arg_ty, param_ty) in enumerate(zip(argument_tys, param_tys))]
            if any([not c[0] for c in checks]):
                error = [c[1] for c in checks if not c[0]][0]
                errs.append(error)
                continue

            # Check the calling conventions match. A &mut argument cal collapse into an & parameter, but the __eq__
            # implementation handles this.
            if any([arg_cc != param_cc for arg_cc, param_cc in zip(argument_ccs, param_ccs)]):
                mismatch_index = [i for i, (arg_cc, param_cc) in enumerate(zip(argument_ccs, param_ccs)) if arg_cc != param_cc][0]
                errs.append(f"Expected argument {mismatch_index + 1} to be passed by '{param_ccs[mismatch_index]}', but got '{argument_ccs[mismatch_index]}'.")
                continue

            # Add the generic map from any previous member accesses into this one too.
            return_type = copy.deepcopy(fn_type.return_type)
            for g, h in ast.op.generic_map.items():
                TypeInfer.substitute_generic_type(return_type, g, h)
            ast.op.arguments = original_call_arguments
            if not is_special_function:
                valid_overloads.append((overload_symbols[i], return_type))
            else:
                valid_overloads.append((None, return_type))

        # Selection of the most constraining overload will occur here
        # todo : implement this
        if valid_overloads:

            # If there is only one valid overload, then return it.
            if len(valid_overloads) == 1:
                return valid_overloads[0]

            # The most constraining is the overload with the least number of parameters whose types are generic types.
            # This is because the generic types are the least constraining, as they can be any type, and fixed types are
            # the most constraining, as they can only be one type.
            else:
                print("-" * 100)
                pprint.pprint([str(x.meta_data["fn_proto"]) for x in [x[0] for x in valid_overloads]])
                generic_param_counts = []

                # todo (for now) return first overload
                return valid_overloads[0]


        ast.op.arguments = original_call_arguments

        NL = "\n\t- "
        sigs.insert(0, "")
        errs.insert(0, "")
        output = []
        for i in range(len(sigs)):
            output.append(f"{sigs[i]}: {errs[i]}")

        # todo : improve the "attempted signature" line of the error message to include the parameter named with their
        #  incorrect types
        raise SystemExit(
            ErrFmt.err(ast.lhs._tok) + f"Could not call function '{ast.lhs}' with the given generics and arguments.\n\n" +
            f"Attempted signature:{NL}{str(ast.lhs)}({', '.join([str(arg_cc or '') + str(arg_ty) for arg_cc, arg_ty in zip(argument_ccs, argument_tys)])}) -> ?\n\n" +
            f"Available signatures{NL.join(output)}")

    @staticmethod
    def infer_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        if ast.op.generic_map:
            generics = list(ast.op.generic_map.values())
        else:
            generics = [a.value for a in ast.lhs.parts[-1].generic_arguments]

        struct_type = copy.deepcopy(TypeInfer.infer_expression(ast.lhs, s))
        struct_type.parts[-1].generic_arguments = [Ast.TypeGenericArgumentAst(None, v, -1) for v in generics]
        return struct_type

    @staticmethod
    def infer_identifier(ast: Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInfer.likely_symbols(ast, SymbolTypes.VariableSymbol, "identifier", s)

    @staticmethod
    def check_type(ast: Ast.TypeAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        if isinstance(ast, Ast.TypeGenericArgumentAst):
            ast = ast.value

        # Check generic arguments given to the type
        try:
            sym = s.current_scope.get_symbol(ast.to_identifier(), SymbolTypes.TypeSymbol)
        except Exception as e:
            extra = " Did you mean to declare it as a generic?" if len(str(ast)) == 1 else ""
            raise SystemExit(
                f"Could not find type symbol '{ast.to_identifier()}':" +
                ErrFmt.err(ast._tok) + f"Type '{ast}' used here." + extra)

        if kwargs.get("check_generics", True):
            given_generic_arguments = ast.parts[-1].generic_arguments
            actual_generic_parameters = sym.type.generic_parameters.copy() if isinstance(sym.type, Ast.ClassPrototypeAst) else []

            for g in given_generic_arguments:
                TypeInfer.check_type(g, s)

            if len(given_generic_arguments) > len(actual_generic_parameters):
                if actual_generic_parameters and actual_generic_parameters[-1].is_variadic:
                    pass
                else:
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Too many generic arguments given to type '{sym.type.to_type()}'.")
            required_generic_parameters = [p for p in actual_generic_parameters if not (p.default or p.is_variadic)]
            if len(given_generic_arguments) < len(required_generic_parameters):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Not enough generic arguments given to type '{sym.type.to_type()}'. Missing {[str(g) for g in actual_generic_parameters]}.")

        return TypeInfer.likely_symbols(ast, SymbolTypes.TypeSymbol, "type", s)

    @staticmethod
    def required_generic_parameters_for_cls(ast: Ast.TypeSingleAst | Ast.ClassPrototypeAst, s: ScopeHandler) -> list[Ast.TypeGenericParameterAst]:
        # Generic parameters can be inferred, for a class, if they are:
        #   - The type, or part of the type, of an attribute.
        #   - Part of another generic type.

        if isinstance(ast, Ast.TypeSingleAst):
            sym = s.current_scope.get_symbol(ast.to_identifier(), SymbolTypes.TypeSymbol)
            if sym is None or isinstance(sym.type, Ast.TypeSingleAst): return []
            ast = sym.type
            generics = sym.type.generic_parameters.copy()
        else:
            generics = ast.generic_parameters.copy() # todo : other parts of the type ie Vec[T].Value[X]. T would be missing here (just flatten all parts' generics)

        generics_names = [g.identifier for g in generics]
        sym = s.global_scope.get_child_scope(ast.to_type())


        # For each attribute of the class, if the type is the generic or composes the generic ie Vec[T], then the type
        # is inferrable, and is therefore not required. Remove it from the list of required generics.

        attrs = sym.all_symbols_exclusive(SymbolTypes.VariableSymbol)
        for attr_name, attr_type in [(attr.name, attr.type) for attr in attrs]:
            for t in TypeInfer.traverse_type(attr_type, s):
                t = t[0]
                if t in generics_names:
                    generics.pop(generics_names.index(t))
                    generics_names.remove(t)
        return generics

    @staticmethod
    def required_generic_parameters_for_fun(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> list[Ast.TypeGenericParameterAst]:
        # Generic parameters can be inferred, for a function, if they are:
        #   - The type, or part of the type, of a parameter.
        #   - Part of another generic type.
        generics = ast.generic_parameters.copy()
        generics_names = [g.identifier for g in generics]

        for ty in [param.type_annotation for param in ast.parameters]:
            for t in TypeInfer.traverse_type(ty, s):
                t = t[0]
                if t in generics_names:
                    generics.pop(generics_names.index(t))
                    generics_names.remove(t)
        return generics

    @staticmethod
    def traverse_type(ast: Ast.TypeAst | Ast.GenericIdentifierAst, s: ScopeHandler) -> Generator[tuple[Ast.IdentifierAst, int], None, None]:
        def inner(ast, s, level) -> Generator[tuple[Ast.IdentifierAst, int], None, None]:
            match ast:
                case Ast.GenericIdentifierAst():
                    yield ast.to_identifier(), level
                    for t in ast.generic_arguments:
                        yield from inner(t, s, level + 1)
                case Ast.TypeSingleAst():
                    yield ast.to_identifier(), level
                    for t in ast.parts:
                        yield from inner(t, s, level + 1)
                case Ast.TypeGenericArgumentAst():
                    yield from inner(ast.value, s, level + 1)
                case Ast.TypeGenericParameterAst():
                    yield ast.identifier, level
                case Ast.TypeTupleAst():
                    for t in ast.types:
                        yield from inner(t, s, level + 1)
                # case Ast.SelfTypeAst():
                #     sym = s.current_scope.get_symbol(Ast.IdentifierAst("Self", ast._tok), SymbolTypes.TypeSymbol)
                #     yield sym.type.parts[-1].identifier, level
                case _:
                    print(" -> ".join(list(reversed([f.frame.f_code.co_name for f in inspect.stack()]))))
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Type '{type(ast).__name__}' not yet supported for traversal. Report as bug.")
        yield from inner(ast, s, 0)


    @staticmethod
    def infer_type(ast: Ast.TypeAst, s: ScopeHandler) -> Ast.TypeAst:
        return ast

    @staticmethod
    def likely_symbols(ast: Ast.IdentifierAst | Ast.TypeAst, sym_ty: type, what: str, s: ScopeHandler) -> Ast.TypeAst:
        # If the symbol isn't in the current of any parent scope, then it doesn't exist, so throw an error, and give any
        # possible matches.
        # check = s.current_scope.has_symbol(ast if isinstance(ast, Ast.IdentifierAst) else ast.parts[-1] if isinstance(ast, Ast.TypeSingleAst) else ast.identifier, sym_ty)
        # check = SemanticAnalysis.analyse_identifier(ast if isinstance(ast, Ast.IdentifierAst) else ast.parts[-1] if isinstance(ast, Ast.TypeSingleAst) else ast.identifier, s, no_throw=True)
        if isinstance(ast, Ast.TypeSingleAst):
            ast = ast.to_identifier()

        check = False
        if sym_ty == SymbolTypes.VariableSymbol:
            check = not s.current_scope.has_symbol(ast, SymbolTypes.VariableSymbol)# and not s.current_scope.has_symbol("__MOCK_" + ast, SymbolTypes.TypeSymbol)
        elif sym_ty == SymbolTypes.TypeSymbol:
            check = not s.current_scope.has_symbol(ast, SymbolTypes.TypeSymbol)

        if check:
            # Get all the variable symbols that are in the scope. Define the most likely to be "-1" so that any symbol
            # will be more likely than it.

            similar_symbols = [sym for sym in s.current_scope.all_symbols(sym_ty) if type(sym) == sym_ty]

            most_likely = (-1.0, "")
            ast_identifier = ast.identifier if isinstance(ast, Ast.IdentifierAst) else str(ast)

            # Iterate through each symbol, and find the one that is most similar to the identifier.
            for sym in similar_symbols:
                if sym.name.identifier.startswith("__") or sym.name.identifier in ["call_ref", "call_mut", "call_one"]:
                    continue

                # Get the ratio of similarity between the identifier and the symbol name.
                ratio = max([
                    SequenceMatcher(None, sym.name.identifier, ast_identifier).ratio(),
                    SequenceMatcher(None, ast_identifier, sym.name.identifier).ratio()])

                # If the ratio is higher than the current most likely, then replace the most likely with the new symbol.
                # If the ratios are the same, do a length comparison, and keep the one closest to the length of the
                # identifier. Same length identifiers don't matter -- the first one is kept.
                if ratio > most_likely[0]:
                    most_likely = (ratio, sym.name.identifier)
                elif ratio == most_likely[0] and abs(len(sym.name.identifier) - len(ast_identifier)) < abs(len(most_likely[1]) - len(ast_identifier)):
                    most_likely = (ratio, sym.name.identifier)

            if most_likely[0] != -1:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown {what} '{ast}'. Did you mean '{most_likely[1]}'?")
            else:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown {what} '{ast}'.")

        if sym_ty == SymbolTypes.VariableSymbol:
            return s.current_scope.get_symbol(ast, SymbolTypes.VariableSymbol, error=False).type
        return s.current_scope.get_symbol(ast, SymbolTypes.TypeSymbol).type

    @staticmethod
    def types_equal_account_for_generic(t1: Ast.TypeAst, t2: Ast.TypeAst, generic_map: dict[Ast.IdentifierAst, Ast.TypeAst], s: ScopeHandler) -> tuple[bool, str]:
        if isinstance(t1, Ast.TypeSingleAst) and isinstance(t2, Ast.TypeSingleAst):
            # t1 will be something like "T", so simplify it down to an identifier AST.
            lhs_generic_type = t1.to_identifier()

            # Recursively do this for the generic arguments of the type
            for i, (a1, a2) in enumerate(zip(t1.parts[-1].generic_arguments, t2.parts[-1].generic_arguments)):
                tests = [TypeInfer.types_equal_account_for_generic(a1.value, a2.value, generic_map, s)]
                if not tests[0][0]:
                    return False, tests[0][1]

            # Non-Generic
            # If the LHS is not a generic type parameter, then the LHS requires a direct match to the RHS. For
            # example, 'Str' must match 'Str'. The parameter and arguments are direct type matches.
            if lhs_generic_type not in generic_map.keys() and not t1.subtype_match(t2, s):
                error = f"Expected type '{t1}', but got type '{t2}'. These types are not equal, and not linked by super-imposition."
                return False, error

            # Bound Generic
            # If the LHS is in the generic map, but the RHS type argument is not the correct (ie it is already known
            # that 'T' is 'Str', but 'T' is being rebound as 'Num'), then instead of return this specific error.
            elif generic_map.get(lhs_generic_type, None) and not generic_map[lhs_generic_type].subtype_match(t2, s):
                error = f"Generic type '{t1}' is already bound to '{generic_map[lhs_generic_type]}', but is being re-bound to '{t2}'."
                return False, error

            # Unbound Generic
            # If the LHS is an "unbound" generic, ie it's the first occurrence of an inferrable generic, then add it to
            # the generic map, and bind it to the RHS type argument.
            elif lhs_generic_type in generic_map.keys():
                generic_map[lhs_generic_type] = t2
                orig_t1 = copy.deepcopy(t1)
                TypeInfer.substitute_generic_type(t1, t1, generic_map[lhs_generic_type])


        # todo : untested with tuples:
        elif isinstance(t1, Ast.TypeTupleAst) and isinstance(t2, Ast.TypeTupleAst):
            tests = [TypeInfer.types_equal_account_for_generic(t1, t2, generic_map, s) for t1, t2 in zip(t1.types, t2.types)]
            if all([t[0] for t in tests]):
                return True, ""
            else:
                return False, tests[0][1]

        else:
            raise SystemExit(ErrFmt.err(t1._tok) + f"[0] Unknown 'Ast.{type(t2).__name__}' being inferred. Report as bug.")

        return True, ""

    @staticmethod
    def substitute_generic_type(ty: Any, q1: Ast.TypeSingleAst, q2: Ast.TypeSingleAst):
        # if isinstance(ty, Ast.IdentifierAst):
        #     if ty == q1:
        #         ty.identifier = q2.identifier
        # elif isinstance(ty, Ast.TypeGenericArgumentAst):
        #     TypeInfer.substitute_generic_type(ty.value, q1, q2)
        # elif isinstance(ty, Ast.GenericIdentifierAst):
        #     if ty.to_identifier() == q1:
        #         ty.identifier = q2.identifier
        #     for j, q in enumerate(ty.generic_arguments):
        #         TypeInfer.substitute_generic_type(q, q1, q2)
        if isinstance(ty, Ast.TypeSingleAst):
            # for i, p in enumerate(ty.parts):
            #     TypeInfer.substitute_generic_type(p, q1, q2)
            if ty == q1:
                ty.parts = q2.parts

        elif isinstance(ty, Ast.TypeTupleAst):
            for p in ty.types:
                TypeInfer.substitute_generic_type(p, q1, q2)
        elif ty is None:
            pass
        else:
            print(" -> ".join(list(reversed([f.frame.f_code.co_name for f in inspect.stack()]))))
            raise SystemExit(ErrFmt.err(ty._tok) + f"[1] Unknown 'Ast.{type(ty).__name__}' being inferred. Report as bug.")
