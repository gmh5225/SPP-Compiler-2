from src.LexicalAnalysis.Tokens import Token
from src.LexicalAnalysis.Lexer import Lexer
from src.SyntacticAnalysis.Ast import ProgramAst
from src.SyntacticAnalysis.Parser import Parser

from src.SemanticAnalysis2.Semantics import Semantics

import dataclasses
from src.Compiler.Printer import save_json

class Compiler:
    _code: str
    _tokens: list[Token]
    _ast: ProgramAst

    def __init__(self, code: str):
        # Load the code into the Compiler class.
        self._code = code

        # Lex the code into a stream of tokens.
        self._tokens = Lexer(code).lex()

        # Parse the tokens into an AST.
        self._ast = Parser(self._tokens).parse()

        d = dataclasses.asdict(self._ast)
        save_json(d, "_out/ast.json")

        Semantics(self._ast)

