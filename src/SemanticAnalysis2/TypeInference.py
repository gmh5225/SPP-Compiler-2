import copy
from difflib import SequenceMatcher
from typing import Generator
import inspect

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes
from src.SemanticAnalysis2.CommonTypes import CommonTypes


def enumerable_any(args: list) -> tuple[int, bool]:
    for i, arg in enumerate(args):
        if arg:
            return i, True
    return -1, False


class TypeInfer:
    @staticmethod
    def infer_expression(ast: Ast.ExpressionAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst(): return TypeInfer.infer_identifier(ast, s)
            case Ast.LambdaAst(): raise NotImplementedError("Lambda expressions are not implemented yet.")
            case Ast.IfStatementAst(): return TypeInfer.infer_if_statement(ast, s)
            case Ast.WhileStatementAst(): return CommonTypes.void()
            case Ast.YieldStatementAst(): raise NotImplementedError("Yield expressions are not implemented yet.")
            case Ast.WithStatementAst(): return TypeInfer.infer_statement(ast.body[-1], s)
            case Ast.InnerScopeAst(): return TypeInfer.infer_statement(ast.body[-1], s)
            case Ast.BinaryExpressionAst(): return TypeInfer.infer_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): return TypeInfer.infer_postfix_expression(ast, s, **kwargs)
            case Ast.AssignmentExpressionAst(): return CommonTypes.void()
            case Ast.PlaceholderAst(): raise NotImplementedError("Placeholder expressions are not implemented yet.")
            case Ast.TypeSingleAst(): return ast
            case Ast.BoolLiteralAst(): return CommonTypes.bool()
            case Ast.StringLiteralAst(): return CommonTypes.string()
            case Ast.ArrayLiteralAst(): return CommonTypes.array(TypeInfer.infer_expression(ast.values[0], s))
            case Ast.RegexLiteralAst(): return CommonTypes.regex()
            case Ast.TupleLiteralAst(): return CommonTypes.tuple([TypeInfer.infer_expression(e, s) for e in ast.values])
            case Ast.NumberLiteralBase02Ast(): return CommonTypes.num()
            case Ast.NumberLiteralBase10Ast(): return CommonTypes.num()
            case Ast.NumberLiteralBase16Ast(): return CommonTypes.num()
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown expression {ast} being inferred. Report as bug.")

    @staticmethod
    def infer_if_statement(ast: Ast.StatementAst, s: ScopeHandler) -> Ast.TypeAst:
        if ast.branches and ast.branches[0].body:
            return TypeInfer.infer_statement(ast.branches[0].body[-1], s)
        return CommonTypes.void()

    @staticmethod
    def infer_statement(ast: Ast.StatementAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast:
            case Ast.TypedefStatementAst(): return CommonTypes.void()
            case Ast.ReturnStatementAst(): return TypeInfer.infer_expression(ast.value, s) if ast.value else CommonTypes.void()
            case Ast.LetStatementAst(): return CommonTypes.void()
            case Ast.FunctionPrototypeAst(): return CommonTypes.void()

    @staticmethod
    def infer_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # Remodel the binary expression into a function call, then analyse the function call. Start with constructing a
        # postfix call to the correct method name. For example, for "x + y", begin with constructing "x.add".
        pos = ast._tok
        fn = Ast.IdentifierAst(Ast.BIN_FN[ast.op.tok.token_type], pos)
        fn = Ast.PostfixMemberAccessAst(fn, pos)
        fn = Ast.PostfixExpressionAst(ast.lhs, fn, pos)

        # Next, convert the right-hand side into a function argument, and construct the function call. The function call
        # creates the "(y)" that is the postfix expression for "x.add", creating "x.add(y)". This is then analysed.
        rhs = Ast.FunctionArgumentAst(None, ast.rhs, Ast.ParameterPassingConventionReferenceAst(False, pos), False, pos)
        fn_call = Ast.PostfixFunctionCallAst([TypeInfer.infer_expression(ast.rhs, s)], [rhs], pos)
        fn_call = Ast.PostfixExpressionAst(fn, fn_call, pos)

        return TypeInfer.infer_expression(fn_call, s)

    @staticmethod
    def infer_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        match ast.op:
            case Ast.PostfixMemberAccessAst(): return TypeInfer.infer_postfix_member_access(ast, s, **kwargs)
            case Ast.PostfixFunctionCallAst(): return TypeInfer.infer_postfix_function_call(ast, s)
            case Ast.PostfixStructInitializerAst(): return TypeInfer.infer_postfix_struct_initializer(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown postfix expression {ast} being inferred. Report as bug.")

    @staticmethod
    def infer_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs) -> Ast.TypeAst:
        ty = None
        if isinstance(ast, Ast.PostfixExpressionAst) and isinstance(ast.op, Ast.PostfixMemberAccessAst):
            match ast.lhs:
                case Ast.PostfixExpressionAst(): ty = TypeInfer.infer_postfix_member_access(ast.lhs, s)
                case Ast.IdentifierAst(): ty = TypeInfer.infer_identifier(ast.lhs, s)
                case _: ty = TypeInfer.infer_type(ast.lhs, s)

        if isinstance(ast, Ast.IdentifierAst):
            ty = TypeInfer.infer_identifier(ast, s)
        elif isinstance(ast, Ast.PostfixExpressionAst) and isinstance(ast.lhs, Ast.TypeSingleAst):
            sym = s.current_scope.get_symbol(ast.lhs.parts[-1], SymbolTypes.TypeSymbol)
            generic_parameters = sym.type.generic_parameters
            generic_arguments  = ast.lhs.parts[-1].generic_arguments
            for g, a in zip(generic_parameters, generic_arguments):
                ast.op.generic_map[g.identifier.identifier] = a.value

        ty = TypeInfer.infer_type(ty, s)
        cls = s.global_scope.get_child_scope(ty)

        if isinstance(ast.op.identifier, Ast.IdentifierAst):
            sym = cls.get_symbol_exclusive(ast.op.identifier, SymbolTypes.VariableSymbol, error=False)
            if isinstance(sym, SymbolTypes.VariableSymbol):
                return sym.type
            return sym
        else:
            ty = TypeInfer.infer_expression(ast.lhs, s)
            sym = s.current_scope.get_symbol(ast.lhs.parts[-1], SymbolTypes.TypeSymbol)
            return ty.parts[-1].generic_arguments[int(ast.op.identifier.integer)]

    @staticmethod
    def infer_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        scope = s
        if isinstance(ast.lhs, Ast.IdentifierAst) and ast.lhs.identifier == "__set__":
            return CommonTypes.void()

        # Generics
        # print(ast.op.type_arguments)

        # To infer something like x.y.z(a, b), we need to infer x.y.z, then infer a and b, then infer the function call.


        arg_tys = [TypeInfer.infer_expression(arg.value, s) for arg in ast.op.arguments]
        arg_ccs = [arg.calling_convention for arg in ast.op.arguments]

        # The next step is because overloads of functions can return different types ie: 'f(Str) -> Num' and
        # 'f(Int) -> Str' can be overloads of 'f'. We need to find the function that matches the arguments, and return
        # the return type of that function.

        # Get the function symbol from the scope.
        sigs = []
        errs = []

        ty = TypeInfer.infer_expression(ast.lhs, s, all=True)
        s = s.global_scope.get_child_scope(ty)
        if not s: # todo -> this error should be picked up in SemanticAnalysis?
            raise SystemExit(ErrFmt.err(ast.lhs._tok) + f"Unknown method '{ast.lhs}(...)'.")

        l = ast.lhs
        default_generic_map = {}
        while type(l) == Ast.PostfixExpressionAst and type(l.op) == Ast.PostfixMemberAccessAst:
            for g, h in l.op.generic_map.items():
                if h:
                    default_generic_map[g] = h
            l = l.lhs
        if type(l) == Ast.IdentifierAst:
            ty = TypeInfer.infer_identifier(l, scope)
            sym = s.get_symbol(ty.parts[-1], SymbolTypes.TypeSymbol)
            if isinstance(sym.type, Ast.ClassPrototypeAst):
                generic_parameters = sym.type.generic_parameters
                generic_arguments  = ty.parts[-1].generic_arguments
                default_generic_map = {gp.identifier.identifier: ga.value for gp, ga in zip(generic_parameters, generic_arguments)}
            else:
                default_generic_map = {}  # todo: ?

        # Analyse each overload for a potential match
        overloads = [x for x in s.all_symbols_exclusive(SymbolTypes.VariableSymbol) if x.name.identifier in ["call_ref", "call_mut", "call_one"]]
        for i, fn_type in enumerate([f.meta_data["fn_proto"] for f in overloads]):
            # Load the generic map
            ast.op.generic_map = default_generic_map
            gs = fn_type.generic_parameters
            for g in gs:
                ast.op.generic_map[g.identifier.identifier] = None

            param_names = [param.identifier.identifier for param in fn_type.parameters]
            param_tys = [param.type_annotation for param in fn_type.parameters]
            param_ccs = [param.calling_convention for param in fn_type.parameters]

            str_fn_type = str(fn_type)
            str_fn_type = str_fn_type[str_fn_type.index("("):].strip()
            sigs.append(str_fn_type)

            # Skip first argument type for non-static functions
            if overloads[i].meta_data.get("is_method", False) and not overloads[i].meta_data.get("is_static", False):
                param_tys = param_tys[1:]
                param_ccs = param_ccs[1:]

            # Check if the function is callable with the number of given arguments.
            if len(param_tys) != len(arg_tys):
                errs.append(f"Expected {len(param_tys)} arguments, but got {len(arg_tys)}.")
                continue

            # Check if the function is callable with the given argument types.

            # substituted_param_tys = [copy.deepcopy(param_ty) for param_ty in param_tys]
            # for g, h in ast.op.generic_map.items():
            #     for param_ty in substituted_param_tys:
            #         TypeInfer.substitute_generic_type(param_ty, g, h.parts[-1].identifier)
            # param_tys = substituted_param_tys
            check = enumerable_any([not TypeInfer.types_equal_account_for_generic(
                ast.op.arguments[arg_tys.index(arg_ty)],
                fn_type.parameters[param_tys.index(param_ty)],
                arg_ty, param_ty, ast.op.generic_map, scope) for arg_ty, param_ty in zip(arg_tys, param_tys)])

            if check[1]:
                mismatch_index = check[0]
                errs.append(f"Expected argument {mismatch_index + 1} to be of type '{param_tys[mismatch_index]}', but got '{arg_tys[mismatch_index]}'.")
                continue

            # Check the calling conventions match. A &mut argument cal collapse into an & parameter, but the __eq__
            # implementation handles this.
            if any([arg_cc != param_cc for arg_cc, param_cc in zip(arg_ccs, param_ccs)]):
                mismatch_index = [i for i, (arg_cc, param_cc) in enumerate(zip(arg_ccs, param_ccs)) if arg_cc != param_cc][0]
                errs.append(f"Expected argument {mismatch_index + 1} to be passed by '{param_ccs[mismatch_index]}', but got '{arg_ccs[mismatch_index]}'.")
                continue

            # If we get here, we have found the function we are looking for. Walk through the type and replace generics
            # with their corresponding type arguments.
            # print("-" * 50)
            # return_type = copy.deepcopy(fn_type.return_type)
            # for t in TypeInfer.traverse_type(return_type, scope):
            #     sym = s.get_symbol(Ast.IdentifierAst(t, -1), SymbolTypes.TypeSymbol)
            #     print(sym)

            # Add the generic map from any previous member accesses into this one too.
            return_type = copy.deepcopy(fn_type.return_type)
            for g, h in ast.op.generic_map.items():
                TypeInfer.substitute_generic_type(return_type, g, h.parts[-1].identifier)
            return return_type

        NL = "\n\t- "
        sigs.insert(0, "")
        errs.insert(0, "")
        output = []
        for i in range(len(sigs)):
            output.append(f"{sigs[i]}: {errs[i]}")

        # TODO : improve the "attempted signature" line of the error message to include the parameter named with their
        #  incorrect types
        raise SystemExit(
            ErrFmt.err(ast.lhs._tok) + f"Could not find function '{ast.lhs}' with the given arguments.\n\n" +
            f"Attempted signature:{NL}({', '.join([str(arg_cc or '') + str(arg_ty) for arg_cc, arg_ty in zip(arg_ccs, arg_tys)])}) -> ?\n\n" +
            f"Available signatures{NL.join(output)}")

    @staticmethod
    def infer_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        return ast.lhs

    @staticmethod
    def infer_identifier(ast: Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInfer.likely_symbols(ast, SymbolTypes.VariableSymbol, "identifier", s)

    @staticmethod
    def check_type(ast: Ast.TypeAst, s: ScopeHandler) -> Ast.TypeAst:
        if isinstance(ast, Ast.TypeGenericArgumentAst):
            ast = ast.value

        # Check generic arguments given to the type
        try:
            sym = s.current_scope.get_symbol(ast.parts[-1], SymbolTypes.TypeSymbol)
        except Exception:
            raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown type '{ast}'.")

        given_generic_arguments = ast.parts[-1].generic_arguments
        actual_generic_parameters = sym.type.generic_parameters if isinstance(sym.type, Ast.ClassPrototypeAst) else []
        if len(given_generic_arguments) > len(actual_generic_parameters):
            if actual_generic_parameters and actual_generic_parameters[-1].is_variadic:
                pass
            else:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Too many generic arguments given to type '{sym.type}'.")
        # if len(given_generic_arguments) < len(missing_generics := TypeInfer.required_generic_parameters_for_cls(sym.type, s)):
        #     raise SystemExit(ErrFmt.err(ast._tok) + f"Not enough generic arguments given to type '{sym.type}'. Missing {missing_generics}.")
        for g in given_generic_arguments:
            TypeInfer.check_type(g, s)

        return TypeInfer.likely_symbols(ast, SymbolTypes.TypeSymbol, "type", s)

    @staticmethod
    def required_generic_parameters_for_cls(ast: Ast.TypeSingleAst | Ast.ClassPrototypeAst, s: ScopeHandler) -> list[Ast.TypeGenericParameterAst]:
        # Generic parameters can be inferred, for a class, if they are:
        #   - The type, or part of the type, of an attribute.
        #   - Part of another generic type.

        if isinstance(ast, Ast.TypeSingleAst):
            sym = s.current_scope.get_symbol(ast.parts[-1], SymbolTypes.TypeSymbol)
            ast = sym.type
            if sym is None: return []

        # print(ast.identifier)
        # print(hash(ast))
        # print([c.id for c in s.global_scope.children])
        # print("-" * 50)

        generics = ast.generic_parameters # todo : other parts of the type ie Vec[T].Value[X]. T would be missing here (just flatten all parts' generics)
        generics_names = [g.identifier.identifier for g in generics]
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
        generics = ast.generic_parameters
        generics_names = [g.identifier for g in generics]

        for ty in [param.type_annotation for param in ast.parameters] + [g for g in ast.generic_parameters]:
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
                case str():
                    yield ast, level
                case Ast.GenericIdentifierAst():
                    yield ast.identifier, level
                    for t in ast.generic_arguments:
                        yield from inner(t, s, level + 1)
                case Ast.TypeSingleAst():
                    yield ast.parts[-1].identifier, level
                    for t in ast.parts:
                        yield from inner(t, s, level + 1)
                case Ast.TypeGenericArgumentAst():
                    yield from inner(ast.value, s, level + 1)
                case Ast.TypeTupleAst():
                    for t in ast.types:
                        yield from inner(t, s, level + 1)
                case Ast.SelfTypeAst():
                    sym = s.current_scope.get_symbol(Ast.IdentifierAst("Self", ast._tok), SymbolTypes.TypeSymbol)
                    yield sym.type.parts[-1].identifier, level
                case _:
                    print(" -> ".join(list(reversed([f.frame.f_code.co_name for f in inspect.stack()]))))
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Type '{type(ast).__name__}' not yet supported for traversal. Report as bug.")
        yield from inner(ast, s, 0)


    @staticmethod
    def infer_type(ast: Ast.TypeAst, s: ScopeHandler) -> Ast.TypeAst:
        if isinstance(ast.parts[-1], Ast.SelfTypeAst):
            return s.current_scope.get_symbol(Ast.IdentifierAst("Self", ast._tok), SymbolTypes.TypeSymbol).type
        return ast

    @staticmethod
    def likely_symbols(ast: Ast.IdentifierAst | Ast.TypeAst, sym_ty: type, what: str, s: ScopeHandler) -> Ast.TypeAst:
        # If the symbol isn't in the current of any parent scope, then it doesn't exist, so throw an error, and give any
        # possible matches.
        # check = s.current_scope.has_symbol(ast if isinstance(ast, Ast.IdentifierAst) else ast.parts[-1] if isinstance(ast, Ast.TypeSingleAst) else ast.identifier, sym_ty)
        # check = SemanticAnalysis.analyse_identifier(ast if isinstance(ast, Ast.IdentifierAst) else ast.parts[-1] if isinstance(ast, Ast.TypeSingleAst) else ast.identifier, s, no_throw=True)
        if isinstance(ast, Ast.TypeSingleAst):
            ast = ast.parts[-1].to_identifier()

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
    def types_equal_account_for_generic(a1, a2, t1: Ast.TypeAst, t2: Ast.TypeAst, generic_map: dict[Ast.IdentifierAst, Ast.TypeAst], s: ScopeHandler) -> bool:
        t1, t2 = t2, t1
        if isinstance(t1, Ast.TypeSingleAst) and isinstance(t2, Ast.TypeSingleAst):
            # - Traverse each part of each type (dot separated)
            # - Traverse each inner part of the part (generic arguments etc)
            # - Generic handling
            #   - If the part is a generic, and in the generic map. If it is, check if the type is the same.
            #   - If the part is a generic, and not in the generic map, add it to the generic map, with the corresponding type.
            #   - Skip the RHS type's corresponding part (type argument).
            # - Non generic handling
            #   - If the part is not a generic, check if the part is the same.
            #   - If the part is not the same, return False.

            for p1, p2 in zip(t1.parts, t2.parts):
                for q1, q2 in zip(TypeInfer.traverse_type(p1, s), TypeInfer.traverse_type(p2, s)):
                    q1, l1 = q1
                    q2, l2 = q2

                    # Non-Generic
                    # If the LHS is not a generic type parameter, then the LHS requires a direct match to the RHS. For
                    # example, 'Str' must match 'Str'. The parameter and arguments are direct type matches.
                    # TODO : allow for subtyping here.
                    if q1 not in generic_map and q1 != q2:
                        return False

                    # Bound Generic
                    # If the LHS is in the generic map, but the RHS type argument is not the correct (ie it is already
                    # known that 'T' is 'Str', but 'T' is being bound to 'Int'), then instead of returning False, throw
                    # an error, because this is a more specific error / specialised case.
                    # TODO : the ast being errored on isn't quite correct: highlight the correct generic argument
                    elif q1 in generic_map and generic_map[q1] and q2 != generic_map[q1].parts[-1].identifier and q2 not in generic_map:
                        ty = TypeInfer.infer_expression(a1.value, s)  #a1.value.lhs.parts[-1]
                        sym = s.current_scope.get_symbol(ty.parts[-1], SymbolTypes.TypeSymbol)
                        gs = sym.type.generic_parameters
                        if gs:
                            gi = gs.index(Ast.TypeGenericParameterAst(Ast.IdentifierAst(q1, -1), [], None, False, -1))
                            ge = a1.value.lhs.parts[-1].generic_arguments[gi]
                            raise SystemExit(ErrFmt.err(ge._tok) + f"Generic type '{q1}' is already bound to '{generic_map[q1]}', but is being re-bound to '{q2}'.")
                        else:
                            raise SystemExit(ErrFmt.err(a1._tok) + f"Generic type '{q1}' is already bound to '{generic_map[q1]}', but is being re-bound to '{q2}'.")

                    elif q1 in generic_map and generic_map[q1] and q2 != generic_map[q1].parts[-1].identifier and q2 in generic_map:
                        TypeInfer.substitute_generic_type(t2, q1, q2)

                    # Unbound Generic
                    # If the LHS is an "unbound" generic, ie it's the first occurrence of an inferrable generic, then
                    # add it to the generic map, and bind it to the RHS type argument. Then skip the rest of q2 because
                    # it is the RHS type argument -- this is the same as jumping q2 to its sibling node rather than its
                    # first child node.
                    elif q1 in generic_map:
                        generic_map[q1] = Ast.TypeSingleAst([Ast.IdentifierAst(q2, -1).to_generic_identifier()], -1)

                        # skip the q2 to sibling node. because Vec[T, Str] compared to Vec[Opt[Num], Str]. clearly the
                        # 2nd one is Vec[Opt[Num], Str] required an extra skip over Num, so that T matches Opt[Num].
                        # this is the same as jumping q2 to its sibling node rather than its first child node.
                        # lx = -1
                        # while lx != l2:
                        #     q2, lx = next(TypeInfer.traverse_type(q2, s))

                        # next, perform a substitution on the RHS type argument, so that all occurrences of the generic
                        # type parameter (LHS) are replaced with the RHS type argument.
                        TypeInfer.substitute_generic_type(t2, q1, q2)

        elif isinstance(t1, Ast.TypeTupleAst) and isinstance(t2, Ast.TypeTupleAst):
            return all([TypeInfer.types_equal_account_for_generic(a1, a2, t1, t2, generic_map, s) for t1, t2 in zip(t1.types, t2.types)])

        else:
            raise SystemExit(ErrFmt.err(a1._tok) + f"Unknown 'Ast.{type(t2).__name__}' being inferred. Report as bug.")

        return True

    @staticmethod
    def substitute_generic_type(ty: Ast.TypeAst, q1: str, q2: str):
        if isinstance(ty, Ast.IdentifierAst):
            if ty.identifier == q1:
                ty.identifier = q2
        if isinstance(ty, Ast.TypeGenericArgumentAst):
            TypeInfer.substitute_generic_type(ty.value, q1, q2)
        elif isinstance(ty, Ast.GenericIdentifierAst):
            if ty.identifier == q1:
                ty.identifier = q2
            for j, q in enumerate(ty.generic_arguments):
                TypeInfer.substitute_generic_type(q, q1, q2)
        elif isinstance(ty, Ast.TypeSingleAst):
            for i, p in enumerate(ty.parts):
                TypeInfer.substitute_generic_type(p, q1, q2)
        elif isinstance(ty, Ast.TypeTupleAst):
            for p in ty.types:
                TypeInfer.substitute_generic_type(p, q1, q2)
        else:
            print(" -> ".join(list(reversed([f.frame.f_code.co_name for f in inspect.stack()]))))
            raise SystemExit(ErrFmt.err(ty._tok) + f"Unknown 'Ast.{type(ty).__name__}' being inferred. Report as bug.")
