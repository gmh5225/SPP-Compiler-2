from __future__ import annotations

import functools
from typing import Optional, Generic, TypeVar, Callable, Any
from src.Ast import *
from src.Tokens import TokenType, Token
import inspect

class ParseError(Exception):
    ...

Rules = list

PREV_ERROR = None


class ErrorFormatter:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def error(self, start_token_index: int) -> str:
        error_position = start_token_index
        error_length = len(self._tokens[error_position].token_metadata)

        while self._tokens[start_token_index].token_type != TokenType.TkNewLine and start_token_index > 0:
            start_token_index -= 1
        end_token_index = start_token_index + 1
        while self._tokens[end_token_index].token_type != TokenType.TkNewLine and end_token_index < len(self._tokens):
            end_token_index += 1

        tokens = self._tokens[start_token_index:end_token_index]
        current_line_string = "".join([token.token_metadata for token in tokens])

        spaces = 0
        for token in tokens:
            spaces += len(token.token_metadata)

        error_line_string = "".join([" " * spaces, "^" * error_length])
        final_string = "\n".join(["\n\n", current_line_string, error_line_string, ""])
        return final_string


class BoundParser:
    _ctor: Callable
    _rules: Rules
    _parser: Parser
    _delayed: bool
    _ast: Optional[Any]

    def __init__(self, constructor: Callable, parser: Parser, rules: Rules):
        self._ctor = constructor
        self._rules = rules
        self._parser = parser
        self._delayed = False
        self._ast = None

    def __ret_value(self):
        return self

    def parse_once(self):
        results = []
        for rule in self._rules:
            print(rule, [frame.function for frame in reversed(inspect.stack()) if not frame.function.startswith("parse")])
            results.append(rule())
        print("-" * 50)

        self._ast = self._ctor(*[result._ast for result in results])
        return self.__ret_value()

    def parse_optional(self):
        restore_index = self._parser._current
        try:
            self.parse_once()
            return self.__ret_value()
        except ParseError as e:
            global PREV_ERROR
            PREV_ERROR = e
            self._parser._current = restore_index
            self._ast = None
            return self.__ret_value()

    def parse_zero_or_more(self):
        results = []
        while True:
            restore_index = self._parser._current
            try:
                results.append(self.parse_once())
            except ParseError:
                self._parser._current = restore_index
                break
        self._ast = results
        return self.__ret_value()

    def parse_one_or_more(self):
        results = [self.parse_once()]
        while True:
            restore_index = self._parser._current
            try:
                results.append(self.parse_once())
            except ParseError:
                self._parser._current = restore_index
                break
        self._ast = results
        return self.__ret_value()

    def delay_parse(self) -> BoundParser:
        self._delayed = True
        return self

    def __or__(self, that: BoundParser) -> BoundParser:
        # Allow chaining n parsers, and one of them has to match
        # Try to parse each one. if one is valid, return it
        # if none are valid, raise an error
        assert self._delayed and that._delayed, "Both parsers must be delayed"

        def parse_one_of_inner():
            f = self.parse_optional()
            if f is None:
                f = that.parse_optional()
            if f is None:
                raise ParseError(f"No valid parser found for selection\n{PREV_ERROR}")
            return f

        b = BoundParser(self._ctor, self._parser, [parse_one_of_inner])
        b.delay_parse()
        return b

    def upgrade_ctor(self, new_ctor: type) -> BoundParser:
        return BoundParser(new_ctor, self._parser, self._rules)

class Parser:
    _tokens: list[Token]
    _current: int
    _indent: int
    _dedents_expected: int

    def WrapInSubParser(self):
        def wrapper(func):
            return BoundParser(lambda x: x, self, [func])
        return wrapper

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._current = 0
        self._indent = 0
        self._dedents_expected = 0

    def parse(self) -> ProgramAst:
        program = self._parse_root().parse_once()
        return program

    """MODULES"""
    def _parse_root(self) -> BoundParser:
        p1 = self._parse_program().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_program(self) -> BoundParser:
        p1 = self._parse_module_prototype().parse_once()
        p2 = self._parse_eof().parse_once()
        return BoundParser(ProgramAst, self, [p1, p2])

    def _parse_eof(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkEOF).parse_once()
        return BoundParser(TokenAst, self, [p1])

    def _parse_module_prototype(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwMod).parse_once()
        p3 = self._parse_module_identifier().parse_once()
        p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
        p5 = self._parse_module_implementation().parse_once()
        return BoundParser(ModulePrototypeAst, self, [p1, p2, p3, p4, p5])

    def _parse_module_implementation(self) -> BoundParser:
        p1 = self._parse_import_block().parse_optional()
        p2 = self._parse_module_member().parse_zero_or_more()
        return BoundParser(ModuleImplementationAst, self, [p1, p2])

    def _parse_module_identifier(self) -> BoundParser:
        def parse_next() -> BoundParser:
            p3 = self._parse_token(TokenType.TkDot).parse_once()
            p4 = self._parse_identifier().parse_once()
            return BoundParser(IdentifierAst, self, [p3, p4])

        p1 = self._parse_identifier().parse_once()
        p2 = parse_next().parse_zero_or_more()
        return BoundParser(ModuleIdentifierAst, self, [p1, p2])

    def _parse_module_member(self) -> BoundParser:
        p1 = self._parse_function_prototype().delay_parse()
        p2 = self._parse_enum_prototype().delay_parse()
        p3 = self._parse_class_prototype().delay_parse()
        p4 = self._parse_sup_prototype().delay_parse()
        p5 = (p1 | p2 | p3 | p4).parse_once()
        return BoundParser(ModuleMemberAst, self, [p5])

    """IMPORTS"""

    def _parse_import_block(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwUse).parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_indent().parse_once()
        p4 = self._parse_import_definition().parse_one_or_more()
        p5 = self._parse_dedent().parse_once()
        return BoundParser(ImportBlockAst, self, [p1, p2, p3, p4, p5])

    def _parse_import_definition(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDot).parse_zero_or_more()
        p2 = self._parse_module_identifier().parse_once()
        p3 = self._parse_token(TokenType.TkRightArrow).parse_once()
        p4 = self._parse_import_identifiers().parse_once()
        p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ImportDefinitionsAst, self, [p1, p2, p3, p4, p5])

    def _parse_import_identifiers(self) -> BoundParser:
        p1 = self._parse_import_all_types().delay_parse()
        p2 = self._parse_import_individual_types().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_import_all_types(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAsterisk).parse_once()
        return BoundParser(ImportTypesAllAst, self, [p1])

    def _parse_import_individual_types(self) -> BoundParser:
        def parse_next_import_identifier_raw():
            p3 = self._parse_token(TokenType.TkComma).parse_once(),
            p4 = self._parse_import_individual_type().parse_once(),
            return BoundParser(lambda ids: ids, self, [p3, p4])

        p1 = self._parse_import_individual_type().parse_once()
        p2 = parse_next_import_identifier_raw().parse_zero_or_more()
        return BoundParser(lambda x, y: ImportTypesIndividualAst([x] + y), self, [p1, p2])

    def _parse_import_individual_type(self) -> BoundParser:
        def parse_import_individual_type_alias():
            p3 = self._parse_token(TokenType.KwAs).parse_once()
            p4 = self._parse_identifier().parse_once()
            return BoundParser(lambda alias: alias, self, [p3, p4])

        p1 = self._parse_identifier().parse_once()
        p2 = parse_import_individual_type_alias().parse_optional()
        return BoundParser(ImportTypeAst, self, [p1, p2])

    """CLASSES"""

    def _parse_access_modifier(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwPub).delay_parse()
        p2 = self._parse_token(TokenType.KwPriv).delay_parse()
        p3 = self._parse_token(TokenType.KwProt).delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(AccessModifierAst, self, [p4])

    def _parse_class_prototype(self) -> BoundParser:
        p1 = self._parse_decorators().parse_optional()
        p2 = self._parse_token(TokenType.KwPart).parse_once()
        p3 = self._parse_access_modifier().parse_optional()
        p4 = self._parse_token(TokenType.KwCls).parse_once()
        p5 = self._parse_class_identifier().parse_once()
        p6 = self._parse_type_generic_parameters().parse_optional()
        p7 = self._parse_where_block().parse_optional()
        p8 = self._parse_class_or_empty_implementation().parse_once()
        return BoundParser(ClassPrototypeAst, self, [p1, p2, p3, p4, p5, p6, p7, p8])

    def _parse_class_or_empty_implementation(self) -> BoundParser:
        def parse_non_empty_prep():
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_indent().parse_once()
            p6 = self._parse_class_implementation().parse_once()
            p7 = self._parse_dedent().parse_once()
            return BoundParser(lambda impl: impl, self, [p4, p5, p6, p7])

        def parse_empty_prep():
            p4 = self._parse_empty_implementation()
            return BoundParser(lambda: ClassImplementationAst([]), self, [p4])

        p1 = parse_empty_prep().delay_parse()
        p2 = parse_non_empty_prep().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda impl: impl, self, [p3])

    def _parse_class_implementation(self) -> BoundParser:
        p1 = self._parse_class_member().parse_one_or_more()
        return BoundParser(ClassImplementationAst, self, [p1])

    def _parse_class_member(self) -> BoundParser:
        p1 = self._parse_class_attribute()
        p2 = self._parse_class_attribute_static()
        p3 = (p1 | p2).parse_once()
        return BoundParser(ClassAttributeAst, self, [p3])

    def _parse_class_attribute(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwMut).parse_optional()
        p3 = self._parse_class_attribute_identifier().parse_once()
        p4 = self._parse_token(TokenType.TkColon).parse_once()
        p5 = self._parse_type_identifier().parse_once()
        p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ClassInstanceAttributeAst, self, [p1, p2, p3, p4, p5, p6])

    def _parse_class_attribute_static(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwMut).parse_optional()
        p3 = self._parse_class_attribute_static_identifier().parse_once()
        p4 = self._parse_token(TokenType.TkEqual).parse_once()
        p5 = self._parse_expression().parse_once()
        p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ClassStaticAttributeAst, self, [p1, p2, p3, p4, p5, p6])

    def _parse_class_attribute_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    def _parse_class_attribute_static_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    def _parse_class_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    """SUPER-IMPOSITIONS"""

    def _parse_sup_prototype(self) -> BoundParser:
        def parse_sup_prototype_normal():
            p5 = self._parse_type_generic_parameters().parse_optional()
            p6 = self._parse_sup_identifier().parse_once()
            p7 = self._parse_where_block().parse_optional()
            p8 = self._parse_sup_or_empty_implementation().parse_once()
            return BoundParser(SupPrototypeNormalAst, self, [p5, p6, p7, p8])

        def parse_sup_prototype_with_inherit():
            p5 = self._parse_type_generic_parameters().parse_optional()
            p6 = self._parse_sup_identifier().parse_once()
            p7 = self._parse_token(TokenType.KwFor).parse_once()
            p8 = self._parse_sup_identifier().parse_once()
            p9 = self._parse_where_block().parse_optional()
            p10 = self._parse_sup_or_empty_implementation().parse_once()
            return BoundParser(SupPrototypeInheritanceAst, self, [p5, p6, p7, p8, p9, p10])

        p1 = self._parse_token(TokenType.KwSup).parse_once()
        p2 = parse_sup_prototype_normal().delay_parse()
        p3 = parse_sup_prototype_with_inherit().delay_parse()
        p4 = (p2 | p3).parse_once()
        return BoundParser(lambda sup: sup, self, [p1, p4])

    def _parse_sup_or_empty_implementation(self) -> BoundParser:
        def parse_non_empty_prep():
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_indent().parse_once()
            p6 = self._parse_sup_implementation().parse_once()
            p7 = self._parse_dedent().parse_once()
            return BoundParser(lambda impl: impl, self, [p4, p5, p6, p7])

        def parse_empty_prep():
            p4 = self._parse_empty_implementation()
            return BoundParser(lambda: SupImplementationAst([]), self, [p4])

        p1 = parse_empty_prep().delay_parse()
        p2 = parse_non_empty_prep().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda impl: impl, self, [p3])

    def _parse_sup_implementation(self) -> BoundParser:
        p1 = self._parse_sup_member().parse_one_or_more()
        return BoundParser(SupImplementationAst, self, [p1])

    def _parse_sup_member(self) -> BoundParser:
        p1 = self._parse_sup_method().delay_parse()
        p2 = self._parse_sup_typedef().delay_parse()
        p3 = (p1 | p2).upgrade_ctor(SupMemberAst).parse_once()
        return BoundParser(SupMemberAst, self, [p3])

    def _parse_sup_identifier(self) -> BoundParser:
        p1 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    def _parse_sup_typedef(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_statement_typedef().parse_once()
        return BoundParser(SupTypedefAst, self, [p1, p2])

    def _parse_sup_method(self) -> BoundParser:
        p1 = self._parse_function_prototype().parse_once()
        return BoundParser(SupMethodPrototypeAst, self, [p1])

    """ENUMS"""

    def _parse_enum_prototype(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwEnum).parse_once()
        p3 = self._parse_enum_identifier().parse_once()
        p4 = self._parse_enum_or_empty_implementation().parse_once()
        return BoundParser(EnumPrototypeAst, self, [p1, p2, p3, p4])

    def _parse_enum_or_empty_implementation(self) -> BoundParser:
        def parse_non_empty_prep():
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_indent().parse_once()
            p6 = self._parse_enum_implementation().parse_once()
            p7 = self._parse_dedent().parse_once()
            return BoundParser(lambda impl: impl, self, [p4, p5, p6, p7])

        def parse_empty_prep():
            p4 = self._parse_empty_implementation()
            return BoundParser(lambda: EnumImplementationAst([]), self, [p4])

        p1 = parse_empty_prep().delay_parse()
        p2 = parse_non_empty_prep().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda impl: impl, self, [p3])

    def _parse_enum_implementation(self) -> BoundParser:
        def parse_next_enum_member():
            p4 = self._parse_token(TokenType.TkComma).parse_once()
            p5 = self._parse_enum_member().parse_once()
            return BoundParser(EnumMemberAst, self, [p4, p5])

        p1 = self._parse_enum_member().parse_once()
        p2 = parse_next_enum_member().parse_zero_or_more()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(EnumImplementationAst, self, [p1, p2, p3])

    def _parse_enum_member(self) -> BoundParser:
        def parse_enum_member_value():
            p3 = self._parse_token(TokenType.TkEqual).parse_once()
            p4 = self._parse_enum_member_value().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_enum_member_identifier().parse_once()
        p2 = parse_enum_member_value().parse_optional()
        return BoundParser(EnumMemberAst, self, [p1, p2])

    def _parse_enum_member_value(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_enum_member_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_enum_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """FUNCTION"""

    def _parse_function_prototype(self) -> BoundParser:
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
        return BoundParser(FunctionPrototypeAst, self, [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12])

    def _parse_function_or_empty_implementation(self) -> BoundParser:
        def parse_non_empty_prep():
            p4 = self._parse_token(TokenType.TkColon).parse_once()
            p5 = self._parse_indent().parse_once()
            p6 = self._parse_function_implementation().parse_once()
            p7 = self._parse_dedent().parse_once()
            return BoundParser(lambda impl: impl, self, [p4, p5, p6, p7])

        def parse_empty_prep():
            p4 = self._parse_empty_implementation()
            return BoundParser(lambda: FunctionImplementationAst([]), self, [p4])

        p1 = parse_empty_prep().delay_parse()
        p2 = parse_non_empty_prep().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda impl: impl, self, [p3])

    def _parse_function_implementation(self) -> BoundParser:
        p1 = self._parse_statement().parse_one_or_more()
        return BoundParser(FunctionImplementationAst, self, [p1])

    def _parse_function_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_function_call_arguments(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_function_call_arguments_normal_then_named().parse_optional()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_function_call_arguments_normal_then_named(self) -> BoundParser:
        p1 = self._parse_function_call_next_normal_arguments().delay_parse()
        p2 = self._parse_function_call_next_named_arguments().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_function_call_next_normal_arguments(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_arguments_normal_then_named().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_call_argument_normal().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_function_call_next_named_arguments(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_argument_named().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_call_argument_named().parse_once()
        p4 = parse_following().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_function_call_argument_normal(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        return BoundParser(FunctionArgumentNormalAst, self, [p1])

    def _parse_function_call_argument_named(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(FunctionArgumentNamedAst, self, [p1, p2, p3])

    def _parse_function_parameters(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_function_parameters_required_then_optional().parse_optional()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_function_parameters_required_then_optional(self) -> BoundParser:
        p1 = self._parse_function_parameters_required_and_following().delay_parse()
        p2 = self._parse_function_parameters_optional_and_following().delay_parse()
        p3 = self._parse_function_parameters_variadic_and_following().delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    def _parse_function_parameters_optional_then_variadic(self) -> BoundParser:
        p1 = self._parse_function_parameters_optional_and_following().delay_parse()
        p2 = self._parse_function_parameters_variadic_and_following().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_function_parameters_required_and_following(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameters_required_then_optional().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_parameter_required().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_function_parameters_optional_and_following(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameters_optional_then_variadic().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_parameter_optional().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_function_parameters_variadic_and_following(self) -> BoundParser:
        p1 = self._parse_function_parameter_variadic().parse_once()
        return BoundParser(lambda x: [x], self, [p1])

    def _parse_function_parameter_required(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMut).parse_optional()
        p2 = self._parse_function_parameter_identifier().parse_once()
        p3 = self._parse_token(TokenType.TkColon).parse_once()
        p4 = self._parse_type_identifier().parse_once()
        return BoundParser(FunctionParameterRequiredAst, self, [p1, p2, p3, p4])

    def _parse_function_parameter_optional(self) -> BoundParser:
        p1 = self._parse_function_parameter_required().parse_once()
        p2 = self._parse_token(TokenType.TkEqual).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(FunctionParameterOptionalAst, self, [p1, p2, p3])

    def _parse_function_parameter_variadic(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
        p2 = self._parse_function_parameter_required().parse_once()
        return BoundParser(FunctionParameterVariadicAst, self, [p1, p2])

    def _parse_function_parameter_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """[TYPE & VALUE GUARD]"""

    def _parse_where_block(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwWhere).parse_once()
        p2 = self._parse_token(TokenType.TkLeftBracket).parse_once()
        p3 = self._parse_where_constraints().parse_optional()
        p4 = self._parse_token(TokenType.TkRightBracket).parse_once()
        return BoundParser(WhereBlockAst, self, [p1, p2, p3, p4])

    def _parse_where_constraints(self) -> BoundParser:
        def parse_next_where_constraint() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_where_constraint().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_where_constraint().parse_once()
        p2 = parse_next_where_constraint().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_where_constraint(self) -> BoundParser:
        p1 = self._parse_type_identifiers().parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_where_constraint_chain().parse_once()
        return BoundParser(WhereConstraintAst, self, [p1, p2, p3])

    def _parse_where_constraint_chain(self) -> BoundParser:
        def parse_next_where_constraint_chain_item() -> BoundParser:
            p1 = self._parse_token(TokenType.TkPlus).parse_once()
            p2 = self._parse_where_constraint_chain_element().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_where_constraint_chain_element().parse_once()
        p4 = parse_next_where_constraint_chain_item().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_where_constraint_chain_element(self) -> BoundParser:
        p1 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_value_guard(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwIf).parse_once()
        p2 = self._parse_expression().parse_once()
        return BoundParser(ValueGuardAst, self, [p1, p2])

    """[DECORATORS]"""

    def _parse_decorator(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAt).parse_once()
        p2 = self._parse_decorator_identifier().parse_once()
        p3 = self._parse_type_generic_arguments().parse_optional()
        p4 = self._parse_function_call_arguments().parse_optional()
        return BoundParser(DecoratorAst, self, [p1, p2, p3, p4])

    def _parse_decorators(self) -> BoundParser:
        def parse_next_decorator():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_decorator().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_decorator().parse_once()
        p2 = parse_next_decorator().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_decorator_identifier(self) -> BoundParser:
        p1 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """[EXPRESSIONS]"""
    def _parse_expressions(self) -> BoundParser:
        def parse_next_expression():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_expression().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_expression().parse_once()
        p2 = parse_next_expression().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_expression(self) -> BoundParser:
        p1 = self._parse_assignment_expression().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_assignment_expression(self) -> BoundParser:
        def parse_multi_assignment() -> BoundParser:
            def parse_multi_lhs() -> BoundParser:
                p9 = self._parse_token(TokenType.TkComma).parse_once()
                p10 = self._parse_null_coalescing_expression().parse_once()
                return BoundParser(lambda x: x, self, [p9, p10])

            def parse_multi_rhs() -> BoundParser:
                p9 = self._parse_token(TokenType.TkComma).parse_once()
                p10 = self._parse_assignment_expression().parse_once()
                return BoundParser(lambda x: x, self, [p9, p10])

            p4 = self._parse_null_coalescing_expression().parse_once()
            p5 = parse_multi_lhs().parse_zero_or_more()
            p6 = self._parse_token(TokenType.TkEqual).parse_once()
            p7 = self._parse_assignment_expression().parse_once()
            p8 = parse_multi_rhs().parse_zero_or_more()
            return BoundParser(
                lambda x, xx, y, yy: MultiAssignmentExpressionAst([x] + xx, [y] + yy), self,
                [p4, p5, p6, p7, p8])

        def parse_single_assignment() -> BoundParser:
            def parse_rhs() -> BoundParser:
                p6 = self._parse_token(TokenType.TkEqual).parse_once()
                p7 = self._parse_assignment_expression().parse_once()
                return BoundParser(lambda x, y: (x, y), self, [p6, p7])

            p4 = self._parse_null_coalescing_expression().parse_once()
            p5 = parse_rhs().parse_optional()
            return BoundParser(
                lambda lhs, op, rhs: lhs if not rhs else BinaryExpressionAst(lhs, op, rhs), self,
                [p4, p5])

        p1 = parse_multi_assignment().parse_once()
        p2 = parse_single_assignment().parse_once()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_null_coalescing_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_or_expression(),
            self._parse_operator_identifier_null_coalescing(),
            self._parse_null_coalescing_expression())

    def _parse_logical_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_and_expression(),
            self._parse_token(TokenType.TkDoubleVerticalBar).parse_once(),
            self._parse_logical_or_expression())

    def _parse_logical_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_or_expression(),
            self._parse_token(TokenType.TkDoubleAmpersand).parse_once(),
            self._parse_logical_and_expression())

    def _parse_bitwise_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_xor_expression(),
            self._parse_token(TokenType.TkVerticalBar).parse_once(),
            self._parse_bitwise_or_expression())

    def _parse_bitwise_xor_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_and_expression(),
            self._parse_token(TokenType.TkCaret).parse_once(),
            self._parse_bitwise_xor_expression())

    def _parse_bitwise_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_equality_expression(),
            self._parse_token(TokenType.TkAmpersand).parse_once(),
            self._parse_bitwise_and_expression())

    def _parse_equality_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_relational_expression(),
            self._parse_operator_identifier_equality(),
            self._parse_equality_expression())

    def _parse_relational_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_shift_expression(),
            self._parse_operator_identifier_relation(),
            self._parse_relational_expression())

    def _parse_shift_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_rotate_expression(),
            self._parse_operator_identifier_shift(),
            self._parse_shift_expression())

    def _parse_rotate_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_additive_expression(),
            self._parse_operator_identifier_rotate(),
            self._parse_rotate_expression())

    def _parse_additive_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_multiplicative_expression(),
            self._parse_operator_identifier_additive(),
            self._parse_additive_expression())

    def _parse_multiplicative_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_power_expression(),
            self._parse_operator_identifier_multiplicative(),
            self._parse_multiplicative_expression())

    def _parse_power_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_pipe_expression(),
            self._parse_token(TokenType.TkDoubleAstrix).parse_once(),
            self._parse_power_expression())

    def _parse_pipe_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_unary_expression(),
            self._parse_token(TokenType.TkPipe).parse_once(),
            self._parse_pipe_expression())

    def _parse_unary_expression(self) -> BoundParser:
        def parse_unary() -> BoundParser:
            p4 = self._parse_operator_identifier_unary().parse_once()
            p5 = self._parse_unary_expression().parse_once()
            return BoundParser(lambda x, y: UnaryExpressionAst(x, y), self, [p4, p5])

        p1 = parse_unary()
        p2 = self._parse_postfix_expression()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_postfix_expression(self) -> BoundParser:
        def parse_postfix() -> BoundParser:
            p4 = self._parse_postfix_expression().parse_once()
            p5 = self._parse_operator_identifier_postfix().parse_once()
            return BoundParser(lambda x, y: PostfixExpressionAst(x, y), self, [p4, p5])

        p1 = parse_postfix()
        p2 = self._parse_primary_expression().parse_once()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_primary_expression(self) -> BoundParser:
        p1 = self._parse_lambda()
        p2 = self._parse_literal()
        p3 = self._parse_static_scoped_generic_identifier()
        p4 = self._parse_parenthesized_expression()
        p5 = self._parse_expression_placeholder()
        p6 = (p1 | p2 | p3 | p4 | p5).parse_once()
        return BoundParser(lambda x: x, self, [p6])

    def _parse_binary_expression(self, _lhs, _op, _rhs) -> BoundParser:
        def parse_rhs() -> BoundParser:
            p3 = _op.parse_once()
            p4 = _rhs.parse_once()
            return BoundParser(lambda x, y: (x, y), self, [p3, p4])

        p1 = _lhs.parse_once()
        p2 = parse_rhs().parse_optional()
        return BoundParser(lambda lhs, op, rhs: lhs if not rhs else BinaryExpressionAst(lhs, op, rhs), self, [p1, p2])

    def _parse_parenthesized_expression(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_expression_placeholder(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkUnderscore).parse_once()
        return BoundParser(PlaceholderAst, self, [p1])

    """[LAMBDA]"""

    def _parse_lambda(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwAsync).parse_optional()
        p2 = self._parse_lambda_capture_list().parse_optional()
        p3 = self._parse_lambda_parameters().parse_once()
        p4 = self._parse_token(TokenType.TkRightArrow).parse_once()
        p5 = self._parse_lambda_implementation().parse_once()
        return BoundParser(LambdaAst, self, [p1, p2, p3, p4, p5])

    def _parse_lambda_capture_list(self) -> BoundParser:
        def parse_next_capture_item() -> BoundParser:
            p5 = self._parse_token(TokenType.TkComma).parse_once()
            p6 = self._parse_lambda_capture_item().parse_once()
            return BoundParser(lambda x, y: y, self, [p5, p6])

        p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
        p2 = self._parse_lambda_capture_item().parse_optional()
        p3 = parse_next_capture_item().parse_zero_or_more()
        p4 = self._parse_token(TokenType.TkRightBracket).parse_once()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2, p3, p4])

    def _parse_lambda_capture_item(self) -> BoundParser:
        def parse_alias() -> BoundParser:
            p3 = self._parse_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkEqual).parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = parse_alias().parse_optional()
        p2 = self._parse_expression().parse_once()
        return BoundParser(LambdaCaptureItemAst, self, [p1, p2])

    def _parse_lambda_parameters(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_lambda_parameters_required().parse_once()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_lambda_parameters_required(self) -> BoundParser:
        def parse_next_parameter() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_lambda_parameter_required().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_lambda_parameter_required().parse_once()
        p2 = parse_next_parameter().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_lambda_parameter_required(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMut).parse_optional()
        p2 = self._parse_function_parameter_identifier().parse_once()
        return BoundParser(LambdaParameterAst, self, [p1, p2])

    def _parse_lambda_implementation(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """[TYPES]"""

    def _parse_type_identifier(self) -> BoundParser:
        p1 = self._parse_unary_operator_reference().parse_optional()
        p2 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(TypeAst, self, [p1, p2])

    def _parse_type_identifiers(self) -> BoundParser:
        def parse_next_type_identifier() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_type_identifier().parse_once()
        p2 = parse_next_type_identifier().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_type_generic_arguments(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftAngleBracket).parse_once()
        p2 = self._parse_type_generic_arguments_normal_then_named().parse_optional()
        p3 = self._parse_token(TokenType.TkRightAngleBracket).parse_once()
        return BoundParser(TypeGenericArgumentAst, self, [p1, p2, p3])

    def _parse_type_generic_arguments_normal_then_named(self) -> BoundParser:
        p1 = self._parse_type_generic_arguments_next_normal().delay_parse()
        p2 = self._parse_type_generic_arguments_next_named().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_type_generic_arguments_next_normal(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_generic_arguments_normal_then_named().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_type_generic_argument_normal().parse_once()
        p2 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_type_generic_arguments_next_named(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_generic_argument_named().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_type_generic_argument_named().parse_once()
        p2 = parse_following().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_type_generic_argument_normal(self) -> BoundParser:
        p1 = self._parse_type_identifier().parse_once()
        return BoundParser(TypeGenericArgumentNormalAst, self, [p1])

    def _parse_type_generic_argument_named(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        p2 = self._parse_token(TokenType.TkEqual).parse_once()
        p3 = self._parse_type_identifier().parse_once()
        return BoundParser(TypeGenericArgumentNamedAst, self, [p1, p2, p3])

    def _parse_type_generic_parameters(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_type_generic_parameters_required_then_optional().parse_optional()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_type_generic_parameters_required_then_optional(self) -> BoundParser:
        p1 = self._parse_type_generic_parameters_required_and_following().delay_parse()
        p2 = self._parse_type_generic_parameters_optional_and_following().delay_parse()
        p3 = self._parse_type_generic_parameters_variadic_and_following().delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    def _parse_type_generic_parameters_optional_then_variadic(self) -> BoundParser:
        p1 = self._parse_type_generic_parameters_optional_and_following().delay_parse()
        p2 = self._parse_type_generic_parameters_variadic_and_following().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_type_generic_parameters_required_and_following(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_type_generic_parameter_required().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_type_generic_parameters_optional_and_following(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameters_optional_then_variadic().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_type_generic_parameter_optional().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    def _parse_type_generic_parameters_variadic_and_following(self) -> BoundParser:
        p1 = self._parse_type_generic_parameter_variadic().parse_once()
        return BoundParser(lambda x: [x], self, [p1])

    def _parse_type_generic_parameter_required(self) -> BoundParser:
        def parse_inline_constraint() -> BoundParser:
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_where_constraint_chain().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_identifier().parse_once()
        p2 = parse_inline_constraint().parse_optional()
        return BoundParser(TypeGenericParameterRequiredAst, self, [p1, p2])

    def _parse_type_generic_parameter_optional(self) -> BoundParser:
        p1 = self._parse_type_generic_parameter_required().parse_once()
        p2 = self._parse_token(TokenType.TkEqual).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(TypeGenericParameterOptionalAst, self, [p1, p2, p3])

    def _parse_type_generic_parameter_variadic(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
        p2 = self._parse_type_generic_parameter_required().parse_once()
        return BoundParser(TypeGenericParameterVariadicAst, self, [p1, p2])

    """[STATEMENTS]"""
    def _parse_statement_inline_definitions(self) -> BoundParser:
        p5 = self._parse_statement_let().parse_once()
        p6 = self._parse_token(TokenType.TkComma).parse_once()
        return BoundParser(lambda x: x, self, [p5, p6])

    def _parse_statement_if(self) -> BoundParser:
        p1 = self._parse_statement_if_branch().parse_once()
        p5 = self._parse_statement_elif_branch().parse_zero_or_more()
        p6 = self._parse_statement_else_branch().parse_optional()
        return BoundParser(IfStatementAst, self, [p1, p5, p6])

    def _parse_statement_if_branch(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwIf).parse_once()
        p2 = self._parse_statement_inline_definitions().parse_zero_or_more()
        p3 = self._parse_expression().parse_once()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(IfStatementBranchAst, self, [p1, p2, p3, p4])

    def _parse_statement_elif_branch(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwElif).parse_once()
        p2 = self._parse_statement_inline_definitions().parse_zero_or_more()
        p3 = self._parse_expression().parse_once()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(IfStatementBranchAst, self, [p1, p2, p3, p4])

    def _parse_statement_else_branch(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwElse).parse_once()
        p2 = self._parse_statement_block().parse_once()
        return BoundParser(ElseStatementBranchAst, self, [p1, p2])

    def _parse_statement_while(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwWhile).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_statement_block().parse_once()
        return BoundParser(WhileStatementAst, self, [p1, p2, p3])

    def _parse_statement_for(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwFor).parse_once()
        p2 = self._parse_local_variable_identifiers().parse_once()
        p3 = self._parse_token(TokenType.KwIn).parse_once()
        p4 = self._parse_expression().parse_once()
        p5 = self._parse_statement_block().parse_once()
        return BoundParser(ForStatementAst, self, [p1, p2, p3, p4, p5])

    def _parse_statement_do(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwDo).parse_once()
        p2 = self._parse_statement_block().parse_once()
        p3 = self._parse_token(TokenType.KwWhile).parse_once()
        p4 = self._parse_expression().parse_once()
        return BoundParser(DoWhileStatementAst, self, [p1, p2, p3, p4])

    def _parse_statement_match(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMatch).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_statement_cases().parse_once()
        return BoundParser(MatchStatementAst, self, [p1, p2, p3])

    def _parse_statement_case(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwCase).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_value_guard().parse_optional()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(CaseStatementAst, self, [p1, p2, p3, p4])

    def _parse_statement_case_default(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwCase).parse_once()
        p2 = self._parse_expression_placeholder().parse_once()
        p3 = self._parse_value_guard().parse_optional()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(CaseStatementAst, self, [p1, p2, p3, p4])

    def _parse_statement_with(self) -> BoundParser:
        def parse_alias() -> BoundParser:
            p5 = self._parse_token(TokenType.KwAs).parse_once()
            p6 = self._parse_local_variable_identifier().parse_once()
            return BoundParser(lambda x: x, self, [p5, p6])

        p1 = self._parse_token(TokenType.KwWith).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = parse_alias().parse_optional()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(WithStatementAst, self, [p1, p2, p3, p4])

    def _parse_statement_return(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwReturn).parse_once()
        p2 = self._parse_expression().parse_optional()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ReturnStatementAst, self, [p1, p2, p3])

    def _parse_statement_yield(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwYield).parse_once()
        p2 = self._parse_expression().parse_optional()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(YieldStatementAst, self, [p1, p2, p3])

    def _parse_statement_typedef(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwUse).parse_once()
        p2 = self._parse_generic_identifier().parse_once()
        p3 = self._parse_token(TokenType.KwAs).parse_once()
        p4 = self._parse_type_identifier().parse_once()
        p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(TypedefStatementAst, self, [p1, p2, p3, p4, p5])

    def _parse_statement_break(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwBreak).parse_once()
        p2 = self._parse_statement_loop_tag().parse_optional()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(BreakStatementAst, self, [p1, p2, p3])

    def _parse_statement_continue(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwContinue).parse_once()
        p2 = self._parse_statement_loop_tag().parse_optional()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ContinueStatementAst, self, [p1, p2, p3])

    def _parse_statement_loop_tag(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwAs).parse_once()
        p2 = self._parse_tag_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1, p2])

    def _parse_tag_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_statement_block(self) -> BoundParser:
        def parse_multiline_block() -> BoundParser:
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_indent().parse_once()
            p7 = self._parse_statement().parse_one_or_more()
            p8 = self._parse_dedent().parse_once()
            return BoundParser(lambda x: x, self, [p5, p6, p7, p8])

        def parse_singleline_block() -> BoundParser:
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_statement().parse_once()
            return BoundParser(lambda x: x, self, [p5, p6])

        def parse_empty_block() -> BoundParser:
            p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
            return BoundParser(lambda x: x, self, [p5])

        p1 = parse_multiline_block()
        p2 = parse_singleline_block()
        p3 = parse_empty_block()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    def _parse_statement_cases(self) -> BoundParser:
        def parse_cases_force_default() -> BoundParser:
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_indent().parse_once()
            p7 = self._parse_statement_case().parse_zero_or_more()
            p8 = self._parse_statement_case_default().parse_one_or_more()
            p9 = self._parse_dedent().parse_once()
            return BoundParser(lambda x, y: x + y, self, [p5, p6, p7, p8, p9])

        def parse_cases_force_exhaustion() -> BoundParser:
            p5 = self._parse_token(TokenType.TkColon).parse_once()
            p6 = self._parse_indent().parse_once()
            p7 = self._parse_statement_case().parse_one_or_more()
            p8 = self._parse_statement_case_default().parse_zero_or_more()
            p9 = self._parse_dedent().parse_once()
            return BoundParser(lambda x, y: x + y, self, [p5, p6, p7, p8, p9])

        def parse_cases_empty_set() -> BoundParser:
            p5 = self._parse_empty_implementation()
            return BoundParser(lambda: [], self, [p5])

        p1 = parse_cases_force_default()
        p2 = parse_cases_force_exhaustion()
        p3 = parse_cases_empty_set()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    def _parse_statement_let(self) -> BoundParser:
        def parse_value() -> BoundParser:
            p6 = self._parse_token(TokenType.TkEqual).parse_once()
            p7 = self._parse_expressions().parse_once()
            return BoundParser(lambda x: x, self, [p6, p7])

        def parse_type_annotation() -> BoundParser:
            p6 = self._parse_token(TokenType.TkColon).parse_once()
            p7 = self._parse_type_identifier().parse_once()
            return BoundParser(lambda x: x, self, [p6, p7])

        p1 = self._parse_token(TokenType.KwLet).parse_once()
        p2 = self._parse_local_variable_identifier().parse_once()
        p3 = parse_type_annotation().parse_optional()
        p4 = parse_value().parse_optional()
        p5 = (p3 | p4).parse_once()
        return BoundParser(LetStatementAst, self, [p1, p2, p5])

    def _parse_local_variable_identifier(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMut).parse_once()
        p2 = self._parse_identifier().parse_once()
        return BoundParser(LocalVariableAst, self, [p1, p2])

    def _parse_local_variable_identifiers(self) -> BoundParser:
        def parse_next() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_local_variable_identifier().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_local_variable_identifier().parse_once()
        p2 = parse_next().parse_zero_or_more()
        return BoundParser(lambda x, y: x + y, self, [p1, p2])

    def _parse_statement_expression(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        p2 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2])

    def _parse_statement(self) -> BoundParser:
        p1 = self._parse_statement_if()
        p2 = self._parse_statement_while()
        p3 = self._parse_statement_for()
        p4 = self._parse_statement_do()
        p5 = self._parse_statement_match()
        p6 = self._parse_statement_with()
        p7 = self._parse_statement_typedef()
        p8 = self._parse_statement_return()
        p9 = self._parse_statement_yield()
        p10 = self._parse_statement_break()
        p11 = self._parse_statement_continue()
        p12 = self._parse_statement_let()
        p13 = self._parse_statement_expression()
        p14 = self._parse_function_prototype()
        p15 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11 | p12 | p13 | p14).upgrade_ctor(StatementAst).parse_once()
        return BoundParser(lambda x: x, self, [p15])

    """[IDENTIFIERS]"""

    def _parse_identifier(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
        return BoundParser(lambda x: IdentifierAst(x), self, [p1])

    def _parse_generic_identifier(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxIdentifier).parse_once()
        p2 = self._parse_type_generic_arguments().parse_optional()
        return BoundParser(lambda x, y: GenericIdentifierAst(x, y), self, [p1, p2])

    def _parse_static_scoped_generic_identifier(self) -> BoundParser:
        def parse_next() -> BoundParser:
            p3 = self._parse_token(TokenType.TkDoubleColon).parse_once()
            p4 = self._parse_generic_identifier().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_generic_identifier().parse_once()
        p2 = parse_next().parse_zero_or_more()
        return BoundParser(lambda x, y: ScopedGenericIdentifierAst([x] + y), self, [p1, p2])


    """[POSTFIX OPERATIONS]"""
    def _parse_postfix_operator_function_call(self) -> BoundParser:
        p1 = self._parse_function_call_arguments().parse_once()
        p2 = self._parse_operator_identifier_variadic().parse_optional()
        return BoundParser(lambda x, y: PostfixFunctionCallAst(x, y is not None), self, [p1, p2])

    def _parse_postfix_operator_member_access(self) -> BoundParser:
        p1 = self._parse_operator_identifier_member_access().parse_once()
        p2 = self._parse_generic_identifier().parse_once()
        return BoundParser(PostfixMemberAccessAst, self, [p1, p2])

    def _parse_postfix_operator_index_access(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_token(TokenType.TkRightBracket).parse_once()
        return BoundParser(PostfixIndexAccessAst, self, [p1, p2, p3])

    def _parse_postfix_operator_slice_access(self) -> BoundParser:
        def parse_step() -> BoundParser:
            p7 = self._parse_token(TokenType.TkComma).parse_once()
            p8 = self._parse_expression().parse_optional()
            return BoundParser(lambda x: x, self, [p7, p8])

        p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
        p2 = self._parse_expression().parse_optional()
        p3 = self._parse_token(TokenType.TkDoubleDot).parse_once()
        p4 = self._parse_expression().parse_optional()
        p5 = parse_step().parse_optional()
        p6 = self._parse_token(TokenType.TkRightBracket).parse_once()
        return BoundParser(PostfixSliceAccessAst, self, [p1, p2, p3, p4, p5, p6])

    def _parse_postfix_operator_struct_initializer(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
        p2 = self._parse_postfix_operator_struct_initializer_fields().parse_optional()
        p3 = self._parse_token(TokenType.TkRightBrace).parse_once()
        return BoundParser(PostfixStructInitializerAst, self, [p1, p2, p3])

    def _parse_postfix_operator_struct_initializer_fields(self) -> BoundParser:
        def parse_next() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_postfix_operator_struct_initializer_field().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_postfix_operator_struct_initializer_field().parse_once()
        p2 = parse_next().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    def _parse_postfix_operator_struct_initializer_field(self) -> BoundParser:
        def parse_field_value_different_to_identifier():
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_expression().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_postfix_operator_struct_initializer_field_identifier().parse_once()
        p2 = parse_field_value_different_to_identifier().parse_optional()
        return BoundParser(PostfixStructInitializerFieldAst, self, [p1, p2])

    def _parse_postfix_operator_struct_initializer_field_identifier(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwSup).delay_parse()
        p2 = self._parse_identifier().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_postfix_operator_type_cast(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwAs).parse_once()
        p2 = self._parse_type_identifier().parse_once()
        return BoundParser(PostfixTypeCastAst, self, [p1, p2])

    """[OPERATOR IDENTIFIERS]"""

    def _parse_operator_identifier_assignment(self) -> BoundParser:
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
        return BoundParser(lambda x: x, self, [p17])

    def _parse_operator_identifier_null_coalescing(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDoubleQuestionMark).delay_parse()
        p2 = self._parse_token(TokenType.TkQuestionMarkColon).delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_operator_identifier_equality(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDoubleEqual).delay_parse()
        p2 = self._parse_token(TokenType.TkExclamationEqual).delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_operator_identifier_relation(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftAngleBracket).delay_parse()
        p2 = self._parse_token(TokenType.TkRightAngleBracket).delay_parse()
        p3 = self._parse_token(TokenType.TkLeftAngleBracketEquals).delay_parse()
        p4 = self._parse_token(TokenType.TkRightAngleBracketEquals).delay_parse()
        p5 = self._parse_token(TokenType.TkDoubleFatArrow).delay_parse()
        p6 = (p1 | p2 | p3 | p4 | p5).parse_once()
        return BoundParser(lambda x: x, self, [p6])

    def _parse_operator_identifier_shift(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDoubleLeftAngleBracket).delay_parse()
        p2 = self._parse_token(TokenType.TkDoubleRightAngleBracket).delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_operator_identifier_rotate(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkTripleLeftAngleBracket).delay_parse()
        p2 = self._parse_token(TokenType.TkTripleRightAngleBracket).delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_operator_identifier_additive(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkPlus).delay_parse()
        p2 = self._parse_token(TokenType.TkHyphen).delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_operator_identifier_multiplicative(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAsterisk).delay_parse()
        p2 = self._parse_token(TokenType.TkForwardSlash).delay_parse()
        p3 = self._parse_token(TokenType.TkDoubleForwardSlash).delay_parse()
        p4 = self._parse_token(TokenType.TkPercent).delay_parse()
        p5 = (p1 | p2 | p3 | p4).parse_once()
        return BoundParser(lambda x: x, self, [p5])

    def _parse_operator_identifier_unary(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkPlus).delay_parse()
        p2 = self._parse_token(TokenType.TkHyphen).delay_parse()
        p3 = self._parse_token(TokenType.TkTilde).delay_parse()
        p4 = self._parse_token(TokenType.TkExclamation).delay_parse()
        p5 = self._parse_unary_operator_reference().delay_parse()
        p6 = self._parse_operator_identifier_variadic().delay_parse()
        p7 = self._parse_token(TokenType.KwAwait).delay_parse()
        p8 = (p1 | p2 | p3 | p4 | p5 | p6 | p7).parse_once()
        return BoundParser(lambda x: x, self, [p8])

    def _parse_unary_operator_reference(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAmpersand).parse_once()
        p2 = self._parse_token(TokenType.KwMut).parse_once()
        return BoundParser(lambda x, y: TokenAst(x.primary, y.primary), self, [p1, p2])

    def _parse_operator_identifier_variadic(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_operator_identifier_member_access(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDot).parse_once()
        return BoundParser(lambda x: x, self, [p1])

    def _parse_operator_identifier_postfix(self) -> BoundParser:
        p1 = self._parse_postfix_operator_function_call().delay_parse()
        p2 = self._parse_postfix_operator_member_access().delay_parse()
        p3 = self._parse_postfix_operator_index_access().delay_parse()
        p4 = self._parse_postfix_operator_slice_access().delay_parse()
        p5 = self._parse_postfix_operator_struct_initializer().delay_parse()
        p6 = self._parse_postfix_operator_type_cast().delay_parse()
        p7 = self._parse_token(TokenType.TkQuestionMark).delay_parse()
        p8 = (p1 | p2 | p3 | p4 | p5 | p6 | p7).parse_once()
        return BoundParser(lambda x: x, self, [p8])

    """[LITERALS]"""

    def _parse_literal(self) -> BoundParser:
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
        p11 = self._parse_literal_generator().delay_parse()
        p12 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11).parse_once()
        return BoundParser(lambda x: x, self, [p12])

    def _parse_literal_number(self) -> BoundParser:
        p1 = self._parse_literal_number_base_02().delay_parse()
        p2 = self._parse_literal_number_base_16().delay_parse()
        p3 = self._parse_literal_number_base_10().delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    def _parse_literal_string(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxDoubleQuoteStr)
        return BoundParser(lambda x: x, self, [p1])

    def _parse_literal_char(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxSingleQuoteChr)
        return BoundParser(lambda x: x, self, [p1])

    def _parse_literal_boolean(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwTrue).delay_parse()
        p2 = self._parse_token(TokenType.KwFalse).delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    def _parse_literal_list(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
        p2 = self._parse_build_container_from_range().delay_parse()
        p3 = self._parse_build_container_from_expressions().delay_parse()
        p4 = self._parse_build_container_from_comprehension().delay_parse()
        p5 = (p2 | p3 | p4).parse_once()
        p6 = self._parse_token(TokenType.TkRightBracket).parse_once()
        return BoundParser(ListLiteralAst, self, [p1, p5, p6])

    def _parse_literal_generator(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_build_container_from_range().delay_parse()
        p3 = self._parse_build_container_from_comprehension().delay_parse()
        p4 = (p2 | p3).parse_once()
        p5 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(ListLiteralAst, self, [p1, p4, p5])

    def _parse_literal_set(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
        p2 = self._parse_build_container_from_range().delay_parse()
        p3 = self._parse_build_container_from_expressions().delay_parse()
        p4 = self._parse_build_container_from_comprehension().delay_parse()
        p5 = (p2 | p3 | p4).parse_once()
        p6 = self._parse_token(TokenType.TkRightBrace).parse_once()
        return BoundParser(ListLiteralAst, self, [p1, p5, p6])

    def _parse_literal_map(self) -> BoundParser:
        def parse_next_pair() -> BoundParser:
            p5 = self._parse_token(TokenType.TkComma).parse_once()
            p6 = self._parse_literal_pair_internal().parse_once()
            return BoundParser(lambda x: x, self, [p5, p6])

        p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
        p2 = self._parse_literal_pair_internal().parse_once()
        p3 = parse_next_pair().parse_zero_or_more()
        p4 = self._parse_token(TokenType.TkRightBrace).parse_once()
        return BoundParser(lambda x, y: MapLiteralAst([x] + y), self, [p1, p2, p3, p4])

    def _parse_literal_pair(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_literal_pair_internal().parse_once()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_literal_pair_internal(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(PairLiteralAst, self, [p1, p2, p3])

    def _parse_literal_pair(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_literal_pair_internal().parse_once()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    def _parse_literal_regex(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxRegex)
        return BoundParser(RegexLiteralAst, self, [p1])

    def _parse_literal_tuple(self) -> BoundParser:
        def parse_0_or_1_element() -> BoundParser:
            p6 = self._parse_expression().parse_optional()
            p7 = self._parse_token(TokenType.TkComma).parse_optional()
            return BoundParser(lambda x: x, self, [p6, p7])

        def parse_multiple_elements() -> BoundParser:
            def parse_next_element() -> BoundParser:
                p8 = self._parse_token(TokenType.TkComma).parse_once()
                p9 = self._parse_expression().parse_once()
                return BoundParser(lambda x: x, self, [p8, p9])
            p10 = self._parse_expression().parse_once()
            p11 = parse_next_element().parse_zero_or_more()
            return BoundParser(lambda x, y: [x] + y, self, [p10, p11])

        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = parse_0_or_1_element().delay_parse()
        p3 = parse_multiple_elements().delay_parse()
        p4 = (p2 | p3).parse_once()
        p5 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(TupleLiteralAst, self, [p1, p4, p5])

    def _parse_literal_number_base_02(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxBinDigits)
        return BoundParser(NumberLiteralBase2Ast, self, [p1])

    def _parse_literal_number_base_10(self) -> BoundParser:
        p1 = self._parse_number()
        return BoundParser(NumberLiteralBase10Ast, self, [p1])

    def _parse_literal_number_base_16(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxHexDigits)
        return BoundParser(NumberLiteralBase16Ast, self, [p1])

    """[CONTAINER BUILDING]"""
    def _parse_build_container_from_range(self):
        def parse_step() -> BoundParser:
            p5 = self._parse_token(TokenType.TkComma).parse_once()
            p6 = self._parse_expression().parse_once()
            return BoundParser(lambda x: x, self, [p5, p6])

        p1 = self._parse_expression().parse_once()
        p2 = self._parse_token(TokenType.TkDoubleDot).parse_once()
        p3 = self._parse_expression().parse_once()
        p4 = parse_step().parse_optional()
        return BoundParser(IterableRangeAst, self, [p1, p2, p3, p4])

    def _parse_build_container_from_expressions(self):
        p1 = self._parse_expressions().parse_optional()
        return BoundParser(IterableFixedAst, self, [p1])

    def _parse_build_container_from_comprehension(self):
        p1 = self._parse_expression().parse_once()
        p2 = self._parse_token(TokenType.KwFor).parse_once()
        p3 = self._parse_local_variable_identifiers().parse_once()
        p5 = self._parse_expression().parse_once()
        p4 = self._parse_token(TokenType.KwIn).parse_once()
        p6 = self._parse_value_guard().parse_optional()
        return BoundParser(IterableComprehensionAst, self, [p1, p2, p3, p4, p5, p6])

    """[NUMBER]"""

    def _parse_number(self) -> BoundParser:
        p1 = self._parse_numeric_integer().parse_once()
        p2 = self._parse_numeric_decimal().parse_optional()
        p3 = self._parse_numeric_complex().parse_optional()
        p4 = self._parse_numeric_exponent().parse_optional()
        return BoundParser(NumberLiteralAst, self, [p1, p2, p3, p4])

    def _parse_numeric_integer(self) -> BoundParser:
        p1 = self._parse_lexeme(TokenType.LxDecDigits)
        return BoundParser(lambda x: x, self, [p1])

    def _parse_numeric_decimal(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDot).parse_once()
        p2 = self._parse_lexeme(TokenType.LxDecDigits)
        return BoundParser(lambda x: x, self, [p1, p2])

    def _parse_numeric_complex(self) -> BoundParser:
        p1 = self._parse_character('i').parse_once()
        return BoundParser(lambda x: True, self, [p1])

    def _parse_numeric_exponent(self) -> BoundParser:
        p1 = self._parse_character('e').parse_once()
        p2 = self._parse_operator_identifier_additive().parse_optional()
        p3 = self._parse_numeric_integer().parse_once()
        return BoundParser(NumberExponentAst, self, [p1, p2, p3])

    """[MISC]"""

    def _parse_token(self, token: TokenType) -> BoundParser:
        def parse_token_inner():
            # print("parse_token", token)
            if self._dedents_expected > 0:
                raise ParseError("Expected a dedent")

            if token != TokenType.TkNewLine: self._skip(TokenType.TkNewLine)
            if token != TokenType.TkWhitespace: self._skip(TokenType.TkWhitespace)

            if self._current >= len(self._tokens):
                raise ParseError(f"Expected <{token}>, got <EOF>")

            current_token = self._tokens[self._current].token_type
            if current_token != token:
                # print([frame.function for frame in reversed(inspect.stack()) if frame.function not in [
                #     "parse_once", "parse_optional", "parse_zero_or_more", "parse_one_or_more", "__or__",
                #     "_internal_parser", "inner"]])
                # print(f"Expected {token}, got <{current_token}>\n")

                raise ParseError(
                    ErrorFormatter(self._tokens).error(self._current) +
                    f"Expected <{token}>, got <{current_token}>\n" +
                    f"{' -> '.join(reversed([frame.function for frame in inspect.stack()]))}\n")

            self._current += 1
            return BoundParser(lambda: self._tokens[self._current - 1], self, [])
            # return self._tokens[self._current - 1]
            # print("parse_token", token, "success")
        return BoundParser(lambda t: t, self, [parse_token_inner])

    def _parse_lexeme(self, lexeme: TokenType) -> BoundParser:
        p1 = self._parse_token(lexeme).parse_once()
        return BoundParser(lambda x: x.token_metadata, self, [p1])


    def _skip(self, token: TokenType):
        while self._current < len(self._tokens) and self._tokens[self._current].token_type == token:
            self._current += 1

    def _parse_indent(self) -> BoundParser:
        def increment_dedents_expected(x):
            self._dedents_expected += x is None

        self._indent += 4
        p1 = self._parse_indented_whitespace().parse_optional()
        if self._tokens[self._current].token_type == TokenType.TkWhitespace:
            raise ParseError("Unexpected whitespace")
        return BoundParser(increment_dedents_expected, self, [p1])

    def _parse_indented_whitespace(self) -> BoundParser:
        def inner():
            for i in range(self._indent):
                self._parse_token(TokenType.TkWhitespace)
        return BoundParser(TokenAst, self, [inner])

    def _parse_dedent(self) -> BoundParser:
        def inner():
            self._indent -= 4
            self._dedents_expected = max(self._dedents_expected - 1, 0)
        return BoundParser(TokenAst, self, [inner])

    def _parse_empty_implementation(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(TokenAst, self, [p1])

    def _parse_character(self, character: str) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        if p1.identifier != character:
            raise ParseError(f"Expected {character}, got {p1.value}")
        return BoundParser(lambda x: x, self, [p1])
