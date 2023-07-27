from src.LexicalAnalysis.Tokens import Token
from src.LexicalAnalysis.Lexer import Lexer, Lexer
from src.SemanticAnalysis.Semantics import Semantics
from src.SyntacticAnalysis.Ast import ProgramAst
from src.SyntacticAnalysis.Parser import Parser

import dataclasses
from src.Compiler.Printer import save_json

class Compiler:
    _code: str
    _tokens: list[Token]
    _ast: ProgramAst

    def __init__(self, code: str):
        self._code = code
        self._tokens = Lexer(code).lex()
        self._parser = Parser(self._tokens)
        self._ast = self._parser.parse()
        d = dataclasses.asdict(self._ast)
        save_json(d, "_out/ast.json")

        Semantics(self._ast)

