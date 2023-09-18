import copy
from typing import Iterable, Optional, TypeVar

from src.LexicalAnalysis.Tokens import TokenType, Token
from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes
from src.SemanticAnalysis2.CommonTypes import CommonTypes
from src.SemanticAnalysis2.TypeInference import TypeInfer


T = TypeVar("T")
def any_elem(iterable: Iterable[T]) -> Optional[T]:
    for element in iterable:
        if element:
            return element
    return None


class SemanticAnalysis:
    ASSIGNMENTS = {}

    @staticmethod
    def analyse(ast: Ast.ProgramAst, s: ScopeHandler):
        SemanticAnalysis.analyse_program(ast, s)

    @staticmethod
    def analyse_program(ast: Ast.ProgramAst, s: ScopeHandler):
        [SemanticAnalysis.analyse_decorator(ast.module, d, s) for d in ast.module.decorators]
        [SemanticAnalysis.analyse_module_member(m, s) for m in ast.module.body.members]

    @staticmethod
    def analyse_module_member(ast: Ast.ModuleMemberAst, s: ScopeHandler):
        # Analyse each module member
        match ast:
            case Ast.ClassPrototypeAst(): SemanticAnalysis.analyse_class_prototype(ast, s)
            case Ast.EnumPrototypeAst(): s.skip_scope()
            case Ast.SupPrototypeNormalAst(): SemanticAnalysis.analyse_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): SemanticAnalysis.analyse_sup_prototype(ast, s)
            case Ast.LetStatementAst(): pass  # SemanticAnalysis.analyse_let_statement(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown module member {ast} being analysed. Report as bug.")

    @staticmethod
    def analyse_function_parameters(asts: list[Ast.FunctionParameterAst], s: ScopeHandler, **kwargs):
        # check no duplicate parameter names
        for i, p in enumerate(asts):
            if p.identifier in [q.identifier for q in asts[i + 1:]]:
                raise SystemExit(ErrFmt.err(p._tok) + f"Duplicate parameter name '{p.identifier}'.")

        current_param_type = "required"
        for i, p in enumerate(asts):
            if p.is_self:
                if i > 0:
                    raise SystemExit(
                        "The 'self' parameter must be the first parameter:\n" +
                        ErrFmt.err(asts[0]._tok) + "First parameter\n..." +
                        ErrFmt.err(p._tok) + "Current parameter.")
                elif not kwargs.get("in_class", False):
                    raise SystemExit(
                        "The 'self' parameter cannot be used in a function\nprototype outside of a class:\n" +
                        ErrFmt.err(p._tok) + "Current parameter.")
                else:
                    continue

            if current_param_type == "optional" and not (p.default_value or p.is_variadic):
                first_optional_parameter = next((p for p in asts if p.default_value), None)
                final_token_1 = asts[asts.index(first_optional_parameter) + 1]._tok if first_optional_parameter != asts[-1] else p.type_annotation._tok
                final_token_2 = asts[asts.index(p) + 1]._tok if p != asts[-1] else p.type_annotation._tok
                raise SystemExit(
                    "Optional parameters must come after required parameters." +
                    ErrFmt.err(first_optional_parameter._tok, final_token_1) + "First optional parameter\n..." +
                    ErrFmt.err(p._tok, final_token_2) + "Current parameter.")

            if current_param_type == "variadic":
                last_optional_parameter = next((p for p in asts[::-1] if p.default_value), None)
                final_token_1 = asts[asts.index(last_optional_parameter) + 1]._tok if last_optional_parameter != asts[-1] else p.type_annotation._tok
                final_token_2 = asts[asts.index(p) + 1]._tok if p != asts[-1] else p.type_annotation._tok
                raise SystemExit(
                    "Variadic parameters must come after required parameters." +
                    ErrFmt.err(last_optional_parameter._tok, final_token_1) + "Last optional parameter\n..." +
                    ErrFmt.err(p._tok, final_token_2) + "Current parameter.")

            if p.default_value: current_param_type = "optional"
            if p.is_variadic  : current_param_type = "variadic"

        # to_analyse = asts[1:] if asts and asts[0].is_self else asts
        for p in asts:
            SemanticAnalysis.analyse_function_parameter(p, s)

    @staticmethod
    def analyse_type_generic_parameters(asts: list[Ast.TypeGenericParameterAst], s: ScopeHandler):
        # check no duplicate generic parameter names
        for i, g in enumerate(asts):
            if g.identifier and g.identifier in [h.identifier for h in asts[i + 1:]]:
                raise SystemExit(ErrFmt.err(g._tok) + f"Duplicate generic parameter name '{g.identifier}'.")

        current_generic_param_type = "required"
        for g in asts:
            if current_generic_param_type == "optional" and not g.default:
                first_optional_parameter = next((p for p in asts if p.default), None)
                final_token_1 = asts[asts.index(first_optional_parameter) + 1]._tok if first_optional_parameter != asts[-1] else g._tok
                final_token_2 = asts[asts.index(g) + 1]._tok if g != asts[-1] else g._tok
                raise SystemExit(
                    "Optional generic parameters must come after required generic parameters." +
                    ErrFmt.err(first_optional_parameter._tok, final_token_1) + "First optional generic parameter\n..." +
                    ErrFmt.err(g._tok, final_token_2) + "Current generic parameter.")

            if current_generic_param_type == "variadic" and not g.is_variadic:
                last_optional_parameter = next((p for p in asts[::-1] if p.default), None)
                final_token_1 = asts[asts.index(last_optional_parameter) + 1]._tok if last_optional_parameter != asts[-1] else g._tok
                final_token_2 = asts[asts.index(g) + 1]._tok if g != asts[-1] else g._tok
                raise SystemExit(
                    "Variadic generic parameters must come after required generic parameters." +
                    ErrFmt.err(last_optional_parameter._tok, final_token_1) + "Last optional generic parameter\n..." +
                    ErrFmt.err(g._tok, final_token_2) + "Current generic parameter.")

            if g.default    : current_generic_param_type = "optional"
            if g.is_variadic: current_generic_param_type = "variadic"

    @staticmethod
    def analyse_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler, **kwargs):
        # Enter the next scope, which will be the function scope. This is to load in the parameters and subsequently
        # declared variables into the sy,bol table in the correct scope.
        s.next_scope()

        # Analyse all the decorators, parameters, generic type parameters, and the return type. This is to ensure
        # correct parameter order and that all the return types are valid.
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        SemanticAnalysis.analyse_function_parameters(ast.parameters, s, **kwargs)
        SemanticAnalysis.analyse_type_generic_parameters(ast.generic_parameters, s)
        TypeInfer.check_type(ast.return_type, s)

        # Analyse each statement in the body of the function.
        for statement in ast.body.statements:
            SemanticAnalysis.analyse_statement(statement, s)

        # Make sure the return type of the last statement matches the return type of the function, unless the method is
        # abstract, in which case it is allowed to not have a return statement. An empty function body has special
        # behaviour as detailed beneath.
        final_statement = ast.body.statements[-1] if ast.body.statements else None

        # The detected return type of a function is the inferred type of the final (return) statement in the function's
        # body, and std.Void otherwise -- this is to ensure that the final statement (returning) is actually a return
        # statement, forcing there to only be 1 way to do anything, in this case, returning a value.
        if not isinstance(final_statement, Ast.ReturnStatementAst):
            t = CommonTypes.void()
        else:
            t = TypeInfer.infer_statement(final_statement, s) if ast.body.statements else CommonTypes.void()

        # If there is a non-void return type and the final statement is not a return statement, then raise an erorr,
        # because
        if ast.return_type != CommonTypes.void() and ast.body.statements and not isinstance(final_statement, Ast.ReturnStatementAst):
            err_ast = ast.body.statements[-1]
            raise SystemExit(
                f"Function returning '{ast.return_type}' must end with a return statement:" +
                ErrFmt.err(ast.return_type._tok) + f"Function return type is '{ast.return_type}'.\n..." +
                ErrFmt.err(err_ast._tok) + f"Final statement is not a return statement.")

        if not t.subtype_match(ast.return_type, s) and ast.body.statements and isinstance(final_statement, Ast.ReturnStatementAst):
            err_ast = ast.body.statements[-1]
            raise SystemExit(
                "Mismatch between function return type and function's final statement:" +
                ErrFmt.err(ast.return_type._tok) + f"Function return type is '{ast.return_type}'.\n..." +
                ErrFmt.err(err_ast._tok) + f"Final statement returns type '{t}'.")

        s.prev_scope()

    @staticmethod
    def analyse_function_parameter(ast: Ast.FunctionParameterAst, s: ScopeHandler):
        TypeInfer.check_type(ast.type_annotation, s)

        # Analyse the parameter type, and Add the parameter to the current scope.
        ty = ast.type_annotation
        sym = SymbolTypes.VariableSymbol(ast.identifier, ty, is_mutable=ast.is_mutable, is_initialized=True)
        sym.mem_info.initialization_ast = ast

        # Check that if a default value if provided, making the parameter optional, that the parameter type is not a
        # reference, and that the default value is of the correct type.
        if ast.default_value:
            if ast.calling_convention:
                raise SystemExit(
                    "Cannot have a default value for a parameter with a calling\nconvention:" +
                    ErrFmt.err(ast.calling_convention._tok) + f"Parameter has the calling convention '{ast.calling_convention}'.\n..." +
                    ErrFmt.err(ast.default_value._tok) + "Default value.")

            # todo : maybe change this to a different error if the parameter type is generic? Just a more concise error
            #  message maybe. also maybe not because all other assignments would need the duplicated adjustment.
            #  probably easier to stick with this error message for all mismatches.
            if not ast.type_annotation.subtype_match(default_type := TypeInfer.infer_expression(ast.default_value, s), s):
                raise SystemExit(
                    "Default value must match the parameter type:" +
                    ErrFmt.err(ast.type_annotation._tok) + f"Parameter has type '{ast.type_annotation}'.\n..." +
                    ErrFmt.err(ast.default_value._tok) + f"Default value has the type '{default_type}'.")

        # Set the symbol borrow information based on the parameter passing convention.
        match ast.calling_convention:
            case Ast.ParameterPassingConventionReferenceAst() if ast.calling_convention.is_mutable:
                sym.mem_info.is_borrowed_mut = True
                sym.mem_info.borrow_ast = ast
            case Ast.ParameterPassingConventionReferenceAst() if not ast.calling_convention.is_mutable:
                sym.mem_info.is_borrowed_ref = True
                sym.mem_info.borrow_ast = ast
            case None: pass

        # Add the symbol to the scope.
        s.current_scope.add_symbol(sym)

        # Analyse the default value
        if ast.default_value:
            SemanticAnalysis.analyse_expression(ast.default_value, s)

    @staticmethod
    def analyse_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeHandler):
        s.next_scope()

        SemanticAnalysis.analyse_type_generic_parameters(ast.generic_parameters, s)
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        [SemanticAnalysis.analyse_class_member(m, s) for m in ast.body.members]

        s.prev_scope()

    @staticmethod
    def analyse_class_member(ast: Ast.ClassAttributeAst, s: ScopeHandler):
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        TypeInfer.check_type(ast.type_annotation, s)

    @staticmethod
    def analyse_sup_prototype(ast: Ast.SupPrototypeAst, s: ScopeHandler):
        s.next_scope()
        SemanticAnalysis.analyse_type_generic_parameters(ast.generic_parameters, s)

        for type_part in ast.identifier.parts:
            [TypeInfer.check_type(g, s) for g in type_part.generic_arguments]

        if type(ast) == Ast.SupPrototypeInheritanceAst:
            TypeInfer.check_type(ast.super_class, s)
            for type_part in ast.super_class.parts if ast.super_class else []:
                [TypeInfer.check_type(g, s) for g in type_part.generic_arguments]

        # if its for a function (__MOCK_...) then check there are no duplicate overloads. get all the super-impositions
        # of the __MOCK_... class
        if str(ast.identifier).startswith("__MOCK_"):
            scope = s.global_scope.get_child_scope(ast.identifier)
            overloads = [x for x in scope.all_symbols_exclusive(SymbolTypes.VariableSymbol) if x.name.identifier in ["call_ref", "call_mut", "call_one"]]
            fn_protos = [f.meta_data["fn_proto"] for f in overloads]

            # identify duplicates by parameters
            fn_protos = [copy.deepcopy(f) for f in fn_protos]

            # firstly, replace type parameters by a number for each type, so f[T](a: T) matches f[U](a: U) - this is the
            # same signature
            generic_mappers = []
            for f in fn_protos:
                generic_mapper = {}
                generic_mappers.append(generic_mapper)
                for i, g in enumerate(f.generic_parameters):
                    if g not in generic_mapper:
                        replacement_generic = Ast.TypeSingleAst([Ast.GenericIdentifierAst(f"__GENERIC_{i}", [], -1)], -1)
                        generic_mapper[g.identifier] = replacement_generic

            for i, f in enumerate(fn_protos):
                for p in f.parameters:
                    for g in f.generic_parameters:
                        TypeInfer.substitute_generic_type(p.type_annotation, g.identifier, generic_mappers[i][g.identifier])

            for i, f in enumerate(fn_protos[:-1]):
                for g in fn_protos[i + 1:]:
                    required_f_params = [p for p in f.parameters if p.is_required()]
                    required_g_params = [p for p in g.parameters if p.is_required()]
                    if all([f_param.type_annotation == g_param.type_annotation for f_param, g_param in zip(required_f_params, required_g_params)]):
                        extra = ""
                        if len(f.parameters) != len(g.parameters):
                            extra = (
                                " One overload\ncannot be a 'subset' of another overload, ie the same but\nwith optional or"
                                "variadic parameters, as calling the function\nwithout any optional or variadic parameters "
                                "would lead to\neither overload being available to call.\n")
                        elif len(required_f_params) == len(required_g_params):
                            extra = (
                                " One overload\ncannot have the same required parameters but different optional or\n"
                                "variadic parameters, as calling the function without any optional or\nvariadic parameters "
                                "would lead to either overload being available\nto call.\n")
                        raise SystemExit(
                            "Duplicate function overloads are not allowed." + extra +
                            ErrFmt.err(f._tok) + f"First overload\n..." +
                            ErrFmt.err(g._tok) + f"Second overload.")

        [SemanticAnalysis.analyse_sup_member(ast, m, s) for m in ast.body.members]

        s.prev_scope()

    @staticmethod
    def analyse_sup_member(owner: Ast.SupPrototypeAst, ast: Ast.SupMemberAst, s: ScopeHandler):
        match ast:
            case Ast.SupTypedefAst(): SemanticAnalysis.analyse_sup_typedef(ast, s)
            case Ast.SupMethodPrototypeAst(): SemanticAnalysis.analyse_sup_method_prototype(owner, ast, s)
            case Ast.ClassPrototypeAst():
                if isinstance(owner, Ast.SupPrototypeInheritanceAst):
                    super_class_scope = s.global_scope.get_child_scope(owner.super_class)
                    reduced_identifier = Ast.IdentifierAst(ast.identifier.identifier.split("__MOCK_")[1], ast.identifier._tok)
                    if not super_class_scope.has_symbol_exclusive(reduced_identifier, SymbolTypes.VariableSymbol): # todo : this check needed?
                        raise SystemExit(ErrFmt.err(ast.identifier._tok) + f"Method '{reduced_identifier}' not found in super class '{owner.super_class}'.")

                SemanticAnalysis.analyse_class_prototype(ast, s)
            case Ast.LetStatementAst(): pass  # SemanticAnalysis.analyse_let_statement(ast, s)
            case Ast.SupPrototypeNormalAst(): SemanticAnalysis.analyse_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): SemanticAnalysis.analyse_sup_prototype(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown sup member '{type(ast).__name__}' being analysed. Report as bug.")

    @staticmethod
    def analyse_sup_method_prototype(owner: Ast.SupPrototypeAst, ast: Ast.SupMethodPrototypeAst, s: ScopeHandler):
        if isinstance(owner, Ast.SupPrototypeInheritanceAst):
            super_class_scope = s.global_scope.get_child_scope(owner.super_class)
            # special = ast.identifier.identifier in ["call_ref", "call_mut", "call_one"]

            if not super_class_scope:
                raise SystemExit(ErrFmt.err(owner.super_class._tok) + f"Super class '{owner.super_class}' not found.")

            # Make sure the method exists in the super class.
            # print(super_class_scope.all_symbols_exclusive(SymbolTypes.VariableSymbol))
            # if not super_class_scope.has_symbol_exclusive(ast.identifier, SymbolTypes.VariableSymbol):
            #     raise SystemExit(ErrFmt.err(ast.identifier._tok) + f"Method '{ast.identifier}' not found in super class '{owner.super_class}'.")

        SemanticAnalysis.analyse_function_prototype(ast, s, in_class=True)

    @staticmethod
    def analyse_sup_typedef(ast: Ast.SupTypedefAst, s: ScopeHandler):
        # Analyse the decorators, then run the normal typedef analysis.
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        SemanticAnalysis.analyse_typedef(ast, s)

    @staticmethod
    def analyse_statement(ast: Ast.StatementAst, s: ScopeHandler):
        match ast:
            case Ast.TypedefStatementAst(): SemanticAnalysis.analyse_typedef(ast, s)
            case Ast.ReturnStatementAst(): SemanticAnalysis.analyse_return_statement(ast, s)
            case Ast.LetStatementAst(): SemanticAnalysis.analyse_let_statement(ast, s)
            case Ast.FunctionPrototypeAst(): SemanticAnalysis.analyse_function_prototype(ast, s)
            case _: SemanticAnalysis.analyse_expression(ast, s)

    @staticmethod
    def analyse_return_statement(ast: Ast.ReturnStatementAst, s: ScopeHandler):
        if ast.value:
            SemanticAnalysis.analyse_expression(ast.value, s)

    @staticmethod
    def analyse_decorator(apply_to: Ast.ModulePrototypeAst | Ast.FunctionPrototypeAst | Ast.ClassPrototypeAst | Ast.EnumPrototypeAst | Ast.SupTypedefAst | Ast.ClassAttributeAst, ast: Ast.DecoratorAst, s: ScopeHandler):
        # TODO
        pass

    @staticmethod
    def analyse_typedef(ast: Ast.TypedefStatementAst, s: ScopeHandler):
        # Analyse the old type, then add a symbol for the new type that points to the old type.
        old_type_sym = s.current_scope.get_symbol(ast.old_type.to_identifier(), SymbolTypes.TypeSymbol)
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(ast.new_type.to_identifier(), old_type_sym.type, old_type_sym.sup_scopes))

    @staticmethod
    def analyse_expression(ast: Ast.ExpressionAst, s: ScopeHandler, **kwargs):
        match ast:
            case Ast.IdentifierAst(): SemanticAnalysis.analyse_identifier(ast, s)
            case Ast.LambdaAst(): raise NotImplementedError("Lambda expressions are not implemented yet.")
            case Ast.IfStatementAst(): SemanticAnalysis.analyse_if_statement(ast, s, **kwargs)
            case Ast.WhileStatementAst(): SemanticAnalysis.analyse_while_statement(ast, s)
            case Ast.YieldStatementAst(): raise NotImplementedError("Yield expressions are not implemented yet.")
            case Ast.WithStatementAst(): SemanticAnalysis.analyse_with_statement(ast, s)
            case Ast.InnerScopeAst(): SemanticAnalysis.analyse_inner_scope(ast, s)
            case Ast.BinaryExpressionAst(): SemanticAnalysis.analyse_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): SemanticAnalysis.analyse_postfix_expression(ast, s, **kwargs)
            case Ast.AssignmentExpressionAst(): SemanticAnalysis.analyse_assignment_expression(ast, s)
            case Ast.PlaceholderAst(): raise NotImplementedError("Placeholder expressions are not implemented yet.")
            case Ast.TypeSingleAst(): TypeInfer.check_type(ast, s)
            case Ast.ArrayLiteralAst(): SemanticAnalysis.analyse_array_literal(ast, s)
            case Ast.TupleLiteralAst(): SemanticAnalysis.analyse_tuple_literal(ast, s)
            case Ast.TokenAst() if ast.tok.token_type == TokenType.KwSelf: pass
            case _:
                if type(ast) in Ast.LiteralAst.__args__ or type(ast) in Ast.NumberLiteralAst.__args__: return
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown expression {ast} being analysed. Report as bug.")

    @staticmethod
    def analyse_array_literal(ast: Ast.ArrayLiteralAst, s: ScopeHandler):
        for e in ast.values:
            SemanticAnalysis.analyse_expression(e, s)
        t0 = TypeInfer.infer_expression(ast.values[0], s)
        for e in ast.values[1:]:
            if t0 != (t1 := TypeInfer.infer_expression(e, s)):
                raise SystemExit(
                    "Array elements must all be the same type:" +
                    ErrFmt.err(ast.values[0]._tok) + f"First element is type '{t0}'\n..." +
                    ErrFmt.err(e._tok) + f"Element is type '{t1}'.")

    @staticmethod
    def analyse_tuple_literal(ast: Ast.TupleLiteralAst, s: ScopeHandler):
        for e in ast.values:
            SemanticAnalysis.analyse_expression(e, s)

    @staticmethod
    def analyse_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs):
        match ast.op:
            case Ast.PostfixMemberAccessAst(): SemanticAnalysis.analyse_postfix_member_access(ast, s, **kwargs)
            case Ast.PostfixFunctionCallAst(): SemanticAnalysis.analyse_postfix_function_call(ast, s)
            case Ast.PostfixStructInitializerAst(): SemanticAnalysis.analyse_postfix_struct_initializer(ast, s)
            case _: raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown postfix expression {ast} being analysed. Report as bug.")

    @staticmethod
    def analyse_identifier(ast: Ast.IdentifierAst, s: ScopeHandler, **kwargs):
        # Special assignment dummy method to check the statement and avoid code duplication.
        if ast.is_special():
            return # TODO : true or false?
        if not s.current_scope.has_symbol(ast, SymbolTypes.VariableSymbol):
            # if not s.current_scope.has_symbol("__MOCK_" + ast, SymbolTypes.TypeSymbol):
                if not kwargs.get("no_throw", False):
                    raise SystemExit(ErrFmt.err(ast._tok) + f"Identifier '{ast}' not found in scope.")
                return False
        return True

    @staticmethod
    def analyse_if_statement(ast: Ast.IfStatementAst, s: ScopeHandler, **kwargs):
        s.enter_scope("if")

        # Analyse the condition expression, and each pattern
        SemanticAnalysis.analyse_expression(ast.condition, s)
        [SemanticAnalysis.analyse_pattern_statement(ast, b, s) for b in ast.branches]

        # If the 'if-statement' is being used for assignment, make sure the final statements in each branch have a
        # matching "return type" => they all infer to be the same type.
        if kwargs.get("assignment", False):
            ret_type = TypeInfer.infer_expression(ast.branches[0].body[-1], s)
            for i, b in enumerate(ast.branches[1:]):
                if (t := TypeInfer.infer_expression(b.body[-1], s)) != ret_type:
                    raise SystemExit(
                        "If an 'if-statement' is being used for assignment, all branches must return the same type" +
                        ErrFmt.err(ast.branches[0].body[-1]._tok) + f"First branch returns type '{ret_type}'\n..." +
                        ErrFmt.err(b.body[-1]._tok) + f"Branch {i + 2} returns type '{t}'.")

        s.exit_scope()

    @staticmethod
    def analyse_pattern_statement(owner: Ast.IfStatementAst, ast: Ast.PatternStatementAst, s: ScopeHandler):
        s.enter_scope("pattern")

        # Check there isn't a comparison operator in the if-statement and the pattern statement.
        if owner.comparison_op and ast.comparison_op:
            raise SystemExit(
                "Cannot have a comparison operator in both the if-statement\nand the pattern-statement:\n" +
                ErrFmt.err(owner.comparison_op._tok) + "Comparison operator in if-statement.\n..." +
                ErrFmt.err(ast._tok) + "Comparison operator in pattern statement.")

        # Check the comparison function exists for each pattern in the pattern statement.
        pat_comp = ast.comparison_op or owner.comparison_op
        if pat_comp:
            for pat in ast.patterns:
                bin_comp = Ast.BinaryExpressionAst(owner.condition, pat_comp, pat.value, pat_comp._tok)
                SemanticAnalysis.analyse_expression(bin_comp, s)

        # Check the pattern guard
        if ast.guard:
            SemanticAnalysis.analyse_expression(ast.guard, s)

        # Check each statement in the pattern statement.
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.exit_scope()

    @staticmethod
    def analyse_inner_scope(ast: Ast.InnerScopeAst, s: ScopeHandler):
        s.enter_scope("inner")
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.exit_scope()

    @staticmethod
    def analyse_with_statement(ast: Ast.WithStatementAst, s: ScopeHandler):
        s.enter_scope("with")
        SemanticAnalysis.analyse_expression(ast.value, s)
        s.current_scope.get_symbol(ast.alias.identifier, SymbolTypes.VariableSymbol).mem_info.is_initialized = True
        s.current_scope.get_symbol(ast.alias.identifier, SymbolTypes.VariableSymbol).mem_info.initialization_ast = ast.alias
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.exit_scope()

    @staticmethod
    def analyse_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler):
        # Remodel the binary expression into a function call, then analyse the function call. Start with constructing a
        # postfix call to the correct method name. For example, for "x + y", begin with constructing "x.add".
        pos = ast.op._tok
        fn = Ast.IdentifierAst(Ast.BIN_FN[ast.op.tok.token_type], pos)
        fn = Ast.PostfixMemberAccessAst(fn, pos)
        fn = Ast.PostfixExpressionAst(ast.lhs, fn, pos)

        # Next, convert the right-hand side into a function argument, and construct the function call. The function call
        # creates the "(y)" that is the postfix expression for "x.add", creating "x.add(y)". This is then analysed.
        rhs = Ast.FunctionArgumentAst(None, ast.rhs, None, False, pos)
        fn_call = Ast.PostfixFunctionCallAst([], [rhs], pos)
        fn_call = Ast.PostfixExpressionAst(fn, fn_call, pos)
        SemanticAnalysis.analyse_expression(fn_call, s)

    @staticmethod
    def analyse_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs):
        lhs_type = TypeInfer.infer_expression(ast.lhs, s)
        lhs_type = isinstance(lhs_type, Ast.TypeTupleAst) and CommonTypes.tup(lhs_type.types) or lhs_type
        sym = s.current_scope.get_symbol(lhs_type.to_identifier(), SymbolTypes.TypeSymbol)
        if not sym:
            raise SystemExit(ErrFmt.err(ast.lhs._tok) + f"Type '{lhs_type}' not found.")

        class_scope = s.global_scope.get_child_scope(lhs_type)
        if not class_scope:
            # Its a generic type (no attributes or methods accessible until constraints are applied)
            # todo: check against all constraints as sup-scopes (when constraints are added to checks)
            raise SystemExit(ErrFmt.err(ast.op._tok) + f"Generic member access not available unless constraints are applied.")

        # For numeric member access, ie "x.0", check the LHS is a tuple type, and that the number is a valid index for
        # the tuple.
        if isinstance(ast.op.identifier, Ast.NumberLiteralBase10Ast):
            # If the member access is a number literal, check the number literal is a valid index for the tuple.
            if not lhs_type.to_identifier().identifier == "std.Tup":
                raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"Cannot index into non-tuple type '{lhs_type}'.")

            if int(ast.op.identifier.integer) >= len(lhs_type.parts[-1].generic_arguments):
                raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"Index {ast.op.identifier.integer} out of range for type '{lhs_type}'.")

        # Else, check the attribute exists on the LHS.
        elif not class_scope.has_symbol_exclusive(ast.op.identifier, SymbolTypes.VariableSymbol): #or s.current_scope.has_symbol("__MOCK_" + ast.op.identifier, SymbolTypes.TypeSymbol)):
            what = "Attribute" if not kwargs.get("call", False) else "Method"
            raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"{what} '{ast.op.identifier}' not found on type '{lhs_type}'.")

        # Check the parts are all initialized.
        while isinstance(ast, Ast.PostfixExpressionAst) and isinstance(ast.lhs, Ast.PostfixExpressionAst):
            ast = ast.lhs

        if not isinstance(ast.lhs, Ast.IdentifierAst):
            return

        sym = s.current_scope.get_symbol(ast.lhs, SymbolTypes.VariableSymbol)
        if not sym.mem_info.is_initialized:
            raise SystemExit(
                "Cannot use a value that is not initialized:\n" +
                ErrFmt.err(sym.mem_info.consume_ast._tok) + f"Value '{ast.lhs}' moved here.\n..." +
                ErrFmt.err(ast.lhs._tok) + f"Value '{ast.lhs}' not initialized.")
        
    @staticmethod
    def analyse_function_arguments(func: Ast.PostfixExpressionAst, fn_target: SymbolTypes.VariableSymbol, asts: list[Ast.FunctionArgumentAst], s: ScopeHandler, **kwargs):
        # Number of memory checks need to occur here. This function handles all function calls, assignment and variable
        # declaration (through the __set__) function.
        ref_borrows = set()
        mut_borrows = set()

        if fn_target and fn_target.meta_data.get("is_method", False) and fn_target.meta_data.get("fn_proto").parameters and fn_target.meta_data.get("fn_proto").parameters[0].is_self:
            asts.insert(0, Ast.FunctionArgumentAst(None, func.lhs.lhs, fn_target.meta_data.get("fn_proto").parameters[0].calling_convention, False, func._tok))

        def collapse_ast_to_list_of_identifiers(ast: Ast.PostfixExpressionAst | Ast.IdentifierAst | Ast.TokenAst):
            match ast:
                case Ast.TokenAst() if ast.tok.token_type == TokenType.KwSelf: return [Ast.IdentifierAst("self", ast.tok)]
                case Ast.IdentifierAst() | Ast.TypeSingleAst(): return [ast]
                case Ast.PostfixExpressionAst() if isinstance(ast.op, Ast.PostfixMemberAccessAst): return collapse_ast_to_list_of_identifiers(ast.lhs) + [ast.op.identifier]
                case _: return []

        for i, arg in enumerate(asts):
            if type(arg.value) in Ast.TypeAst.__args__:
                raise SystemExit(
                    "Cannot pass a type as an argument to a function - maybe\nyou meant to use it as a generic argument?:" +
                    ErrFmt.err(arg.value._tok) + f"Type '{arg.value}' passed as argument.")

            SemanticAnalysis.analyse_expression(arg.value, s)

            check_for_move = isinstance(func.lhs, Ast.IdentifierAst) and (not func.lhs.is_special() or (func.lhs.is_special() and i > 0))
            sym = s.current_scope.get_symbol(arg.value, SymbolTypes.VariableSymbol, error=False)

            # Record the initialization of single identifier let statements, so if their mutability checks fail later,
            # this AST can be pointed back to to show a immutable variable declaration.
            if isinstance(func.lhs, Ast.IdentifierAst) and func.lhs.is_special() and isinstance(arg.value, Ast.IdentifierAst) and not sym.mem_info.is_initialized:
                sym.mem_info.initialization_ast = arg.value

            # Check if the argument being borrowed is valid to borrow from, ie it hasn't yet been moved elsewhere. The
            # convention of the argument doesn't matter at this stage, because moving or borrowing an uninitialized
            # value is illegal.
            if sym and check_for_move and not sym.mem_info.is_initialized:
                raise SystemExit(
                    "Cannot use a value that is not initialized:\n" +
                    ErrFmt.err(sym.mem_info.consume_ast._tok) + f"Value '{arg.value}' moved here.\n..." +
                    ErrFmt.err(arg.value._tok) + f"Value '{arg.value}' not initialized.")

            # No operations can be done on a value at all if any part of it has been moved -- this is because the only
            # way to ensure the object is completely initialized before an operation is to keep it in the same scope,
            # until it can be confirmed that it is completely initialized. Once the missing attributes have been added
            # back, the object is completely initialized, and can be moved or borrowed from.
            if sym and sym.mem_info.is_partially_moved:
                raise SystemExit(
                    "Cannot use a value that is partially moved:\n" +
                    "\n".join([ErrFmt.err(a._tok) + f"Value '{arg.value}' partially moved here - {a} has been moved." for a in sym.mem_info.partially_moved_asts]) + "\n" +
                    ErrFmt.err(arg.value._tok) + f"Value '{arg.value}' is not completely initialized.")

            match arg.calling_convention:
                # Check for law of exclusivity violations if the argument is a borrow of any kind. This enforces that
                # there can only be 1 mutable or n immutable borrows of an object at 1 time. It also allows multiple
                # borrows of non-overlapping parts of an object to occur at the same time, however, such as
                # &mut x.a, &mut x.b, as there is no overlap and is therefore safe.
                case Ast.ParameterPassingConventionReferenceAst():
                    if arg.calling_convention.is_mutable and collapse_ast_to_list_of_identifiers(func.lhs)[-1].identifier != "__set__":  # and ((isinstance(func.lhs, Ast.IdentifierAst) and not func.lhs.identifier == "__set__") or not isinstance(func.lhs, Ast.IdentifierAst)):
                        identifiers = collapse_ast_to_list_of_identifiers(arg.value)
                        if identifiers is None:
                            raise SystemExit(
                                "Cannot borrow from a value that is not a variable:\n" if func.lhs.identifier != "__assign__" else "Cannot assign to a value that's not a variable:\n" +
                                ErrFmt.err(arg.value._tok) + f"Value '{arg.value}' is not a variable.")

                        outermost_identifier = collapse_ast_to_list_of_identifiers(arg.value)[0]
                        outermost_symbol = s.current_scope.get_symbol(outermost_identifier, SymbolTypes.VariableSymbol)

                        if not outermost_symbol.is_mutable and not outermost_symbol.mem_info.is_borrowed_mut:
                            if collapse_ast_to_list_of_identifiers(func.lhs)[-1].identifier == "__assign__":
                                final_error_message = ErrFmt.err(arg.value._tok) + f"Assignment to '{arg.value}' attempted here."
                            else:
                                final_error_message = ErrFmt.err(arg.value._tok) + f"Value '{arg.value}' borrowed mutably here."
                            raise SystemExit(
                                "Cannot take a mutable borrow from an immutable value:\n" +
                                ErrFmt.err(outermost_symbol.mem_info.initialization_ast._tok) + f"Value '{outermost_identifier}' declared immutably here.\n..." +
                                final_error_message)

                    # A mutable borrow of the argument is occurring. Ensure that no part of the argument is already
                    # mutably or immutably borrowed.
                    for currently_borrowed_ast in (ref_borrows | mut_borrows) if arg.calling_convention.is_mutable else mut_borrows:
                        currently_borrowed = collapse_ast_to_list_of_identifiers(currently_borrowed_ast)

                        # &mut a.b.c is illegal if any of [&mut a, &mut a.b, &mut a.b.c] are being borrowed. However, if
                        # only &mut a.d is being borrowed, then &mut a.b.c is legal, as there is no overlap.
                        identifiers = collapse_ast_to_list_of_identifiers(arg.value)
                        check = identifiers[:len(currently_borrowed)] == currently_borrowed or currently_borrowed[:len(identifiers)] == identifiers
                        if check:
                            raise SystemExit(
                                "The Law of Exclusivity requires that either 1 mutable or n\nimmutable borrows can be active at one time, but not\nconcurrently.\n" +
                                ErrFmt.err(currently_borrowed_ast._tok) + f"1st borrow of (part of) '{arg.value}'\n..." +
                                ErrFmt.err(arg.value._tok) + f"2nd borrow of '{arg.value}'.")
                    mut_borrows.add(arg.value) if arg.calling_convention.is_mutable else ref_borrows.add(arg.value)

                case None:
                    # If there is no borrow occurring, then a move is taking place. However, the move may be complete or
                    # partial. Complete moves are when the entire object is moved, and partial moves are when only part
                    # of the object is moved. For example, "let y = a" is a complete move, but "let z = b.c" is a
                    # partial move; that is, "b" is partially moved. Partially moved objects cannot be borrowed from or
                    # moved, until they are complete again.
                    sym = s.current_scope.get_symbol(arg.value, SymbolTypes.VariableSymbol, error=False)
                    if sym:
                        sym.mem_info.is_initialized = False
                        sym.mem_info.consume_ast = arg.value

                    elif isinstance(arg.value, Ast.PostfixExpressionAst) and isinstance(arg.value.op, Ast.PostfixMemberAccessAst):
                        identifier_chain = collapse_ast_to_list_of_identifiers(arg.value)
                        # todo [1] : handle partial moves here

                        outermost_item = arg.value
                        while isinstance(outermost_item, Ast.PostfixExpressionAst):
                            outermost_item = outermost_item.lhs

                        # This check can only happen if the outermost item is an identifier. Otherwise, the outermost
                        # symbol is either a function or struct-initialization -- in either case, an initialized, owned
                        # value.
                        if isinstance(outermost_item, Ast.IdentifierAst):
                            outermost_symbol = s.current_scope.get_symbol(identifier_chain[0], SymbolTypes.VariableSymbol, error=False)
                            if outermost_symbol.mem_info.is_borrowed():
                                raise SystemExit(
                                    "Cannot move from a borrowed context:\n" +
                                    ErrFmt.err(outermost_symbol.mem_info.borrow_ast._tok) + f"Value '{arg.value}' borrowed here.\n..." +
                                    ErrFmt.err(arg.value._tok) + f"Value '{arg.value}' moved here.")
                            else:
                                outermost_symbol.mem_info.is_partially_moved = True
                                outermost_symbol.mem_info.partially_moved_asts.append(arg.value)

    @staticmethod
    def analyse_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler, **kwargs):
        # Check the LHS is a function, and that the arguments match the function's parameters.
        SemanticAnalysis.analyse_expression(ast.lhs, s)
        fn_target, _ = TypeInfer.infer_postfix_function_call(ast, s)
        SemanticAnalysis.analyse_function_arguments(ast, fn_target, ast.op.arguments, s, **kwargs)

    @staticmethod
    def analyse_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler):
        cls_ty = TypeInfer.check_type(ast.lhs, s, check_generics=False)
        if isinstance(cls_ty, Ast.TypeSingleAst):
            raise SystemExit(ErrFmt.err(ast.lhs._tok) + f"Cannot initialize generic type '{cls_ty}'.")
        cls_ty = cls_ty.to_type()

        # Generic parameters check
        # SemanticAnalysis.analyse_type_generic_arguments(ast.lhs.parts[-1].generic_arguments, s)
        required_generic_parameters = TypeInfer.required_generic_parameters_for_cls(cls_ty, s)
        given_generic_arguments = ast.lhs.parts[-1].generic_arguments

        if len(given_generic_arguments) < len(required_generic_parameters):
            raise SystemExit(
                f"Not enough generic parameters have been given to '{cls_ty}:\n" +
                ErrFmt.err(cls_ty._tok) + "Class definition here.\n..." +
                ErrFmt.err(ast.lhs._tok) + f"Generic parameters given: [{', '.join([str(g) for g in given_generic_arguments])}]\n..." +
                ErrFmt.err(ast.lhs._tok) + f"Generic parameters required: [{', '.join([str(g) for g in required_generic_parameters])}]"
            )

        if len(given_generic_arguments) > len(required_generic_parameters):
            # todo: include the inferrable generics in the error message?
            raise SystemExit(
                f"Too many generic parameters have been given to '{cls_ty}:\n" +
                ErrFmt.err(cls_ty._tok) + "Class definition here.\n..." +
                ErrFmt.err(ast.lhs._tok) + f"Generic parameters given: [{', '.join([str(g) for g in given_generic_arguments])}]\n..." +
                ErrFmt.err(ast.lhs._tok) + f"Generic parameters required: [{', '.join([str(g) for g in required_generic_parameters])}] (probably inferrable)" # todo : proof of inferability required
            )

        # After verifying all the generics are given correctly, their types need to be registered in the generic map, so
        # type checking can happen correctly. todo

        # Check that each variable being passed into the initializer is valid, ie hasn't been moved already.
        given_fields = [f.identifier.identifier for f in ast.op.fields if isinstance(f.identifier, Ast.IdentifierAst)]
        for given_field in ast.op.fields:
            SemanticAnalysis.analyse_expression(given_field.value or given_field.identifier, s)

            if isinstance(given_field.value or given_field.identifier, Ast.IdentifierAst) and not s.current_scope.get_symbol(given_field, SymbolTypes.VariableSymbol).mem_info.is_initialized:
                raise SystemExit(ErrFmt.err(given_field._tok) + f"Argument {given_field} is not initialized or has been moved.")
            if isinstance(given_field.value or given_field.identifier, Ast.IdentifierAst):
                s.current_scope.get_symbol(given_field.value or given_field.identifier, SymbolTypes.VariableSymbol).mem_info.is_initialized = False

        # The "default_obj_given" field is a special field that is used to provide a default value for all fields not
        # given explicitly. If this field is present, then all fields not given explicitly are moved from the default
        # object to the current one. The "default_obj_given" field is given by the "else=..." syntax.
        default_objs_given = [f for f in ast.op.fields if isinstance(f.identifier, Ast.TokenAst) and f.identifier.tok.token_type == TokenType.KwElse]
        if len(default_objs_given) > 1:
            raise SystemExit("Only one default object can be given to a struct initializer." +
                ErrFmt.err(default_objs_given[0]._tok) + "First default object given here.\n...\n" +
                ErrFmt.err(default_objs_given[1]._tok) + "Second default object given here.")
        default_obj_given = default_objs_given[0] if default_objs_given else None

        # Get all the actual fields on a class, so that the given arguments can be checked against them.
        # todo : is this check correct? should be checking the type exists?
        cls_definition_scope = s.global_scope.get_child_scope(cls_ty)
        if cls_definition_scope is None:
            raise SystemExit(ErrFmt.err(ast.lhs._tok) + f"Cannot find definition for class '{cls_ty}'.")

        actual_fields = [v.name.identifier for v in cls_definition_scope.all_symbols_exclusive(SymbolTypes.VariableSymbol, sup=False) if not v.is_comptime]
        actual_fields = [a for a in actual_fields if str(a) not in ["call_ref", "call_mut", "call_one"]]

        # If a fields has been given twice, then raise an error
        if given_twice := any_elem([f for f in ast.op.fields if isinstance(f.identifier, Ast.IdentifierAst) and given_fields.count(f.identifier.identifier) > 1]):
            raise SystemExit(ErrFmt.err(given_twice._tok) + f"Field {given_twice} given twice in struct initializer.")

        # If the given fields contains identifiers not present on the class definition, then these are invalid, so raise
        # an error for the first unknown field.
        difference = set(given_fields) - set(actual_fields)
        if difference and (unknown_field := difference.pop()):
            raise SystemExit(ErrFmt.err(ast.op.fields[given_fields.index(unknown_field)]._tok) + f"Struct initializer for '{cls_ty}' contains unknown field: '{unknown_field}'.")

        # If there are less given fields than actual fields, then the default object must be given. If it hasn't been
        # given, then an error is raised.
        if len(given_fields) < len(actual_fields) and not default_obj_given:
            # todo : add the class definition to the error message
            raise SystemExit(ErrFmt.err(ast._tok) + f"Struct initializer for '{cls_ty}' is missing fields: '{', '.join(set(actual_fields) - set(given_fields))}'.")

        # Handle the default object given (if it is given). Make sure it is the correct type, and not a borrowed object
        # from a parameter.
        if default_obj_given:
            default_obj_ty = TypeInfer.infer_expression(default_obj_given.value, s)
            if default_obj_ty != cls_ty:
                raise SystemExit(ErrFmt.err(default_obj_given._tok) + f"Default object given to struct initializer is not of type '{cls_ty}'.")

        # Register all the generic parameters of the class as None in the generic map.
        sym = s.current_scope.get_symbol(cls_ty.to_identifier(), SymbolTypes.TypeSymbol)
        gs = sym.type.generic_parameters
        for g in gs:
            ast.op.generic_map[g.identifier] = None

        # Check each field given is the correct type. Sort the two field lists, as they are going to be iterated at the
        # same time, so their order has to be the same.
        for given, actual in zip(sorted(given_fields), sorted(actual_fields)):
            given_ty = TypeInfer.infer_expression(ast.op.fields[given_fields.index(given)].value or ast.op.fields[given_fields.index(given)].identifier, s)
            actual_ty = cls_definition_scope.get_symbol(Ast.IdentifierAst(actual, -1), SymbolTypes.VariableSymbol).type
            acc_sym = cls_definition_scope.get_symbol(actual_ty.to_identifier(), SymbolTypes.TypeSymbol)

            # Fill in the inferrable generics from the attributes being given
            # -> TODO : shift this to type comparison where-ever that is?
            # -> TODO : also traverse the type tree and replace generic parameters with their actual types

            if type(acc_sym.type) == Ast.TypeSingleAst:
                gi = actual_ty.to_identifier()
                ast.op.generic_map[gi] = given_ty

            check = TypeInfer.types_equal_account_for_generic(actual_ty, given_ty, ast.op.generic_map, s)
            if not check[0]:
                err_pos = (ast.op.fields[given_fields.index(given)].identifier or ast.op.fields[given_fields.index(given)].value)._tok
                raise SystemExit(ErrFmt.err(err_pos) + check[1])  # f"Field '{given}' given to struct initializer is type '{given_ty}', but should be '{actual_ty}'.")

    @staticmethod
    def analyse_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler):
        # The "let" statement has the same semantics as a regular assignment, so treat it the same way. Assignment has
        # the same semantics as a function call, so treat it like that. Ultimately, "let x = 5" becomes "let x: Num" and
        # "x.set(5)", which is then analysed as a function call. There are some extra checks for the "let" though.

        # Check that the type of the variable is not "Void". This is because "Void" values don't exist, and therefore
        # cannot be assigned to a variable.
        let_statement_type = ast.type_annotation or TypeInfer.infer_expression(ast.value, s)
        if let_statement_type == CommonTypes.void():
            raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot define a variable with 'Void' type.")

        new_syms = []

        # For a single variable, infer its type and set it in the symbol table.
        if len(ast.variables) == 1:
            sym = SymbolTypes.VariableSymbol(ast.variables[0].identifier, let_statement_type, is_mutable=ast.variables[0].is_mutable)
            new_syms.append(sym)
            s.current_scope.add_symbol(sym)

        # Handle the tuple assignment case. There are a few special checks that need to take place, mostly concerning
        # destructuring.
        else:
            ty = TypeInfer.infer_expression(ast.value, s)

            # Ensure that the RHS is a tuple type. # todo ?
            if not ty.to_identifier().identifier != "std.Tup":
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot unpack a non-tuple type ({ty}) into to {len(ast.variables)} variables.")

            # Ensure that the tuple contains the correct number of elements.
            if len(ty.parts[-1].generic_arguments) != len(ast.variables):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot unpack a {len(ty.parts[-1].generic_arguments)}-tuple to {len(ast.variables)} variables.")

            # Infer the type of each variable, and set it in the symbol table.
            for variable in ast.variables:
                t = TypeInfer.infer_expression(ty.parts[-1].generic_arguments[ast.variables.index(variable)], s)
                sym = SymbolTypes.VariableSymbol(variable.identifier, t, is_mutable=variable.is_mutable)
                new_syms.append(sym)
                s.current_scope.add_symbol(sym)

        # Handle the "else" clause for the let statement. Check that the type returned from the "else" block is valid.
        if ast.if_null:
            for statement in ast.if_null.body:
                SemanticAnalysis.analyse_statement(statement, s)

            else_ty = TypeInfer.infer_expression(ast.if_null.body[-1], s) if ast.if_null.body else CommonTypes.void()
            if else_ty != let_statement_type:
                raise SystemExit(ErrFmt.err(ast.if_null._tok) + f"Type of else clause for let statement is not of type '{let_statement_type}'. Found '{else_ty}'.")

        # Because the assignment can handle multiple ie "x, y = (1, 2), all the variables will be passed to the
        # assignment in one go, and the assignment will handle the multiple function calls for tuples etc.
        if ast.value:
            mock_assignment_token = Ast.TokenAst(Token("=", TokenType.TkAssign), ast._tok)
            mock_assignment = Ast.AssignmentExpressionAst([x.identifier for x in ast.variables], mock_assignment_token, ast.value, ast._tok)
            SemanticAnalysis.analyse_assignment_expression(mock_assignment, s, let=True)

        for sym in new_syms:
            sym.mem_info.is_initialized = True


    @staticmethod
    def analyse_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler, **kwargs):
        special_function_name = "__set__" if kwargs.get("let", False) else "__assign__"

        # A manual mutability check is performed here, because whilst the function call handles all the memory and
        # mutability checks, the "set" function doesn't exist, so the mutability check has to be done manually.
        for lhs in ast.lhs:

            # Check the LHS is valid for assignment. Only allow assignment to variables or attributes.
            match lhs:
                case Ast.IdentifierAst(): pass
                case Ast.PostfixExpressionAst() if isinstance(lhs.op, Ast.PostfixMemberAccessAst): pass
                case _: raise SystemExit(
                    "Cannot assign to a value that is not a variable or attribute:\n" +
                    ErrFmt.err(lhs._tok) + f"Value '{lhs}' is not a variable or attribute.")

            SemanticAnalysis.analyse_expression(lhs, s)

            # For postfix member access operations, check that the outermost identifier is mutable. Field mutability is
            # dictated by the mutability of the object itself, so only the outermost value needs to be checked.
            while isinstance(lhs, Ast.PostfixExpressionAst) and isinstance(lhs.op, Ast.PostfixMemberAccessAst):
                lhs = lhs.lhs

            # For identifiers, just check the mutability of the identifier in the symbol table. This will also work for
            # the outermost identifier in a postfix member access operation. If the outermost of a member access is a
            # function call ie "a.b.c().d.e" will be "c()", then the mutability is irrelevant, as mutability is tied to
            # values not types.
            # if isinstance(lhs, Ast.IdentifierAst):
            #     sym = s.current_scope.get_symbol(lhs, SymbolTypes.VariableSymbol)
            #     if not sym.is_mutable and sym.mem_info.is_initialized and not sym.is_comptime:
            #         raise SystemExit(ErrFmt.err(lhs._tok) + f"Cannot assign to an immutable variable.")

        # Create a mock function call for the assignment, and analyse it. Do 1 per variable, so that the function call
        # analysis can handle the multiple function calls for tuples etc. Don't analyse the RHS, because the mock
        # function call will analyse the RHS value(s) as arguments, and double-analysis will lead to double-moves etc.
        rhs_ty = TypeInfer.infer_expression(ast.rhs, s)
        if len(ast.lhs) == 1:
            # lhs_sym = s.current_scope.get_symbol(ast.lhs[0], SymbolTypes.VariableSymbol)
            # convention = None
            # if lhs_sym.mem_info.is_borrowed_mut:
            #     convention = Ast.ParameterPassingConventionReferenceAst(True, -1)
            # elif lhs_sym.mem_info.is_borrowed_ref:
            #     convention = Ast.ParameterPassingConventionReferenceAst(False, -1)

            fn_call = Ast.PostfixFunctionCallAst(
                [], [
                    Ast.FunctionArgumentAst(None, ast.lhs[0], Ast.ParameterPassingConventionReferenceAst(True, -1), False, ast.lhs[0]._tok),
                    Ast.FunctionArgumentAst(None, ast.rhs, None, False, ast.rhs._tok)
                ], ast.op._tok)
            fn_call_expr = Ast.PostfixExpressionAst(Ast.IdentifierAst(special_function_name, ast.op._tok), fn_call, ast.op._tok)
            SemanticAnalysis.analyse_postfix_function_call(fn_call_expr, s, **kwargs)

        # The tuple checks have to be done again, because for normal assignment they have to exist, and for assignment
        # from a let statement, the let statement analyser needs to check the tuple types are valid before settings the
        # types of the symbols in the table prior to assignment.
        else:
            # Ensure that the RHS is a tuple type.
            # Ensure that the RHS is a tuple type.
            if not rhs_ty.to_identifier() == "std.Tup":
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot unpack a non-tuple type ({rhs_ty}) into to {len(ast.lhs)} variables.")

            # Ensure that the tuple contains the correct number of elements.
            if len(rhs_ty.parts[-1].generic_arguments) != len(ast.lhs):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot unpack a {len(rhs_ty.parts[-1].generic_arguments)}-tuple to {len(ast.lhs)} variables.")

            # Create a function prototype for each variable in the tuple.
            for i, lhs in enumerate(ast.lhs):
                fn_call = Ast.PostfixFunctionCallAst(
                    [], [
                        Ast.FunctionArgumentAst(None, lhs, Ast.ParameterPassingConventionReferenceAst(False, -1), False, lhs._tok),
                        Ast.FunctionArgumentAst(None, ast.rhs.values[i], None, False, ast.rhs._tok),
                    ], ast.op._tok)
                fn_call_expr = Ast.PostfixExpressionAst(Ast.IdentifierAst(special_function_name, ast.op._tok), fn_call, ast.op._tok)
                SemanticAnalysis.analyse_postfix_function_call(fn_call_expr, s, **kwargs)

        # Set this variable as initialized. All other memory issues will be handled by the function call analysis of the
        # "set" function.
        # todo : this doesn't work? check how the type inference works for attributes (probs needs recursion)
        # todo : issue is for postfix ie a.b.c = 1 etc because the symbol a.b.c doesn't exist
        for variable in ast.lhs:
            while isinstance(variable, Ast.PostfixExpressionAst) and isinstance(variable.op, Ast.PostfixMemberAccessAst):
                variable = variable.lhs
            s.current_scope.get_symbol(variable, SymbolTypes.VariableSymbol).mem_info.is_initialized = True

        # Extra checks for assignment: mutability and type

    @staticmethod
    def analyse_while_statement(ast: Ast.WhileStatementAst, s: ScopeHandler):
        s.enter_scope("while")
        SemanticAnalysis.analyse_expression(ast.condition, s)
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.exit_scope()

def chain_generators(*gens):
    for gen in gens:
        yield from gen
