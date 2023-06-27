from src.Ast import ProgramAst
from src.Lexer import Lexer
from src.Parser import Parser
from src.Tokens import Token
import pprint, dataclasses

class Compiler:
    _code: str
    _tokens: list[Token]
    _ast: ProgramAst

    def __init__(self, code: str):
        self._code = code
        self._tokens = Lexer(code).lex()
        print(self._tokens)
        self._parser = Parser(self._tokens)
        self._ast = self._parser.parse()
        pprint.pprint(dataclasses.asdict(self._ast), sort_dicts=False)
