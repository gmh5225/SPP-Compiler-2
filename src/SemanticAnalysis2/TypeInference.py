from difflib import SequenceMatcher
from typing import Callable

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes
from src.SemanticAnalysis2.CommonTypes import CommonTypes


class TypeInfer:
    @staticmethod
    def infer_expression(ast: Ast.ExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast:
            case Ast.IdentifierAst(): return TypeInfer.infer_identifier(ast, s)
            case Ast.LambdaAst(): raise NotImplementedError("Lambda expressions are not implemented yet.")
            case Ast.IfStatementAst(): return TypeInfer.infer_statement(ast.body[-1], s)
            case Ast.WhileStatementAst(): return CommonTypes.void()
            case Ast.YieldStatementAst(): raise NotImplementedError("Yield expressions are not implemented yet.")
            case Ast.WithStatementAst(): return TypeInfer.infer_statement(ast.body[-1], s)
            case Ast.InnerScopeAst(): return TypeInfer.infer_statement(ast.body[-1], s)
            case Ast.BinaryExpressionAst(): return TypeInfer.infer_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): return TypeInfer.infer_postfix_expression(ast, s)
            case Ast.AssignmentExpressionAst(): return CommonTypes.void()
            case Ast.PlaceholderAst(): raise NotImplementedError("Placeholder expressions are not implemented yet.")
            case Ast.TypeSingleAst(): return ast
            case Ast.BoolLiteralAst(): return CommonTypes.bool()
            case Ast.StringLiteralAst(): return CommonTypes.string()
            case Ast.CharLiteralAst(): return CommonTypes.char()
            case Ast.RegexLiteralAst(): return CommonTypes.regex()
            case Ast.TupleLiteralAst(): return CommonTypes.tuple([TypeInfer.infer_expression(e, s) for e in ast.elements])
            case Ast.NumberLiteralBase02Ast(): return CommonTypes.num()
            case Ast.NumberLiteralBase10Ast(): return CommonTypes.num()
            case Ast.NumberLiteralBase16Ast(): return CommonTypes.num()
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown expression {ast} being inferred. Report as bug.")

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
    def infer_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        match ast.op:
            case Ast.PostfixMemberAccessAst(): return TypeInfer.infer_postfix_member_access(ast, s)
            case Ast.PostfixFunctionCallAst(): return TypeInfer.infer_postfix_function_call(ast, s)
            case Ast.PostfixStructInitializerAst(): return TypeInfer.infer_postfix_struct_initializer(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown postfix expression {ast} being inferred. Report as bug.")

    @staticmethod
    def infer_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        ty = None
        if isinstance(ast, Ast.PostfixExpressionAst) and isinstance(ast.op, Ast.PostfixMemberAccessAst):
            ty = TypeInfer.infer_postfix_member_access(ast.lhs, s)
        if isinstance(ast, Ast.IdentifierAst):
            ty = TypeInfer.infer_identifier(ast, s)
        sym = s.global_scope.get_child_scope(ty).get_symbol_exclusive(ast.op.identifier, SymbolTypes.VariableSymbol)
        return sym.type

    @staticmethod
    def infer_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        # To infer something like x.y.z(a, b), we need to infer x.y.z, then infer a and b, then infer the function call.

        lhs_type = TypeInfer.infer_expression(ast.lhs, s)
        arg_tys = [TypeInfer.infer_expression(arg.value, s) for arg in ast.op.arguments]
        arg_ccs = [arg.calling_convention for arg in ast.op.arguments]

        # Get the function symbol from the scope
        syms = s.global_scope.get_child_scope(lhs_type).get_symbol_exclusive(ast.op.identifier, SymbolTypes.FunctionSymbol)
        sigs = []
        for sym in syms:
            fn_type = sym.type
            param_tys = [param.type_annotation for param in fn_type.parameters]
            param_ccs = [param.calling_convention for param in fn_type.parameters]
            sigs.append(",".join([f"{param_cc}{param_ty}" for param_cc, param_ty in zip(param_ccs, param_tys)]))

            # Check if the function is callable with the number of given arguments.
            if len(param_tys) != len(arg_tys):
                continue

            # Check if the function is callable with the given argument types.
            if any([arg_ty != param_ty for arg_ty, param_ty in zip(arg_tys, param_tys)]):
                continue

            # Check the calling conventions match.
            if any([arg_cc != param_cc for arg_cc, param_cc in zip(arg_ccs, param_ccs)]):
                continue

            # If we get here, we have found the function we are looking for.
            return fn_type.return_type

        NL = "\n"
        raise SystemExit(ErrFmt.err(ast._tok) + f"Could not find function {ast.op.identifier} with the given arguments. Available signatures: {NL.join(sigs)}")

    @staticmethod
    def infer_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler) -> Ast.TypeAst:
        return ast.lhs

    @staticmethod
    def infer_identifier(ast: Ast.IdentifierAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInfer.likely_symbols(ast, SymbolTypes.VariableSymbol, "identifier", s)

    @staticmethod
    def check_type(ast: Ast.TypeAst, s: ScopeHandler) -> Ast.TypeAst:
        return TypeInfer.likely_symbols(ast, SymbolTypes.TypeSymbol, "type", s)

    @staticmethod
    def infer_type(ast: Ast.TypeAst, s: ScopeHandler) -> Ast.TypeAst:
        return ast

    @staticmethod
    def likely_symbols(ast: Ast.IdentifierAst | Ast.TypeAst, sym_ty: type, what: str, s: ScopeHandler) -> Ast.TypeAst:
        # If the symbol isn't in the current of any parent scope, then it doesn't exist, so throw an error, and give any
        # possible matches.
        if not s.current_scope.has_symbol(ast, sym_ty):

            # Get all the variable symbols that are in the scope. Define the most likely to be "-1" so that any symbol
            # will be more likely than it.
            similar_symbols = s.current_scope.all_symbols(sym_ty)
            most_likely = (-1.0, "")

            # Iterate through each symbol, and find the one that is most similar to the identifier.
            for sym in similar_symbols:
                # Get the ratio of similarity between the identifier and the symbol name.
                ast_identifier = ast.identifier if isinstance(ast, Ast.IdentifierAst) else ast.parts[-1].identifier
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

            if most_likely[0] == -1:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown {what} {ast}. Did you mean {most_likely[1]}?")
        return ast if what == "type" else s.current_scope.get_symbol(ast, SymbolTypes.VariableSymbol).type
