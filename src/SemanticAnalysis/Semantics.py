from __future__ import annotations
from src.SemanticAnalysis.SymbolTable import SymbolTableBuilder, ScopeManager
from src.SyntacticAnalysis import Ast
from pprint import pprint


class Semantic:
    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast
        self._scope_manager = ScopeManager(self._ast.module.identifier)
        SymbolTableBuilder.build_program(self._ast, self._scope_manager)

        pprint(self._scope_manager.json())
