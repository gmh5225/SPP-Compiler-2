import unittest
from src.Lexer import Lexer
from src.Parser import Parser


def parse(code):
    tok = Lexer(code).lex()
    ast = Parser(tok).parse()
    return ast


class TestParsingExpressions(unittest.TestCase):
    def setUp(self):
        self._boilerplate_module = "module main;"
        self._boilerplate_function = "pub fun main():\n\t"

    def parse_assignment(self):
        code = self._boilerplate_module + self._boilerplate_function + "a = b;"
        ast = parse(code)

    def parse_null_coalescing(self):
        code = self._boilerplate_module + self._boilerplate_function + "a ?? b;"
        ast = parse(code)

    def parse_elvis(self):
        code = self._boilerplate_module + self._boilerplate_function + "a ?: b;"
        ast = parse(code)


