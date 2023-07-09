import json

from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolTableGeneration import SymbolTableGenerator, ScopeManager
from src.Compiler.Printer import save_json


class SemanticAnalysis:
    _program_ast: Ast.ProgramAst

    def __init__(self, ast: Ast.ProgramAst):
        self._program_ast = ast
        self._generate_symbol_table()

    def _generate_symbol_table(self):
        scope_manager = ScopeManager()
        SymbolTableGenerator.build_symbols_program(self._program_ast, scope_manager)
        # json.dump(scope_manager.global_scope.to_json(), open("_out/symbols.json", "w"))
        save_json(scope_manager.global_scope.to_json(), "_out/symbols.json")

