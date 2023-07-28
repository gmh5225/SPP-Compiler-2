from __future__ import annotations

from typing import Optional

from src.SyntacticAnalysis import Ast
from src.LexicalAnalysis.Lexer import Lexer
from src.SyntacticAnalysis.Parser import Parser, ErrorFormatter
from src.SemanticAnalysis2.Scopes import ScopeHandler, Sym



class SymGen:
    @staticmethod
    def build_symtbl(program: Ast.ProgramAst) -> ScopeHandler:
        scope_handler = ScopeHandler()
        SymGen.build_program_symtbl(program, scope_handler)
        return scope_handler

    @staticmethod
    def build_program_symtbl(program: Ast.ProgramAst, scope_handler: ScopeHandler) -> None:
        scope_handler.enter_scope()
        for imp in program.module.body.imports.imports:
            SymGen.build_import_symtbl(imp, scope_handler)
        for decl in program.module.body.members:
            SymGen.build_decl_symtbl(program.module, decl, scope_handler)
        scope_handler.exit_scope()

    @staticmethod
    def build_import_symtbl(imp: Ast.ImportStatementAst, scope_handler: ScopeHandler) -> None:
        # todo : circular imports - check cache of imported modules
        # todo : only make available imp.what-to-import

        mod_contents = open(imp.module.to_string() + ".spp", "r").read()
        mod_ast = Parser(Lexer(mod_contents).lex()).parse()

        scope_handler.enter_scope()
        SymGen.build_program_symtbl(mod_ast, scope_handler)
        scope_handler.exit_scope()

    @staticmethod
    def build_decl_symtbl(mod: Ast.ModulePrototypeAst, decl: Ast.ModuleMemberAst, scope_handler: ScopeHandler) -> None:
        match decl:
            case Ast.FunctionPrototypeAst(): SymGen.build_func_proto_symtbl(mod, decl, scope_handler)
            case Ast.ClassPrototypeAst(): SymGen.build_class_proto_symtbl(mod, decl, scope_handler)
            case Ast.EnumPrototypeAst(): SymGen.build_enum_proto_symtbl(mod, decl, scope_handler)
            case Ast.SupPrototypeNormalAst() | Ast.SupPrototypeInheritanceAst(): SymGen.build_sup_proto_symtbl(mod, decl, scope_handler)
            case _:
                raise Exception(
                    ErrorFormatter.error(decl._tok) +
                    f"Trying to analyse module member of type {decl.__class__.__name__}. Report this as a bug.")

    @staticmethod
    def build_func_proto_symtbl(mod: Optional[Ast.ModulePrototypeAst], func_proto: Ast.FunctionPrototypeAst, scope_handler: ScopeHandler) -> None:
        # todo: utility method for getting function type

        scope_handler.current_scope.add_sym(Sym(mod.identifier, func_proto.identifier, TypeAbstraction.get_function_type(func_proto)))
        scope_handler.enter_scope()
        for param in func_proto.parameters:
            scope_handler.current_scope.add_sym(Sym(None, param.identifier, param.type_annotation))
        for stmt in func_proto.body.statements:
            SymGen.build_stmt_symtbl(stmt, scope_handler)
        scope_handler.exit_scope()

    @staticmethod
    def build_class_proto_symtbl(mod: Ast.ModulePrototypeAst, class_proto: Ast.ClassPrototypeAst, scope_handler: ScopeHandler) -> None:
        # todo: utility method for getting class type

        scope_handler.current_scope.add_sym(Sym(mod.identifier, class_proto.identifier, TypeAbstraction.get_class_type(class_proto)))
        scope_handler.enter_scope()
        for member in class_proto.body.members:
            SymGen.build_class_member_symtbl(member, scope_handler)
        scope_handler.exit_scope()

    @staticmethod
    def build_class_member_symtbl(member: Ast.ClassAttributeAst, scope_handler: ScopeHandler) -> None:
        scope_handler.current_scope.add_sym(Sym(None, member.identifier, member.type_annotation))

    @staticmethod
    def build_enum_proto_symtbl(mod: Ast.ModulePrototypeAst, enum_proto: Ast.EnumPrototypeAst, scope_handler: ScopeHandler) -> None:
        # todo: utility method for getting enum type

        scope_handler.current_scope.add_sym(Sym(mod.identifier, enum_proto.identifier, TypeAbstraction.get_enum_type(enum_proto)))

    @staticmethod
    def build_sup_proto_symtbl(mod: Ast.ModulePrototypeAst, sup_proto: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, scope_handler: ScopeHandler) -> None:
        class_to_implement_on = sup_proto.identifier
        class_sym = scope_handler.current_scope.get_sym(class_to_implement_on.to_string())
        if not class_sym:
            raise Exception(
                ErrorFormatter.error(sup_proto.identifier._tok) +
                f"Class {class_to_implement_on.to_string()} not found in current scope.")

        scope_handler.enter_scope()
        class_sym.bases.append(scope_handler.current_scope)
        for member in sup_proto.body.members:
            SymGen.build_sup_member_symtbl(member, scope_handler)
        scope_handler.exit_scope()

    @staticmethod
    def build_stmt_symtbl(stmt: Ast.StatementAst, scope_handler: ScopeHandler) -> None:
        match stmt:
            case Ast.TypedefStatementAst(): SymGen.build_typedef_stmt_symtbl(stmt, scope_handler)
            case Ast.ReturnStatementAst(): SymGen.build_return_stmt_symtbl(stmt, scope_handler)
            case Ast.LetStatementAst(): SymGen.build_let_stmt_symtbl(stmt, scope_handler)
            case Ast.ExpressionAst(): SymGen.build_expr_stmt_symtbl(stmt, scope_handler)
            case Ast.FunctionPrototypeAst(): SymGen.build_func_proto_symtbl(None, stmt, scope_handler)
            case _:
                raise Exception(
                    ErrorFormatter.error(stmt._tok) +
                    f"Trying to analyse statement of type {stmt.__class__.__name__}. Report this as a bug.")

    @staticmethod
    def build_typedef_stmt_symtbl(typedef_stmt: Ast.TypedefStatementAst, scope_handler: ScopeHandler) -> None:
        # todo: types aren't correct

        scope_handler.current_scope.add_sym(Sym(None, typedef_stmt.new_type, typedef_stmt.old_type))

    @staticmethod
    def build_return_stmt_symtbl(return_stmt: Ast.ReturnStatementAst, scope_handler: ScopeHandler) -> None:
        SymGen.build_expr_symtbl(return_stmt.value, scope_handler)

    @staticmethod
    def build_let_stmt_symtbl(let_stmt: Ast.LetStatementAst, scope_handler: ScopeHandler) -> None:
        for variable in let_stmt.variables:
            scope_handler.current_scope.add_sym(Sym(None, variable.identifier, let_stmt.type_annotation))
            if variable.value:
                SymGen.build_expr_symtbl(variable.value, scope_handler)
