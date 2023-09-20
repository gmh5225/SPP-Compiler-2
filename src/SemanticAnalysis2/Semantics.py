from src.SyntacticAnalysis import Ast

from src.SemanticAnalysis2.SymbolGeneration import SymbolGeneration
from src.Compiler.Printer import save_json


class Semantics:
    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast
        s = SymbolGeneration.generate(ast)
        save_json(s.json(), "_out/symbol_table.json")
