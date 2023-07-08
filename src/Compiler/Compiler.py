from src.LexicalAnalysis.Tokens import Token
from src.LexicalAnalysis.Lexer import Lexer
from src.SyntacticAnalysis.Ast import ProgramAst
from src.SyntacticAnalysis.Parser import Parser
# from src.SemanticAnalysis.Semantic import SemanticAnalyser
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
        d = dataclasses.asdict(self._ast)
        open("ast.json", "w").write(pprint.pformat(d, indent=1, compact=True).replace("'", '"').replace("None", "null").replace("False", "false").replace("True", "true"))

        # SemanticAnalyser(self._ast)
