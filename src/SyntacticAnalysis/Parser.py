from __future__ import annotations

import functools
import colorama
import re

from typing import Callable, Any, Optional, ParamSpec, TypeVar, Generic
from src.SyntacticAnalysis import Ast
from src.LexicalAnalysis.Tokens import TokenType, Token


class ParseSyntaxError(Exception):
    ...

class ParseSyntaxMultiError(Exception):
    ...

class ParseNegativeLookaheadError(Exception):
    ...

class ParsePositiveLookaheadError(Exception):
    ...

class ParserError(Exception):
    ...


colorama.init()

P = ParamSpec("P")
T = TypeVar("T")


EXPECTED_TOKENS = []
ERRS = []
CUR_ERR_IND = 0


class ErrFmt:
    TOKENS: list[Token] = []
    FILE_PATH: str = ""

    @staticmethod
    def escape_ansi(line):
        ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', line)
    
    @staticmethod
    def err(start_token_index: int, extend_tok_len = -1) -> str:
        while ErrFmt.TOKENS[start_token_index].token_type in [TokenType.TkNewLine, TokenType.TkWhitespace]:
            start_token_index += 1

        # The error position for the ("^") will be from the provisional start token index. If the error position is end
        # of the file, then the error position have to be decremented by one, so that the error position is not pointing
        # to the EOF token. The start token index has to be moved back to that the newline behind the EOF is skipped (if
        # there is one).
        error_position = start_token_index
        if ErrFmt.TOKENS[error_position].token_type == TokenType.TkEOF:
            error_position -= 1
            extend_tok_len -= 1
        if ErrFmt.TOKENS[error_position].token_type == TokenType.TkEOF and ErrFmt.TOKENS[error_position - 1] == TokenType.TkNewLine:
            start_token_index -= 1 # todo : not -1, need to minus off the number of newlines before the EOF

        # If the start index is on a newline token, then move it back until it is not on a newline, so that the correct
        # line can be tracked over in reverse to fin the start of it. Once a non-newline has been found, move the
        # counter back until another newline is found - this will be the start of the line.
        while start_token_index > 0 and ErrFmt.TOKENS[start_token_index].token_type == TokenType.TkNewLine:
            start_token_index -= 1
        while start_token_index > 0 and ErrFmt.TOKENS[start_token_index].token_type != TokenType.TkNewLine:
            start_token_index -= 1

        # The end of the line is the first newline after the start of the line. If The re-scan forward is required
        # because there could have been multiple newlines after the current line, so only go to the first one.
        end_token_index = start_token_index + 1
        if end_token_index < len(ErrFmt.TOKENS) and ErrFmt.TOKENS[end_token_index].token_type == TokenType.TkNewLine:
            end_token_index += 1
        while end_token_index < len(ErrFmt.TOKENS) and ErrFmt.TOKENS[end_token_index].token_type != TokenType.TkNewLine:
            end_token_index += 1

        # Get the tokens on the current line by slicing the tokens between the start and end indexes just found from
        # backwards and forward newline-scanning
        tokens = ErrFmt.TOKENS[start_token_index:end_token_index]

        # The number of spaces before the "^" characters is the error message position variable from the start - this
        # hasn't been altered
        spaces = 0
        for token in tokens[:error_position - start_token_index - 1]:
            spaces += len(token.token_metadata)

        # Format the line number into the error message string
        line_number = "".join([
            f"{colorama.Fore.WHITE}{colorama.Style.BRIGHT}",
            str([t.token_type for t in ErrFmt.TOKENS[:end_token_index]].count(TokenType.TkNewLine) + 1),
            f" | {colorama.Style.RESET_ALL}"])

        line_containing_error_string = "".join([
            line_number,
            f"{colorama.Fore.GREEN}"
            "".join([token.token_metadata for token in tokens]).lstrip("\n"),
            f"{colorama.Style.RESET_ALL}"
        ])

        # The number of "^" characters is the length of the current tokens metadata (ie the symbol or length of keyword
        # / lexeme). Append the repeated "^" characters to the spaces, and then add the error message to the string.
        error_length = max(1, len(ErrFmt.TOKENS[error_position].token_metadata)) if extend_tok_len < 0 else extend_tok_len - error_position
        number_margin_len = len(ErrFmt.escape_ansi(line_number)) - 2

        file_path_string = "".join([
            "-> ",
            f"{colorama.Fore.WHITE}{colorama.Style.BRIGHT}",
            ErrFmt.FILE_PATH,
            f": [Tok: {start_token_index}]"
            f"{colorama.Style.RESET_ALL}"])

        top_line_padding_string = "".join([
            " " * number_margin_len,
            f"{colorama.Fore.WHITE}{colorama.Style.BRIGHT}| {colorama.Style.RESET_ALL}"])

        error_description_string = "".join([
            " " * number_margin_len,
            f"{colorama.Fore.WHITE}{colorama.Style.BRIGHT}| {colorama.Style.RESET_ALL}",
            f"{colorama.Fore.RED}{colorama.Style.BRIGHT}",
            "".join([" " * spaces, "^" * error_length]),
            f"{colorama.Style.RESET_ALL}",
            " <- "])

        final_string = "\n".join([
            "",
            file_path_string,
            top_line_padding_string,
            line_containing_error_string,
            error_description_string])
        return final_string


class BoundParser(Generic[T]):
    _rule: Callable[P, T]
    _parser: Parser
    _delayed: bool
    _ast: Optional[Any]

    def __init__(self, parser: Parser, rule: Optional[Callable[P, T]]):
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

    def parse_negative_lookahead(self) -> None:
        restore_index = self._parser.current
        try:
            _ = self.parse_once()
            raise ParseNegativeLookaheadError("Expected no result")
        except (ParseSyntaxError, ParseSyntaxMultiError):
            self._parser.current = restore_index
            return

    def parse_positive_lookahead(self) -> None:
        restore_index = self._parser.current
        try:
            _ = self.parse_once()
            self._parser.current = restore_index
            return
        except (ParseSyntaxError, ParseSyntaxMultiError):
            raise ParsePositiveLookaheadError("Expected a result")

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

    def __init__(self, tokens: list[Token], file_path: str):
        self._tokens = tokens
        self._current = 0

        ErrFmt.TOKENS = self._tokens
        ErrFmt.FILE_PATH = file_path

    def _current_token_index(self) -> int:
        return self._current

    def parse(self) -> Ast.ProgramAst:
        try:
            program = self._parse_program().parse_once()
            return program
        except ParseSyntaxError: # todo : experimental
            final_error = None
            final_error_line_number = -1
            final_error_where_on_line = -1

            for error in ERRS:
                error_where, error = error.split(" ", 1)
                error = ErrFmt.err(int(error_where)) + error

                current_error = ErrFmt.escape_ansi(error.split("\n")[3])
                current_error_line_number = int(current_error[:current_error.index(" ")])
                current_error_where_on_line = ErrFmt.escape_ansi(error.replace('\n', '\\n').split("\n")[-1]).index("^") + 1

                if (current_error_line_number > final_error_line_number) or (current_error_line_number == final_error_line_number and current_error_where_on_line > final_error_where_on_line):
                    final_error = error
                    final_error_line_number = current_error_line_number
                    final_error_where_on_line = current_error_where_on_line

            e = ParseSyntaxError(final_error)
            # e = ParseSyntaxError("\n".join(ERRS))
            raise SystemExit(e) from None


    def _parse_program(self) -> BoundParser:
        """
        [Program] => [ModulePrototype] [EOF]
        - [ModulePrototype] => Contents of the current module.
        - [EOF] => Ensure there is no invalid code after the module.

        The [Program] is the root parser for the code being parsed. It parses for a [ModulePrototype], and then ensures
        that there is no invalid code after the module, by checking for the [EOF]. This check is required because
        otherwise any code would parse, as the parser would leave the rest of the code unparsed but be "complete".

        @return: The [Program]'s Ast.ProgramAst, the root of the AST for the code being parsed.
        """
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_module_prototype().parse_once()
            p2 = self._parse_eof().parse_once()
            return Ast.ProgramAst(p1, p2, c1)
        return BoundParser(self, inner)

    def _parse_eof(self) -> BoundParser:
        """
        [EOF] => [Token(EOF)]
        - [Token(EOF)] => The end of the file token inserted by the Lexer post-lexing.

        The [EOF] parser ensures that there is no invalid code after the module. It does this by parsing for the
        [Token(EOF)] token, which is inserted by the Lexer post-lexing. If the [Token(EOF)] is not found, then the
        parser has not reached the end of the file, and there is invalid code after the module.

        @return: The [EOF]'s Ast.TokenAst, maintaining consistency with the other parser functions.
        """
        def inner():
            p1 = self._parse_token(TokenType.TkEOF).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_module_prototype(self) -> BoundParser:
        """
        [ModulePrototype] => [Decorators]? [Token(Mod)] [ModuleIdentifier] [Token(NewLine)] [ModuleImplementation]
        - [Decorators]? => Zero or more [Decorators] used to decorate the module.
        - [Token(Mod)] => The [Token(Mod)] token, which is the keyword "mod", identifying that this is a module.
        - [ModuleIdentifier] => The [ModuleIdentifier] of the module, which is the name of the module.
        - [Token(NewLine)] => The [Token(NewLine)] token, which terminates the end of the line
        - [ModuleImplementation] => The [ModuleImplementation] of the module, which is the contents of the module.

        The [ModulePrototype] parser parses for the prototype of the module. It parses checks for decorators, and the
        identifier of the module. The [ModuleImplementation] contains all the functions/class definitions etc of the
        module.
        @return:
        """
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_decorators().parse_optional() or []
            p2 = self._parse_token(TokenType.KwMod).parse_once()
            p3 = self._parse_module_identifier().parse_once()
            p5 = self._parse_module_implementation().parse_once()
            return Ast.ModulePrototypeAst(p1, p3, p5, c1)
        return BoundParser(self, inner)

    def _parse_module_implementation(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            # p1 = self._parse_import_block().parse_optional()
            p2 = self._parse_module_member().parse_zero_or_more()
            return Ast.ModuleImplementationAst(None, p2, c1)
        return BoundParser(self, inner)

    def _parse_module_identifier(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_module_identifier_next_part().parse_zero_or_more()
            return Ast.ModuleIdentifierAst([p1, *p2], c1)
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
            c1 = self._current_token_index()
            p1 = self._parse_import_statement().parse_one_or_more()
            return Ast.ImportBlockAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_import_statement(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwUse).parse_once()
            p2 = self._parse_import_identifier().parse_once()
            p3 = self._parse_import_what().parse_once()
            return Ast.ImportStatementAst(p2, p3, c1)
        return BoundParser(self, inner)

    def _parse_import_identifier(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_import_identifier_part().parse_one_or_more()
            return Ast.ImportIdentifierAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_import_identifier_part(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkDot).parse_once()
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
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkMul).parse_once()
            return Ast.ImportTypesAllAst(c1)
        return BoundParser(self, inner)

    def _parse_import_single(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_import_type().parse_once()
            return Ast.ImportTypesIndividualAst([p1], c1)
        return BoundParser(self, inner)

    def _parse_import_multiple(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkBraceL).parse_once()
            p2 = self._parse_import_types().parse_once()
            p3 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.ImportTypesIndividualAst(p2, c1)
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
            c1 = self._current_token_index()
            p1 = self._parse_upper_identifier().parse_once()
            p2 = self._parse_import_type_alias().parse_optional()
            return Ast.ImportTypeAst(p1, p2, c1)
        return BoundParser(self, inner)

    def _parse_import_type_alias(self):
        def inner():
            p1 = self._parse_token(TokenType.KwAs).parse_once()
            p2 = self._parse_upper_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    # Classes

    def _parse_class_prototype(self) -> BoundParser:
        """
        [ClassPrototype] => [Decorators*] [Token(cls)
        @return:
        """
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_decorators().parse_optional() or []
            p2 = self._parse_token(TokenType.KwCls).parse_once()
            p3 = self._parse_class_identifier().parse_once()
            p4 = self._parse_type_generic_parameters().parse_optional() or []
            p5 = self._parse_where_block().parse_optional()
            p6 = self._parse_token(TokenType.TkBraceL).parse_once()
            p7 = self._parse_class_implementation().parse_once()
            p8 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.ClassPrototypeAst(p1, p3, p4, p5, p7, c1)
        return BoundParser(self, inner)

    def _parse_class_implementation(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_class_member().parse_zero_or_more()
            return Ast.ClassImplementationAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_class_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_attribute().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_attribute(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_decorators().parse_optional() or []
            p3 = self._parse_class_attribute_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_type_identifier().parse_once()
            return Ast.ClassAttributeAst(p1, p3, p5, c1)
        return BoundParser(self, inner)

    def _parse_class_attribute_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_upper_identifier().parse_once()
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
            c1 = self._current_token_index()
            p1 = self._parse_type_generic_parameters().parse_optional() or []
            p2 = self._parse_sup_identifier().parse_once()
            p3 = self._parse_where_block().parse_optional()
            p4 = self._parse_token(TokenType.TkBraceL).parse_once()
            p5 = self._parse_sup_implementation().parse_once()
            p6 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.SupPrototypeNormalAst(p1, p2, p3, p5, c1)
        return BoundParser(self, inner)

    def _parse_sup_prototype_with_inherit(self):
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_type_generic_parameters().parse_optional() or []
            p2 = self._parse_sup_identifier().parse_once()
            p3 = self._parse_token(TokenType.KwFor).parse_once()
            p4 = self._parse_sup_identifier().parse_once()
            p5 = self._parse_where_block().parse_optional()
            p6 = self._parse_token(TokenType.TkBraceL).parse_once()
            p7 = self._parse_sup_implementation().parse_once()
            p8 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.SupPrototypeInheritanceAst(p1, p4, p5, p7, c1, p2)
        return BoundParser(self, inner)

    def _parse_sup_implementation(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_sup_member().parse_zero_or_more()
            return Ast.SupImplementationAst(p1, c1)
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
            p1 = self._parse_single_type_identifier_no_self().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_typedef(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_decorators().parse_optional() or []
            p2 = self._parse_statement_typedef().parse_once()
            return Ast.SupTypedefAst(p2.new_type, p2.old_type, c1, p1)
        return BoundParser(self, inner)

    def _parse_sup_method_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_prototype().parse_once()
            return Ast.SupMethodPrototypeAst(p1.decorators, p1.is_coro, p1.identifier, p1.generic_parameters, p1.parameters, p1.return_type, p1.where_block, p1.body, p1._tok)
        return BoundParser(self, inner)

    # Enums

    def _parse_enum_prototype(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_decorators().parse_optional() or []
            p2 = self._parse_token(TokenType.KwEnum).parse_once()
            p3 = self._parse_enum_identifier().parse_once()
            p4 = self._parse_type_generic_parameters().parse_optional()
            p5 = self._parse_where_block().parse_optional()
            p6 = self._parse_token(TokenType.TkBraceL).parse_once()
            p7 = self._parse_enum_implementation().parse_once()
            p8 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.EnumPrototypeAst(p1, p3, p4, p5, p7, c1)
        return BoundParser(self, inner)

    def _parse_enum_implementation(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_enum_member().parse_once()
            p2 = self._parse_enum_member_next().parse_zero_or_more()
            return Ast.EnumImplementationAst([p1, *p2], c1)
        return BoundParser(self, inner)

    def _parse_enum_member_next(self):
        def inner():
            p4 = self._parse_token(TokenType.TkComma).parse_once()
            p5 = self._parse_enum_member().parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_enum_member(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_enum_member_identifier().parse_once()
            p2 = self._parse_enum_member_value_wrapper().parse_optional()
            return Ast.EnumMemberAst(p1, p2, c1)
        return BoundParser(self, inner)

    def _parse_enum_member_value_wrapper(self):
        def inner():
            p3 = self._parse_token(TokenType.TkAssign).parse_once()
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
            p1 = self._parse_upper_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Function Prototype & Implementation

    def _parse_function_structure_type(self) -> BoundParser:
        """
        The <FunctionStructureType> determines the type of the underlying structure for the function. This will be
        either a subroutine (fn), or a coroutine (gn). The keyword `fn` was chosen for its simplicity and common use,
        and `gn` for "generate" and "g" follows "f", despite it being a coroutine not a generator (can send a value to
        it) with std::Gen[T]::next(...).
        :return: The type of the function structure.
        """
        def inner():
            p1 = self._parse_token(TokenType.KwFn).delay_parse()
            p2 = self._parse_token(TokenType.KwGn).delay_parse()
            p3 = (p1 | p2).parse_once().tok.token_type == TokenType.KwGn
            return p3
        return BoundParser(self, inner)

    def _parse_function_prototype(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_decorators().parse_optional() or []
            p2 = self._parse_function_structure_type().parse_once()
            p3 = self._parse_function_identifier().parse_once()
            p4 = self._parse_type_generic_parameters().parse_optional() or []
            p5 = self._parse_function_parameters().parse_once()
            p6 = self._parse_token(TokenType.TkArrowR).parse_once()
            p7 = self._parse_type_identifier().parse_once()
            p8 = self._parse_where_block().parse_optional()
            p10 = self._parse_token(TokenType.TkBraceL).parse_once()
            p11 = self._parse_function_implementation().parse_once()
            p12 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.FunctionPrototypeAst(p1, p2, p3, p4, p5, p7, p8, p11, c1)
        return BoundParser(self, inner)

    def _parse_function_implementation(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_statement().parse_zero_or_more()
            return Ast.FunctionImplementationAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_function_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Function Call Arguments

    def _parse_function_call_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkParenL).parse_once()
            p2 = self._parse_function_call_arguments_internal().parse_optional() or []
            p3 = self._parse_token(TokenType.TkParenR).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_argument_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_call_normal_argument().delay_parse()
            p2 = self._parse_function_call_named_argument().delay_parse()
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_call_arguments_internal_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_argument_internal().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_arguments_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_call_argument_internal().parse_once()
            p2 = self._parse_function_call_arguments_internal_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_function_call_normal_argument(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_parameter_passing_convention().parse_optional()
            p2 = self._parse_operator_identifier_variadic().parse_optional() is not None
            p3 = self._parse_non_assignment_expression().parse_once()
            return Ast.FunctionArgumentNormalAst(p1, p3, p2, c1)
        return BoundParser(self, inner)

    def _parse_function_call_named_argument(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkAssign).parse_once()
            p3 = self._parse_parameter_passing_convention().parse_optional()
            p4 = self._parse_non_assignment_expression().parse_once()
            return Ast.FunctionArgumentNamedAst(p1, p3, p4, c1)
        return BoundParser(self, inner)

    # Function Parameters

    def _parse_function_parameters(self) -> BoundParser:
        """
        All variants of a function parameter can be parsed here n times, and the semantic analysis will verify that the
        order of parameters is [required -> optional -> variadic]. This simplifies the parser heavily.
        """
        def inner():
            p1 = self._parse_token(TokenType.TkParenL).parse_once()
            p2 = self._parse_function_parameters_internal().parse_optional() or []
            p3 = self._parse_token(TokenType.TkParenR).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_parameter_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_parameter_self().delay_parse()
            p2 = self._parse_function_parameter_required().delay_parse()
            p3 = self._parse_function_parameter_optional().delay_parse()
            p4 = self._parse_function_parameter_variadic().delay_parse()
            p5 = (p1 | p4 | p3 | p2).parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_function_parameters_internal_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameter_internal().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_parameters_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_parameter_internal().parse_once()
            p2 = self._parse_function_parameters_internal_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_function_parameter_self(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_function_parameter_self_calling_convention().parse_optional()
            p2 = self._parse_token(TokenType.KwSelf).parse_once()
            return Ast.FunctionParameterSelfAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_function_parameter_self_calling_convention(self) -> BoundParser:
        def inner():
            p1 = self._parse_parameter_passing_convention().delay_parse()
            p2 = self._parse_token(TokenType.KwMut).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_parameter_required(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            p2 = self._parse_identifier().parse_once()
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_parameter_passing_convention().parse_optional()
            p5 = self._parse_type_identifier().parse_once()
            return Ast.FunctionParameterRequiredAst(p1, p2, p4, p5, c1)
        return BoundParser(self, inner)

    def _parse_function_parameter_optional(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_parameter_required().parse_once()
            p2 = self._parse_token(TokenType.TkAssign).parse_once()
            p3 = self._parse_non_assignment_expression().parse_once()
            return Ast.FunctionParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_function_parameter_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_operator_identifier_variadic().parse_once()
            p2 = self._parse_function_parameter_required().parse_once()
            return Ast.FunctionParameterVariadicAst(p2)
        return BoundParser(self, inner)

    # Type Constraints & Value Guard

    def _parse_where_block(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwWhere).parse_once()
            p2 = self._parse_token(TokenType.TkBrackL).parse_once()
            p3 = self._parse_where_constraints().parse_once()
            p4 = self._parse_token(TokenType.TkBrackR).parse_once()
            return Ast.WhereBlockAst(p3, c1)
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
            c1 = self._current_token_index()
            p1 = self._parse_type_identifiers().parse_once()
            p2 = self._parse_token(TokenType.TkColon).parse_once()
            p3 = self._parse_where_constraint_chain().parse_once()
            return Ast.WhereConstraintAst(p1, p3, c1)
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
            p1 = self._parse_single_type_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    # Decorators

    def _parse_decorator(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkAt).parse_once()
            p2 = self._parse_decorator_identifier().parse_once()
            p3 = self._parse_type_generic_arguments().parse_optional() or []
            p4 = self._parse_function_call_arguments().parse_optional() or []
            return Ast.DecoratorAst(p2, p3, p4, c1)
        return BoundParser(self, inner)

    def _parse_decorators(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorator().parse_zero_or_more()
            return p1
        return BoundParser(self, inner)

    def _parse_decorator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_module_identifier().parse_once()
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
            p1 = self._parse_stage_1_binary_expression().parse_once()
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
            self._parse_non_assignment_expression(),
            self._parse_operator_identifier_assignment(),
            self._parse_non_assignment_expression)

    def _parse_assignment_expression_multiple(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_non_assignment_expression().parse_once()
            p2 = self._parse_assignment_multiple_lhs().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkAssign).parse_once()
            p4 = self._parse_non_assignment_expression().parse_once()
            return Ast.AssignmentExpressionAst([p1, *p2], p3, p4, c1)
        return BoundParser(self, inner)

    def _parse_assignment_multiple_lhs(self) -> BoundParser:
        def inner():
            p9 = self._parse_token(TokenType.TkComma).parse_once()
            p10 = self._parse_non_assignment_expression().parse_once()
            return p10
        return BoundParser(self, inner)

    def _parse_stage_1_binary_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_stage_2_binary_expression(),
            self._parse_stage_1_binary_operator_identifier(),
            self._parse_stage_1_binary_expression)

    def _parse_stage_2_binary_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_stage_3_binary_expression(),
            self._parse_stage_2_binary_operator_identifier(),
            self._parse_stage_2_binary_expression)

    def _parse_stage_3_binary_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_stage_4_binary_expression(),
            self._parse_stage_3_binary_operator_identifier(),
            self._parse_stage_3_binary_expression)

    def _parse_stage_4_binary_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_stage_5_binary_expression(),
            self._parse_stage_4_binary_operator_identifier(),
            self._parse_stage_4_binary_expression)

    def _parse_stage_5_binary_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_stage_6_binary_expression(),
            self._parse_stage_5_binary_operator_identifier(),
            self._parse_stage_5_binary_expression)

    def _parse_stage_6_binary_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_postfix_expression(),
            self._parse_stage_6_binary_operator_identifier(),
            self._parse_stage_6_binary_expression)

    def _parse_postfix_expression(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_primary_expression().parse_once()
            p2 = self._parse_operator_identifier_postfix().parse_zero_or_more()
            return functools.reduce(lambda p, op: Ast.PostfixExpressionAst(p, op, c1), p2, p1)
        return BoundParser(self, inner)

    def _parse_primary_expression(self) -> BoundParser:
        """
        [PrimaryExpression] => [SelfKeyword] | [SingleTypeIdentifierForInitialization] | [TypeIdentifier] | [Identifier]
                             | [Literal] | [Lambda] | [OperatorIdentifierVariadic] | [ExpressionPlaceholder]
                             | [StatementIf] | [StatementWhile] | [StatementNewScope] | [StatementYield]
                             | [StatementWith]
        [SelfKeyword] => "self" can be used as part of an identifier. Its a keyword so needs own parsing function.
        TODO
        """
        def inner():
            p1 = self._parse_self_keyword().delay_parse()  # self.function();
            p2 = self._parse_single_type_identifier_for_initialization().delay_parse()  # let x: std.Num{};
            p3 = self._parse_single_type_identifier().delay_parse()  # let x = std.Num.new();
            p4 = self._parse_identifier().delay_parse()  # let x = identifier
            p5 = self._parse_literal().delay_parse()  # let x = 123
            p6 = self._parse_lambda().delay_parse()  # let x = (x) => {x + 1}
            p7 = self._parse_operator_identifier_variadic().delay_parse()  # let x = 0 + ... + args
            p8 = self._parse_expression_placeholder().delay_parse()  # let x = f(_, 1, 2);
            p9 = self._parse_statement_if().delay_parse()
            p10 = self._parse_statement_while().delay_parse()
            p11 = self._parse_statement_new_scope().delay_parse()
            p12 = self._parse_statement_yield().delay_parse()
            p13 = self._parse_statement_with().delay_parse()
            p14 = (p9 | p10 | p11 | p12 | p13 | p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8).parse_once()
            return p14
        return BoundParser(self, inner)

    def _parse_self_keyword(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwSelf).parse_once()
            return Ast.IdentifierAst("self", c1)
        return BoundParser(self, inner)

    def _parse_single_type_identifier_for_initialization(self) -> BoundParser:
        def inner():
            p1 = self._parse_single_type_identifier().parse_once()
            p2 = self._parse_postfix_operator_struct_initializer().parse_once()
            return Ast.PostfixExpressionAst(p1, p2, p1._tok)
        return BoundParser(self, inner)

    def _parse_binary_expression(self, __lhs, __op, __rhs) -> BoundParser:
        def inner(lhs, op, rhs):
            c1 = self._current_token_index()
            p1 = lhs.parse_once()
            p2 = self._parse_binary_expression_rhs(op, rhs).parse_optional()
            return p1 if p2 is None else Ast.BinaryExpressionAst(p1, p2[0], p2[1], c1)
        return BoundParser(self, functools.partial(inner, __lhs, __op, __rhs))

    def _parse_binary_expression_rhs(self, __op, __rhs) -> BoundParser:
        def inner(op, rhs):
            p3 = op.parse_once()
            p4 = rhs().parse_once()
            return p3, p4
        return BoundParser(self, functools.partial(inner, __op, __rhs))

    def _parse_expression_placeholder(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkUnderscore).parse_once()
            return Ast.PlaceholderAst(c1)
        return BoundParser(self, inner)

    # Lambda

    def _parse_lambda(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lambda_capture_list().parse_optional()
            p2 = self._parse_lambda_parameters().parse_once()
            p3 = self._parse_token(TokenType.TkArrowR).parse_once()
            p4 = self._parse_statement_new_scope().parse_once()
            return Ast.LambdaAst(p1, p2, p4.body, c1)
        return BoundParser(self, inner)

    def _parse_lambda_capture_list(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkBrackL).parse_once()
            p2 = self._parse_lambda_capture_item().parse_once()
            p3 = self._parse_lambda_capture_item_next().parse_zero_or_more()
            p4 = self._parse_token(TokenType.TkBrackR).parse_once()
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
            c1 = self._current_token_index()
            p1 = self._parse_lambda_capture_item_alias().parse_optional()
            p2 = self._parse_parameter_passing_convention().parse_optional()
            p3 = self._parse_identifier().parse_once()
            return Ast.LambdaCaptureItemAst(p1, p2, p3, c1)
        return BoundParser(self, inner)

    def _parse_lambda_capture_item_alias(self) -> BoundParser:
        def inner():
            p3 = self._parse_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkAssign).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_lambda_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkParenL).parse_once()
            p2 = self._parse_lambda_parameters_required().parse_optional() or []
            p3 = self._parse_token(TokenType.TkParenR).parse_once()
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
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwMut).parse_optional()
            p2 = self._parse_identifier().parse_once()
            return Ast.LambdaParameterAst(p1, p2, c1)
        return BoundParser(self, inner)

    # Type Identifiers

    def _parse_type_identifier(self) -> BoundParser:
        """
        [TypeIdentifier] => [SingleTypeIdentifier | TupleTypeIdentifier]
        - [SingleTypeIdentifier] => A single type, such as std.Num.
        - [TupleTypeIdentifier] => A tuple of types, such as (std.Num, std.Str).

        A type identifier can be either a single or a tuple type. Both can be used in all contexts of a "type", so the
        choice to parse either happens at the top level of the type identifier parser.
        """

        def inner():
            p1 = self._parse_single_type_identifier().delay_parse()
            p2 = self._parse_tuple_type_identifiers().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().parse_once()
            p2 = self._parse_type_identifier_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_identifier_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_single_type_identifier(self) -> BoundParser:
        """
        [SingleTypeIdentifier] => [TypeIdentifierWithSelf | TypeIdentifierNoSelf]
        - [TypeIdentifierWithSelf] => A type identifier that starts with "Self::", such as "Self.Output.A".
        - [TypeIdentifierNoSelf] => A type identifier that does not start with "Self::", such as "std.Num".
        """

        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_single_type_identifier_with_self().delay_parse()
            p2 = self._parse_single_type_identifier_no_self().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_tuple_type_identifiers(self) -> BoundParser:
        """
        [TupleTypeIdentifier] => [Token(ParenL)] [TypeIdentifiers?] [Token(ParenR)]
        - [Token(ParenL)] => The left parenthesis that opens the tuple type.
        - [TypeIdentifiers]? => The optional types that make up the tuple type.
        - [Token(ParenR)] => The right parenthesis that closes the tuple type.

        A tuple type identifier is a collection of different types, that form a numerically accessible type. For
        example, "(std.Num, std.Str).0" is a valid expression, and will return the type std.Num.
        """

        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkParenL).parse_once()
            p2 = self._parse_type_identifiers().parse_optional() or []
            p3 = self._parse_token(TokenType.TkParenR).parse_once()
            return Ast.TypeTupleAst(p2, c1)
        return BoundParser(self, inner)

    def _parse_single_type_identifier_with_self(self) -> BoundParser:
        """
        [TypeIdentifierWithSelf] => [Token(SelfType)] [TypeIdentifierUpperTypesFollowingSelf?]
        - [Token(SelfType)] => The "Self" keyword, which is a type identifier.
        - [TypeIdentifierUpperTypesFollowingSelf?] => The optional types that follow the "Self" keyword.

        Only uppercase types (ie no namespacing) can follow the "Self" that starts a type. This means that while
        "Self.A" is valid, "Self.std.Num" is invalid at the parser level. Types following "Self" are optional, as the
        type "Self" is valid on it's own (context dependant).
        """

        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwSelfType).parse_once()
            p2 = self._parse_type_identifier_upper_types_following_self().parse_optional() or []
            return Ast.TypeSingleAst([Ast.GenericIdentifierAst("Self", [], c1), *p2], c1)
        return BoundParser(self, inner)

    def _parse_type_identifier_upper_types_following_self(self) -> BoundParser:
        """
        [TypeIdentifierUpperTypesFollowingSelf] => [Token(Dot)] [TypeIdentifierUpperTypes?]
        - [Token(Dot)] => The dot that separates the "Self" keyword from the types that follow it.
        - [TypeIdentifierUpperTypes?] => The optional types that follow the "Self" keyword.

        This method checks for types following the "Self" keyword. Firstly check for a "." after the "Self", and then
        for multiple following types.
        @return:
        """
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            p2 = self._parse_type_identifier_upper_types().parse_optional() or []
            return p2
        return BoundParser(self, inner)

    def _parse_single_type_identifier_no_self(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier_namespace_then_types().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_type_identifier_namespace(self) -> BoundParser:
        def inner():
            p2 = self._parse_type_identifier_namespace_parts().parse_zero_or_more()
            return p2
        return BoundParser(self, inner)

    def _parse_type_identifier_namespace_parts(self) -> BoundParser:
        def inner():
            p2 = self._parse_identifier().parse_once()
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            return p2.to_generic_identifier()
        return BoundParser(self, inner)

    def _parse_type_identifier_namespace_then_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier_namespace().parse_optional() or []
            p2 = self._parse_type_identifier_upper_types().parse_once()
            return Ast.TypeSingleAst([*p1, *p2], p1[0]._tok if p1 else p2[0]._tok)
        return BoundParser(self, inner)

    def _parse_type_identifier_upper_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier_upper_type_exclusive().parse_once()
            p2 = self._parse_type_identifier_next_upper_type().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_identifier_next_upper_type(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            p2 = self._parse_type_identifier_upper_type_or_number().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_identifier_upper_type_exclusive(self) -> BoundParser:
        def inner():
            p2 = self._parse_generic_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_identifier_upper_type_or_number(self) -> BoundParser:
        def inner():
            p1 = self._parse_generic_identifier().delay_parse()
            p2 = self._parse_numeric_integer().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    # Type Generic Arguments

    def _parse_type_generic_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkBrackL).parse_once()
            p2 = self._parse_type_generic_arguments_internal().parse_optional() or []
            p3 = self._parse_token(TokenType.TkBrackR).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_argument_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_argument_normal().delay_parse()
            p2 = self._parse_type_generic_argument_named().delay_parse()
            p3 = (p2 | p1).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_generic_argument_internal_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_argument_internal().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_arguments_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_argument_internal().parse_once()
            p2 = self._parse_type_generic_argument_internal_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_generic_argument_normal(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_type_identifier().parse_once()
            return Ast.TypeGenericArgumentNormalAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_type_generic_argument_named(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_upper_identifier().parse_once()
            p2 = self._parse_token(TokenType.TkAssign).parse_once()
            p3 = self._parse_type_identifier().parse_once()
            return Ast.TypeGenericArgumentNamedAst(p1, p3, c1)
        return BoundParser(self, inner)

    # Type Generic Parameters

    def _parse_type_generic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkBrackL).parse_once()
            p2 = self._parse_type_generic_parameters_internal().parse_optional() or []
            p3 = self._parse_token(TokenType.TkBrackR).parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_parameter_required().delay_parse()
            p2 = self._parse_type_generic_parameter_optional().delay_parse()
            p3 = self._parse_type_generic_parameter_variadic().delay_parse()
            p4 = (p3 | p2 | p1).parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_internal_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameter_internal().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_parameters_internal(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_parameter_internal().parse_once()
            p2 = self._parse_type_generic_parameter_internal_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_required(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_upper_identifier().parse_once()
            p2 = self._parse_type_generic_parameter_inline_constraint().parse_optional() or []
            return Ast.TypeGenericParameterRequiredAst(p1, p2, c1)
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_optional(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_parameter_required().parse_once()
            p2 = self._parse_token(TokenType.TkAssign).parse_once()
            p3 = self._parse_type_identifier().parse_once()
            return Ast.TypeGenericParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
            p2 = self._parse_type_generic_parameter_required().parse_once()
            return Ast.TypeGenericParameterVariadicAst(p2)
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_inline_constraint(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_where_constraint_chain().parse_once()
            return p4
        return BoundParser(self, inner)

    # Statements

    def _parse_statement_if(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwIf).parse_once()
            p2 = self._parse_non_assignment_expression().parse_once()
            p3 = self._parse_pattern_op().parse_optional()
            p4 = self._parse_token(TokenType.TkBraceL).parse_once()
            p5 = self._parse_statement_pattern().parse_zero_or_more()
            p6 = self._parse_statement_pattern_default().parse_optional()
            p7 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.IfStatementAst(p2, p3, [*p5, p6] if p6 else p5, c1)
        return BoundParser(self, inner)

    def _parse_statement_pattern(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_pattern_op().parse_optional()
            p2 = self._parse_pattern_composite().parse_once()
            p3 = self._parse_pattern_guard().parse_optional()
            p4 = self._parse_statement_new_scope().parse_once()
            return Ast.PatternStatementAst(p1, p2, p3, p4.body, c1)
        return BoundParser(self, inner)

    def _parse_statement_pattern_default(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwElse).parse_once()
            p3 = self._parse_statement_new_scope().parse_once()
            return Ast.PatternStatementAst(None, [Ast.PatternAst(Ast.BoolLiteralAst(True, c1), c1)], None, p3.body, c1) # c1?
        return BoundParser(self, inner)

    def _parse_pattern_op(self) -> BoundParser:
        def inner():
            p1 = self._parse_stage_3_binary_operator_identifier().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_pattern_guard(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkDoubleAmpersand).parse_once()
            p2 = self._parse_non_assignment_expression().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_pattern_composite(self) -> BoundParser:
        def inner():
            p1 = self._parse_pattern_val().parse_once()
            p2 = self._parse_pattern_val_next().parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_pattern_val(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_pattern_match_object().delay_parse()
            p2 = self._parse_literal().delay_parse()
            p3 = (p1 | p2).parse_once()
            return Ast.PatternAst(p3, c1)
        return BoundParser(self, inner)

    def _parse_pattern_val_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkPipe).parse_once()
            p2 = self._parse_pattern_val().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_pattern_match_object(self) -> BoundParser:
        def inner():
            p1 = self._parse_single_type_identifier().parse_once()
            p2 = self._parse_postfix_operator_struct_initializer().parse_once()
            return Ast.PostfixExpressionAst(p1, p2, p2._tok)
        return BoundParser(self, inner)

    def _parse_statement_while(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwWhile).parse_once()
            p2 = self._parse_expression().parse_once()
            p4 = self._parse_statement_new_scope().parse_once()
            p5 = self._parse_statements_residual_action().parse_optional()
            return Ast.WhileStatementAst(p2, p4.body, p5, c1)
        return BoundParser(self, inner)

    def _parse_statement_with(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwWith).parse_once()
            p2 = self._parse_expression().parse_once()
            p3 = self._parse_statement_alias_for_with_expression().parse_optional()
            p4 = self._parse_statement_new_scope().parse_once()
            return Ast.WithStatementAst(p2, p3, p4.body, c1)
        return BoundParser(self, inner)

    def _parse_statement_alias_for_with_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwAs).parse_once()
            p2 = self._parse_local_variable_identifier().parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_statement_return(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwRet).parse_once()
            p2 = self._parse_expression().parse_optional()
            return Ast.ReturnStatementAst(p2, c1)
        return BoundParser(self, inner)

    def _parse_statement_yield(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwYield).parse_once()
            p2 = self._parse_parameter_passing_convention().parse_optional()
            p3 = self._parse_expression().parse_optional()
            return Ast.YieldStatementAst(p2, p3, c1)
        return BoundParser(self, inner)

    def _parse_statement_typedef(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwUse).parse_once()
            p2 = self._parse_generic_identifier().parse_once()
            p3 = self._parse_token(TokenType.KwAs).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            return Ast.TypedefStatementAst(Ast.TypeSingleAst([p2], c1), p4, c1)
        return BoundParser(self, inner)

    def _parse_statement_let(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_let_with_value().delay_parse()
            p2 = self._parse_statement_let_with_type().delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_statement_let_with_value(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwLet).parse_once()
            p2 = self._parse_local_variable_identifiers().parse_once()
            p3 = self._parse_token(TokenType.TkAssign).parse_once()
            p4 = self._parse_non_assignment_expression().parse_once()
            p5 = self._parse_statements_residual_action().parse_optional()
            return Ast.LetStatementAst(p2, p4, None, p5, c1)
        return BoundParser(self, inner)

    def _parse_statements_residual_action(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwElse).parse_once()
            p2 = self._parse_statement_new_scope().parse_once()
            return Ast.InnerScopeAst(p2.body, c1)
        return BoundParser(self, inner)

    def _parse_statement_let_with_type(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwLet).parse_once()
            p2 = self._parse_local_variable_identifiers().parse_once()
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            return Ast.LetStatementAst(p2, None, p4, None, c1)
        return BoundParser(self, inner)

    def _parse_local_variable_identifier(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            p2 = self._parse_identifier().parse_once()
            return Ast.LocalVariableAst(p1, p2, c1)
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

    def _parse_statement_new_scope(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkBraceL).parse_once()
            p2 = self._parse_statement().parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.InnerScopeAst(p2, c1)
        return BoundParser(self, inner)

    def _parse_statement(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_typedef().delay_parse()
            p2 = self._parse_statement_return().delay_parse()
            p3 = self._parse_statement_let().delay_parse()
            p4 = self._parse_expression().delay_parse()
            p5 = self._parse_function_prototype().delay_parse()
            p6 = (p4 | p1 | p2 | p3 | p5).parse_once()
            return p6
        return BoundParser(self, inner)

    # def _parse_statement_expression(self) -> BoundParser:
    #     def inner():
    #         p1 = self._parse_expression().parse_once()
    #         return p1
    #     return BoundParser(self, inner)

    # Identifiers

    def _parse_identifier(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
            return Ast.IdentifierAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_upper_identifier(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxUpperIdentifier).parse_once()
            return Ast.IdentifierAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_generic_identifier(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxUpperIdentifier).parse_once()
            p2 = self._parse_type_generic_arguments().parse_optional() or []
            return Ast.GenericIdentifierAst(p1, p2, c1)
        return BoundParser(self, inner)

    # Postfix operations

    def _parse_postfix_operator_function_call(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_type_generic_arguments().parse_optional() or []
            p2 = self._parse_function_call_arguments().parse_once()
            return Ast.PostfixFunctionCallAst(p1, p2, c1)
        return BoundParser(self, inner)

    def _parse_postfix_operator_member_access(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkDot).parse_once()
            p2 = self._parse_identifier().delay_parse()
            p3 = self._parse_number().delay_parse()
            p4 = (p2 | p3).parse_once()
            return Ast.PostfixMemberAccessAst(p4, c1)
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkBraceL).parse_once()
            p2 = self._parse_postfix_operator_struct_initializer_fields().parse_optional() or []
            p3 = self._parse_token(TokenType.TkBraceR).parse_once()
            return Ast.PostfixStructInitializerAst(p2, c1)
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
            c1 = self._current_token_index()
            p1 = self._parse_postfix_operator_struct_initializer_field_identifier().parse_once()
            p2 = self._parse_postfix_operator_struct_initializer_field_value_different_to_identifier().parse_optional()
            return Ast.PostfixStructInitializerFieldAst(p1, p2, c1)
        return BoundParser(self, inner)

    def _parse_postfix_operator_struct_initializer_field_value_different_to_identifier(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkAssign).parse_once()
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
            p6 = self._parse_token(TokenType.TkAddEq).delay_parse()
            p7 = self._parse_token(TokenType.TkSubEq).delay_parse()
            p8 = self._parse_token(TokenType.TkMulEq).delay_parse()
            p9 = self._parse_token(TokenType.TkDivEq).delay_parse()
            p10 = self._parse_token(TokenType.TkRemEq).delay_parse()
            p11 = self._parse_token(TokenType.TkDoubleAngleLEquals).delay_parse()
            p12 = self._parse_token(TokenType.TkDoubleAngleREquals).delay_parse()
            p13 = self._parse_token(TokenType.TkTripleAngleLEquals).delay_parse()
            p14 = self._parse_token(TokenType.TkTripleAngleREquals).delay_parse()
            p15 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11 | p12 | p13 | p14).parse_once()
            return p15
        return BoundParser(self, inner)

    def _parse_stage_1_binary_operator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoublePipe).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_stage_2_binary_operator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleAmpersand).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_stage_3_binary_operator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkEq).delay_parse()
            p2 = self._parse_token(TokenType.TkNe).delay_parse()
            p3 = self._parse_token(TokenType.TkLt).delay_parse()
            p4 = self._parse_token(TokenType.TkGt).delay_parse()
            p5 = self._parse_token(TokenType.TkLe).delay_parse()
            p6 = self._parse_token(TokenType.TkGe).delay_parse()
            p7 = self._parse_token(TokenType.TkSs).delay_parse()
            p8 = (p1 | p2 | p3 | p4 | p5 | p6 | p7).parse_once()
            return p8
        return BoundParser(self, inner)

    def _parse_stage_4_binary_operator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDoubleAngleL).delay_parse()
            p2 = self._parse_token(TokenType.TkDoubleAngleR).delay_parse()
            p3 = self._parse_token(TokenType.TkTripleAngleL).delay_parse()
            p4 = self._parse_token(TokenType.TkTripleAngleR).delay_parse()
            p5 = (p1 | p2 | p3 | p4).parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_stage_5_binary_operator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAdd).delay_parse()
            p2 = self._parse_token(TokenType.TkSub).delay_parse()
            p3 = self._parse_token(TokenType.TkPipe).delay_parse()
            p4 = self._parse_token(TokenType.TkCaret).delay_parse()
            p5 = (p1 | p2 | p3 | p4).parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_stage_6_binary_operator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkMul).delay_parse()
            p2 = self._parse_token(TokenType.TkDiv).delay_parse()
            p3 = self._parse_token(TokenType.TkRem).delay_parse()
            p4 = self._parse_token(TokenType.TkAmpersand).delay_parse()
            p5 = (p1 | p2 | p3 | p4).parse_once()
            return p5
        return BoundParser(self, inner)


    def _parse_operator_identifier_additive(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAdd).delay_parse()
            p2 = self._parse_token(TokenType.TkSub).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_parameter_passing_convention(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkAmpersand).parse_once()
            p2 = self._parse_token(TokenType.KwMut).parse_optional() is not None
            return Ast.ParameterPassingConventionReferenceAst(p2, c1)
        return BoundParser(self, inner)

    def _parse_operator_identifier_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_operator_identifier_postfix(self) -> BoundParser:
        def inner():
            p1 = self._parse_postfix_operator_member_access().delay_parse()
            p2 = self._parse_postfix_operator_function_call().delay_parse()
            p3 = self._parse_token(TokenType.TkQst).delay_parse()
            p4 = (p1 | p2 | p3).parse_once()
            return p4
        return BoundParser(self, inner)

    # Literals

    def _parse_literal(self) -> BoundParser:
        def inner():
            p1 = self._parse_literal_number().delay_parse()
            p2 = self._parse_literal_string().delay_parse()
            p3 = self._parse_literal_array().delay_parse()
            p4 = self._parse_literal_boolean().delay_parse()
            p5 = self._parse_literal_tuple().delay_parse()
            p6 = self._parse_literal_regex().delay_parse()
            p7 = (p1 | p2 | p3 | p4 | p5 | p6).parse_once()
            return p7
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
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxDoubleQuoteStr).parse_once()
            return Ast.StringLiteralAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_literal_array(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkBrackL).parse_once()
            p2 = self._parse_expressions().parse_optional() or []
            p3 = self._parse_token(TokenType.TkBrackR).parse_once()
            return Ast.ArrayLiteralAst(p2, c1)
        return BoundParser(self, inner)

    def _parse_literal_boolean(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.KwTrue).delay_parse()
            p2 = self._parse_token(TokenType.KwFalse).delay_parse()
            p3 = (p1 | p2).parse_once()
            return Ast.BoolLiteralAst(p3.tok.token_type == TokenType.KwTrue, c1)
        return BoundParser(self, inner)

    def _parse_literal_regex(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxRegex).parse_once()
            return Ast.RegexLiteralAst(p1, c1)
        return BoundParser(self, inner)

    def _parse_literal_tuple(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_token(TokenType.TkParenL).parse_once()
            p2 = self._parse_expressions().parse_optional() or []
            p3 = self._parse_token(TokenType.TkParenR).parse_once()
            return Ast.TupleLiteralAst(p2, c1) if len(p2) != 1 else p2[0]
        return BoundParser(self, inner)

    def _parse_literal_number_base_02(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxBinDigits).parse_once()
            return Ast.NumberLiteralBase02Ast(p1, c1)
        return BoundParser(self, inner)

    def _parse_literal_number_base_10(self) -> BoundParser:
        def inner():
            p1 = self._parse_number().parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_literal_number_base_16(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_lexeme(TokenType.LxHexDigits).parse_once()
            return Ast.NumberLiteralBase16Ast(p1, c1)
        return BoundParser(self, inner)

    # Number

    def _parse_number(self) -> BoundParser:
        def inner():
            c1 = self._current_token_index()
            p1 = self._parse_numeric_sign().parse_optional()
            p2 = self._parse_numeric_integer().parse_once()
            p3 = self._parse_numeric_decimal().parse_optional()
            p4 = self._parse_numeric_complex().parse_optional()
            p5 = self._parse_numeric_exponent().parse_optional() is not None
            return Ast.NumberLiteralBase10Ast(p1, p2, p3, p4, p5, c1)
        return BoundParser(self, inner)

    def _parse_numeric_sign(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAdd).delay_parse()
            p2 = self._parse_token(TokenType.TkSub).delay_parse()
            p3 = (p1 | p2).parse_once()
            return p3
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
            c1 = self._current_token_index()
            p1 = self._parse_character('e').parse_once()
            p2 = self._parse_operator_identifier_additive().parse_optional()
            p3 = self._parse_numeric_integer().parse_once()
            return Ast.NumberExponentAst(p2, p3, c1)
        return BoundParser(self, inner)

    # Misc

    def _parse_token(self, token: TokenType) -> BoundParser:
        def inner():
            if token != TokenType.TkNewLine: self._skip(TokenType.TkNewLine)
            self._skip(TokenType.TkWhitespace)
            c1 = self._current_token_index()

            if self._current >= len(self._tokens):
                raise ParseSyntaxError(f"Expected '{token.value}', got <EOF>")

            global EXPECTED_TOKENS
            current_token = self._tokens[self._current]
            if current_token.token_type != token:
                got_token = current_token.token_type.value if not current_token.token_type.name.startswith("Lx") else current_token.token_type.name[2:]
                exp_token = token.value if not token.name.startswith("Lx") else token.name[2:]

                error = ParseSyntaxError(
                    f"{self._current} Expected one of ¬, got: '{got_token}'.")

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

            return Ast.TokenAst(self._tokens[self._current - 1], c1)
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
