from __future__ import annotations

import functools
from typing import Callable, Any, Optional, ParamSpec, TypeVar, Generic
from src.SyntacticAnalysis import Ast
from src.LexicalAnalysis.Tokens import TokenType, Token


class ParseSyntaxError(Exception):
    ...

class ParseSyntaxMultiError(Exception):
    ...

class ParserError(Exception):
    ...


P = ParamSpec("P")
T = TypeVar("T")


EXPECTED_TOKENS = []
ERRS = []
CUR_ERR_IND = None

# todo:
#  - remove ">>" and ">>>" tokens and convert them to rules (generics ending in multiple ">" don't match the ">>" tok)

class ErrorFormatter:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def error(self, start_token_index: int) -> str:
        # The error position for the ("^") will be from the provisional start token index. If the error position is end
        # of the file, then the error position have to be decremented by one, so that the error position is not pointing
        # to the EOF token. The start token index has to be moved back to that the newline behind the EOF is skipped (if
        # there is one).
        error_position = start_token_index
        if self._tokens[error_position].token_type == TokenType.TkEOF:
            error_position -= 1
        if self._tokens[error_position].token_type == TokenType.TkEOF and self._tokens[error_position - 1] == TokenType.TkNewLine:
            start_token_index -= 1 # todo : not -1, need to minus off the number of newlines before the EOF

        # If the start index is on a newline token, then move it back until it is not on a newline, so that the correct
        # line can be tracked over in reverse to fin the start of it. Once a non-newline has been found, move the
        # counter back until another newline is found - this will be the start of the line.
        while start_token_index > 0 and self._tokens[start_token_index].token_type == TokenType.TkNewLine:
            start_token_index -= 1
        while start_token_index > 0 and self._tokens[start_token_index].token_type != TokenType.TkNewLine:
            start_token_index -= 1

        # The end of the line is the first newline after the start of the line. If The re-scan forward is required
        # because there could have been multiple newlines after the current line, so only go to the first one.
        end_token_index = start_token_index + 1
        if end_token_index < len(self._tokens) and self._tokens[end_token_index].token_type == TokenType.TkNewLine:
            end_token_index += 1
        while end_token_index < len(self._tokens) and self._tokens[end_token_index].token_type != TokenType.TkNewLine:
            end_token_index += 1

        # Get the tokens on the current line by slicing the tokens between the start and end indexes just found from
        # backwards and forward newline-scanning
        tokens = self._tokens[start_token_index:end_token_index]
        current_line_string = "".join([token.token_metadata for token in tokens])

        # The number of spaces before the "^" characters is the error message position variable from the start - this
        # hasn't been altered
        spaces = 0
        for token in tokens[:error_position - start_token_index - 1]:
            spaces += len(token.token_metadata)

        # Format the line number into the error message string
        line_number = str([t.token_type for t in self._tokens[:end_token_index]].count(TokenType.TkNewLine) + 1) + " | "
        current_line_string = line_number + current_line_string.lstrip("\n")

        # The number of "^" characters is the length of the current tokens metadata (ie the symbol or length of keyword
        # / lexeme). Append the repeated "^" characters to the spaces, and then add the error message to the string.
        error_length = max(1, len(self._tokens[error_position].token_metadata))
        error_line_string = " " * (len(line_number) - 2) + "| " + "".join([" " * spaces, "^" * error_length]) + " <- "
        final_string = "\n".join(["", " " * (len(line_number) - 2) + "| ", current_line_string, error_line_string])
        return final_string


class BoundParser(Generic[T]):
    _rule: Callable[P, T]
    _parser: Parser
    _delayed: bool
    _ast: Optional[Any]

    def __init__(self, parser: Parser, rule: Callable[P, T]):
        self._rule = rule
        self._parser = parser
        self._delayed = False
        self._ast = None

    def parse_once(self) -> T:
        # Try to parse the rule once. If there is an error whilst parsing the rule, then catch it, append the current
        # BoundParser's error to the error message, and re-raise the error. This allows for the error message to be
        # propagated up the call stack.
        results = self._rule()

        # Remove None from a list of results (where a parse_optional has added a None to the list).
        while isinstance(results, list) and None in results:
            results.remove(None)

        # Save the result to the ast attribute, and return the ast out of the class.
        self._ast = results
        return self._ast

    def parse_optional(self) -> Optional[T]:
        # Save the current index of the parser -- it will need to be restored if the optional parse fails, so that the
        # next rule can start from this point.
        restore_index = self._parser.current

        # Try to parse the rule by calling the 'parse_once()' parse function -- this allows for the error message to be
        # formatted before being returned to the optional parser. If the parse is successful, then return the ast (the
        # attribute will have already been set from the 'parse_once()' call).
        try:
            self.parse_once()
            return self._ast

        # If there is an error in the optional parse, then the token index of the parser is restored, and the ast is set
        # to None. The None value is also returned, and functions can specify alternatives ie '.parse_optional() or []'
        except (ParseSyntaxError, ParseSyntaxMultiError):
            self._parser._current = restore_index
            self._ast = None
            return self._ast

    def parse_zero_or_more(self) -> list[T]:
        results = []

        # Use a 'while True' sot hat the parsing can continue until an error causes the loop to be returned from. This
        # allows for 0+ items to be parsed.
        while True:

            # Save the index for restoring when a parse fails.
            restore_index = self._parser.current

            # Call the 'parse_once()' function to parse the rule and handle error message formatting. Append the result
            # to the result list.
            try:
                result = self.parse_once()
                results.append(result)

            # If an error is caught, then the next parse has failed, so restore the index, and don't append anything to
            # the result list. Set the ast to the list of results (usually a list of other asts), and return this list.
            except (ParseSyntaxError, ParseSyntaxMultiError):
                self._parser.current = restore_index
                self._ast = results
                return self._ast

    def parse_one_or_more(self) -> list[T]:
        results = self.parse_zero_or_more()
        if not results:
            raise ParseSyntaxError("Expected at least one result")
        return results

    def delay_parse(self) -> BoundParser:
        self._delayed = True
        return self

    def __or__(self, that: BoundParser) -> BoundParser:
        # Allow chaining n parsers, and one of them has to match
        # Try to parse each one. if one is valid, return it
        # if none are valid, raise an error
        if not (self._delayed and that._delayed):
            raise ParserError("Both parsers must be delayed")

        if isinstance(self, MultiBoundParser):
            self.add_bound_parser(that)
            return self

        else:
            multi_bound_parser = MultiBoundParser(self._parser)
            multi_bound_parser.delay_parse()
            multi_bound_parser.add_bound_parser(self)
            multi_bound_parser.add_bound_parser(that)
            return multi_bound_parser


class MultiBoundParser(BoundParser):
    _bound_parsers: list[BoundParser]

    def __init__(self, parser: Parser):
        super().__init__(parser, None)
        self._bound_parsers = []

    def add_bound_parser(self, bound_parser: BoundParser):
        self._bound_parsers.append(bound_parser)

    def parse_once(self):
        for bound_parser in self._bound_parsers:
            restore_index = self._parser.current
            try:
                result = bound_parser.parse_once()
                return result
            except ParseSyntaxError:
                self._parser._current = restore_index

        raise ParseSyntaxError("Error parsing from selection")


class Parser:
    _tokens: list[Token]
    _current: int
    _indent: int
    _dedents_expected: int

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._current = 0
        self._indent = 0
        self._dedents_expected = 0

    def parse(self) -> Ast.ProgramAst:
        try:
            program = self._parse_program().parse_once()
            return program
        except ParseSyntaxError as e:
            # error = ""
            # for err in ERRS:
            #     if err.find("^ <-") > error.find("^ <-"):
            #         error = err
            # raise ParseSyntaxError(error)
            raise ParseSyntaxError("\n".join(ERRS))


    def _parse_program(self) -> BoundParser:
        def inner():
            p1 = self._parse_module_prototype().parse_once()
            p2 = self._parse_eof().parse_once()
            return Ast.ProgramAst(p1)
        return BoundParser(self, inner)

    def _parse_eof(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkEOF).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_module_prototype(self) -> BoundParser:
        def inner():
            p2 = self._parse_token(TokenType.KwMod).parse_once()
            p3 = self._parse_module_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
            p5 = self._parse_module_implementation().parse_once()
            return Ast.ModulePrototypeAst(p3, p5)
        return BoundParser(self, inner)

    def _parse_module_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_block().parse_optional()
            p2 = self._parse_module_member().parse_zero_or_more()
            return Ast.ModuleImplementationAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_module_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_module_identifier_next_part().parse_zero_or_more()
            return Ast.ModuleIdentifierAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_module_identifier_next_part(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleColon).parse_once()
            p2 = self._parse_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_module_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_prototype().delay_parse()
            p2 = self._parse_enum_prototype().delay_parse()
            p3 = self._parse_class_prototype().delay_parse()
            p4 = self._parse_sup_prototype().delay_parse()
            p5 = (p1 | p2 | p3 | p4).parse_once()
            return p5
        return BoundParser(self, inner)

    # Imports

    def _parse_import_block(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_statement().parse_one_or_more()
            return Ast.ImportBlockAst(p1)
        return BoundParser(self, inner)

    def _parse_import_statement(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwUse).parse_once()
            p2 = self._parse_import_identifier().parse_once()
            p3 = self._parse_import_what().parse_once()
            p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.ImportStatementAst(p2, p3)
        return BoundParser(self, inner)

    def _parse_import_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_identifier_part().parse_one_or_more()
            return Ast.ImportIdentifierAst(p1)
        return BoundParser(self, inner)

    def _parse_import_identifier_part(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkDoubleColon).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_import_what(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_all().delay_parse()
            p2 = self._parse_import_single().delay_parse()
            p3 = self._parse_import_multiple().delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_import_all(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAsterisk).parse_once()
            return Ast.ImportTypesAllAst()
        return BoundParser(self, inner)

    def _parse_import_single(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_type().parse_once()
            return Ast.ImportTypesIndividualAst([p1])
        return BoundParser(self, inner)

    def _parse_import_multiple(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_import_types().parse_once()
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.ImportTypesIndividualAst(p2)
        return BoundParser(self, inner)

    def _parse_import_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_type().parse_once()
            p2 = self._parse_import_types_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_import_types_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_import_type().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_import_type(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_import_type_alias().parse_optional()
            return Ast.ImportTypeAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_import_type_alias(self):
        def inner():
            p1 = self._parse_token(TokenType.KwAs).parse_once()
            p2 = self._parse_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    # Classes
    def _parse_class_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorators().parse_optional()
            p3 = self._parse_token(TokenType.KwCls).parse_once()
            p4 = self._parse_class_identifier().parse_once()
            p5 = self._parse_type_generic_parameters().parse_optional() or []
            p6 = self._parse_classes_metaclass().parse_optional()
            p7 = self._parse_where_block().parse_optional()
            p8 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p9 = self._parse_class_implementation().parse_once()
            p10 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.ClassPrototypeAst(p1, p4, p5, p6, p7, p9)
        return BoundParser(self, inner)

    def _parse_classes_metaclass(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWith).parse_once()
            p2 = self._parse_type_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_class_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_member().parse_zero_or_more()
            return Ast.ClassImplementationAst(p1)
        return BoundParser(self, inner)

    def _parse_class_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_attribute().delay_parse()
            p2 = self._parse_class_attribute_static().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_class_attribute(self) -> BoundParser:
        def inner():
            p2 = self._parse_token(TokenType.KwMut).parse_optional()
            p3 = self._parse_class_attribute_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_type_identifier().parse_once()
            p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.ClassInstanceAttributeAst(p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_class_attribute_static(self) -> BoundParser:
        def inner():
            p2 = self._parse_token(TokenType.KwMut).parse_optional()
            p3 = self._parse_class_attribute_static_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkEqual).parse_once()
            p5 = self._parse_non_assignment_expression().parse_once()
            p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.ClassStaticAttributeAst(p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_class_attribute_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_attribute_static_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Super-Impositions

    def _parse_sup_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwSup).parse_once()
            p2 = self._parse_sup_prototype_with_inherit().delay_parse()
            p3 = self._parse_sup_prototype_normal().delay_parse()
            p4 = (p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_sup_prototype_normal(self):
        def inner():
            p5 = self._parse_type_generic_parameters().parse_optional() or []
            p6 = self._parse_sup_identifier().parse_once()
            p7 = self._parse_where_block().parse_optional()
            p8 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p9 = self._parse_sup_implementation().parse_once()
            p10 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.SupPrototypeNormalAst(p5, p6, p7, p9)
        return BoundParser(self, inner)

    def _parse_sup_prototype_with_inherit(self):
        def inner():
            p5 = self._parse_type_generic_parameters().parse_optional() or []
            p6 = self._parse_sup_identifier().parse_once()
            p7 = self._parse_token(TokenType.KwFor).parse_once()
            p8 = self._parse_sup_identifier().parse_once()
            p9 = self._parse_where_block().parse_optional()
            p10 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p11 = self._parse_sup_implementation().parse_once()
            p12 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.SupPrototypeInheritanceAst(p5, p8, p9, p11, p6)
        return BoundParser(self, inner)

    def _parse_sup_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_member().parse_zero_or_more()
            return Ast.SupImplementationAst(p1)
        return BoundParser(self, inner)

    def _parse_sup_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_method_prototype().delay_parse()
            p2 = self._parse_sup_typedef().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_sup_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_typedef(self) -> BoundParser:
        def inner():
            p2 = self._parse_statement_typedef().parse_once()
            return Ast.SupTypedefAst(p2.new_type, p2.old_type)
        return BoundParser(self, inner)

    def _parse_sup_method_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_prototype().parse_once()
            return Ast.SupMethodPrototypeAst(p1.decorators, p1.identifier, p1.generic_parameters, p1.parameters, p1.return_type, p1.where_block, p1.value_guard, p1.body)
        return BoundParser(self, inner)

    # Enums

    def _parse_enum_prototype(self) -> BoundParser:
        def inner():
            p2 = self._parse_token(TokenType.KwEnum).parse_once()
            p3 = self._parse_enum_identifier().parse_once()
            p4 = self._parse_type_generic_parameters().parse_optional()
            p5 = self._parse_where_block().parse_optional()
            p6 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p7 = self._parse_enum_implementation().parse_once()
            p8 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.EnumPrototypeAst(p3, p4, p5, p7)
        return BoundParser(self, inner)

    def _parse_enum_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_member().parse_once()
            p2 = self._parse_enum_member_next().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.EnumImplementationAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_enum_member_next(self):
        def inner():
            p4 = self._parse_token(TokenType.TkComma).parse_once()
            p5 = self._parse_enum_member().parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_enum_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_member_identifier().parse_once()
            p2 = self._parse_enum_member_value_wrapper().parse_optional()
            return Ast.EnumMemberAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_enum_member_value_wrapper(self):
        def inner():
            p3 = self._parse_token(TokenType.TkEqual).parse_once()
            p4 = self._parse_non_assignment_expression().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_enum_member_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_enum_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Function Prototype & Implementation

    def _parse_function_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorators().parse_optional() or []
            p4_a = self._parse_token(TokenType.KwFn).delay_parse()
            p4_b = self._parse_token(TokenType.KwGn).delay_parse()
            p4 = (p4_a | p4_b).parse_once().tok.token_type == TokenType.KwGn
            p5 = self._parse_function_identifier().parse_once()
            p6 = self._parse_type_generic_parameters().parse_optional() or []
            p7 = self._parse_function_parameters().parse_once()
            p8 = self._parse_token(TokenType.TkRightArrow).parse_once()
            p9 = self._parse_type_identifier().parse_once()
            p10 = self._parse_where_block().parse_optional()
            p11 = self._parse_value_guard().parse_optional()
            p12 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p13 = self._parse_function_implementation().parse_once()
            p14 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.FunctionPrototypeAst(p1, p4, p5, p6, p7, p9, p10, p11, p13)
        return BoundParser(self, inner)

    def _parse_function_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement().parse_zero_or_more()
            return Ast.FunctionImplementationAst(p1)
        return BoundParser(self, inner)

    def _parse_function_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Function Call Arguments

    def _parse_function_call_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_function_call_arguments_normal_then_named().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_arguments_normal_then_named(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_call_normal_arguments().delay_parse()
            p2 = self._parse_function_call_named_arguments().delay_parse()
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_call_normal_arguments(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_call_normal_argument().parse_once()
            p4 = self._parse_function_call_rest_of_normal_arguments().parse_optional()
            return [p3, p4]
        return BoundParser(self, inner)

    def _parse_function_call_rest_of_normal_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_arguments_normal_then_named().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_named_arguments(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_call_named_argument().parse_once()
            p4 = self._parse_function_call_next_named_argument().parse_zero_or_more()
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_function_call_next_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_named_argument().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_normal_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_parameter_passing_convention().parse_optional()
            p2 = self._parse_operator_identifier_variadic().parse_optional() is not None
            p3 = self._parse_non_assignment_expression().parse_once()
            return Ast.FunctionArgumentNormalAst(p1, p3, p2)
        return BoundParser(self, inner)

    def _parse_function_call_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_parameter_passing_convention().parse_optional()
            p4 = self._parse_non_assignment_expression().parse_once()
            return Ast.FunctionArgumentNamedAst(p1, p3, p4)
        return BoundParser(self, inner)

    # Function Parameters

    def _parse_function_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_function_parameters_required_then_optional().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_parameters_required_then_optional(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_required_parameters().delay_parse()
            p2 = self._parse_function_optional_parameters().delay_parse()
            p3 = self._parse_function_variadic_parameter().delay_parse()
            p4 = (p3 | p2 | p1).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_function_parameters_optional_then_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_optional_parameters().delay_parse()
            p2 = self._parse_function_variadic_parameter().delay_parse()
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_required_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_required_parameter().parse_once()
            p4 = self._parse_function_rest_of_required_parameters().parse_optional() or []
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_function_rest_of_required_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameters_required_then_optional().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_optional_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_optional_parameter().parse_once()
            p4 = self._parse_function_rest_of_optional_parameters().parse_optional() or []
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_function_rest_of_optional_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameters_optional_then_variadic().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_required_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMut).parse_optional()
            p2 = self._parse_function_parameter_identifier().parse_once()
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_parameter_passing_convention().parse_optional()
            p5 = self._parse_type_identifier().parse_once()
            return Ast.FunctionParameterRequiredAst(p1 is not None, p2, p4, p5)
        return BoundParser(self, inner)

    def _parse_function_optional_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_required_parameter().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_non_assignment_expression().parse_once()
            return Ast.FunctionParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_function_variadic_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_operator_identifier_variadic().parse_once()
            p2 = self._parse_function_required_parameter().parse_once()
            return Ast.FunctionParameterVariadicAst(p2)
        return BoundParser(self, inner)

    def _parse_function_parameter_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Type Constraints & Value Guard

    def _parse_where_block(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWhere).parse_once()
            p2 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p3 = self._parse_where_constraints().parse_once()
            p4 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return Ast.WhereBlockAst(p3)
        return BoundParser(self, inner)

    def _parse_where_constraints(self) -> BoundParser:
        def inner():
            p1 = self._parse_where_constraint().parse_once()
            p2 = self._parse_where_constraint_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_where_constraint_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_where_constraint().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_where_constraint(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifiers().parse_once()
            p2 = self._parse_token(TokenType.TkColon).parse_once()
            p3 = self._parse_where_constraint_chain().parse_once()
            return Ast.WhereConstraintAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_where_constraint_chain(self) -> BoundParser:
        def inner():
            p3 = self._parse_where_constraint_chain_element().parse_once()
            p4 = self._parse_where_constraint_chain_element_next().parse_zero_or_more()
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_where_constraint_chain_element_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAmpersand).parse_once()
            p2 = self._parse_where_constraint_chain_element().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_where_constraint_chain_element(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_value_guard(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwIf).parse_once()
            p2 = self._parse_non_assignment_expression().parse_once()
            return Ast.ValueGuardAst(p2)
        return BoundParser(self, inner)

    # Decorators

    def _parse_decorator(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAt).parse_once()
            p2 = self._parse_decorator_identifier().parse_once()
            p3 = self._parse_type_generic_arguments().parse_optional()
            p4 = self._parse_function_call_arguments().parse_optional()
            return Ast.DecoratorAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_decorators(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorator().parse_zero_or_more()
            return p1
        return BoundParser(self, inner)

    def _parse_decorator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Expressions

    def _parse_expressions(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_expression_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_expression_next(self):
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_expression().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_assignment_expression().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_non_assignment_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_null_coalescing_expression().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_assignment_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_assignment_expression_single().delay_parse() # +=, -= etc
            p2 = self._parse_assignment_expression_multiple().delay_parse() # =
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_assignment_expression_single(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_null_coalescing_expression(),
            self._parse_operator_identifier_assignment(),
            self._parse_null_coalescing_expression)

    def _parse_assignment_expression_multiple(self) -> BoundParser:
        def inner():
            p4 = self._parse_null_coalescing_expression().parse_once()
            p5 = self._parse_assignment_multiple_lhs().parse_zero_or_more()
            p6 = self._parse_token(TokenType.TkEqual).parse_once()
            p7 = self._parse_null_coalescing_expression().parse_once()
            return Ast.AssignmentExpressionAst([p4, *p5], p7)
        return BoundParser(self, inner)

    def _parse_assignment_multiple_lhs(self) -> BoundParser:
        def inner():
            p9 = self._parse_token(TokenType.TkComma).parse_once()
            p10 = self._parse_null_coalescing_expression().parse_once()
            return p10
        return BoundParser(self, inner)

    def _parse_null_coalescing_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_or_expression(),
            self._parse_token(TokenType.TkDoubleQuestionMark),
            self._parse_null_coalescing_expression)

    def _parse_logical_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_and_expression(),
            self._parse_token(TokenType.TkDoublePipe),
            self._parse_logical_or_expression)

    def _parse_logical_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_or_expression(),
            self._parse_token(TokenType.TkDoubleAmpersand),
            self._parse_logical_and_expression)

    def _parse_bitwise_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_xor_expression(),
            self._parse_token(TokenType.TkPipe),
            self._parse_bitwise_or_expression)

    def _parse_bitwise_xor_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_and_expression(),
            self._parse_token(TokenType.TkCaret),
            self._parse_bitwise_xor_expression)

    def _parse_bitwise_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_equality_expression(),
            self._parse_token(TokenType.TkAmpersand),
            self._parse_bitwise_and_expression)

    def _parse_equality_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_relational_expression(),
            self._parse_operator_identifier_equality(),
            self._parse_equality_expression)

    def _parse_relational_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_shift_expression(),
            self._parse_operator_identifier_relation(),
            self._parse_relational_expression)

    def _parse_shift_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_rotate_expression(),
            self._parse_operator_identifier_shift(),
            self._parse_shift_expression)

    def _parse_rotate_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_additive_expression(),
            self._parse_operator_identifier_rotate(),
            self._parse_rotate_expression)

    def _parse_additive_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_multiplicative_expression(),
            self._parse_operator_identifier_additive(),
            self._parse_additive_expression)

    def _parse_multiplicative_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_power_expression(),
            self._parse_operator_identifier_multiplicative(),
            self._parse_multiplicative_expression)

    def _parse_power_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_pipe_expression(),
            self._parse_token(TokenType.TkDoubleAsterisk),
            self._parse_power_expression)

    def _parse_pipe_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_unary_expression(),
            self._parse_token(TokenType.TkPipeArrow),
            self._parse_pipe_expression)

    def _parse_unary_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_operator_identifier_unary().parse_zero_or_more()
            p2 = self._parse_postfix_expression().parse_once()
            for op in reversed(p1):
                p2 = Ast.UnaryExpressionAst(op, p2)
            return p2
        return BoundParser(self, inner)

    def _parse_postfix_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_primary_expression().parse_once()
            p2 = self._parse_operator_identifier_postfix().parse_zero_or_more()
            for op in p2:
                p1 = Ast.PostfixExpressionAst(p1, op)
            return p1
        return BoundParser(self, inner)

    def _parse_primary_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().delay_parse()
            p2 = self._parse_literal().delay_parse()
            p3 = self._parse_lambda().delay_parse()
            p4 = self._parse_single_type_identifier().delay_parse()
            # p5 = self._parse_parenthesized_expression().delay_parse()
            p6 = self._parse_expression_placeholder().delay_parse()
            p7 = self._parse_statement_if().delay_parse()
            p8 = self._parse_statement_match().delay_parse()
            p9 = self._parse_statement_while().delay_parse()
            p10 = self._parse_statement_for().delay_parse()
            p11 = self._parse_statement_do().delay_parse()
            p12 = self._parse_statement_new_scope().delay_parse()
            p13 = (p7 | p8 | p9 | p10 | p11 | p12 | p4 | p3 | p1 | p2 | p6).parse_once()
            return p13
        return BoundParser(self, inner)

    def _parse_binary_expression(self, __lhs, __op, __rhs) -> BoundParser:
        def inner(lhs, op, rhs):
            p1 = lhs.parse_once()
            p2 = self._parse_binary_expression_rhs(op, rhs).parse_optional()
            return p1 if p2 is None else Ast.BinaryExpressionAst(p1, p2[0], p2[1])
        return BoundParser(self, functools.partial(inner, __lhs, __op, __rhs))

    def _parse_binary_expression_rhs(self, __op, __rhs) -> BoundParser:
        def inner(op, rhs):
            p3 = op.parse_once()
            p4 = rhs().parse_once()
            return p3, p4
        return BoundParser(self, functools.partial(inner, __op, __rhs))

    def _parse_expression_placeholder(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkUnderscore).parse_once()
            return Ast.PlaceholderAst()
        return BoundParser(self, inner)

    # Lambda

    def _parse_lambda(self) -> BoundParser:
        def inner():
            p2 = self._parse_lambda_capture_list().parse_optional()
            p3 = self._parse_lambda_parameters().parse_once()
            p4 = self._parse_token(TokenType.TkRightFatArrow).parse_once()
            p5 = self._parse_lambda_implementation().parse_once()
            return Ast.LambdaAst(p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_lambda_capture_list(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_lambda_capture_item().parse_once()
            p3 = self._parse_lambda_capture_item_next().parse_zero_or_more()
            p4 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return [p2, *p3]
        return BoundParser(self, inner)

    def _parse_lambda_capture_item_next(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkComma).parse_once()
            p6 = self._parse_lambda_capture_item().parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_lambda_capture_item(self) -> BoundParser:
        def inner():
            p1 = self._parse_lambda_capture_item_alias().parse_optional()
            p2 = self._parse_parameter_passing_convention().parse_optional()
            p3 = self._parse_identifier().parse_once()
            return Ast.LambdaCaptureItemAst(p1, p2, p3)
        return BoundParser(self, inner)

    def _parse_lambda_capture_item_alias(self) -> BoundParser:
        def inner():
            p3 = self._parse_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkEqual).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_lambda_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_lambda_parameters_required().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_lambda_parameters_required(self) -> BoundParser:
        def inner():
            p1 = self._parse_lambda_parameter_required().parse_once()
            p2 = self._parse_lambda_parameter_required_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_lambda_parameter_required_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_lambda_parameter_required().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_lambda_parameter_required(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMut).parse_optional()
            p2 = self._parse_function_parameter_identifier().parse_once()
            return Ast.LambdaParameterAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_lambda_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_non_assignment_expression().parse_once()
            return p1
        return BoundParser(self, inner)

    # Type Identifiers

    def _parse_type_self_prefix(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwSelf).parse_once()
            p2 = self._parse_type_raw_identifiers_rest().parse_optional() or []
            return Ast.TypeSingleAst([Ast.SelfTypeAst(), *p2])
        return BoundParser(self, inner)

    def _parse_type_raw_identifiers_rest(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleColon).parse_once()
            p2 = self._parse_type_raw_identifiers().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_raw_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_generic_identifier().parse_once()
            p2 = self._parse_type_raw_identifiers_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_raw_identifiers_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkDoubleColon).parse_once()
            p4 = self._parse_type_raw_identifier().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_raw_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_generic_identifier().delay_parse()
            p2 = self._parse_numeric_integer().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_single_type_identifier().delay_parse()
            p2 = self._parse_tuple_type_identifiers().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_single_type_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_self_prefix().delay_parse()
            p2 = self._parse_type_raw_identifiers().delay_parse()
            p3 = (p1 | p2).parse_once()
            return Ast.TypeSingleAst(p3)
        return BoundParser(self, inner)

    def _parse_tuple_type_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_type_identifiers().parse_once()
            p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return Ast.TypeTupleAst(p2)
        return BoundParser(self, inner)

    def _parse_type_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().parse_once()
            p2 = self._parse_type_identifier_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_identifier_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            return p4
        return BoundParser(self, inner)

    # Type Generic Arguments

    def _parse_type_generic_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_type_generic_arguments_normal_then_named().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_arguments_normal_then_named(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_normal_arguments().delay_parse()
            p2 = self._parse_type_generic_named_arguments().delay_parse()
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_generic_normal_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_normal_argument().parse_once()
            p2 = self._parse_type_generic_rest_of_normal_arguments().parse_optional() or []
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_normal_arguments(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_generic_arguments_normal_then_named().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_named_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_named_argument().parse_once()
            p2 = self._parse_type_generic_next_named_argument().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_generic_next_named_argument(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_generic_named_argument().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_normal_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().parse_once()
            return Ast.TypeGenericArgumentNormalAst(p1)
        return BoundParser(self, inner)

    def _parse_type_generic_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_type_identifier().parse_once()
            return Ast.TypeGenericArgumentNamedAst(p1, p3)
        return BoundParser(self, inner)

    # Type Generic Parameters

    def _parse_type_generic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_parameters_required_then_optional(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_required_parameters().delay_parse()
            p2 = self._parse_type_generic_optional_parameters().delay_parse()
            p3 = self._parse_type_generic_variadic_parameters().delay_parse()
            p4 = (p3 | p2 | p1).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_parameters_optional_then_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_optional_parameters().delay_parse()
            p2 = self._parse_type_generic_variadic_parameters().delay_parse()
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_generic_required_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_type_generic_required_parameter().parse_once()
            p4 = self._parse_type_generic_rest_of_required_parameters().parse_optional() or []
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_required_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_optional_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_type_generic_optional_parameter().parse_once()
            p4 = self._parse_type_generic_rest_of_optional_parameters().parse_optional() or []
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_optional_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameters_optional_then_variadic().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_required_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_type_generic_parameter_inline_constraint().parse_optional()
            return Ast.TypeGenericParameterRequiredAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_type_generic_optional_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_required_parameter().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_type_identifier().parse_once()
            return Ast.TypeGenericParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_type_generic_variadic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_variadic_parameter().parse_once()
            p2 = self._parse_type_generic_rest_of_variadic_parameters().parse_optional() or []
            return [p1, p2]
        return BoundParser(self, inner)

    def _parse_type_generic_variadic_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
            p2 = self._parse_type_generic_required_parameter().parse_once()
            return Ast.TypeGenericParameterVariadicAst(p2)
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_variadic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_variadic_parameter().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_inline_constraint(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_where_constraint_chain().parse_once()
            return p4
        return BoundParser(self, inner)

    # Statements

    def _parse_statement_inline_definition(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_let_with_value().parse_optional()
            p2 = self._parse_token(TokenType.TkComma).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_statement_if(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_if_branch().parse_once()
            p5 = self._parse_statement_elif_branch().parse_zero_or_more()
            p6 = self._parse_statement_else_branch().parse_optional()
            return Ast.IfStatementAst(p1, p5, p6)
        return BoundParser(self, inner)

    def _parse_statement_if_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwIf).parse_once()
            p2 = self._parse_statement_inline_definition().parse_zero_or_more()
            p3 = self._parse_expression().parse_once()
            p4 = self._parse_statement_block().parse_once()
            return Ast.IfStatementBranchAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_elif_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwElif).parse_once()
            p2 = self._parse_statement_inline_definition().parse_zero_or_more()
            p3 = self._parse_expression().parse_once()
            p4 = self._parse_statement_block().parse_once()
            return Ast.ElifStatementBranchAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_else_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwElse).parse_once()
            p2 = self._parse_statement_block().parse_once()
            return Ast.ElseStatementBranchAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_while(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWhile).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_loop_tag().parse_optional()
            p4 = self._parse_statement_block().parse_once()
            return Ast.WhileStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_for(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwFor).parse_once()
            p2 = self._parse_local_variable_identifiers().parse_once()
            p3 = self._parse_token(TokenType.KwIn).parse_once()
            p4 = self._parse_expression().parse_once()
            p5 = self._parse_statement_loop_tag().parse_optional()
            p6 = self._parse_statement_block().parse_once()
            return Ast.ForStatementAst(p2, p4, p5, p6)
        return BoundParser(self, inner)

    def _parse_statement_do(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwDo).parse_once()
            p2 = self._parse_statement_loop_tag().parse_optional()
            p3 = self._parse_statement_block().parse_once()
            p4 = self._parse_token(TokenType.KwWhile).parse_once()
            p5 = self._parse_expression().parse_once()
            return Ast.DoWhileStatementAst(p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_statement_match(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMatch).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_cases().parse_once()
            return Ast.MatchStatementAst(p2, p3)
        return BoundParser(self, inner)

    def _parse_statement_case_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_statement_case_expression_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_statement_case_expression().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_statement_case_expressions(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_case_expression().parse_once()
            p2 = self._parse_statement_case_expression_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_statement_case(self) -> BoundParser:
        def inner():
            p2 = self._parse_statement_case_expressions().parse_once()
            p3 = self._parse_value_guard().parse_optional()
            p4 = self._parse_token(TokenType.TkRightFatArrow).parse_once()
            p5 = self._parse_statement_block().parse_once()
            return Ast.CaseStatementAst(p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_statement_with(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWith).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_alias_for_with_expression().parse_optional()
            p4 = self._parse_statement_block().parse_once()
            return Ast.WithStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_alias_for_with_expression(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.KwAs).parse_once()
            p6 = self._parse_local_variable_identifier().parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_statement_return(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwReturn).parse_once()
            p2 = self._parse_expression().parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.ReturnStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_yield(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwYield).parse_once()
            p2 = self._parse_expression().parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.YieldStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_typedef(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwUse).parse_once()
            p2 = self._parse_generic_identifier().parse_once()
            p3 = self._parse_token(TokenType.KwAs).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.TypedefStatementAst(Ast.TypeSingleAst([p2]), p4)
        return BoundParser(self, inner)

    def _parse_statement_break(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwBreak).parse_once()
            p2 = self._parse_statement_tag_identifier().parse_optional()
            p3 = self._parse_expression().parse_optional() or []
            p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.BreakStatementAst(p2, p3)
        return BoundParser(self, inner)

    def _parse_statement_continue(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwContinue).parse_once()
            p2 = self._parse_statement_tag_identifier().parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return Ast.ContinueStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_loop_tag(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwAs).parse_once()
            p2 = self._parse_statement_tag_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_statement_tag_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxTag).parse_once()
            return Ast.TagIdentifierAst(p1[1:])
        return BoundParser(self, inner)

    def _parse_statement_block(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_statement().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_statement_cases(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_statement_case().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_statement_let(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_let_with_value().delay_parse()
            p2 = self._parse_statement_let_with_type().delay_parse()
            p3 = (p1 | p2).parse_once()
            p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_statement_let_with_value(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwLet).parse_once()
            p2 = self._parse_local_variable_identifiers().parse_once()
            p3 = self._parse_token(TokenType.TkEqual).parse_once()
            p4 = self._parse_non_assignment_expression().parse_once()
            p5 = self._parse_statement_else_branch().parse_optional()
            return Ast.LetStatementAst(p2, p4, None, p5)
        return BoundParser(self, inner)

    def _parse_statement_let_with_type(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwLet).parse_once()
            p2 = self._parse_local_variable_identifiers().parse_once()
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            return Ast.LetStatementAst(p2, None, p4, None)
        return BoundParser(self, inner)

    def _parse_local_variable_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            p2 = self._parse_identifier().parse_once()
            return Ast.LocalVariableAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_local_variable_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_local_variable_identifier().parse_once()
            p2 = self._parse_local_variable_identifier_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_local_variable_identifier_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_local_variable_identifier().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_statement_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_statement_new_scope(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_statement().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.InnerScopeAst(p2)
        return BoundParser(self, inner)

    def _parse_statement(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_if().delay_parse()
            p2 = self._parse_statement_while().delay_parse()
            p3 = self._parse_statement_for().delay_parse()
            p4 = self._parse_statement_do().delay_parse()
            p5 = self._parse_statement_match().delay_parse()
            p6 = self._parse_statement_with().delay_parse()
            p7 = self._parse_statement_typedef().delay_parse()
            p8 = self._parse_statement_return().delay_parse()
            p9 = self._parse_statement_yield().delay_parse()
            p10 = self._parse_statement_let().delay_parse()
            p11 = self._parse_statement_break().delay_parse()
            p12 = self._parse_statement_continue().delay_parse()
            p13 = self._parse_statement_expression().delay_parse()
            p14 = self._parse_function_prototype().delay_parse()
            p15 = self._parse_statement_new_scope().delay_parse()
            p16 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11 | p12 | p13 | p14 | p15).parse_once()
            return p16
        return BoundParser(self, inner)

    # Identifiers

    def _parse_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
            return Ast.IdentifierAst(p1)
        return BoundParser(self, inner)

    def _parse_generic_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
            p2 = self._parse_type_generic_arguments().parse_optional() or []
            return Ast.GenericIdentifierAst(p1, p2)
        return BoundParser(self, inner)

    # Postfix operations

    def _parse_postfix_operator_function_call(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_call_arguments().parse_once()
            return Ast.PostfixFunctionCallAst(p1)
        return BoundParser(self, inner)

    def _parse_postfix_operator_member_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_operator_identifier_member_access().parse_once()
            p2 = self._parse_generic_identifier().delay_parse()
            p3 = self._parse_number().delay_parse()
            p4 = (p2 | p3).parse_once()
            return Ast.PostfixMemberAccessAst(p1, p4)
        return BoundParser(self, inner)

    def _parse_postfix_operator_index_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_non_assignment_expression().parse_once()
            p3 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return Ast.PostfixIndexAccessAst(p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_postfix_operator_struct_initializer_fields().parse_optional()
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return Ast.PostfixStructInitializerAst(p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_fields(self) -> BoundParser:
        def inner():
            p1 = self._parse_postfix_operator_struct_initializer_field().parse_once()
            p2 = self._parse_postfix_operator_struct_initializer_field_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_postfix_operator_struct_initializer_field().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field(self) -> BoundParser:
        def inner():
            p1 = self._parse_postfix_operator_struct_initializer_field_identifier().parse_once()
            p2 = self._parse_postfix_operator_struct_initializer_field_value_different_to_identifier().parse_optional()
            return Ast.PostfixStructInitializerFieldAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field_value_different_to_identifier(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_non_assignment_expression().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwSup).delay_parse()
            p2 = self._parse_token(TokenType.KwElse).delay_parse()
            p3 = self._parse_identifier().delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    # Operator identifiers

    def _parse_operator_identifier_assignment(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoublePipeEquals).delay_parse()
            p2 = self._parse_token(TokenType.TkDoubleAmpersandEquals).delay_parse()
            p3 = self._parse_token(TokenType.TkAmpersandEquals).delay_parse()
            p4 = self._parse_token(TokenType.TkPipeEquals).delay_parse()
            p5 = self._parse_token(TokenType.TkCaretEquals).delay_parse()
            p6 = self._parse_token(TokenType.TkDoubleLeftAngleBracketEquals).delay_parse()
            p7 = self._parse_token(TokenType.TkDoubleRightAngleBracketEquals).delay_parse()
            p8 = self._parse_token(TokenType.TkTripleLeftAngleBracketEquals).delay_parse()
            p9 = self._parse_token(TokenType.TkTripleRightAngleBracketEquals).delay_parse()
            p10 = self._parse_token(TokenType.TkPlusEquals).delay_parse()
            p11 = self._parse_token(TokenType.TkHyphenEquals).delay_parse()
            p12 = self._parse_token(TokenType.TkAsteriskEquals).delay_parse()
            p13 = self._parse_token(TokenType.TkForwardSlashEquals).delay_parse()
            p14 = self._parse_token(TokenType.TkDoubleForwardSlashEquals).delay_parse()
            p15 = self._parse_token(TokenType.TkPercentEquals).delay_parse()
            p16 = self._parse_token(TokenType.TkDoubleAsteriskEquals).delay_parse()
            p17 = self._parse_token(TokenType.TkDoubleQuestionMarkEquals).delay_parse()
            p18 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11 | p12 | p13 | p14 | p15 | p16 | p17).parse_once()
            return p18
        return BoundParser(self, inner)

    def _parse_operator_identifier_equality(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleEquals).delay_parse()
            p2 = self._parse_token(TokenType.TkExclamationEquals).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_operator_identifier_relation(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftAngleBracket).delay_parse()
            p2 = self._parse_token(TokenType.TkRightAngleBracket).delay_parse()
            p3 = self._parse_token(TokenType.TkLeftAngleBracketEquals).delay_parse()
            p4 = self._parse_token(TokenType.TkRightAngleBracketEquals).delay_parse()
            p5 = self._parse_token(TokenType.TkDoubleFatArrow).delay_parse()
            p6 = (p1 | p2 | p3 | p4 | p5).parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_operator_identifier_shift(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleLeftAngleBracket).delay_parse()
            p2 = self._parse_token(TokenType.TkDoubleRightAngleBracket).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_operator_identifier_rotate(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleLeftAngleBracket).delay_parse()
            p2 = self._parse_token(TokenType.TkTripleRightAngleBracket).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_operator_identifier_additive(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkPlus).delay_parse()
            p2 = self._parse_token(TokenType.TkHyphen).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_operator_identifier_multiplicative(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAsterisk).delay_parse()
            p2 = self._parse_token(TokenType.TkForwardSlash).delay_parse()
            p3 = self._parse_token(TokenType.TkDoubleForwardSlash).delay_parse()
            p4 = self._parse_token(TokenType.TkPercent).delay_parse()
            p5 = (p1 | p2 | p3 | p4).parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_operator_identifier_unary(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkPlus).delay_parse()
            p2 = self._parse_token(TokenType.TkHyphen).delay_parse()
            p3 = self._parse_token(TokenType.TkTilde).delay_parse()
            p4 = self._parse_token(TokenType.TkExclamation).delay_parse()
            p6 = (p1 | p2 | p3 | p4).parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_parameter_passing_convention(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAmpersand).parse_once()
            p2 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            return Ast.ParameterPassingConventionReferenceAst(p2)
        return BoundParser(self, inner)

    def _parse_operator_identifier_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_operator_identifier_member_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_operator_identifier_postfix(self) -> BoundParser:
        def inner():
            p1 = self._parse_postfix_operator_function_call().delay_parse()
            p2 = self._parse_postfix_operator_member_access().delay_parse()
            # p3 = self._parse_postfix_operator_index_access().delay_parse()
            p5 = self._parse_postfix_operator_struct_initializer().delay_parse()
            p7 = self._parse_token(TokenType.TkQuestionMark).delay_parse()
            p8 = (p1 | p2| p5 | p7).parse_once()
            return p8
        return BoundParser(self, inner)

    # Literals

    def _parse_literal(self) -> BoundParser:
        def inner():
            p1 = self._parse_literal_number().delay_parse()
            p2 = self._parse_literal_string().delay_parse()
            p3 = self._parse_literal_char().delay_parse()
            p4 = self._parse_literal_boolean().delay_parse()
            p8 = self._parse_literal_tuple().delay_parse()
            p9 = self._parse_literal_regex().delay_parse()
            p10 = self._parse_literal_range().delay_parse()
            p11 = (p1 | p2 | p3 | p4 | p8 | p9).parse_once()
            return p11
        return BoundParser(self, inner)

    def _parse_literal_number(self) -> BoundParser:
        def inner():
            p1 = self._parse_literal_number_base_02().delay_parse()
            p2 = self._parse_literal_number_base_16().delay_parse()
            p3 = self._parse_literal_number_base_10().delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_literal_string(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxDoubleQuoteStr).parse_once()
            return Ast.StringLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_char(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxSingleQuoteChr).parse_once()
            return Ast.CharLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_boolean(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwTrue).delay_parse()
            p2 = self._parse_token(TokenType.KwFalse).delay_parse()
            p3 = (p1 | p2).parse_once()
            return Ast.BoolLiteralAst(p3.tok.token_type == TokenType.KwTrue)
        return BoundParser(self, inner)

    def _parse_literal_regex(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxRegex).parse_once()
            return Ast.RegexLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_tuple(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p4 = self._parse_expressions().parse_optional() or []
            p6 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return Ast.TupleLiteralAst(p4) if len(p4) != 1 else p4[0]
        return BoundParser(self, inner)

    def _parse_literal_range(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_token(TokenType.TkDoubleDot).parse_once()
            p3 = self._parse_expression().parse_optional()
            return Ast.RangeLiteralAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_literal_number_base_02(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxBinDigits).parse_once()
            return Ast.NumberLiteralBase02Ast(p1)
        return BoundParser(self, inner)

    def _parse_literal_number_base_10(self) -> BoundParser:
        def inner():
            p1 = self._parse_number().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_literal_number_base_16(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxHexDigits).parse_once()
            return Ast.NumberLiteralBase16Ast(p1)
        return BoundParser(self, inner)

    # Number

    def _parse_number(self) -> BoundParser:
        def inner():
            p1 = self._parse_numeric_integer().parse_once()
            p2 = self._parse_numeric_decimal().parse_optional()
            p3 = self._parse_numeric_complex().parse_optional()
            p4 = self._parse_numeric_exponent().parse_optional() is not None
            return Ast.NumberLiteralBase10Ast(p1, p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_numeric_integer(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxDecDigits).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_numeric_decimal(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            p2 = self._parse_lexeme(TokenType.LxDecDigits).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_numeric_complex(self) -> BoundParser:
        def inner():
            p1 = self._parse_character('i').parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_numeric_exponent(self) -> BoundParser:
        def inner():
            p1 = self._parse_character('e').parse_once()
            p2 = self._parse_operator_identifier_additive().parse_optional()
            p3 = self._parse_numeric_integer().parse_once()
            return Ast.NumberExponentAst(p2, p3)
        return BoundParser(self, inner)

    # Misc

    def _parse_token(self, token: TokenType) -> BoundParser:
        def inner():
            if self._dedents_expected > 0:
                raise ParseSyntaxError("Expected a dedent")

            if token != TokenType.TkNewLine: self._skip(TokenType.TkNewLine)
            if token != TokenType.TkWhitespace: self._skip(TokenType.TkWhitespace)

            if self._current >= len(self._tokens):
                raise ParseSyntaxError(f"Expected '{token.value}', got <EOF>")

            global EXPECTED_TOKENS
            current_token = self._tokens[self._current]
            if current_token.token_type != token:
                got_token = current_token.token_type.value if not current_token.token_type.name.startswith("Lx") else current_token.token_type.name[2:]
                exp_token = token.value if not token.name.startswith("Lx") else token.name[2:]

                error = ParseSyntaxError(
                    ErrorFormatter(self._tokens).error(self._current) +
                    f"Expected one of ¬, got: '{got_token}'")

                global CUR_ERR_IND
                if CUR_ERR_IND == self._current:
                    if "'" + exp_token + "'" not in EXPECTED_TOKENS:
                        EXPECTED_TOKENS.append(str("'" + exp_token + "'"))
                    if ERRS:
                        ERRS[-1] = str(error).replace("¬", ", ".join(EXPECTED_TOKENS))
                    else:
                        ERRS.append(str(error).replace("¬", ", ".join(EXPECTED_TOKENS)))
                    raise error
                else:
                    CUR_ERR_IND = self._current
                    EXPECTED_TOKENS = [str("'" + exp_token + "'")]
                    ERRS.append(str(error).replace("¬", ", ".join(EXPECTED_TOKENS)))
                    raise ParseSyntaxError("\n".join(ERRS))

            EXPECTED_TOKENS.clear()
            if ERRS: ERRS.pop(-1)

            self._current += 1

            return Ast.TokenAst(self._tokens[self._current - 1])
        return BoundParser(self, inner)

    def _parse_lexeme(self, lexeme: TokenType) -> BoundParser:
        def inner():
            p1 = self._parse_token(lexeme).parse_once()
            return p1.tok.token_metadata
        return BoundParser(self, inner)

    def _parse_character(self, character: str) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            if p1.identifier != character:
                raise ParseSyntaxError(f"Expected {character}, got {p1.identifier}")
            return p1
        return BoundParser(self, inner)

    def _skip(self, token: TokenType):
        while self._current < len(self._tokens) and self._tokens[self._current].token_type == token:
            self._current += 1

    @property
    def current(self) -> int:
        return self._current

    @current.setter
    def current(self, value: int) -> None:
        self._current = value
