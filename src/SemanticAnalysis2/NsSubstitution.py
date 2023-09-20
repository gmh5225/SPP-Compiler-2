import sys

import watchpoints

from src.SemanticAnalysis2.SymbolTable import ScopeHandler, SymbolTypes
from src.SyntacticAnalysis import Ast


class NsSubstitution:
    @staticmethod
    def substitute_for_program(ast: Ast.ProgramAst, s: ScopeHandler):
        NsSubstitution.substitute_for_module(ast.module, s)
        # s.switch_to_global_scope()

    @staticmethod
    def substitute_for_module(ast: Ast.ModulePrototypeAst, s: ScopeHandler):
        for member in ast.body.members:
            NsSubstitution.substitute_for_module_member(member, s)

    @staticmethod
    def substitute_for_module_member(ast: Ast.ModuleMemberAst, s: ScopeHandler):
        match ast:
            case Ast.ClassPrototypeAst(): NsSubstitution.substitute_for_class_prototype(ast, s)
            case Ast.SupPrototypeNormalAst(): NsSubstitution.substitute_for_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): NsSubstitution.substitute_for_sup_prototype(ast, s)
            case Ast.LetStatementAst(): NsSubstitution.substitute_for_sup_fn_let_statement(ast, s)
            case _:
                raise SystemExit(f"Unknown module member {ast} being substituted. Report as bug.")

    @staticmethod
    def substitute_for_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeHandler):
        s.next_scope()
        for member in ast.body.members:
            NsSubstitution.do_substitution(member.type_annotation, s)
        s.prev_scope()

    @staticmethod
    def substitute_for_sup_prototype(ast: Ast.SupPrototypeAst, s: ScopeHandler):
        s.next_scope()

        for member in ast.body.members:
            NsSubstitution.substitute_sup_member(member, s)

        overload_symbols = [x for x in s.current_scope.all_symbols_exclusive(SymbolTypes.VariableSymbol) if x.name.identifier in ["call_ref", "call_mut", "call_one"]]
        for overload_symbol in overload_symbols:
            NsSubstitution.do_substitution(overload_symbol.type, s)

        s.prev_scope()

    @staticmethod
    def substitute_sup_member(ast: Ast.SupMemberAst, s: ScopeHandler):
        match ast:
            case Ast.SupTypedefAst(): pass
            case Ast.SupMethodPrototypeAst(): NsSubstitution.substitute_for_function_prototype(ast, s)
            case Ast.ClassPrototypeAst(): NsSubstitution.substitute_for_class_prototype(ast, s)
            case Ast.LetStatementAst(): NsSubstitution.substitute_for_sup_fn_let_statement(ast, s)
            case Ast.SupPrototypeNormalAst(): NsSubstitution.substitute_for_sup_prototype(ast, s)
            case Ast.SupPrototypeInheritanceAst(): NsSubstitution.substitute_for_sup_prototype(ast, s)
            case _:
                raise SystemExit(f"Unknown sup member '{type(ast).__name__}' being substituted. Report as bug.")

    @staticmethod
    def substitute_for_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeHandler):
        s.next_scope()
        for param in ast.parameters:
            NsSubstitution.do_substitution(param.type_annotation, s)
        NsSubstitution.do_substitution(ast.return_type, s)
        s.prev_scope()

    @staticmethod
    def substitute_for_sup_fn_let_statement(ast: Ast.LetStatementAst, s: ScopeHandler):
        pass

    @staticmethod
    def do_substitution(ast_type: Ast.TypeAst, s: ScopeHandler):
        sym = s.current_scope.get_symbol(ast_type.to_identifier(), SymbolTypes.TypeSymbol)
        ast_type.register_symbol(sym)
