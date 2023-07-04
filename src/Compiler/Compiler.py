from src.LexicalAnalysis.Tokens import Token
from src.LexicalAnalysis.Lexer import Lexer
from src.SyntacticAnalysis.Ast import ProgramAst
from src.SyntacticAnalysis.Parser import Parser
import pprint, dataclasses

class Compiler:
    _code: str
    _tokens: list[Token]
    _ast: ProgramAst

    def __init__(self, code: str):
        self._code = code
        self._tokens = Lexer(code).lex()
        self._parser = Parser(self._tokens)
        self._ast = self._parser.parse()
        pprint.pprint(dataclasses.asdict(self._ast), sort_dicts=False)
