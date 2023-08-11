import inspect
from typing import Iterable, Optional, TypeVar

from src.LexicalAnalysis.Tokens import TokenType, Token
from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes, VariableSymbolMemoryStatus
from src.SemanticAnalysis2.CommonTypes import CommonTypes
from src.SemanticAnalysis2.TypeInference import TypeInfer

T = TypeVar("T")
def any_elem(iterable: Iterable[T]) -> Optional[T]:
    for element in iterable:
        if element:
            return element
    return None


class SemanticAnalysis:
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
            case Ast.FunctionPrototypeAst(): SemanticAnalysis.analyse_function_prototype(ast, s)
            case Ast.ClassPrototypeAst(): SemanticAnalysis.analyse_class_prototype(ast, s)
            case Ast.EnumPrototypeAst(): s.skip_scope()
            case Ast.SupPrototypeNormalAst(): SemanticAnalysis.analyse_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): SemanticAnalysis.analyse_sup_prototype(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown module member {ast} being analysed. Report as bug.")

    @staticmethod
    def analyse_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler):
        function_symbol = s.current_scope.get_symbol(ast.identifier, SymbolTypes.FunctionSymbol)[0]
        s.next_scope()

        # Mark global methods as "static" ie don't have a "self" parameter
        if s.current_scope == s.global_scope:
            fun_symbol = s.current_scope.get_symbol(ast.identifier, SymbolTypes.FunctionSymbol)[0]
            fun_symbol.static = True

        # Analyse all the decorators and parameters, and the return type
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        [SemanticAnalysis.analyse_parameter(p, s) for p in ast.parameters]
        TypeInfer.check_type(ast.return_type, s)
        ast.return_type = TypeInfer.infer_type(ast.return_type, s)

        # Analyse the generic type parameters -- they must all be inferrable
        # [s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier))) for g in ast.generic_parameters]
        parameter_types = [p.type_annotation for p in ast.parameters]
        generic_constraints = [g.constraints for g in ast.generic_parameters]
        generic_constraints = [c for c in generic_constraints if c]
        all_individual_types = chain_generators(*[SemanticAnalysis.traverse_type(t, s) for t in parameter_types + generic_constraints])
        temp = {*all_individual_types}

        if g := any_elem([g.as_type() for g in ast.generic_parameters if g.identifier.identifier not in temp]):
            raise SystemExit(ErrFmt.err(g._tok) + "Generic parameter type cannot be inferred.")

        # Make sure abstract methods have no body
        if function_symbol.abstract and ast.body.statements:
            raise SystemExit(
                ErrFmt.err([d for d in ast.decorators if d.identifier.parts == ["meta", "abstractmethod"]][0]._tok) + "Method defined as abstract here\n...\n",
                ErrFmt.err(ast.body.statements[0]._tok) + "Abstract methods cannot have a body.")

        # Analyse each statement
        if not function_symbol.abstract:
            for statement in ast.body.statements:
                SemanticAnalysis.analyse_statement(statement, s)

        # Make sure the return type of the last statement matches the return type of the function, unless the method is
        # abstract, in which case it is allowed to not have a return statement
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body.statements]
        t = TypeInfer.infer_statement(ast.body.statements[-1], s) if ast.body.statements else CommonTypes.void()
        if t != ast.return_type and not function_symbol.abstract:
            err_ast = ast.body.statements[-1] if ast.body.statements else ast.body
            raise SystemExit(ErrFmt.err(err_ast._tok) + f"Expected return type of function to be {ast.return_type}, but got {t}.")

        s.prev_scope()

    @staticmethod
    def analyse_parameter(ast: Ast.FunctionParameterAst, s: ScopeHandler):
        # Analyse the parameter type, and Add the parameter to the current scope.
        ast.type_annotation = TypeInfer.infer_type(ast.type_annotation, s)
        ty = ast.type_annotation if not isinstance(ast.type_annotation.parts[0], Ast.SelfTypeAst) else Ast.IdentifierAst("Self", ast.type_annotation._tok)
        s.current_scope.add_symbol(SymbolTypes.VariableSymbol(ast.identifier, ty, VariableSymbolMemoryStatus(), ast.is_mutable))

        # Analyse the default value
        if ast.default_value:
            SemanticAnalysis.analyse_expression(ast.default_value, s)

    @staticmethod
    def analyse_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeHandler):
        s.next_scope()
        # for g in ast.generic_parameters:
        #     s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier)))
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        [SemanticAnalysis.analyse_class_member(m, s) for m in ast.body.members]
        s.prev_scope()

    @staticmethod
    def analyse_class_member(ast: Ast.ClassAttributeAst, s: ScopeHandler):
        [SemanticAnalysis.analyse_decorator(ast, d, s) for d in ast.decorators]
        ast.type_annotation = TypeInfer.infer_type(ast.type_annotation, s)

    @staticmethod
    def analyse_sup_prototype(ast: Ast.SupPrototypeAst, s: ScopeHandler):
        s.next_scope()
        if type(ast) == Ast.SupPrototypeInheritanceAst:
            TypeInfer.check_type(ast.super_class, s)
        [SemanticAnalysis.analyse_sup_member(ast, m, s) for m in ast.body.members]
        s.prev_scope()

    @staticmethod
    def analyse_sup_member(owner: Ast.SupPrototypeAst, ast: Ast.SupMemberAst, s: ScopeHandler):
        match ast:
            case Ast.SupTypedefAst(): SemanticAnalysis.analyse_sup_typedef(ast, s)
            case Ast.SupMethodPrototypeAst(): SemanticAnalysis.analyse_sup_method_prototype(owner, ast, s)

    @staticmethod
    def analyse_sup_method_prototype(owner: Ast.SupPrototypeAst, ast: Ast.SupMethodPrototypeAst, s: ScopeHandler):
        if isinstance(owner, Ast.SupPrototypeInheritanceAst):
            super_class_scope = s.global_scope.get_child_scope(owner.super_class)

            # Make sure the method exists in the super class.
            if not super_class_scope.has_symbol_exclusive(ast.identifier, SymbolTypes.FunctionSymbol):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Method '{ast.identifier}' not found in super class '{owner.super_class}'.")

            # Make sure the method in the super-class is overridable -- virtual or abstract.
            if not super_class_scope.get_symbol_exclusive(ast.identifier, SymbolTypes.FunctionSymbol)[0].overridable():
                raise SystemExit(ErrFmt.err(ast._tok) + f"Method '{ast.identifier}' in super class '{owner.super_class}' is not virtual or abstract.")

        SemanticAnalysis.analyse_function_prototype(ast, s)

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
        match [i.identifier for i in ast.identifier.parts]:
            case ["meta", "private"]: ...
            case ["meta", "public"]: ...
            case ["meta", "protected"]: ...
            case ["meta", "virtualmethod"]:
                if not isinstance(apply_to, Ast.FunctionPrototypeAst): raise SystemExit(ErrFmt.err(ast._tok) + "virtualmethod decorator can only be applied to functions.")
                fun_symbol = s.current_scope.get_symbol(apply_to.identifier, SymbolTypes.FunctionSymbol)[0]
                fun_symbol.virtual = True
            case ["meta", "abstractmethod"]:
                if not isinstance(apply_to, Ast.FunctionPrototypeAst): raise SystemExit(ErrFmt.err(ast._tok) + "abstractmethod decorator can only be applied to functions.")
                fun_symbol = s.current_scope.get_symbol(apply_to.identifier, SymbolTypes.FunctionSymbol)[0]
                fun_symbol.abstract = True
            case ["meta", "staticmethod"]:
                if not isinstance(apply_to, Ast.FunctionPrototypeAst): raise SystemExit(ErrFmt.err(ast._tok) + "staticmethod decorator can only be applied to functions.")
                fun_symbol = s.current_scope.get_symbol(apply_to.identifier, SymbolTypes.FunctionSymbol)[0]
                fun_symbol.static = True
            case ["meta", _]:
                raise SystemExit(ErrFmt.err(ast._tok) + "Unknown meta decorator.")
            case _:
                # todo : normal decorator application
                ...

    @staticmethod
    def analyse_typedef(ast: Ast.TypedefStatementAst, s: ScopeHandler):
        # Analyse the old type, then add a symbol for the new type that points to the old type.
        ast.old_type = TypeInfer.infer_type(ast.old_type, s)
        old_type_sym = s.current_scope.get_symbol(ast.old_type.parts[-1].identifier, SymbolTypes.TypeSymbol)
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(ast.new_type.parts[-1].to_identifier(), old_type_sym.type, old_type_sym.sup_scopes))

    @staticmethod
    def analyse_expression(ast: Ast.ExpressionAst, s: ScopeHandler):
        match ast:
            case Ast.IdentifierAst(): SemanticAnalysis.analyse_identifier(ast, s)
            case Ast.LambdaAst(): raise NotImplementedError("Lambda expressions are not implemented yet.")
            case Ast.IfStatementAst(): SemanticAnalysis.analyse_if_statement(ast, s)
            case Ast.WhileStatementAst(): SemanticAnalysis.analyse_while_statement(ast, s)
            case Ast.YieldStatementAst(): raise NotImplementedError("Yield expressions are not implemented yet.")
            case Ast.WithStatementAst(): SemanticAnalysis.analyse_with_statement(ast, s)
            case Ast.InnerScopeAst(): SemanticAnalysis.analyse_inner_scope(ast, s)
            case Ast.BinaryExpressionAst(): SemanticAnalysis.analyse_binary_expression(ast, s)
            case Ast.PostfixExpressionAst(): SemanticAnalysis.analyse_postfix_expression(ast, s)
            case Ast.AssignmentExpressionAst(): SemanticAnalysis.analyse_assignment_expression(ast, s)
            case Ast.PlaceholderAst(): raise NotImplementedError("Placeholder expressions are not implemented yet.")
            case Ast.TypeSingleAst(): TypeInfer.check_type(ast, s)
            case _:
                if type(ast) in Ast.LiteralAst.__args__ or type(ast) in Ast.NumberLiteralAst.__args__: return
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown expression {ast} being analysed. Report as bug.")

    @staticmethod
    def analyse_postfix_expression(ast: Ast.PostfixExpressionAst, s: ScopeHandler):
        match ast.op:
            case Ast.PostfixMemberAccessAst(): SemanticAnalysis.analyse_postfix_member_access(ast, s)
            case Ast.PostfixFunctionCallAst(): SemanticAnalysis.analyse_postfix_function_call(ast, s)
            case Ast.PostfixStructInitializerAst(): SemanticAnalysis.analyse_postfix_struct_initializer(ast, s)
            case _: raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown postfix expression {ast} being analysed. Report as bug.")

    @staticmethod
    def analyse_identifier(ast: Ast.IdentifierAst, s: ScopeHandler):
        # Special assignment dummy method to check the statement and avoid code duplication.
        if ast.identifier == "__set__":
            return
        if not s.current_scope.has_symbol(ast, SymbolTypes.VariableSymbol):
            raise SystemExit(ErrFmt.err(ast._tok) + f"Identifier {ast} not found in scope.")

    @staticmethod
    def analyse_if_statement(ast: Ast.IfStatementAst, s: ScopeHandler, **kwargs):
        s.next_scope()
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
                        ErrFmt.err(ast.branches[0].body[-1]._tok) + f"First branch returns type '{ret_type}'\n...\n" +
                        ErrFmt.err(b.body[-1]._tok) + f"Branch {i} returns type '{t}'.")

        s.prev_scope()

    @staticmethod
    def analyse_pattern_statement(owner: Ast.IfStatementAst, ast: Ast.PatternStatementAst, s: ScopeHandler):
        s.next_scope()
        # Check there isn't a comparison operator in the if-statement and the pattern statement.
        if owner.comparison_op and ast.comparison_op:
            raise SystemExit(
                "Cannot have a comparison operator in both the if-statement and the pattern statement." +
                ErrFmt.err(owner._tok) + "Comparison operator in if-statement.\n...\n" +
                ErrFmt.err(ast._tok) + "Comparison operator in pattern statement.")

        # Check the comparison function exists for each pattern in the pattern statement.
        pat_comp = ast.comparison_op or owner.comparison_op
        for pat in ast.patterns:
            bin_comp = Ast.BinaryExpressionAst(owner.condition, pat_comp, pat, pat_comp._tok)
            SemanticAnalysis.analyse_expression(bin_comp, s)

        # Check the pattern guard
        if ast.guard:
            SemanticAnalysis.analyse_expression(ast.guard, s)

        # Check each statement in the pattern statement.
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.prev_scope()

    @staticmethod
    def analyse_inner_scope(ast: Ast.InnerScopeAst, s: ScopeHandler):
        s.next_scope()
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.prev_scope()

    @staticmethod
    def analyse_with_statement(ast: Ast.WithStatementAst, s: ScopeHandler):
        s.next_scope()
        SemanticAnalysis.analyse_expression(ast.value, s)
        s.current_scope.get_symbol(ast.alias.identifier, SymbolTypes.VariableSymbol).mem_info.is_initialized = True
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.prev_scope()

    @staticmethod
    def analyse_binary_expression(ast: Ast.BinaryExpressionAst, s: ScopeHandler):
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
        SemanticAnalysis.analyse_expression(fn_call, s)

    @staticmethod
    def analyse_postfix_member_access(ast: Ast.PostfixExpressionAst, s: ScopeHandler):
        lhs_type = TypeInfer.infer_expression(ast.lhs, s)
        # lhs_type = TypeInfer.infer_type(lhs_type, s)
        lhs_type = isinstance(lhs_type, Ast.TypeTupleAst) and CommonTypes.tuple(lhs_type.types) or lhs_type
        class_scope = s.global_scope.get_child_scope(lhs_type)

        # For numeric member access, ie "x.0", check the LHS is a tuple type, and that the number is a valid index for
        # the tuple.
        if isinstance(ast.op.identifier, Ast.NumberLiteralBase10Ast):
            # If the member access is a number literal, check the number literal is a valid index for the tuple.
            if not (lhs_type.parts[0].identifier == "std" and lhs_type.parts[1].identifier == "Tup" and len(lhs_type.parts) == 2):
                raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"Cannot index into non-tuple type '{lhs_type}'.")

            if int(ast.op.identifier.integer) >= len(lhs_type.parts[1].generic_arguments):
                raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"Index {ast.op.identifier.integer} out of range for type '{lhs_type}'.")

        # Else, check the attribute exists on the LHS.
        elif not (class_scope.has_symbol_exclusive(ast.op.identifier, SymbolTypes.VariableSymbol) or class_scope.has_symbol_exclusive(ast.op.identifier, SymbolTypes.FunctionSymbol)):
            raise SystemExit(ErrFmt.err(ast.op.identifier._tok) + f"Attribute '{ast.op.identifier}' not found in type '{lhs_type}'.")
        
    @staticmethod
    def analyse_postfix_function_call(ast: Ast.PostfixExpressionAst, s: ScopeHandler):
        # Verify the LHS is valid
        SemanticAnalysis.analyse_expression(ast.lhs, s)

        ref_args = {}
        mut_args = {}
        arg_ts   = []

        # TODO : multiple partial moves are not checked at the moment
        # TODO : add "self" into the arguments

        for i, arg in enumerate(ast.op.arguments):
            # Check the argument is valid.
            SemanticAnalysis.analyse_expression(arg.value, s)

            # No calling convention means that a move is taking place.
            if not arg.calling_convention:
                # This can only happen from a non-borrowed context, so check that the argument is an attribute of a borrowed variable.
                if isinstance(arg.value, Ast.PostfixExpressionAst) and isinstance(arg.value.op, Ast.PostfixMemberAccessAst) and (value := arg.value):

                    # For a move to be valid, no part of the attribute chain can be borrowed.
                    while isinstance(value, Ast.PostfixExpressionAst) and isinstance(value.op, Ast.PostfixMemberAccessAst):
                        if value in ref_args: raise SystemExit(ErrFmt.err(value._tok) + f"Cannot move a value that is already borrowed.")
                        if value in mut_args: raise SystemExit(ErrFmt.err(value._tok) + f"Cannot move a value that is already mutably borrowed.")
                        value = value.lhs

                elif isinstance(arg.value, Ast.IdentifierAst) and (value := arg.value):
                    if value in ref_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot move a value that is already borrowed.")
                    if value in mut_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot move a value that is already mutably borrowed.")
                    sym = s.current_scope.get_symbol(value, SymbolTypes.VariableSymbol)
                    sym.mem_info.is_initialized = False

            # Handle mutable borrows
            if arg.calling_convention and arg.calling_convention.is_mutable:
                # Because field mutability is determines by the mutability of the actual object itself, only the
                # outermost value on the member access, up-to a function call, has to be mutable. However, each
                # attribute in the chain has to be checked for borrowed. "a.b" cannot be mutably borrowed if "a" is
                # borrowed. However, "a.b" and "a.c" can be borrowed mutably at the same time, as there is no overlap.
                if isinstance(arg.value, Ast.PostfixExpressionAst) and isinstance(arg.value.op, Ast.PostfixMemberAccessAst) and (value := arg.value):
                    while isinstance(value, Ast.PostfixExpressionAst) and isinstance(value.op, Ast.PostfixMemberAccessAst):
                        if value in mut_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot mutably borrow a value that is already mutably borrowed.")
                        if value in ref_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot mutably borrow a value that is already immutably borrowed.")
                        value = value.lhs
                    mut_args |= {value}

                    # Check the outermost identifier is mutable. The mutability of a value dictates the mutability of
                    # its fields, so only the outermost value needs to be checked.
                    if isinstance(value, Ast.IdentifierAst):
                        sym = s.current_scope.get_symbol(value, SymbolTypes.VariableSymbol)
                        if not sym.is_mutable: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot mutably borrow from an immutable value.")

                    # If the outermost value is the result of a function call, then the value being returned cannot have
                    # any active borrows, and mutability is determined by values, not types, so the borrow will always
                    # be valid. No checks are needed.

                # For a single identifier, just check that it isn't borrowed, and that it is mutable.
                elif isinstance(arg.value, Ast.IdentifierAst) and (value := arg.value):
                    sym = s.current_scope.get_symbol(arg.value, SymbolTypes.VariableSymbol)
                    if value in mut_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot mutably borrow a value that is already mutably borrowed.")
                    if value in ref_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot mutably borrow a value that is already immutably borrowed.")
                    if not sym.is_mutable: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot mutably borrow from an immutable value.")
                    mut_args |= {value}

            # Handle immutable borrows -- they are slightly more relaxed than mutable borrows, as they can overlap, and
            # n immutable borrows can occur at the same time (but not with a mutable borrow).
            if arg.calling_convention and not arg.calling_convention.is_mutable:
                # The mutability of the outermost value doesn't matter for an immutable borrow. The only check required
                # is that not part of the value is not mutably borrowed.
                if isinstance(arg.value, Ast.PostfixExpressionAst) and isinstance(arg.value.op, Ast.PostfixMemberAccessAst) and (value := arg.value):
                    while isinstance(value, Ast.PostfixExpressionAst) and isinstance(value.op, Ast.PostfixMemberAccessAst):
                        if value in ref_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot immutably borrow a value that is already immutably borrowed.")
                        value = value.lhs
                    ref_args |= {value}

                # For a single identifier, just check that it isn't borrowed mutably.
                elif isinstance(arg.value, Ast.IdentifierAst) and (value := arg.value):
                    if value in mut_args: raise SystemExit(ErrFmt.err(arg.value._tok) + f"Cannot immutably borrow a value that is already mutably borrowed.")
                    ref_args |= {value}

    @staticmethod
    def analyse_postfix_struct_initializer(ast: Ast.PostfixExpressionAst, s: ScopeHandler):
        print(f"STRUCT-INIT {ast}")

        cls_ty = TypeInfer.check_type(ast.lhs, s)

        # Check that each variable being passed into the initializer is valid, ie hasn't been moved already.
        given_fields = [f.identifier.identifier for f in ast.op.fields if isinstance(f.identifier, Ast.IdentifierAst)]
        for given_field in ast.op.fields:
            SemanticAnalysis.analyse_expression(given_field.value or given_field.identifier, s)

            if isinstance(given_field.value or given_field.identifier, Ast.IdentifierAst) and not s.current_scope.get_symbol(given_field, SymbolTypes.VariableSymbol).mem_info.is_initialized:
                raise SystemExit(ErrFmt.err(given_field._tok) + f"Argument {given_field} is not initialized or has been moved.")
            print(given_field)
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
        cls_definition_scope = s.global_scope.get_child_scope(cls_ty)
        if cls_definition_scope is None:
            raise SystemExit(ErrFmt.err(ast.lhs._tok) + f"Cannot find definition for class '{cls_ty}'.")

        actual_fields = [v.name.identifier for v in cls_definition_scope.all_symbols_exclusive(SymbolTypes.VariableSymbol)]

        # If a fields has been given twice, then raise an error
        if given_twice := any_elem([f for f in ast.op.fields if given_fields.count(f.identifier.identifier) > 1]):
            raise SystemExit(ErrFmt.err(given_twice._tok) + f"Field {given_twice} given twice in struct initializer.")

        # If the given fields contains identifiers not present on the class definition, then these are invalid, so raise
        # an error for the first unknown field.
        difference = set(given_fields) - set(actual_fields)
        if difference and (unknown_field := difference.pop()):
            raise SystemExit(ErrFmt.err(ast.op.fields[given_fields.index(unknown_field)]._tok) + f"Struct initializer for '{cls_ty}' contains unknown fields: '{unknown_field}'.")

        # If there are less given fields than actual fields, then the default object must be given. If it hasn't been
        # given, then an error is raised.
        if len(given_fields) < len(actual_fields) and not default_obj_given:
            # todo : add the class definition to the error message
            raise SystemExit(ErrFmt.err(ast.op._tok) + f"Struct initializer for '{cls_ty}' is missing fields: '{','.join(set(actual_fields) - set(given_fields))}'.")

        # Handle the default object given (if it is given). Make sure it is the correct type, and not a borrowed object
        # from a parameter.
        if default_obj_given:
            default_obj_ty = TypeInfer.infer_expression(default_obj_given.value, s)
            if default_obj_ty != cls_ty:
                raise SystemExit(ErrFmt.err(default_obj_given._tok) + f"Default object given to struct initializer is not of type '{cls_ty}'.")

        # Check each field given is the correct type. Sort the two field lists, as they are going to be iterated at the
        # same time, so their order has to be the same.
        for given, actual in zip(sorted(given_fields), sorted(actual_fields)):
            given_ty = TypeInfer.infer_expression(ast.op.fields[given_fields.index(given)].value or ast.op.fields[given_fields.index(given)].identifier, s)
            actual_ty = cls_definition_scope.get_symbol(Ast.IdentifierAst(identifier=actual, _tok=-1), SymbolTypes.VariableSymbol).type

            if given_ty != actual_ty:
                err_pos = (ast.op.fields[given_fields.index(given)].value or ast.op.fields[given_fields.index(given)].identifier)._tok
                raise SystemExit(ErrFmt.err(err_pos) + f"Field '{given}' given to struct initializer is type '{given_ty}', but should be '{actual_ty}'.")

    @staticmethod
    def analyse_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler):
        # The "let" statement has the same semantics as a regular assignment, so treat it the same way. Assignment has
        # the same semantics as a function call, so treat it like that. Ultimately, "let x = 5" becomes "let x: Num" and
        # "x.set(5)", which is then analysed as a function call. There are some extra checks for the "let" though.

        # Check that the type of the variable is not "Void". This is because "Void" values don't exist, and therefore
        # cannot be assigned to a variable.
        let_statement_type = TypeInfer.infer_type(ast.type_annotation, s) if ast.type_annotation else TypeInfer.infer_expression(ast.value, s)
        if let_statement_type == CommonTypes.void():
            raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot define a variable with 'Void' type.")

        # For a single variable, infer its type and set it in the symbol table.
        if len(ast.variables) == 1:
            s.current_scope.add_symbol(SymbolTypes.VariableSymbol(ast.variables[0].identifier, let_statement_type, VariableSymbolMemoryStatus(), ast.variables[0].is_mutable))

        # Handle the tuple assignment case. There are a few special checks that need to take place, mostly concerning
        # destructuring.
        else:
            ty = TypeInfer.infer_expression(ast.value, s)

            # Ensure that the RHS is a tuple type.
            if not isinstance(ty, Ast.TypeTupleAst):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot assign non-tuple type to a tuple. Found {ty}")

            # Ensure that the tuple contains the correct number of elements.
            if len(ty.types) != len(ast.variables):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot assign tuple of length {len(ty.types)} to a tuple of length {len(ast.variables)}.")

            # Infer the type of each variable, and set it in the symbol table.
            for variable in ast.variables:
                t = TypeInfer.infer_expression(ty.types[ast.variables.index(variable)], s)
                s.current_scope.add_symbol(SymbolTypes.VariableSymbol(variable.identifier, t, VariableSymbolMemoryStatus(), variable.is_mutable))

        # Handle the "else" clause for the let statement. Check that the type returned from the "else" block is valid.
        if ast.if_null and (else_ty := TypeInfer.infer_expression(ast.if_null, s)) != let_statement_type:
            raise SystemExit(ErrFmt.err(ast.if_null._tok) + f"Type of else clause for let statement is not of type '{let_statement_type}'. Found '{else_ty}'")

        # Because the assignment can handle multiple ie "x, y = (1, 2), all the variables will be passed to the
        # assignment in one go, and the assignment will handle the multiple function calls for tuples etc.
        mock_assignment = Ast.AssignmentExpressionAst([x.identifier for x in ast.variables], Ast.TokenAst(Token("=", TokenType.TkAssign), ast._tok), ast.value, ast._tok)
        SemanticAnalysis.analyse_assignment_expression(mock_assignment, s)

    @staticmethod
    def analyse_assignment_expression(ast: Ast.AssignmentExpressionAst, s: ScopeHandler):
        # A manual mutability check is performed here, because whilst the function call handles all the memory and
        # mutability checks, the "set" function doesn't exist, so the mutability check has to be done manually.
        for lhs in ast.lhs:
            # For postfix member access operations, check that the outermost identifier is mutable. Field mutability is
            # dictated by the mutability of the object itself, so only the outermost value needs to be checked.
            while isinstance(lhs, Ast.PostfixExpressionAst) and isinstance(lhs.op, Ast.PostfixMemberAccessAst):
                lhs = lhs.lhs

            # For identifiers, just check the mutability of the identifier in the symbol table. This will also work for
            # the outermost identifier in a postfix member access operation. If the outermost of a member access is a
            # function call ie "a.b.c().d.e" will be "c()", then the mutability is irrelevant, as mutability is tied to
            # values not types.
            if isinstance(lhs, Ast.IdentifierAst):
                sym = s.current_scope.get_symbol(lhs, SymbolTypes.VariableSymbol)
                if not sym.is_mutable and sym.mem_info.is_initialized:
                    raise SystemExit(ErrFmt.err(lhs._tok) + f"Cannot assign to an immutable variable.")

        # Create a mock function call for the assignment, and analyse it. Do 1 per variable, so that the function call
        # analysis can handle the multiple function calls for tuples etc.
        ty = TypeInfer.infer_expression(ast.rhs, s)
        if len(ast.lhs) == 1:
            fn_call = Ast.PostfixFunctionCallAst(
                [], [
                    Ast.FunctionArgumentAst(None, ast.lhs[0], None, False, ast.lhs[0]._tok),
                    Ast.FunctionArgumentAst(None, ast.rhs, None, False, ast.rhs._tok)
                ], ast.op._tok)
            fn_call_expr = Ast.PostfixExpressionAst(Ast.IdentifierAst("__set__", ast.op._tok), fn_call, ast.op._tok)
            SemanticAnalysis.analyse_postfix_function_call(fn_call_expr, s)

        # The tuple checks have to be done again, because for normal assignment they have to exist, and for assignment
        # from a let statement, the let statement analyser needs to check the tuple types are valid before settings the
        # types of the symbols in the table prior to assignment.
        else:
            # Ensure that the RHS is a tuple type.
            if not isinstance(ty, Ast.TypeTupleAst):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot assign non-tuple type to a tuple. Found {ty}")

            # Ensure that the tuple contains the correct number of elements.
            if len(ty.types) != len(ast.lhs):
                raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot assign tuple of length {len(ty.types)} to a tuple of length {len(ast.lhs)}.")

            # Create a function prototype for each variable in the tuple.
            for i, lhs in enumerate(ast.lhs):
                fn_call = Ast.PostfixFunctionCallAst(
                    [], [
                        Ast.FunctionArgumentAst(None, lhs, None, False, lhs._tok),
                        Ast.FunctionArgumentAst(None, ast.rhs.values[i], None, False, ast.rhs._tok),
                    ], ast.op._tok)
                fn_call_expr = Ast.PostfixExpressionAst(Ast.IdentifierAst("__set__", ast.op._tok), fn_call, ast.op._tok)
                SemanticAnalysis.analyse_postfix_function_call(fn_call_expr, s)

        # Set this variable as initialized. All other memory issues will be handled by the function call analysis of the
        # "set" function.
        for variable in ast.lhs:
            s.current_scope.get_symbol(variable, SymbolTypes.VariableSymbol).mem_info.is_initialized = True

    @staticmethod
    def analyse_while_statement(ast: Ast.WhileStatementAst, s: ScopeHandler):
        s.next_scope()
        SemanticAnalysis.analyse_expression(ast.condition, s)
        [SemanticAnalysis.analyse_statement(st, s) for st in ast.body]
        s.prev_scope()

    @staticmethod
    def traverse_type(ast: Ast.TypeAst | Ast.GenericIdentifierAst, s: ScopeHandler):
        match ast:
            case Ast.GenericIdentifierAst():
                yield ast.identifier
                for t in ast.generic_arguments:
                    yield from SemanticAnalysis.traverse_type(t.value, s)
            case Ast.TypeSingleAst():
                yield ast.parts[-1].identifier
                for t in ast.parts:
                    yield from SemanticAnalysis.traverse_type(t, s)
            case Ast.TypeTupleAst():
                for t in ast.types:
                    yield from SemanticAnalysis.traverse_type(t, s)
            case Ast.SelfTypeAst():
                sym = s.current_scope.get_symbol(Ast.IdentifierAst("Self", ast._tok), SymbolTypes.TypeSymbol)
                yield sym.type.parts[-1].identifier
            case _:
                print(" -> ".join(list(reversed([f.frame.f_code.co_name for f in inspect.stack()]))))
                raise SystemExit(ErrFmt.err(ast._tok) + f"Type '{type(ast)}' not yet supported for traversal. Report as bug.")

def chain_generators(*gens):
    for gen in gens:
        yield from gen
