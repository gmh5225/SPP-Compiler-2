from __future__ import annotations

from src.LexicalAnalysis.Tokens import Token, TokenType
import re


class Lexer:
    _code: str

    def __init__(self, code: str):
        self._code = code.replace("\t", "    ")

    def lex(self):
        current = 0
        output = []

        # Sort the tokens and keywords by length, so for example, "<=" isn't matched against "<" and "=" individually.
        # Do the same for keywords, as although there aren't any conflicting keywords right now, it is scalable for the
        # future.
        tokens = list(filter(lambda t: t.startswith("Tk"), TokenType.__dict__["_member_names_"]))
        tokens.sort(key=lambda t: len(TokenType[t].value), reverse=True)

        keywords = list(filter(lambda t: t.startswith("Kw"), TokenType.__dict__["_member_names_"]))
        keywords.sort(key=lambda t: len(TokenType[t].value), reverse=True)

        # Lexemes don't need sorting as they're matched by regex, and the order of the regexes is already correct (in
        # the TokenTypes order).
        lexemes = list(filter(lambda t: t.startswith("Lx"), TokenType.__dict__["_member_names_"]))

        # Combine the sorted tokens into one list, so that the lexer doesn't have to check each token class
        # individually. Keywords are first, as they need to be matched before identifiers, and tokens are last, because
        # identifiers starting with "_" need to be matched before an individual "_" is found as a potential token.
        available_tokens = keywords + lexemes + tokens

        # Iterate through the code, attempting to match each token in the available_tokens list. If a token is matched,
        # add it to the output list, and move the current index forward by the length of the token. If no token is
        # matched, raise an exception.
        while current < len(self._code):
            for token in available_tokens:
                value = getattr(TokenType, token).value
                upper = current + len(value)
                match token[:2]:
                    # Do the same for the keywords, but also check that the next character isn't a letter, as otherwise
                    # the lexer will think that "mod_id" is "mod" and "id", rather than the "mod_id" identifier.
                    case "Kw" if self._code[current:upper] == value and not (self._code[upper].isalpha() or self._code[upper] == "_"):
                        output.append(Token(value, TokenType[token]))
                        current += len(value)
                        break

                    # Match a lexeme by attempting to get a regex match against the current code. This means that the
                    # regex will keep searching until the longest match is made. Increment the counter by the length of
                    # the found regex match.
                    case "Lx" if matched := re.match(value, self._code[current:]):
                        if TokenType[token] != TokenType.LxSingleLineComment:
                            output.append(Token(matched.group(0), TokenType[token]))
                        current += len(matched.group(0))
                        break

                    # Match a token by comparing its value against a subscript of the code -- the subscript length is
                    # the length of the token being inspected. Increment the counter by the length of the token value.
                    case "Tk" if self._code[current:upper] == value:
                        output.append(Token(value, TokenType[token]))
                        current += len(value)
                        break
            else:
                # Raise an error if the token is unknown.
                raise Exception(f"Unknown token at {current}: {bytes(self._code[current], 'utf-8')}")

        # Return the list of tokens, followed by the special EOF Token.
        return output + [Token("", TokenType.TkEOF)]
