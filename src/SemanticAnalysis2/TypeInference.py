from difflib import SequenceMatcher
from typing import Callable

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes
from src.SemanticAnalysis2.CommonTypes import CommonTypes


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
            case Ast.ArrayLiteralAst(): return CommonTypes.array(TypeInfer.infer_expression(ast.elements[0], s))
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
            case Ast.ReturnStatementAst(): return TypeInfer.infer_expression(ast.value, s)
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
            ty = TypeInfer.infer_postfix_member_access(ast.lhs, s) if isinstance(ast.lhs, Ast.PostfixExpressionAst) else TypeInfer.infer_identifier(ast.lhs, s) if isinstance(ast.lhs, Ast.IdentifierAst) else TypeInfer.infer_type(ast.lhs, s)
        if isinstance(ast, Ast.IdentifierAst):
            ty = TypeInfer.infer_identifier(ast, s)
        ty = TypeInfer.infer_type(ty, s)
        cls = s.global_scope.get_child_scope(ty)

        if isinstance(ast.op.identifier, Ast.IdentifierAst):
            sym = cls.get_symbol_exclusive(ast.op.identifier, SymbolTypes.VariableSymbol, error=False)
            if not sym:
                raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"Unknown member '{ast.op.identifier}' of type '{ty}'.")
            if isinstance(sym, SymbolTypes.VariableSymbol):
                return sym.type
            return sym#, [s.type for s in sym]
        else:
            ty = TypeInfer.infer_expression(ast.lhs, s)
            return ty.parts[-1].generic_arguments[int(ast.op.identifier.integer)]

    @staticmethod
    def infer_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # To infer something like x.y.z(a, b), we need to infer x.y.z, then infer a and b, then infer the function call.

        ty = TypeInfer.infer_expression(ast.lhs, s, all=True)
        arg_tys = [TypeInfer.infer_expression(arg.value, s) for arg in ast.op.arguments]
        arg_ccs = [arg.calling_convention for arg in ast.op.arguments]

        # The next step is because overloads of functions can return different types ie: 'f(Str) -> Num' and
        # 'f(Int) -> Str' can be overloads of 'f'. We need to find the function that matches the arguments, and return
        # the return type of that function.

        # Get the function symbol from the scope.
        sigs = []
        errs = []

        s = s.global_scope.get_child_scope(ty)
        overloads = [x for x in s.all_symbols_exclusive(SymbolTypes.VariableSymbol) if x.name.identifier in ["call_ref", "call_mut", "call_one"]]
        for i, fn_type in enumerate([f.meta_data["fn_proto"] for f in overloads]):
            param_names = [param.identifier.identifier for param in fn_type.parameters]
            param_tys = [param.type_annotation for param in fn_type.parameters]
            param_ccs = [param.calling_convention for param in fn_type.parameters]
            sigs.append(str(fn_type))

            # Skip first argument type for non-static functions
            if overloads[i].meta_data.get("is_method", False) and not overloads[i].meta_data.get("is_static", False):
                param_tys = param_tys[1:]
                param_ccs = param_ccs[1:]

            # Check if the function is callable with the number of given arguments.
            if len(param_tys) != len(arg_tys):
                errs.append(f"Expected {len(param_tys)} arguments, but got {len(arg_tys)}.")
                continue

            # Check if the function is callable with the given argument types.
            if any([arg_ty != param_ty for arg_ty, param_ty in zip(arg_tys, param_tys)]):
                errs.append(f"Expected arguments of types {', '.join([str(ty) for ty in param_tys])}, but got {', '.join([str(ty) for ty in arg_tys])}.")
                continue

            # Check the calling conventions match. A &mut argument cal collapse into an & parameter, but the __eq__
            # implementation handles this.
            if any([arg_cc != param_cc for arg_cc, param_cc in zip(arg_ccs, param_ccs)]):
                errs.append(f"Expected arguments with calling conventions [{', '.join([str(cc) for cc in param_ccs])}], but got [{', '.join([str(cc) for cc in arg_ccs])}].")
                continue

            # If we get here, we have found the function we are looking for.
            return fn_type.return_type

        NL = "\n\t- "
        sigs.insert(0, "")
        errs.insert(0, "")
        output = []
        for i in range(len(sigs)):
            output.append(f"{sigs[i]}: {errs[i]}")

        raise SystemExit(ErrFmt.err(ast.lhs._tok) + f"Could not find function '{ast.lhs}' with the given arguments.\nAvailable signatures{NL.join(output)}")

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
        return TypeInfer.likely_symbols(ast, SymbolTypes.TypeSymbol, "type", s)

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
