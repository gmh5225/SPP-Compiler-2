from src.SyntacticAnalysis.Parser import Parser
from src.LexicalAnalysis.Tokens import TokenType
from inflection import camelize, underscore
from inspect import getsource


# class Intellij2:
#     @staticmethod
#     def to_bnf() -> str:
#         output  = ""
#
#         how_to_parse_map = {
#             "parseOnce": " ",
#             "parseOptional": "? ",
#             "parseZeroOrMore": "* ",
#             "parseOneOrMore": "+ "
#         }
#
#         for function_name, code in [(k, v) for k, v in Parser.__dict__.items() if k.startswith("_parse")]:
#             src_code = getsource(code)
#             inner_function = src_code[src_code.find("def inner():") + len("def inner():") : getsource(code).find("return BoundParser")]
#             inner_function = inner_function.strip().split("\n")
#             inner_function = [line.strip() for line in inner_function if line.strip()]
#             inner_function = [line for line in inner_function if not line.startswith("#")]
#
#             output += camelize(function_name.removeprefix("_parse_")) + " ::= "
#             for line in inner_function[inner_function[0].startswith("c") : -1]:
#                 line = line.replace("TokenType.", "TokenType#")
#                 line = line[line.find(" = ") + len(" = "):]
#                 line = line.replace("self._parse_", "")
#                 line = camelize(line).strip()
#
#                 line, how_to_parse = line.split(".", 1)
#                 output += f"{line} {how_to_parse_map[how_to_parse[:how_to_parse.find('(')]]} "
#
#             output += "\n"
#
#
#
#         return output


class Intellij:
    @staticmethod
    def convert_lexer_code():
        out = ""

        for token_type in TokenType.__dict__.items():
            if token_type[0].startswith("_"): continue

            token_name, token_value = token_type[1].name, token_type[1].value
            token_name = underscore(token_name).upper()
            if token_name.startswith("LX"):
                token_value = f"regexp:{token_value}"

            out += f"{token_name} = \"{token_value}\"\n"

        return out

    @staticmethod
    def convert_parser_code():
        parse_functions = filter(lambda pair: pair[0].startswith("_parse"), Parser.__dict__.items())
        parse_functions = dict(parse_functions)

        blacklist_functions = ["_parse_token", "_parse_lexeme", "_parse_binary_expression", "_parse_binary_expression_rhs", "_parse_character", "_parse_eof"]
        out = ""

        for function_name, code in parse_functions.items():
            if any([function_name.startswith(blacklist_function) for blacklist_function in blacklist_functions]):
                continue

            intellij_parse_string = camelize(function_name.removeprefix("_parse_")) + " ::= "
            function_source = getsource(code)
            temp_ors = {}

            inner_function_bounds = ("def inner():", "return Bound")
            if inner_function_bounds[0] not in function_source:
                # special case -- binary expression functions
                inner_function_bounds = ("return self._parse_binary_expression(", ")")


            inner_function = function_source[function_source.find(inner_function_bounds[0]) + len(inner_function_bounds[0]) : function_source.find(inner_function_bounds[1])]
            inner_function_lines = inner_function.split("\n")
            inner_function_lines = [line.strip() for line in inner_function_lines if line.strip()]
            if not inner_function_lines:
                out += intellij_parse_string.strip() + "\n"
                continue

            for line in inner_function_lines[inner_function_lines[0].startswith("c") : -1]:
                try:
                    original_line = line
                    parser_id = line[:line.find(" = ")].strip()
                    line = line.replace(parser_id + " = ", "")
                    line = line.replace("self._parse_", "")
                    line = line[:line.find(" #")]
                    line = camelize(line).strip()

                    if not line: continue
                    if line.startswith("#"): continue
                    if line == "self.Current": continue

                    line = line[0].upper() + line[1:]

                    line = line.replace("TokenType.", "TokenType#")
                    parse_function, how_to_parse = line.split(".", 1)

                    if " or" in how_to_parse:
                        how_to_parse = how_to_parse[:how_to_parse.find(" or")]

                    if "|" in parse_function:
                        intellij_parse_string += "("
                        for item in parse_function.split(" | "):
                            item = item.replace("(", "").replace(")", "")
                            item = temp_ors[item].replace("()", "")
                            if "TokenType#" in item:
                                item = Intellij.extract_token(item)
                            item = item + " | "
                            intellij_parse_string += item
                        intellij_parse_string = intellij_parse_string[:-3]
                        intellij_parse_string += ") "

                    if "delayParse" in how_to_parse:
                        temp_ors[parser_id] = parse_function
                        continue

                    if parse_function[:parse_function.find("(")] in ["Token", "Lexeme"]:
                        matcher = Intellij.extract_token(parse_function)
                        intellij_parse_string += f"{matcher}"

                    if not parse_function[:parse_function.find("(")] in ["Token", "Lexeme"]:
                        intellij_parse_string += parse_function[:parse_function.find("(")]

                    # print(how_to_parse)
                    intellij_parse_string += {
                        "parseOnce": " ",
                        "parseOptional": "? ",
                        "parseZeroOrMore": "* ",
                        "parseOneOrMore": "+ "
                    }[how_to_parse[:how_to_parse.find("(")].split(" ")[0]]
                except Exception as e:
                    print(e)
                    pass
                    # raise e

            out += intellij_parse_string.strip() + "\n"
        return out

    @staticmethod
    def extract_token(parse_function: str) -> str:
        matcher = parse_function[parse_function.find("(") + 1 : parse_function.rfind(")")]
        matcher = matcher.replace("TokenType#", "")
        matcher = underscore(matcher).upper()
        return matcher


if __name__ == "__main__":
    i = Intellij()
    tokens = i.convert_lexer_code()
    parser = i.convert_parser_code()

    print(parser)
