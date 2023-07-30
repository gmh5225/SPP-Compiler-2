from __future__ import annotations

from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.SymbolGeneration import SymbolTableBuilder
from src.SemanticAnalysis.TypeInference import TypeInference
from src.Compiler.Printer import save_json


class Semantics:
    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast
        self._scope_handler = SymbolTableBuilder.build(ast)
        save_json(self._scope_handler.json(), "_out/symbol_table.json")

        TypeInference.infer(ast, self._scope_handler)
        save_json(self._scope_handler.json(), "_out/type_inferred.json")
