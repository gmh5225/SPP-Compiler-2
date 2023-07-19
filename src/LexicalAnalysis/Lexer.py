from src.LexicalAnalysis.Tokens import Token, TokenType
import re


class Lexer:
    _code: str

    def __init__(self, code: str):
        self._code = code.replace("\t", "    ")

    def lex(self):
        current = 0
        output = []

        keywords = list(filter(lambda t: t.startswith("Kw"), TokenType.__dict__["_member_names_"])); keywords.sort(key=lambda t: len(TokenType[t].value), reverse=True)
        tokens   = list(filter(lambda t: t.startswith("Tk"), TokenType.__dict__["_member_names_"])); tokens.sort(key=lambda t: len(TokenType[t].value), reverse=True)
        lexemes  = list(filter(lambda t: t.startswith("Lx"), TokenType.__dict__["_member_names_"]))
        available_tokens = tokens + keywords + lexemes

        while current < len(self._code):
            for token in available_tokens:
                value = TokenType[token].value
                match token[:2]:
                    case "Tk" if self._code[current:current + 1] == "_" and token == TokenType.TkUnderscore.name and re.match(TokenType.LxIdentifier.value, self._code[current + 1]):
                        break
                    case "Tk" if self._code[current:current + len(value)] == value:
                        output.append(Token(value, TokenType[token]))
                        current += len(value)
                        break
                    case "Kw" if self._code[current:current + len(value)] == value and not self._code[current + len(value)].isalpha():
                        output.append(Token(value, TokenType[token]))
                        current += len(value)
                        break
                    case "Lx" if matched := re.match(value, self._code[current:]):
                        output.append(Token(matched.group(0), TokenType[token]))
                        current += len(matched.group(0))
                        break
            else:
                raise Exception(f"Unknown token at {current}: {bytes(self._code[current], 'utf-8')}")
        return output + [Token("", TokenType.TkEOF)]
