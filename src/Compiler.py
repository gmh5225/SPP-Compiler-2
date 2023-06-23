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
        self._ast = Parser(self._tokens).parse()

        print("Successfully parsed AST")
        print(vars(self._ast))
        pprint.pprint(dataclasses.asdict(self._ast), sort_dicts=False)
