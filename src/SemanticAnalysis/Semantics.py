from __future__ import annotations
from src.SemanticAnalysis.SymbolTable import SymbolTableBuilder, ScopeManager
from src.SyntacticAnalysis import Ast
from src.Compiler.Printer import save_json


class Semantic:
    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast
        self._scope_manager = ScopeManager(self._ast.module.identifier)
        SymbolTableBuilder.build_program(self._ast, self._scope_manager)

        save_json(self._scope_manager.json(), "_out/symbol_table.json")
