from src.SyntacticAnalysis.Parser import Parser
from inflection import camelize, underscore, titleize
from inspect import getsource


class Intellij:
    @staticmethod
    def convert_to_grammar_kit_parser_code() -> str:
        parse_functions = filter(lambda pair: pair[0].startswith("_parse"), Parser.__dict__.items())
        parse_functions = dict(parse_functions)

        blacklist_functions = ["_parse_token", "_parse_lexeme", "_parse_binary_expression", "_parse_binary_expression_rhs", "_parse_character"]
        out = ""

        for function_name, code in parse_functions.items():
            if any([function_name.startswith(blacklist_function) for blacklist_function in blacklist_functions]):
                continue

            intellij_parse_string = camelize(function_name.removeprefix("_parse_")) + " ::= "
            function_source = getsource(code)
            temp_ors = {}

            inner_function_bounds = ("def inner():", "return")
            if inner_function_bounds[0] not in function_source:
                # special case -- binary expression functions
                inner_function_bounds = ("return self._parse_binary_expression(", ")")


            inner_function = function_source[function_source.find(inner_function_bounds[0]) + len(inner_function_bounds[0]) : function_source.find(inner_function_bounds[1])]
            for line in inner_function.split("\n"):
                try:
                    original_line = line
                    parser_id = line[:line.find(" = ")].strip()
                    line = line.replace(parser_id + " = ", "")
                    line = line.replace("self._parse_", "")
                    line = camelize(line).strip()
                    if not line: continue

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

                    intellij_parse_string += {
                        "parseOnce": " ",
                        "parseOptional": "? ",
                        "parseZeroOrMore": "* ",
                        "parseOneOrMore": "+ "
                    }[how_to_parse[:how_to_parse.find("(")].split(" ")[0]]
                except Exception as e:
                    pass

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
    s = i.convert_to_grammar_kit_parser_code()
    print(s)
