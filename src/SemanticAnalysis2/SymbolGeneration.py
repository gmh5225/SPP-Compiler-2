import copy

from src.LexicalAnalysis.Lexer import Lexer
from src.SemanticAnalysis2.NsSubstitution import NsSubstitution
from src.SemanticAnalysis2.SemanticAnalysis import SemanticAnalysis
from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt, Parser
from src.SemanticAnalysis2.AstReduction import AstReduction
from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes
from src.SemanticAnalysis2.ModuleTree import ModuleTree


class SymbolGeneration:
    ALL_MODS = []

    @staticmethod
    def generate(ast: Ast.ProgramAst) -> ScopeHandler:
        s = ScopeHandler()

        module_tree = ModuleTree.grab()
        SymbolGeneration.ALL_MODS = [(s.global_scope, ast)]
        SymbolGeneration.generate_program(ast, s)
        SymbolGeneration.generate_imports(ast, module_tree, s)

        t = copy.deepcopy(s)
        for scope, mod in SymbolGeneration.ALL_MODS:
            # set the scope to the entry point of the module, and perform type-ns substitutions.
            # s.current_scope = scope

            ErrFmt.TOKENS = Lexer(open(".\\TestCode\\" + mod.module.identifier.as_file_path(), "r").read()).lex()
            ErrFmt.FILE_PATH = str(mod.module.identifier)
            NsSubstitution.substitute_for_program(mod, s)


        s.switch_to_global_scope()
        for scope, mod in SymbolGeneration.ALL_MODS:
            # set the scope to the entry point of the module, and perform semantic analysis.
            # s.current_scope = scope

            ErrFmt.TOKENS = Lexer(open(".\\TestCode\\" + mod.module.identifier.as_file_path(), "r").read()).lex()
            ErrFmt.FILE_PATH = str(mod.module.identifier)
            SemanticAnalysis.analyse(mod, s)


        s.switch_to_global_scope()
        return s

    @staticmethod
    def generate_program(ast: Ast.ProgramAst, s: ScopeHandler):
        AstReduction.reduce(ast)
        for member in ast.module.body.members:
            SymbolGeneration.generate_module_member(member, s)

    @staticmethod
    def generate_module_member(ast: Ast.ModuleMemberAst, s: ScopeHandler):
        match ast:
            case Ast.ClassPrototypeAst(): SymbolGeneration.generate_class_prototype(ast, s)
            case Ast.EnumPrototypeAst():
                raise SystemExit(ErrFmt.err(ast._tok) + "Enums are not supported yet.")
            case Ast.SupPrototypeNormalAst(): SymbolGeneration.generate_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): SymbolGeneration.generate_sup_prototype(ast, s)
            case Ast.LetStatementAst(): SymbolGeneration.generate_sup_fn_let_statement(ast, s) # fn building
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown module member {ast} being generated. Report as bug.")

    @staticmethod
    def generate_imports(root: Ast.ProgramAst, files: list[str], s: ScopeHandler):
        for mod_name in files:
            mod_code = open(mod_name, "r").read()

            ts = ErrFmt.TOKENS.copy()
            fp = ErrFmt.FILE_PATH
            open("_out/new_code.spp", "a").write(mod_code)

            new_toks = Lexer(mod_code).lex()
            new_mod = Parser(new_toks, mod_name).parse()

            # Separate all the scopes -- for example, if the module is `a.b.c`, then we need to separate the scopes "a",
            # "b", and "c". Set the current scope to the global scope (where modules are all found, then layered from)
            scopes = new_mod.module.identifier.remove_last().parts
            current = s.global_scope

            # Iterate through the scopes.
            for scope in scopes:

                # If the scope already exists, ie a module in the same directory, then we can just set the current scope
                # to that scope, and generate the program if it's the last scope.
                if scope in [y.name for y in current.children]:
                    c = s.current_scope
                    s.current_scope = current.get_child_scope(scope)
                    if scope == scopes[-1]:
                        SymbolGeneration.generate_program(new_mod, s)
                        SymbolGeneration.ALL_MODS.append((s.current_scope, new_mod))
                    current = s.current_scope

                # Otherwise, we need to create a new scope, and generate the program if it's the last scope.
                else:
                    s.enter_scope(scope, is_mod=True)
                    if scope == scopes[-1]:
                        SymbolGeneration.generate_program(new_mod, s)
                        SymbolGeneration.ALL_MODS.append((s.current_scope, new_mod))

            s.switch_to_global_scope()
            ErrFmt.TOKENS = ts
            ErrFmt.FILE_PATH = fp

    @staticmethod
    def generate_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler):
        is_method = getattr(ast, "is_method", False)
        fn_type = AstReduction.deduce_function_type(is_method, ast.parameters, ast.return_type)

        sym = SymbolTypes.VariableSymbol(ast.identifier, fn_type, is_comptime=True)  # todo : is_comptime needed here?
        sym.meta_data["fn_proto"] = ast
        sym.meta_data["is_method"] = is_method
        s.current_scope.add_symbol(sym)

        s.enter_scope(ast.identifier)
        [s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier))) for g in ast.generic_parameters]
        s.exit_scope()

    @staticmethod
    def generate_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeHandler, hidden: bool = False):
        ty = Ast.TypeSingleAst([ast.identifier.to_generic_identifier()], ast._tok)
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(ty.to_identifier(), ast))

        s.enter_scope(ty, hidden=hidden)
        [s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier))) for g in ast.generic_parameters]

        if not ast.identifier.identifier.startswith("__"):
            s.current_scope.add_symbol(SymbolTypes.TypeSymbol(Ast.IdentifierAst("Self", ast.identifier._tok), ast))

        for attr in ast.body.members:
            s.current_scope.add_symbol(SymbolTypes.VariableSymbol(attr.identifier, attr.type_annotation))

        s.exit_scope()

    @staticmethod
    def generate_sup_prototype(ast: Ast.SupPrototypeAst, s: ScopeHandler, hidden: bool = False):
        s.enter_scope(ast.identifier.to_identifier().identifier + "#SUP", hidden=hidden)

        # todo : ultimately, i want to remove this constraint, but it throws some errors at the moment that i will
        #  handle another time.
        if ast.identifier.has_namespace():
            raise SystemExit(
                "Cannot super-impose onto a class from another module." +
                ErrFmt.err(ast.identifier._tok) + f"Class '{ast.identifier}' is from another module.")

        if not (ast.identifier.parts[-1].identifier.startswith("__") or ast.identifier.parts[-1].identifier[0].islower()):
            s.current_scope.add_symbol(SymbolTypes.TypeSymbol(Ast.IdentifierAst("Self", ast.identifier._tok), ast.identifier))

        for g in ast.generic_parameters:
            s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier)))

        for member in ast.body.members:
            SymbolGeneration.generate_sup_member(member, s)

        cls_scope = s.current_scope.parent.get_child_scope(ast.identifier)

        if not cls_scope:
            raise SystemExit(ErrFmt.err(ast.identifier._tok) + f"Class '{ast.identifier}' not found.")

        cls_scope.sup_scopes.append(s.current_scope)
        # if isinstance(ast, Ast.SupPrototypeInheritanceAst) and ast.super_class.parts[-1].identifier not in ["FnRef", "FnMut", "FnOne"]:
        #     super_class_scope = s.global_scope.get_child_scope(ast.super_class)
        #
        #     cls_scope.sup_scopes.append(s.global_scope.get_child_scope(ast.super_class))
        #     cls_scope.sup_scopes.extend(s.global_scope.get_child_scope(ast.super_class).sup_scopes)

        s.exit_scope()

    @staticmethod
    def generate_sup_member(ast: Ast.SupMemberAst, s: ScopeHandler):
        match ast:
            case Ast.SupMethodPrototypeAst(): SymbolGeneration.generate_sup_method_prototype(ast, s)
            case Ast.SupTypedefAst(): SymbolGeneration.generate_sup_typedef(ast, s)
            case Ast.SupPrototypeNormalAst(): SymbolGeneration.generate_sup_prototype(ast, s, hidden=True) # fn building
            case Ast.SupPrototypeInheritanceAst(): SymbolGeneration.generate_sup_prototype(ast, s, hidden=True) # fn building
            case Ast.ClassPrototypeAst(): SymbolGeneration.generate_class_prototype(ast, s, hidden=True) # fn building
            case Ast.LetStatementAst(): SymbolGeneration.generate_sup_fn_let_statement(ast, s) # fn building
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown sup member '{ast}' being generated. Report as bug.")

    @staticmethod
    def generate_sup_fn_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler):
        sym = SymbolTypes.VariableSymbol(ast.variables[0].identifier, ast.type_annotation, is_mutable=False, is_comptime=True)
        s.current_scope.add_symbol(sym)

    @staticmethod
    def generate_sup_method_prototype(ast: Ast.SupMethodPrototypeAst, s: ScopeHandler):
        SymbolGeneration.generate_function_prototype(ast, s)

    @staticmethod
    def generate_sup_typedef(ast: Ast.SupTypedefAst, s: ScopeHandler):
        old_type_sym = s.current_scope.get_symbol(ast.old_type.to_identifier(), SymbolTypes.TypeSymbol, error=False)
        if not old_type_sym:
            raise SystemExit(ErrFmt.err(ast.old_type._tok) + f"Type '{ast.old_type}' not found.")

        old_type_scope = s.global_scope.get_child_scope(ast.old_type)
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(ast.new_type.to_identifier(), old_type_sym.type))
        s.current_scope.sup_scopes.extend(old_type_scope.sup_scopes)

    @staticmethod
    def dummy_generic_type(ast: Ast.IdentifierAst) -> Ast.TypeAst:
        return Ast.TypeSingleAst([ast.to_generic_identifier()], ast._tok)


x = False
