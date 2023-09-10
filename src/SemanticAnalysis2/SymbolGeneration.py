import dataclasses
import copy

from src.LexicalAnalysis.Lexer import Lexer

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt, Parser
from src.SemanticAnalysis2.AstReduction import AstReduction
from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes


class SymbolGeneration:
    @staticmethod
    def generate(ast: Ast.ProgramAst) -> ScopeHandler:
        s = ScopeHandler()
        AstReduction.reduce(ast)

        from src.Compiler.Printer import save_json
        save_json(dataclasses.asdict(ast), "_out/reduced-ast.json")

        SymbolGeneration.generate_program(ast, s)
        s.switch_to_global_scope()
        return s

    @staticmethod
    def generate_program(ast: Ast.ProgramAst, s: ScopeHandler):
        for member in ast.module.body.members:
            SymbolGeneration.generate_module_member(member, s)

        if ast.module.body.import_block:
            for imp in ast.module.body.import_block.imports: # todo : check against already imported modules
                SymbolGeneration.generate_import(ast, imp, s)

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
    def generate_import(root: Ast.ProgramAst, ast: Ast.ImportStatementAst, s: ScopeHandler):
        mod_name = f"./TestCode/{ast.module}.spp"
        try:
            mod_code = open(mod_name, "r").read()
        except FileNotFoundError:
            raise SystemExit(
                f"The module {ast.module} was not found" +
                ErrFmt.err(ast.module._tok) + f"The module was attempted to be imported here.")

        ts = ErrFmt.TOKENS.copy()
        fp = ErrFmt.FILE_PATH
        open("_out/new_code.spp", "a").write(mod_code)

        new_mod = Parser(Lexer(mod_code).lex(), f"{ast.module}.spp").parse()

        # Separate all the scopes -- for example, if the module is `a.b.c`, then we need to separate the scopes "a",
        # "b", and "c". Set the current scope to the global scope (where modules are all found, then layered from)
        scopes = ast.module.remove_last().parts
        current = s.global_scope
        scope_restore = s.current_scope

        # Iterate through the scopes.
        for scope in scopes:

            # If the scope already exists, ie a module in the same directory, then we can just set the current scope
            # to that scope, and generate the program if it's the last scope.
            if scope in [y.name for y in current.children]:
                c = s.current_scope
                s.current_scope = current.get_child_scope(scope)
                if scope == scopes[-1]:
                    SymbolGeneration.generate_program(new_mod, s)
                current = s.current_scope

            # Otherwise, we need to create a new scope, and generate the program if it's the last scope.
            else:
                s.enter_scope(scope)
                if scope == scopes[-1]:
                    SymbolGeneration.generate_program(new_mod, s)

        s.current_scope = scope_restore

        root.module.body.members.extend(new_mod.module.body.members)

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
        ty = Ast.TypeSingleAst([Ast.GenericIdentifierAst(ast.identifier.identifier, [], ast._tok)], ast._tok)
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

        if not (ast.identifier.parts[-1].identifier.startswith("__") or ast.identifier.parts[-1].identifier[0].islower()):
            s.current_scope.add_symbol(SymbolTypes.TypeSymbol(Ast.IdentifierAst("Self", ast.identifier._tok), ast.identifier))

        for g in ast.generic_parameters: s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier)))
        for member in ast.body.members: SymbolGeneration.generate_sup_member(member, s)

        c = copy.deepcopy(ast)
        c.identifier.parts[-1] = ("__MOCK_" + c.identifier.parts[-1].to_identifier()).to_generic_identifier()
        cls_scope = s.global_scope.get_child_scope(ast.identifier) or s.global_scope.get_child_scope(c.identifier) or s.current_scope.parent.get_child_scope(c.identifier)
        if not cls_scope:
            raise SystemExit(ErrFmt.err(ast.identifier._tok) + f"Class '{ast.identifier}' not found.")

        cls_scope.sup_scopes.append(s.current_scope)
        if isinstance(ast, Ast.SupPrototypeInheritanceAst) and ast.super_class.parts[-1].identifier not in ["FnRef", "FnMut", "FnOne"]:
            cls_scope.sup_scopes.append(s.global_scope.get_child_scope(ast.super_class))
            cls_scope.sup_scopes.extend(s.global_scope.get_child_scope(ast.super_class).sup_scopes)

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
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst(ast.identifier, [], ast._tok)], ast._tok)


x = False
