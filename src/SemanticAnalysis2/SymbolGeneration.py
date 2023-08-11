from src.LexicalAnalysis.Lexer import Lexer

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt, Parser
from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes, VariableSymbolMemoryStatus


class SymbolGeneration:
    @staticmethod
    def generate(ast: Ast.ProgramAst) -> ScopeHandler:
        s = ScopeHandler()
        SymbolGeneration.generate_program(ast, s)
        s.switch_to_global_scope()
        return s

    @staticmethod
    def generate_program(ast: Ast.ProgramAst, s: ScopeHandler):
        for member in ast.module.body.members: SymbolGeneration.generate_module_member(member, s)
        if ast.module.body.import_block:
            for imp in ast.module.body.import_block.imports: SymbolGeneration.generate_import(imp, s)

    @staticmethod
    def generate_module_member(ast: Ast.ModuleMemberAst, s: ScopeHandler):
        match ast:
            case Ast.FunctionPrototypeAst(): SymbolGeneration.generate_function_prototype(ast, s)
            case Ast.ClassPrototypeAst(): SymbolGeneration.generate_class_prototype(ast, s)
            case Ast.EnumPrototypeAst():
                raise SystemExit(ErrFmt.err(ast._tok) + "Enums are not supported yet.")
            case Ast.SupPrototypeNormalAst(): SymbolGeneration.generate_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): SymbolGeneration.generate_sup_prototype(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown module member {ast} being generated. Report as bug.")

    @staticmethod
    def generate_import(ast: Ast.ImportStatementAst, s: ScopeHandler):
        mod_name = f"./TestCode/{ast.module}.spp"
        try:
            mod_code = open(mod_name, "r").read()
        except FileNotFoundError:
            raise SystemExit(ErrFmt.err(ast.module._tok) + f"Module '{ast.module}' not found.")
        ts = ErrFmt.TOKENS
        SymbolGeneration.generate_program(Parser(Lexer(mod_code).lex()).parse(), s)
        ErrFmt.TOKENS = ts

    @staticmethod
    def generate_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler):
        s.current_scope.add_symbol(SymbolTypes.FunctionSymbol(ast.identifier, ast, False, False, False))
        s.enter_scope(ast.identifier)
        [s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier))) for g in ast.generic_parameters]
        s.exit_scope()

    @staticmethod
    def generate_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeHandler):
        ty = Ast.TypeSingleAst([Ast.GenericIdentifierAst(ast.identifier.identifier, [None for _ in range(len(ast.generic_parameters))], ast._tok)], ast._tok)
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(ty.parts[-1].to_identifier(), ast))
        s.enter_scope(ty)
        [s.current_scope.add_symbol(SymbolTypes.TypeSymbol(g.identifier, SymbolGeneration.dummy_generic_type(g.identifier))) for g in ast.generic_parameters]
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(Ast.IdentifierAst("Self", ast.identifier._tok), ast))
        for attr in ast.body.members:
            s.current_scope.add_symbol(SymbolTypes.VariableSymbol(attr.identifier, attr.type_annotation, VariableSymbolMemoryStatus(), False))
        s.exit_scope()

    @staticmethod
    def generate_sup_prototype(ast: Ast.SupPrototypeAst, s: ScopeHandler):
        s.enter_scope(Ast.IdentifierAst(ast.identifier.parts[-1].identifier + "#SUP", ast.identifier._tok))
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(Ast.IdentifierAst("Self", ast.identifier._tok), ast.identifier))
        for member in ast.body.members: SymbolGeneration.generate_sup_member(member, s)
        s.global_scope.get_child_scope(ast.identifier).sup_scopes.append(s.current_scope)
        s.exit_scope()

    @staticmethod
    def generate_sup_member(ast: Ast.SupMemberAst, s: ScopeHandler):
        match ast:
            case Ast.SupMethodPrototypeAst(): SymbolGeneration.generate_sup_method_prototype(ast, s)
            case Ast.SupTypedefAst(): SymbolGeneration.generate_sup_typedef(ast, s)
            case _:
                raise SystemExit(ErrFmt.err(ast._tok) + f"Unknown sup member '{ast}' being generated. Report as bug.")

    @staticmethod
    def generate_sup_method_prototype(ast: Ast.SupMethodPrototypeAst, s: ScopeHandler):
        SymbolGeneration.generate_function_prototype(ast, s)

    @staticmethod
    def generate_sup_typedef(ast: Ast.SupTypedefAst, s: ScopeHandler):
        old_type_sym = s.current_scope.get_symbol(ast.old_type.parts[-1], SymbolTypes.TypeSymbol, error=False)
        if not old_type_sym:
            raise SystemExit(ErrFmt.err(ast.old_type._tok) + f"Type '{ast.old_type}' not found.")

        old_type_scope = s.global_scope.get_child_scope(ast.old_type)
        s.current_scope.add_symbol(SymbolTypes.TypeSymbol(ast.new_type.parts[-1].to_identifier(), old_type_sym.type))
        s.current_scope.sup_scopes.extend(old_type_scope.sup_scopes)

    @staticmethod
    def dummy_generic_type(ast: Ast.IdentifierAst) -> Ast.TypeAst:
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst(ast.identifier, [], ast._tok)], ast._tok)


x = False
