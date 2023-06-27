from __future__ import annotations

import functools
from typing import Callable, Any
from src.Ast import *
from src.Tokens import TokenType, Token


class ParseSyntaxError(Exception):
    ...

class ParseSyntaxMultiError(Exception):
    ...

class ParserError(Exception):
    ...


Rule = Callable

FOLD = ""
EXPECTED_TOKENS = []
ERRS = []
CUR_ERR_IND = None


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

        # The number of "^" characters is the length of the current tokens metadata (ie the symbol or length of keyword
        # / lexeme). Append the repeated "^" characters to the spaces, and then add the error message to the string.
        error_length = max(1, len(self._tokens[error_position].token_metadata))
        error_line_string = "".join([" " * spaces, "^" * error_length]) + " <- "
        final_string = "\n".join(["", current_line_string, error_line_string])
        return final_string


class BoundParser:
    _rule: Rule
    _parser: Parser
    _delayed: bool
    _ast: Optional[Any]

    def __init__(self, parser: Parser, rule: Rule):
        self._rule = rule
        self._parser = parser
        self._delayed = False
        self._ast = None

    def parse_once(self):
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

    def parse_optional(self):
        # Save the current index of the parser -- it will need to be restored if the optional parse fails, so that the
        # next rule can start from this point.
        restore_index = self._parser._current

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


    def parse_zero_or_more(self):
        results = []

        # Use a 'while True' sot hat the parsing can continue until an error causes the loop to be returned from. This
        # allows for 0+ items to be parsed.
        while True:

            # Save the index for restoring when a parse fails.
            restore_index = self._parser._current

            # Call the 'parse_once()' function to parse the rule and handle error message formatting. Append the result
            # to the result list.
            try:
                result = self.parse_once()
                results.append(result)

            # If an error is caught, then the next parse has failed, so restore the index, and don't append anything to
            # the result list. Set the ast to the list of results (usually a list of other asts), and return this list.
            except (ParseSyntaxError, ParseSyntaxMultiError) as e:
                self._parser._current = restore_index
                self._ast = results
                return self._ast

    def parse_one_or_more(self):
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
        errors = []
        for bound_parser in self._bound_parsers:
            restore_index = self._parser._current
            try:
                result = bound_parser.parse_once()
                return result
            except ParseSyntaxError as e:
                self._parser._current = restore_index
                errors.append(str(e).replace("£", "€"))

        raise ParseSyntaxMultiError("£".join(errors))


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

    def parse(self) -> ProgramAst:
        program = self._parse_root().parse_once()
        return program

    # Modules

    def _parse_root(self) -> BoundParser:
        def inner():
            p1 = self._parse_program().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_program(self) -> BoundParser:
        def inner():
            p1 = self._parse_module_prototype().parse_once()
            p2 = self._parse_eof().parse_once()
            return ProgramAst(p1)
        return BoundParser(self, inner)

    def _parse_eof(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkEOF).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_module_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().parse_optional()
            p2 = self._parse_token(TokenType.KwMod).parse_once()
            p3 = self._parse_module_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
            p5 = self._parse_module_implementation().parse_once()
            return ModulePrototypeAst(p1, p3, p5)
        return BoundParser(self, inner)

    def _parse_module_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_block().parse_optional()
            p2 = self._parse_module_member().parse_zero_or_more()
            return ModuleImplementationAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_module_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_module_identifier_next_part().parse_zero_or_more()
            return ModuleIdentifierAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_module_identifier_next_part(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_once()
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
            p1 = self._parse_token(TokenType.KwUse).parse_once()
            p2 = self._parse_token(TokenType.TkColon).parse_once()
            p3 = self._parse_indent().parse_once()
            p4 = self._parse_import_definition().parse_one_or_more()
            p5 = self._parse_dedent().parse_once()
            return ImportBlockAst(p4)
        return BoundParser(self, inner)

    def _parse_import_definition(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_zero_or_more()
            p2 = self._parse_module_identifier().parse_once()
            p3 = self._parse_token(TokenType.TkRightArrow).parse_once()
            p4 = self._parse_import_identifiers().parse_once()
            p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return ImportDefinitionsAst(p1, p2, p4)
        return BoundParser(self, inner)

    def _parse_import_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_all_types().delay_parse()
            p2 = self._parse_import_individual_types().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_import_all_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAsterisk).parse_once()
            return ImportTypesAllAst()
        return BoundParser(self, inner)

    def _parse_import_individual_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_individual_type().parse_once()
            p2 = self._parse_import_individual_type_next().parse_zero_or_more()
            return ImportTypesIndividualAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_import_individual_type_next(self):
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_import_individual_type().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_import_individual_type(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_import_individual_type_alias().parse_optional()
            return ImportTypeAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_import_individual_type_alias(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.KwAs).parse_once()
            p4 = self._parse_identifier().parse_once()
            return p4
        return BoundParser(self, inner)

    """CLASSES"""

    def _parse_access_modifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwPub).delay_parse()
            p2 = self._parse_token(TokenType.KwPriv).delay_parse()
            p3 = self._parse_token(TokenType.KwProt).delay_parse()
            p4 = (p1 | p2 | p3).parse_optional()
            return p4
        return BoundParser(self, inner)

    def _parse_class_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorators().parse_optional()
            p2 = self._parse_token(TokenType.KwPart).parse_optional()
            p3 = self._parse_access_modifier().parse_optional()
            p4 = self._parse_token(TokenType.KwCls).parse_once()
            p5 = self._parse_class_identifier().parse_once()
            p6 = self._parse_type_generic_parameters().parse_optional()
            p7 = self._parse_where_block().parse_optional()
            p8 = self._parse_class_or_empty_implementation().parse_once()
            return ClassPrototypeAst(p1, p3, p5, p6, p6, p7, p8)
        return BoundParser(self, inner)

    def _parse_class_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_or_empty_implementation_empty_prep().delay_parse()
            p2 = self._parse_class_or_empty_implementation_non_empty_prep().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_class_or_empty_implementation_empty_prep(self):
        def inner():
            p1 = self._parse_empty_implementation().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_or_empty_implementation_non_empty_prep(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).parse_once()
            p2 = self._parse_indent().parse_once()
            p3 = self._parse_class_implementation().parse_once()
            p4 = self._parse_dedent().parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_class_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_member().parse_one_or_more()
            return ClassImplementationAst(p1)
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
            p1 = self._parse_access_modifier().parse_optional()
            p2 = self._parse_token(TokenType.KwMut).parse_optional()
            p3 = self._parse_class_attribute_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_type_identifier().parse_once()
            p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return ClassInstanceAttributeAst(p1, p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_class_attribute_static(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().parse_optional()
            p2 = self._parse_token(TokenType.KwMut).parse_optional()
            p3 = self._parse_class_attribute_static_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkEqual).parse_once()
            p5 = self._parse_expression().parse_once()
            p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return ClassStaticAttributeAst(p1, p2, p3, p5)
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
            p8 = self._parse_sup_or_empty_implementation().parse_once()
            return SupPrototypeNormalAst(p5, p6, p7, p8)
        return BoundParser(self, inner)

    def _parse_sup_prototype_with_inherit(self):
        def inner():
            p5 = self._parse_type_generic_parameters().parse_optional()
            p6 = self._parse_sup_identifier().parse_once()
            p7 = self._parse_token(TokenType.KwFor).parse_once()
            p8 = self._parse_sup_identifier().parse_once()
            p9 = self._parse_where_block().parse_optional()
            p10 = self._parse_sup_or_empty_implementation().parse_once()
            return SupPrototypeInheritanceAst(p5, p6, p8, p9, p10)
        return BoundParser(self, inner)

    def _parse_sup_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_or_empty_implementation_empty_prep().delay_parse()
            p2 = self._parse_sup_or_empty_implementation_non_empty_prep().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_sup_or_empty_implementation_empty_prep(self):
        def inner():
            p1 = self._parse_empty_implementation().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_or_empty_implementation_non_empty_prep(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).parse_once()
            p2 = self._parse_indent().parse_once()
            p3 = self._parse_sup_implementation().parse_once()
            p4 = self._parse_dedent().parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_sup_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_member().parse_one_or_more()
            return p1
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
            p1 = self._parse_static_scoped_generic_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_typedef(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().parse_optional()
            p2 = self._parse_statement_typedef().parse_once()
            return SupTypedefAst(p1, p2.old_type, p2.new_type)
        return BoundParser(self, inner)

    def _parse_sup_method_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_prototype().parse_once()
            return SupMethodPrototypeAst(p1.decorators, p1.modifier, p1.is_async, p1.identifier, p1.generic_parameters, p1.parameters, p1.return_type, p1.where_block, p1.value_guard, p1.body)
        return BoundParser(self, inner)

    """ENUMS"""

    def _parse_enum_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().parse_optional()
            p2 = self._parse_token(TokenType.KwEnum).parse_once()
            p3 = self._parse_enum_identifier().parse_once()
            p4 = self._parse_enum_or_empty_implementation().parse_once()
            return EnumPrototypeAst(p1, p3, p4)
        return BoundParser(self, inner)

    def _parse_enum_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_or_empty_implementation_empty_prep().delay_parse()
            p2 = self._parse_enum_or_empty_implementation_non_empty_prep().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_enum_or_empty_implementation_empty_prep(self):
        def inner():
            p1 = self._parse_empty_implementation().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_enum_or_empty_implementation_non_empty_prep(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).parse_once()
            p2 = self._parse_indent().parse_once()
            p3 = self._parse_enum_implementation().parse_once()
            p4 = self._parse_dedent().parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_enum_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_member().parse_once()
            p2 = self._parse_enum_member_next().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return EnumImplementationAst([p1, *p2])
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
            return EnumMemberAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_enum_member_value_wrapper(self):
        def inner():
            p3 = self._parse_token(TokenType.TkEqual).parse_once()
            p4 = self._parse_enum_member_value().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_enum_member_value(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            return p1
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
            p1 = self._parse_decorators().parse_optional()
            p2 = self._parse_access_modifier().parse_optional()
            p3 = self._parse_token(TokenType.KwAsync).parse_optional()
            p4 = self._parse_token(TokenType.KwFun).parse_once()
            p5 = self._parse_function_identifier().parse_once()
            p6 = self._parse_type_generic_parameters().parse_optional()
            p7 = self._parse_function_parameters().parse_once()
            p8 = self._parse_token(TokenType.TkRightArrow).parse_once()
            p9 = self._parse_type_identifiers().parse_once()
            p10 = self._parse_where_block().parse_optional()
            p11 = self._parse_value_guard().parse_optional()
            p12 = self._parse_function_or_empty_implementation().parse_once()
            return FunctionPrototypeAst(p1, p2, p3, p5, p6, p7, p9, p10, p11, p12)
        return BoundParser(self, inner)

    def _parse_function_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_or_empty_implementation_empty_prep().delay_parse()
            p2 = self._parse_function_or_empty_implementation_non_empty_prep().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_or_empty_implementation_empty_prep(self):
        def inner():
            p4 = self._parse_empty_implementation().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_function_or_empty_implementation_non_empty_prep(self):
        def inner():
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_indent().parse_once()
            p6 = self._parse_function_implementation().parse_once()
            p7 = self._parse_dedent().parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_function_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement().parse_one_or_more()
            return FunctionImplementationAst(p1)
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
            p1 = self._parse_expression().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_function_call_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkColon).parse_once()
            p3 = self._parse_expression().parse_once()
            return FunctionArgumentNamedAst(p1, p3)
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
            p4 = self._parse_function_rest_of_required_parameters().parse_optional()
            return [p3, p4]
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
            p4 = self._parse_function_rest_of_optional_parameters().parse_optional()
            return [p3, p4]
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
            p4 = self._parse_type_identifier().parse_once()
            return FunctionParameterRequiredAst(p1 is not None, p2, p4)
        return BoundParser(self, inner)

    def _parse_function_optional_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_required_parameter().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_expression().parse_once()
            return FunctionParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_function_variadic_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
            p2 = self._parse_function_required_parameter().parse_once()
            return FunctionParameterVariadicAst(p2)
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
            return WhereBlockAst(p3)
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
            return WhereConstraintAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_where_constraint_chain(self) -> BoundParser:
        def inner():
            p3 = self._parse_where_constraint_chain_element().parse_once()
            p4 = self._parse_where_constraint_chain_element_next().parse_zero_or_more()
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_where_constraint_chain_element_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkPlus).parse_once()
            p2 = self._parse_where_constraint_chain_element().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_where_constraint_chain_element(self) -> BoundParser:
        def inner():
            p1 = self._parse_static_scoped_generic_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_value_guard(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwIf).parse_once()
            p2 = self._parse_expression().parse_once()
            return ValueGuardAst(p2)
        return BoundParser(self, inner)

    # Decorators

    def _parse_decorator(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAt).parse_once()
            p2 = self._parse_decorator_identifier().parse_once()
            p3 = self._parse_type_generic_arguments().parse_optional()
            p4 = self._parse_function_call_arguments().parse_optional()
            return DecoratorAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_decorators(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorator().parse_once()
            p2 = self._parse_decorator_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_decorator_next(self):
        def inner():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_decorator().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_decorator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_static_scoped_generic_identifier().parse_once()
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

    def _parse_assignment_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_assignment_single().delay_parse()
            p2 = self._parse_assignment_multiple().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_assignment_multiple(self) -> BoundParser:
        def inner():
            p4 = self._parse_null_coalescing_expression().parse_once()
            p5 = self._parse_assignment_multiple_lhs().parse_zero_or_more()
            p6 = self._parse_token(TokenType.TkEqual).parse_once()
            p7 = self._parse_assignment_expression().parse_once()
            p8 = self._parse_assignment_multiple_rhs().parse_zero_or_more()
            return MultiAssignmentExpressionAst([p4, *p5], [p7, *p8])
        return BoundParser(self, inner)

    def _parse_assignment_multiple_lhs(self) -> BoundParser:
        def inner():
            p9 = self._parse_token(TokenType.TkComma).parse_once()
            p10 = self._parse_null_coalescing_expression().parse_once()
            return p10
        return BoundParser(self, inner)

    def _parse_assignment_multiple_rhs(self) -> BoundParser:
        def inner():
            p9 = self._parse_token(TokenType.TkComma).parse_once()
            p10 = self._parse_assignment_expression().parse_once()
            return p10
        return BoundParser(self, inner)

    def _parse_assignment_single(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_null_coalescing_expression(),
            self._parse_operator_identifier_assignment(),
            self._parse_assignment_expression)

    def _parse_null_coalescing_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_or_expression(),
            self._parse_operator_identifier_null_coalescing(),
            self._parse_null_coalescing_expression)

    def _parse_logical_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_and_expression(),
            self._parse_token(TokenType.TkDoubleVerticalBar),
            self._parse_logical_or_expression)

    def _parse_logical_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_or_expression(),
            self._parse_token(TokenType.TkDoubleAmpersand),
            self._parse_logical_and_expression)

    def _parse_bitwise_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_xor_expression(),
            self._parse_token(TokenType.TkVerticalBar),
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
            self._parse_token(TokenType.TkDoubleAstrix),
            self._parse_power_expression)

    def _parse_pipe_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_unary_expression(),
            self._parse_token(TokenType.TkPipe),
            self._parse_pipe_expression)

    def _parse_unary_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_operator_identifier_unary().parse_zero_or_more()
            p2 = self._parse_postfix_expression().parse_once()
            for op in reversed(p1):
                p2 = UnaryExpressionAst(op, p2)
            return p2
        return BoundParser(self, inner)

    def _parse_postfix_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_primary_expression().parse_once()
            p2 = self._parse_operator_identifier_postfix().parse_zero_or_more()
            for op in p2:
                p1 = PostfixExpressionAst(p1, op)
            return p1
        return BoundParser(self, inner)

    def _parse_rvalue(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().delay_parse()
            p2 = self._parse_literal().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_primary_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_rvalue().delay_parse()
            p2 = self._parse_lambda().delay_parse()
            p3 = self._parse_static_scoped_generic_identifier().delay_parse()
            p4 = self._parse_parenthesized_expression().delay_parse()
            p5 = self._parse_expression_placeholder().delay_parse()
            p6 = (p1 | p2 | p3 | p4 | p5).parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_binary_expression(self, __lhs, __op, __rhs) -> BoundParser:
        def inner(lhs, op, rhs):
            p1 = lhs.parse_once()
            p2 = self._parse_binary_expression_rhs(op, rhs).parse_optional()
            return p1 if p2 is None else BinaryExpressionAst(p1, p2[0], p2[1])
        return BoundParser(self, functools.partial(inner, __lhs, __op, __rhs))

    def _parse_binary_expression_rhs(self, __op, __rhs) -> BoundParser:
        def inner(op, rhs):
            p3 = op.parse_once()
            p4 = rhs().parse_once()
            return p3, p4
        return BoundParser(self, functools.partial(inner, __op, __rhs))

    def _parse_parenthesized_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return ParenthesizedExpressionAst(p2)
        return BoundParser(self, inner)

    def _parse_expression_placeholder(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkUnderscore).parse_once()
            return PlaceholderAst()
        return BoundParser(self, inner)

    # Lambda

    def _parse_lambda(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwAsync).parse_optional()
            p2 = self._parse_lambda_capture_list().parse_optional()
            p3 = self._parse_lambda_parameters().parse_once()
            p4 = self._parse_token(TokenType.TkRightArrow).parse_once()
            p5 = self._parse_lambda_implementation().parse_once()
            return LambdaAst(p1, p2, p3, p5)
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
            p2 = self._parse_expression().parse_once()
            return LambdaCaptureItemAst(p1, p2)
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
            return LambdaParameterAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_lambda_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            return p1
        return BoundParser(self, inner)

    # Type Identifiers

    def _parse_type_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_unary_operator_reference().parse_optional()
            p2 = self._parse_static_scoped_generic_identifier().parse_once()
            return TypeAst(p1, p2)
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
            p1 = self._parse_token(TokenType.TkLeftAngleBracket).parse_once()
            p2 = self._parse_type_generic_arguments_normal_then_named().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightAngleBracket).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_arguments_normal_then_named(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_normal_arguments().delay_parse()
            p2 = self._parse_type_generic_named_arguments().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_generic_normal_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_normal_argument().parse_once()
            p2 = self._parse_type_generic_rest_of_normal_arguments().parse_optional()
            return [p1, p2]
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
            return TypeGenericArgumentNormalAst(p1)
        return BoundParser(self, inner)

    def _parse_type_generic_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_type_identifier().parse_once()
            return TypeGenericArgumentNamedAst(p1, p3)
        return BoundParser(self, inner)

    # Type Generic Parameters

    def _parse_type_generic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftAngleBracket).parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightAngleBracket).parse_once()
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
            p4 = self._parse_type_generic_rest_of_required_parameters().parse_optional()
            return [p3, p4]
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
            p4 = self._parse_type_generic_rest_of_optional_parameters().parse_optional()
            return [p3, p4]
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
            return TypeGenericParameterRequiredAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_type_generic_optional_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_required_parameter().parse_once()
            p2 = self._parse_token(TokenType.TkEqual).parse_once()
            p3 = self._parse_type_identifier().parse_once()
            return TypeGenericParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_type_generic_variadic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_variadic_parameter().parse_once()
            p2 = self._parse_type_generic_rest_of_variadic_parameters().parse_optional()
            return [p1, p2]
        return BoundParser(self, inner)

    def _parse_type_generic_variadic_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
            p2 = self._parse_type_generic_required_parameter().parse_once()
            return TypeGenericParameterVariadicAst(p2)
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

    def _parse_statement_inline_definitions(self) -> BoundParser:
        def inner():
            p5 = self._parse_statement_let().parse_once()
            p6 = self._parse_token(TokenType.TkComma).parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_statement_if(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_if_branch().parse_once()
            p5 = self._parse_statement_elif_branch().parse_zero_or_more()
            p6 = self._parse_statement_else_branch().parse_optional()
            return IfStatementAst(p1, p5, p6)
        return BoundParser(self, inner)

    def _parse_statement_if_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwIf).parse_once()
            p2 = self._parse_statement_inline_definitions().parse_zero_or_more()
            p3 = self._parse_expression().parse_once()
            p4 = self._parse_statement_block().parse_once()
            return IfStatementBranchAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_elif_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwElif).parse_once()
            p2 = self._parse_statement_inline_definitions().parse_zero_or_more()
            p3 = self._parse_expression().parse_once()
            p4 = self._parse_statement_block().parse_once()
            return ElifStatementBranchAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_else_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwElse).parse_once()
            p2 = self._parse_statement_block().parse_once()
            return ElseStatementBranchAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_while(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWhile).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_loop_tag().parse_optional()
            p4 = self._parse_statement_block_for_looping().parse_once()
            return WhileStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_for(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwFor).parse_once()
            p2 = self._parse_local_variable_identifiers().parse_once()
            p3 = self._parse_token(TokenType.KwIn).parse_once()
            p4 = self._parse_expression().parse_once()
            p5 = self._parse_statement_loop_tag().parse_optional()
            p6 = self._parse_statement_block_for_looping().parse_once()
            return ForStatementAst(p2, p4, p5, p6)
        return BoundParser(self, inner)

    def _parse_statement_do(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwDo).parse_once()
            p2 = self._parse_statement_block_for_looping().parse_once()
            p3 = self._parse_token(TokenType.KwWhile).parse_once()
            p4 = self._parse_expression().parse_once()
            p5 = self._parse_statement_loop_tag().parse_optional()
            return DoWhileStatementAst(p2, p4, p5)
        return BoundParser(self, inner)

    def _parse_statement_match(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMatch).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_cases().parse_once()
            return MatchStatementAst(p2, p3)
        return BoundParser(self, inner)

    def _parse_statement_case_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_rvalue().parse_once()
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
            p1 = self._parse_token(TokenType.KwCase).parse_once()
            p2 = self._parse_statement_case_expressions().parse_once()
            p3 = self._parse_value_guard().parse_optional()
            p4 = self._parse_statement_block().parse_once()
            return CaseStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_case_default(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwCase).parse_once()
            p2 = self._parse_expression_placeholder().parse_once()
            p3 = self._parse_value_guard().parse_optional()
            p4 = self._parse_statement_block().parse_once()
            return CaseStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_with(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWith).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_with_expression_alias().parse_optional()
            p4 = self._parse_statement_block().parse_once()
            return WithStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_with_expression_alias(self) -> BoundParser:
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
            return ReturnStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_yield(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwYield).parse_once()
            p2 = self._parse_expression().parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return YieldStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_typedef(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwUse).parse_once()
            p2 = self._parse_generic_identifier().parse_once()
            p3 = self._parse_token(TokenType.KwAs).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return TypedefStatementAst(p2, p4)
        return BoundParser(self, inner)

    def _parse_statement_break(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwBreak).parse_once()
            p2 = self._parse_statement_loop_tag().parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return BreakStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_continue(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwContinue).parse_once()
            p2 = self._parse_statement_loop_tag().parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return ContinueStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_loop_tag(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwAs).parse_once()
            p2 = self._parse_tag_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_tag_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxTag).parse_once()
            return TagIdentifierAst(p1)
        return BoundParser(self, inner)

    def _parse_statement_block(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_block_multiple_lines().delay_parse()
            p2 = self._parse_statement_block_single_line().delay_parse()
            p3 = self._parse_empty_implementation().delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_statement_block_multiple_lines(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_indent().parse_once()
            p7 = self._parse_statement().parse_one_or_more()
            p8 = self._parse_dedent().parse_once()
            return p7
        return BoundParser(self, inner)

    def _parse_statement_block_single_line(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_statement().parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_statement_block_for_looping(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_block_multiple_lines_for_looping().delay_parse()
            p2 = self._parse_statement_block_single_line_for_looping().delay_parse()
            p3 = self._parse_empty_implementation().delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_statement_block_multiple_lines_for_looping(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).parse_once()
            p2 = self._parse_indent().parse_once()
            p3 = self._parse_statement_for_looping().parse_one_or_more()
            p4 = self._parse_dedent().parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_statement_block_single_line_for_looping(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).parse_once()
            p2 = self._parse_statement_for_looping().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_statement_cases(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_cases_force_default()
            p2 = self._parse_statement_cases_force_exhaustion()
            p3 = self._parse_empty_implementation()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_statement_cases_force_default(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_indent().parse_once()
            p7 = self._parse_statement_case().parse_zero_or_more()
            p8 = self._parse_statement_case_default().parse_one_or_more()
            p9 = self._parse_dedent().parse_once()
            return [p7, *p8]
        return BoundParser(self, inner)

    def _parse_statement_cases_force_exhaustion(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_indent().parse_once()
            p7 = self._parse_statement_case().parse_one_or_more()
            p8 = self._parse_statement_case_default().parse_zero_or_more()
            p9 = self._parse_dedent().parse_once()
            return [p7, *p8]
        return BoundParser(self, inner)

    def _parse_statement_let(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwLet).parse_once()
            p2 = self._parse_local_variable_identifier().parse_once()
            p3 = self._parse_statement_let_type_annotation().delay_parse()
            p4 = self._parse_statement_let_value().delay_parse()
            p5 = (p3 | p4).parse_once()
            return LetStatementAst(p2, [], p5) if isinstance(p5, TypeAst) else LetStatementAst(p2, p5, None)
        return BoundParser(self, inner)

    def _parse_statement_let_value(self) -> BoundParser:
        def inner():
            p6 = self._parse_token(TokenType.TkEqual).parse_once()
            p7 = self._parse_expressions().parse_once()
            return p7
        return BoundParser(self, inner)

    def _parse_statement_let_type_annotation(self) -> BoundParser:
        def inner():
            p6 = self._parse_token(TokenType.TkColon).parse_once()
            p7 = self._parse_type_identifier().parse_once()
            return p7
        return BoundParser(self, inner)

    def _parse_local_variable_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            p2 = self._parse_identifier().parse_once()
            return LocalVariableAst(p1, p2)
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

    def _parse_statement_let_for_statement(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_let().parse_once()
            p2 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return p1
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
            p10 = self._parse_statement_let_for_statement().delay_parse()
            p11 = self._parse_statement_expression().delay_parse()
            # p12 = self._parse_function_prototype().delay_parse()
            p13 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11).parse_once()
            return p13
        return BoundParser(self, inner)

    def _parse_statement_for_looping(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement().delay_parse()
            p2 = self._parse_statement_break().delay_parse()
            p3 = self._parse_statement_continue().delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    # Identifiers

    def _parse_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
            return IdentifierAst(p1)
        return BoundParser(self, inner)

    def _parse_generic_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
            p2 = self._parse_type_generic_arguments().parse_optional()
            return GenericIdentifierAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_static_scoped_generic_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_generic_identifier().parse_once()
            p2 = self._parse_static_scoped_generic_identifier_next().parse_zero_or_more()
            return ScopedGenericIdentifierAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_static_scoped_generic_identifier_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkDoubleColon).parse_once()
            p4 = self._parse_generic_identifier().parse_once()
            return p4
        return BoundParser(self, inner)

    # Postfix operations

    def _parse_postfix_operator_function_call(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_call_arguments().parse_once()
            p2 = self._parse_operator_identifier_variadic().parse_optional() is not None
            return PostfixFunctionCallAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_member_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_operator_identifier_member_access().parse_once()
            p2 = self._parse_generic_identifier().parse_once()
            return PostfixMemberAccessAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_index_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return PostfixIndexAccessAst(p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_slice_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_expression().parse_optional()
            p3 = self._parse_token(TokenType.TkDoubleDot).parse_once()
            p4 = self._parse_expression().parse_optional()
            p5 = self._parse_iterable_step().parse_optional()
            p6 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return PostfixSliceAccessAst(p2, p4, p5)
        return BoundParser(self, inner)

    def _parse_iterable_step(self) -> BoundParser:
        def inner():
            p7 = self._parse_token(TokenType.TkComma).parse_once()
            p8 = self._parse_expression().parse_optional()
            return p8
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_postfix_operator_struct_initializer_fields().parse_optional()
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return PostfixStructInitializerAst(p2)
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
            return PostfixStructInitializerFieldAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field_value_different_to_identifier(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_expression().parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwSup).delay_parse()
            p2 = self._parse_identifier().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_postfix_operator_type_cast(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwAs).parse_once()
            p2 = self._parse_type_identifier().parse_once()
            return PostfixTypeCastAst(p2)
        return BoundParser(self, inner)

    """[OPERATOR IDENTIFIERS]"""

    def _parse_operator_identifier_assignment(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleVerticalBarEquals).delay_parse()
            p2 = self._parse_token(TokenType.TkDoubleAmpersandEquals).delay_parse()
            p3 = self._parse_token(TokenType.TkAmpersandEquals).delay_parse()
            p4 = self._parse_token(TokenType.TkVerticalBarEquals).delay_parse()
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
            p16 = self._parse_token(TokenType.TkDoubleAstrixEquals).delay_parse()
            p17 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11 | p12 | p13 | p14 | p15 | p16).parse_once()
            return p17
        return BoundParser(self, inner)

    def _parse_operator_identifier_null_coalescing(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleQuestionMark).delay_parse()
            p2 = self._parse_token(TokenType.TkQuestionMarkColon).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_operator_identifier_equality(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleEqual).delay_parse()
            p2 = self._parse_token(TokenType.TkExclamationEqual).delay_parse()
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
            p5 = self._parse_unary_operator_reference().delay_parse()
            p6 = self._parse_operator_identifier_variadic().delay_parse()
            p7 = self._parse_token(TokenType.KwAwait).delay_parse()
            p8 = (p1 | p2 | p3 | p4 | p5 | p6 | p7).parse_once()
            return p8
        return BoundParser(self, inner)

    def _parse_unary_operator_reference(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAmpersand).parse_once()
            p2 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            return TokenAst(p1.primary, p2 is not None)
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
            p3 = self._parse_postfix_operator_index_access().delay_parse()
            p4 = self._parse_postfix_operator_slice_access().delay_parse()
            p5 = self._parse_postfix_operator_struct_initializer().delay_parse()
            p6 = self._parse_postfix_operator_type_cast().delay_parse()
            p7 = self._parse_token(TokenType.TkQuestionMark).delay_parse()
            p8 = (p1 | p2 | p3 | p4 | p5 | p6 | p7).parse_once()
            return p8
        return BoundParser(self, inner)

    # Literals

    def _parse_literal(self) -> BoundParser:
        def inner():
            p1 = self._parse_literal_number().delay_parse()
            p2 = self._parse_literal_string().delay_parse()
            p3 = self._parse_literal_char().delay_parse()
            p4 = self._parse_literal_boolean().delay_parse()
            p5 = self._parse_literal_list().delay_parse()
            p6 = self._parse_literal_map().delay_parse()
            p7 = self._parse_literal_set().delay_parse()
            p8 = self._parse_literal_pair().delay_parse()
            p9 = self._parse_literal_tuple().delay_parse()
            p10 = self._parse_literal_regex().delay_parse()
            p11 = self._parse_literal_range().delay_parse()
            p12 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11).parse_once()
            return p12
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
            return StringLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_char(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxSingleQuoteChr).parse_once()
            return CharLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_boolean(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwTrue).delay_parse()
            p2 = self._parse_token(TokenType.KwFalse).delay_parse()
            p3 = (p1 | p2).parse_once()
            return BoolLiteralAst(p3 == TokenType.KwTrue)
        return BoundParser(self, inner)

    def _parse_literal_list(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_expressions().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return ListLiteralAst(p2)
        return BoundParser(self, inner)

    def _parse_literal_set(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_expressions().parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return SetLiteralAst(p2)
        return BoundParser(self, inner)

    def _parse_literal_map(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_literal_pair_internal().parse_once()
            p3 = self._parse_literal_map_next_pair().parse_zero_or_more()
            p4 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return MapLiteralAst([p2, *p3])
        return BoundParser(self, inner)

    def _parse_literal_map_next_pair(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkComma).parse_once()
            p6 = self._parse_literal_pair_internal().parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_literal_pair(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_literal_pair_internal().parse_once()
            p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_literal_pair_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_token(TokenType.TkColon).parse_once()
            p3 = self._parse_expression().parse_once()
            return PairLiteralAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_literal_regex(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxRegex).parse_once()
            return RegexLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_tuple(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_literal_tuple_with_0_or_1_element().delay_parse()
            p3 = self._parse_literal_tuple_with_multiple_elements().delay_parse()
            p4 = (p2 | p3).parse_once()
            p5 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return TupleLiteralAst(p4)
        return BoundParser(self, inner)

    def _parse_literal_tuple_with_0_or_1_element(self) -> BoundParser:
        def inner():
            p6 = self._parse_expression().parse_optional()
            p7 = self._parse_token(TokenType.TkComma).parse_optional()
            return p6
        return BoundParser(self, inner)

    def _parse_literal_tuple_with_multiple_elements(self) -> BoundParser:
        def inner():
            p10 = self._parse_expression().parse_once()
            p11 = self._parse_literal_tuple_with_multiple_elements_next().parse_zero_or_more()
            return [p10, *p11]
        return BoundParser(self, inner)

    def _parse_literal_tuple_with_multiple_elements_next(self) -> BoundParser:
        def inner():
            p8 = self._parse_token(TokenType.TkComma).parse_once()
            p9 = self._parse_expression().parse_once()
            return p9
        return BoundParser(self, inner)

    def _parse_literal_range(self) -> BoundParser:
        def inner():
            p1 = self._parse_literal_range_opt_start().delay_parse()
            p2 = self._parse_literal_range_opt_end().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_literal_range_opt_start(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_optional()
            p2 = self._parse_token(TokenType.TkDoubleDot).parse_once()
            p3 = self._parse_expression().parse_once()
            return RangeLiteralAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_literal_range_opt_end(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_token(TokenType.TkDoubleDot).parse_once()
            p3 = self._parse_expression().parse_optional()
            return RangeLiteralAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_literal_number_base_02(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxBinDigits).parse_once()
            return NumberLiteralBase02Ast(p1)
        return BoundParser(self, inner)

    def _parse_literal_number_base_10(self) -> BoundParser:
        def inner():
            p1 = self._parse_number().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_literal_number_base_16(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxHexDigits).parse_once()
            return NumberLiteralBase16Ast(p1)
        return BoundParser(self, inner)

    # Number

    def _parse_number(self) -> BoundParser:
        def inner():
            p1 = self._parse_numeric_integer().parse_once()
            p2 = self._parse_numeric_decimal().parse_optional()
            p3 = self._parse_numeric_complex().parse_optional()
            p4 = self._parse_numeric_exponent().parse_optional() is not None
            return NumberLiteralBase10Ast(p1, p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_numeric_integer(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxDecDigits)
            return p1
        return BoundParser(self, inner)

    def _parse_numeric_decimal(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            p2 = self._parse_lexeme(TokenType.LxDecDigits)
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
            return NumberExponentAst(p2, p3)
        return BoundParser(self, inner)

    """[MISC]"""

    def _parse_token(self, token: TokenType) -> BoundParser:
        def inner():
            # print(f"parse_token: {token}")
            if self._dedents_expected > 0:
                raise ParseSyntaxError("Expected a dedent")

            if self._current < len(self._tokens) and \
                    self._tokens[self._current].token_type == TokenType.TkSemicolon \
                    and self._tokens[self._current + 1].token_type == TokenType.TkNewLine \
                    and token == TokenType.TkSemicolon:
                self._current += 2
                for _ in range(self._indent):
                    self._parse_token(TokenType.TkWhitespace)
                return TokenAst(Token(";", TokenType.TkSemicolon), None)


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
            ERRS.clear()
            self._current += 1

            return TokenAst(self._tokens[self._current - 1], None)
        return BoundParser(self, inner)

    def _parse_lexeme(self, lexeme: TokenType) -> BoundParser:
        def inner():
            p1 = self._parse_token(lexeme).parse_once()
            return p1.primary.token_metadata
        return BoundParser(self, inner)


    def _skip(self, token: TokenType):
        while self._current < len(self._tokens) and self._tokens[self._current].token_type == token:
            self._current += 1

    def _parse_indent(self) -> BoundParser:
        def increment_dedents_expected(x): # todo
            self._dedents_expected += x is None

        def inner():
            self._indent += 4
            p1 = self._parse_indented_whitespace().parse_once()
            if self._tokens[self._current].token_type == TokenType.TkWhitespace:
                raise ParseSyntaxError("Unexpected whitespace")

        return BoundParser(self, inner)

    def _parse_indented_whitespace(self) -> BoundParser:
        def inner():
            for i in range(self._indent):
                self._parse_token(TokenType.TkWhitespace).parse_once()
        return BoundParser(self, inner)

    def _parse_dedent(self) -> BoundParser:
        def inner():
            self._indent -= 4
            self._dedents_expected = max(self._dedents_expected - 1, 0)
        return BoundParser(self, inner)

    def _parse_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_character(self, character: str) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            if p1.identifier != character:
                raise ParseSyntaxError(f"Expected {character}, got {p1.value}")
            return p1
        return BoundParser(self, inner)
