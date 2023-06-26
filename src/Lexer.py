from src.Tokens import Token, TokenType
import re


class Lexer:
    _code: str

    def __init__(self, code: str):
        self._code = code.replace("\t", "    ")

    def lex(self):
        current = 0
        lexed_tokens = []

        keywords = list(filter(lambda t: t.startswith("Kw"), TokenType.__dict__["_member_names_"])); keywords.sort(key=lambda t: len(TokenType[t].value), reverse=True)
        tokens   = list(filter(lambda t: t.startswith("Tk"), TokenType.__dict__["_member_names_"])); tokens.sort(key=lambda t: len(TokenType[t].value), reverse=True)
        lexemes  = list(filter(lambda t: t.startswith("Lx"), TokenType.__dict__["_member_names_"]))

        print(tokens)

        while current < len(self._code):
            f = False

            for token in tokens:
                value = TokenType[token].value
                if self._code[current:current + len(value)] == value:
                    lexed_tokens.append(Token(value, TokenType[token]))
                    current += len(value)
                    f = True
                    break
            if f:
                continue

            for keyword in keywords:
                value = TokenType[keyword].value
                if self._code[current:current + len(value)] == value and not self._code[current + len(value)].isalpha():
                    lexed_tokens.append(Token(value, TokenType[keyword]))
                    current += len(value)
                    f = True
                    break
            if f:
                continue

            for lexeme in lexemes:
                value = TokenType[lexeme].value
                if matched := re.match(value, self._code[current:]):
                    lexed_tokens.append(Token(matched.group(0), TokenType[lexeme]))
                    current += len(matched.group(0))
                    f = True
                    break
            if f:
                continue

            print(self._code[current:current+len(TokenType.TkWhitespace.value)] == TokenType.TkWhitespace.value)
            raise Exception(f"Unknown token at {current}: {bytes(self._code[current], 'utf-8')}")
        return lexed_tokens + [Token("", TokenType.TkEOF)]
