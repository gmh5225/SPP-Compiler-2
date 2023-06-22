from __future__ import annotations

from typing import Optional, Generic, TypeVar, Callable, Any
from src.Ast import *
from src.Tokens import TokenType
import inspect

class ParseError(Exception):
    ...

Rules = list

class BoundParser:
    _ctor: type | Callable
    _rules: Rules
    _parser: Parser

    def __init__(self, constructor: type | Callable, parser: Parser, rules: Rules):
        self._ctor = constructor
        self._rules = rules
        self._parser = parser

    def parse_once(self, remove_tokens: bool = True):
        results = []
        for rule in self._rules:
            results.append(rule())

        # remove the token results
        if remove_tokens:
            results = [result for result in results if not isinstance(result, TokenAst)]
        return self._ctor(*results)

    def parse_optional(self, remove_tokens: bool = True):
        restore_index = self._parser._current
        try:
            results = self.parse_once(remove_tokens)
            return results
        except ParseError:
            self._parser._current = restore_index
            return None

    def parse_zero_or_more(self):
        results = []
        while True:
            restore_index = self._parser._current
            try:
                results.append(self.parse_once())
            except ParseError:
                self._parser._current = restore_index
                break
        return results

    def delay_parse(self) -> BoundParser:
        return self

    def parse_one_or_more(self):
        results = [self.parse_once()]
        results.extend(self.parse_zero_or_more())
        return results

    def __or__(self, that: BoundParser) -> BoundParser:
        # Allow chaining n parsers, and one of them has to match
        # Try to parse each one. if one is valid, return it
        # if none are valid, raise an error
        def inner():
            f = self.parse_optional()
            if f is None:
                f = that.parse_optional()
            if f is None:
                raise ParseError("No valid parser found for selection")
            return f
        return BoundParser(self._ctor, self._parser, [inner])

    def upgrade_ctor(self, new_ctor: type) -> BoundParser:
        return BoundParser(new_ctor, self._parser, self._rules)

# def partial_parse(function):
#
#     def inner(self, *args):
#         def _internal_parser():
#             return function(self, *args)
#         return BoundParser(lambda x: x, self, [_internal_parser])
#     return inner

class partial_parse:
    def __init__(self, function):
        self._function = function

    def __call__(self, *args, **kwargs):
        def _internal_parser():
            return self._function(*args, **kwargs)
        return BoundParser(lambda x: x, self, [_internal_parser])


class Parser:
    _tokens: list[Token]
    _current: int
    _indent: int

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._current = 0
        self._indent = 0

    def parse(self) -> ProgramAst:
        return self._parse_program().parse_once()

    """MODULES"""

    @partial_parse
    def _parse_program(self) -> BoundParser:
        p1 = self._parse_module_prototype().parse_once()
        p2 = self._parse_eof().parse_once()
        return BoundParser(ProgramAst, self, [p1, p2])

    @partial_parse
    def _parse_eof(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkEOF).parse_once()
        return BoundParser(TokenAst, self, [p1])

    @partial_parse
    def _parse_module_prototype(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwMod).parse_once()
        p3 = self._parse_module_identifier().parse_once()
        p4 = self._parse_token(TokenType.TkSemicolon).parse_once()
        p5 = self._parse_module_implementation().parse_once()
        return BoundParser(ModulePrototypeAst, self, [p1, p2, p3, p4, p5])

    @partial_parse
    def _parse_module_implementation(self) -> BoundParser:
        p1 = self._parse_import_block().parse_optional()
        p2 = self._parse_module_member().parse_one_or_more()
        return BoundParser(ModuleImplementationAst, self, [p1, p2])

    @partial_parse
    def _parse_module_identifier(self) -> BoundParser:
        p1 = self._parse_dot_scoped_identifier().parse_once()
        return BoundParser(IdentifierAst, self, [p1])

    @partial_parse
    def _parse_module_member(self) -> BoundParser:
        p1 = self._parse_function_prototype().delay_parse()
        p2 = self._parse_enum_prototype().delay_parse()
        p3 = self._parse_class_prototype().delay_parse()
        p4 = self._parse_sup_prototype().delay_parse()
        p5 = (p1 | p2 | p3 | p4).parse_once()
        return BoundParser(ModuleMemberAst, self, [p5])

    """IMPORTS"""

    @partial_parse
    def _parse_import_block(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwUse).parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_indent().parse_once()
        p4 = self._parse_import_definition().parse_one_or_more()
        p5 = self._parse_dedent().parse_once()
        return BoundParser(ImportBlockAst, self, [p1, p2, p3, p4, p5])

    @partial_parse
    def _parse_import_definition(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkDot).parse_zero_or_more()
        p2 = self._parse_module_identifier().parse_once()
        p3 = self._parse_token(TokenType.TkRightArrow).parse_once()
        p4 = self._parse_import_identifiers().parse_once()
        p5 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ImportDefinitionsAst, self, [p1, p2, p3, p4, p5])

    @partial_parse
    def _parse_import_identifiers(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAsterisk).delay_parse()
        p2 = self._parse_import_identifiers_raw().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(ImportTypeAst, self, [p3])

    @partial_parse
    def _parse_import_all_types(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAsterisk).parse_once()
        return BoundParser(lambda: ImportTypesAst([], True), self, [p1])

    @partial_parse
    def _parse_import_identifiers_raw(self) -> BoundParser:
        def parse_next_import_identifier_raw():
            p3 = self._parse_token(TokenType.TkComma).parse_once(),
            p4 = self._parse_import_identifier_raw().parse_once(),
            return BoundParser(lambda ids: ids, self, [p3, p4])

        p1 = self._parse_import_identifier_raw().parse_once()
        p2 = parse_next_import_identifier_raw().parse_zero_or_more()
        return BoundParser(ImportTypesAst, self, [p1, p2])

    @partial_parse
    def _parse_import_identifier_raw(self) -> BoundParser:
        def parse_import_identifier_raw_alias():
            p3 = self._parse_token(TokenType.KwAs).parse_once()
            p4 = self._parse_identifier().parse_once()
            return BoundParser(lambda alias: alias, self, [p3, p4])

        p1 = self._parse_identifier().parse_once()
        p2 = parse_import_identifier_raw_alias().parse_optional()
        return BoundParser(ImportTypeAst, self, [p1, p2])

    """CLASSES"""

    @partial_parse
    def _parse_access_modifier(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwPub).delay_parse()
        p2 = self._parse_token(TokenType.KwPriv).delay_parse()
        p3 = self._parse_token(TokenType.KwProt).delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(AccessModifierAst, self, [p4])

    @partial_parse
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

    @partial_parse
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

    @partial_parse
    def _parse_class_implementation(self) -> BoundParser:
        p1 = self._parse_class_member().parse_one_or_more()
        return BoundParser(ClassImplementationAst, self, [p1])

    @partial_parse
    def _parse_class_member(self) -> BoundParser:
        p1 = self._parse_class_attribute()
        p2 = self._parse_class_attribute_static()
        p3 = (p1 | p2).parse_once()
        return BoundParser(ClassAttributeAst, self, [p3])

    @partial_parse
    def _parse_class_attribute(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwMut).parse_optional()
        p3 = self._parse_class_attribute_identifier().parse_once()
        p4 = self._parse_token(TokenType.TkColon).parse_once()
        p5 = self._parse_type_identifier().parse_once()
        p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ClassInstanceAttributeAst, self, [p1, p2, p3, p4, p5, p6])

    @partial_parse
    def _parse_class_attribute_static(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwMut).parse_optional()
        p3 = self._parse_class_attribute_static_identifier().parse_once()
        p4 = self._parse_token(TokenType.TkEqual).parse_once()
        p5 = self._parse_expression().parse_once()
        p6 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(ClassStaticAttributeAst, self, [p1, p2, p3, p4, p5, p6])

    @partial_parse
    def _parse_class_attribute_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    @partial_parse
    def _parse_class_attribute_static_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    @partial_parse
    def _parse_class_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    """SUPER-IMPOSITIONS"""

    @partial_parse
    def _parse_sup_prototype(self) -> BoundParser:
        def parse_sup_prototype_normal():
            p4 = self._parse_type_generic_parameters().parse_optional()
            p5 = self._parse_sup_identifier().parse_once()
            p6 = self._parse_where_block().parse_optional()
            p7 = self._parse_sup_or_empty_implementation().parse_once()
            return BoundParser(SupPrototypeNormalAst, self, [p4, p5, p6, p7])

        def parse_sup_prototype_with_inherit():
            p4 = self._parse_type_generic_parameters().parse_optional()
            p5 = self._parse_sup_identifier().parse_once()
            p6 = self._parse_token(TokenType.KwFor).parse_once()
            p7 = self._parse_sup_identifier().parse_once()
            p8 = self._parse_where_block().parse_optional()
            p9 = self._parse_sup_or_empty_implementation().parse_once()
            return BoundParser(SupPrototypeInheritanceAst, self, [p4, p5, p6, p7, p8, p9])

        p1 = self._parse_token(TokenType.KwSup).parse_once()
        p2 = parse_sup_prototype_normal().delay_parse()
        p3 = parse_sup_prototype_with_inherit().delay_parse()
        p4 = (p2 | p3).parse_once()
        return BoundParser(lambda sup: sup, self, [p1, p4])

    @partial_parse
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

    @partial_parse
    def _parse_sup_implementation(self) -> BoundParser:
        p1 = self._parse_sup_member().parse_one_or_more()
        return BoundParser(SupImplementationAst, self, [p1])

    @partial_parse
    def _parse_sup_member(self) -> BoundParser:
        p1 = self._parse_sup_method().delay_parse()
        p2 = self._parse_sup_typedef().delay_parse()
        p3 = (p1 | p2).upgrade_ctor(SupMemberAst).parse_once()
        return BoundParser(SupMemberAst, self, [p3])

    @partial_parse
    def _parse_sup_identifier(self) -> BoundParser:
        p1 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(lambda i: i, self, [p1])

    @partial_parse
    def _parse_sup_typedef(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_statement_typedef().parse_once()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(SupTypedefAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_sup_method(self) -> BoundParser:
        p1 = self._function_prototype().parse_once()
        return BoundParser(SupMethodPrototypeAst, self, [p1])

    """ENUMS"""

    @partial_parse
    def _parse_enum_prototype(self) -> BoundParser:
        p1 = self._parse_access_modifier().parse_optional()
        p2 = self._parse_token(TokenType.KwEnum).parse_once()
        p3 = self._parse_enum_identifier().parse_once()
        p4 = self._parse_enum_or_empty_implementation().parse_once()
        return BoundParser(EnumPrototypeAst, self, [p1, p2, p3, p4])

    @partial_parse
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

    @partial_parse
    def _parse_enum_implementation(self) -> BoundParser:
        def parse_next_enum_member():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_enum_member().parse_once()
            return BoundParser(EnumMemberAst, self, [p3, p4])

        p1 = self._parse_enum_member().parse_once()
        p2 = parse_next_enum_member().parse_zero_or_more()
        p3 = self._parse_token(TokenType.TkSemicolon).parse_once()
        return BoundParser(EnumImplementationAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_enum_member(self) -> BoundParser:
        def parse_enum_member_value():
            p3 = self._parse_token(TokenType.TkEqual).parse_once()
            p4 = self._parse_enum_member_value().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_enum_member_identifier().parse_once()
        p2 = parse_enum_member_value().parse_optional()
        return BoundParser(EnumMemberAst, self, [p1, p2])

    @partial_parse
    def _parse_enum_member_value(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    @partial_parse
    def _parse_enum_member_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    @partial_parse
    def _parse_enum_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """FUNCTION"""

    @partial_parse
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
        p11 = self._parse_value_guard_block().parse_optional()
        p12 = self._parse_function_or_empty_implementation().parse_once()
        return BoundParser(FunctionPrototypeAst, self, [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12])

    @partial_parse
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

    @partial_parse
    def _parse_function_implementation(self) -> BoundParser:
        p1 = self._parse_statement().parse_one_or_more()
        return BoundParser(FunctionImplementationAst, self, [p1])

    @partial_parse
    def _parse_function_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    @partial_parse
    def _parse_function_call_arguments(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_function_call_arguments_normal_then_named().parse_optional()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    @partial_parse
    def _parse_function_call_arguments_normal_then_named(self) -> BoundParser:
        p1 = self._parse_function_call_next_normal_arguments().delay_parse()
        p2 = self._parse_function_call_next_named_arguments().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_function_call_next_normal_arguments(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_arguments_normal_then_named().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_call_argument_normal().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_function_call_next_named_arguments(self) -> BoundParser:
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_call_argument_named().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_call_argument_named().parse_once()
        p4 = parse_following().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_function_call_argument_normal(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        return BoundParser(lambda x: FunctionArgumentAst(None, x), self, [p1])

    @partial_parse
    def _parse_function_call_argument_named(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(FunctionArgumentAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_function_parameters(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_function_parameters_required_then_optional().parse_optional()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    @partial_parse
    def _parse_function_parameters_required_then_optional(self) -> BoundParser:
        p1 = self._parse_function_parameters_required_and_following().delay_parse()
        p2 = self._parse_function_parameters_optional_and_following().delay_parse()
        p3 = self._parse_function_parameters_variadic_and_following().delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    @partial_parse
    def _parse_function_parameters_optional_then_variadic(self) -> BoundParser:
        p1 = self._parse_function_parameters_optional_and_following().delay_parse()
        p2 = self._parse_function_parameters_variadic_and_following().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_function_parameters_required_and_following(self) -> BoundParser:
        @partial_parse
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameters_required_then_optional().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_parameter_required().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_function_parameters_optional_and_following(self) -> BoundParser:
        @partial_parse
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_function_parameters_optional_then_variadic().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_function_parameter_optional().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_function_parameters_variadic_and_following(self) -> BoundParser:
        p1 = self._parse_function_parameter_variadic().parse_once()
        return BoundParser(lambda x: [x], self, [p1])

    @partial_parse
    def _parse_function_parameter_required(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMut).parse_optional()
        p2 = self._parse_function_parameter_identifier().parse_once()
        p3 = self._parse_token(TokenType.TkColon).parse_once()
        p4 = self._parse_type_identifier().parse_once()
        return BoundParser(FunctionParameterAst_Required, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_function_parameter_optional(self) -> BoundParser:
        p1 = self._parse_function_parameter_required().parse_once()
        p2 = self._parse_token(TokenType.TkEqual).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(FunctionParameterAst_Optional, self, [p1, p2, p3])

    @partial_parse
    def _parse_function_parameter_variadic(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
        p2 = self._parse_function_parameter_required().parse_once()
        return BoundParser(FunctionParameterAst_Variadic, self, [p1, p2])

    @partial_parse
    def _parse_function_parameter_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """[TYPE & VALUE GUARD]"""

    @partial_parse
    def _parse_where_block(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwWhere).parse_once()
        p2 = self._parse_token(TokenType.TkLeftBracket).parse_once()
        p3 = self._parse_where_constraints().parse_optional()
        p4 = self._parse_token(TokenType.TkRightBracket).parse_once()
        return BoundParser(WhereBlockAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_where_constraints(self) -> BoundParser:
        @partial_parse
        def parse_next_where_constraint() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_where_constraint().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_where_constraint().parse_once()
        p2 = parse_next_where_constraint().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_where_constraint(self) -> BoundParser:
        p1 = self._parse_static_scoped_generic_identifiers().parse_once()
        p2 = self._parse_token(TokenType.TkColon).parse_once()
        p3 = self._parse_where_constraint_chain().parse_once()
        return BoundParser(WhereConstraintAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_where_constraint_chain(self) -> BoundParser:
        @partial_parse
        def parse_next_where_constraint_chain_item() -> BoundParser:
            p1 = self._parse_token(TokenType.TkPlus).parse_once()
            p2 = self._parse_where_constraint_chain_item_element().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_where_constraint_chain_element().parse_once()
        p4 = parse_next_where_constraint_chain_item().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_where_constraint_chain_element(self) -> BoundParser:
        p1 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    @partial_parse
    def _parse_value_guard(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwIf).parse_once()
        p2 = self._parse_expression().parse_once()
        return BoundParser(ValueGuardAst, self, [p1, p2])

    """[DECORATORS]"""

    @partial_parse
    def _parse_decorator(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkAt).parse_once()
        p2 = self._parse_decorator_identifier().parse_once()
        p3 = self._parse_type_generic_arguments().parse_optional()
        p4 = self._parse_function_call_arguments().parse_optional()
        return BoundParser(DecoratorAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_decorators(self) -> BoundParser:
        @partial_parse
        def parse_next_decorator():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_decorator().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_decorator().parse_once()
        p2 = parse_next_decorator().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_decorator_identifier(self) -> BoundParser:
        p1 = self._parse_static_scoped_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """[EXPRESSIONS]"""
    @partial_parse
    def _parse_expressions(self) -> BoundParser:
        @partial_parse
        def parse_next_expression():
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_expression().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_expression().parse_once()
        p2 = parse_next_expression().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_expression(self) -> BoundParser:
        p1 = self._parse_assignment_expression().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    @partial_parse
    def _parse_assignment_expression(self) -> BoundParser:
        @partial_parse
        def parse_multi_assignment() -> BoundParser:
            @partial_parse
            def parse_multi_lhs() -> BoundParser:
                p9 = self._parse_token(TokenType.TkComma).parse_once()
                p10 = self._parse_null_coalescing_expression().parse_once()
                return BoundParser(lambda x: x, self, [p9, p10])

            @partial_parse
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

        @partial_parse
        def parse_single_assignment() -> BoundParser:
            @partial_parse
            def parse_rhs() -> BoundParser:
                p6 = self._parse_token(TokenType.TkEqual).parse_once()
                p7 = self._parse_assignment_expression().parse_once()
                return BoundParser(lambda x, y: (x, y), self, [p6, p7])

            p4 = self._parse_null_coalescing_expression().parse_once()
            p5 = parse_rhs().parse_optional(remove_tokens=False)
            return BoundParser(
                lambda lhs, op, rhs: lhs if not rhs else BinaryExpressionAst(lhs, op, rhs), self,
                [p4, p5])

        p1 = parse_multi_assignment().parse_once()
        p2 = parse_single_assignment().parse_once()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_null_coalescing_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_or_expression(),
            self._parse_operator_identifier_null_coalescing(),
            self._parse_null_coalescing_expression())

    @partial_parse
    def _parse_logical_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_logical_and_expression(),
            self._parse_token(TokenType.TkDoubleVerticalBar).parse_once(),
            self._parse_logical_or_expression())

    @partial_parse
    def _parse_logical_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_or_expression(),
            self._parse_token(TokenType.TkDoubleAmpersand).parse_once(),
            self._parse_logical_and_expression())

    @partial_parse
    def _parse_bitwise_or_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_xor_expression(),
            self._parse_token(TokenType.TkVerticalBar).parse_once(),
            self._parse_bitwise_or_expression())

    @partial_parse
    def _parse_bitwise_xor_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_bitwise_and_expression(),
            self._parse_token(TokenType.TkCaret).parse_once(),
            self._parse_bitwise_xor_expression())

    @partial_parse
    def _parse_bitwise_and_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_equality_expression(),
            self._parse_token(TokenType.TkAmpersand).parse_once(),
            self._parse_bitwise_and_expression())

    @partial_parse
    def _parse_equality_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_relational_expression(),
            self._parse_operator_identifier_equality(),
            self._parse_equality_expression())

    @partial_parse
    def _parse_relational_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_shift_expression(),
            self._parse_operator_identifier_relational(),
            self._parse_relational_expression())

    @partial_parse
    def _parse_shift_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_rotate_expression(),
            self._parse_operator_identifier_shift(),
            self._parse_shift_expression())

    @partial_parse
    def _parse_rotate_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_additive_expression(),
            self._parse_operator_identifier_rotate(),
            self._parse_rotate_expression())

    @partial_parse
    def _parse_additive_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_multiplicative_expression(),
            self._parse_operator_identifier_additive(),
            self._parse_additive_expression())

    @partial_parse
    def _parse_multiplicative_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_power_expression(),
            self._parse_operator_identifier_multiplicative(),
            self._parse_multiplicative_expression())

    @partial_parse
    def _parse_power_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_pipe_expression(),
            self._parse_operator_identifier_power(),
            self._parse_power_expression())

    @partial_parse
    def _parse_pipe_expression(self) -> BoundParser:
        return self._parse_binary_expression(
            self._parse_unary_expression(),
            self._parse_operator_identifier_pipe(),
            self._parse_pipe_expression())

    @partial_parse
    def _parse_unary_expression(self) -> BoundParser:
        @partial_parse
        def parse_unary() -> BoundParser:
            p4 = self._parse_operator_identifier_unary().parse_once()
            p5 = self._parse_unary_expression().parse_once()
            return BoundParser(lambda x, y: UnaryExpressionAst(x, y), self, [p4, p5])

        p1 = parse_unary()
        p2 = self._parse_postfix_expression()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_postfix_expression(self) -> BoundParser:
        @partial_parse
        def parse_postfix() -> BoundParser:
            p4 = self._parse_postfix_expression().parse_once()
            p5 = self._parse_operator_identifier_postfix().parse_once()
            return BoundParser(lambda x, y: PostfixExpressionAst(x, y), self, [p4, p5])

        p1 = parse_postfix()
        p2 = self._parse_primary_expression().parse_once()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_primary_expression(self) -> BoundParser:
        p1 = self._parse_lambda()
        p2 = self._parse_literal()
        p3 = self._parse_identifier()
        p4 = self._parse_parenthesized_expression()
        p5 = self._parse_expression_placeholder()
        p5 = (p1 | p2 | p3 | p4).parse_once()
        return BoundParser(lambda x: x, self, [p5])

    @partial_parse
    def _parse_binary_expression(self, lhs, op, rhs) -> BoundParser:
        @partial_parse
        def parse_rhs() -> BoundParser:
            p3 = op.parse_once()
            p4 = rhs.parse_once()
            return BoundParser(lambda x, y: (x, y), self, [p3, p4])

        p1 = lhs.parse_once()
        p2 = parse_rhs().parse_optional(remove_tokens=False)
        return BoundParser(lambda lhs, op, rhs: lhs if not rhs else BinaryExpressionAst(lhs, op, rhs), self, [p1, p2])

    @partial_parse
    def _parse_parenthesized_expression(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    @partial_parse
    def _parse_expression_placeholder(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkUnderscore).parse_once()
        return BoundParser(PlaceholderAst, self, [p1])

    """[LAMBDA]"""

    @partial_parse
    def _parse_lambda(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwAsync).parse_optional(remove_tokens=False)
        p2 = self._parse_lambda_capture_list().parse_optional()
        p3 = self._parse_lambda_parameters().parse_once()
        p4 = self._parse_token(TokenType.TkRightArrow).parse_once()
        p5 = self._parse_lambda_implementation().parse_once()
        return BoundParser(LambdaAst, self, [p1, p2, p3, p4, p5])

    @partial_parse
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

    @partial_parse
    def _parse_lambda_capture_item(self) -> BoundParser:
        def parse_alias() -> BoundParser:
            p3 = self._parse_identifier().parse_once()
            p4 = self._parse_token(TokenType.TkEqual).parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = parse_alias().parse_optional()
        p2 = self._parse_expression().parse_once()
        return BoundParser(LambdaCaptureItemAst, self, [p1, p2])

    @partial_parse
    def _parse_lambda_parameters(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_lambda_parameters_required().parse_once()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    @partial_parse
    def _parse_lambda_parameters_required(self) -> BoundParser:
        def parse_next_parameter() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_lambda_parameter_required().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_lambda_parameter_required().parse_once()
        p2 = parse_next_parameter().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_lambda_parameter_required(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMut).parse_optional(remove_tokens=False)
        p2 = self._parse_function_parameter_identifier().parse_once()
        return BoundParser(LambdaParameterAst, self, [p1, p2])

    @partial_parse
    def _parse_lambda_implementation(self) -> BoundParser:
        p1 = self._parse_expression().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    """[TYPES]"""

    @partial_parse
    def _parse_type_identifier(self) -> BoundParser:
        p1 = self._parse_operator_identifier_unary_reference().parse_optional(remove_tokens=False)
        p2 = self._parse_static_scoped_generic_identifier().parse_once()
        return BoundParser(TypeAst, self, [p1, p2])

    @partial_parse
    def _parse_type_identifiers(self) -> BoundParser:
        def parse_next_type_identifier() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_identifier().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_type_identifier().parse_once()
        p2 = parse_next_type_identifier().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_type_generic_arguments(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftAngleBracket).parse_once()
        p2 = self._parse_type_generic_arguments_normal_then_named().parse_optional()
        p3 = self._parse_token(TokenType.TkRightAngleBracket).parse_once()
        return BoundParser(TypeGenericArgumentAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_type_generic_arguments_normal_then_named(self) -> BoundParser:
        p1 = self._parse_type_generic_arguments_next_normal().delay_parse()
        p2 = self._parse_type_generic_arguments_next_named().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_type_generic_arguments_next_normal(self) -> BoundParser:
        @partial_parse
        def parse_following() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_generic_arguments_normal_then_named().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_type_generic_argument_normal().parse_once()
        p2 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_type_generic_arguments_next_named(self) -> BoundParser:
        @partial_parse
        def parse_following() -> BoundParser:
            p3 = self._parse_token(TokenType.TkComma).parse_once()
            p4 = self._parse_type_generic_argument_named().parse_once()
            return BoundParser(lambda x, y: y, self, [p3, p4])

        p1 = self._parse_type_generic_argument_named().parse_once()
        p2 = parse_following().parse_zero_or_more()
        return BoundParser(lambda x, y: [x] + y, self, [p1, p2])

    @partial_parse
    def _parse_type_generic_argument_normal(self) -> BoundParser:
        p1 = self._parse_type_identifier().parse_once()
        return BoundParser(TypeGenericArgumentAst_Normal, self, [p1])

    @partial_parse
    def _parse_type_generic_argument_named(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        p2 = self._parse_token(TokenType.TkEqual).parse_once()
        p3 = self._parse_type_identifier().parse_once()
        return BoundParser(TypeGenericArgumentAst_Named, self, [p1, p2, p3])

    @partial_parse
    def _parse_type_generic_parameters(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
        p2 = self._parse_type_generic_parameters_required_then_optional().parse_optional()
        p3 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
        return BoundParser(lambda x: x, self, [p1, p2, p3])

    @partial_parse
    def _parse_type_generic_parameters_required_then_optional(self) -> BoundParser:
        p1 = self._parse_type_generic_parameters_required_and_following().delay_parse()
        p2 = self._parse_type_generic_parameters_optional_and_following().delay_parse()
        p3 = self._parse_type_generic_parameters_variadic_and_following().delay_parse()
        p4 = (p1 | p2 | p3).parse_once()
        return BoundParser(lambda x: x, self, [p4])

    @partial_parse
    def _parse_type_generic_parameters_optional_then_variadic(self) -> BoundParser:
        p1 = self._parse_type_generic_parameters_optional_and_following().delay_parse()
        p2 = self._parse_type_generic_parameters_variadic_and_following().delay_parse()
        p3 = (p1 | p2).parse_once()
        return BoundParser(lambda x: x, self, [p3])

    @partial_parse
    def _parse_type_generic_parameters_required_and_following(self) -> BoundParser:
        @partial_parse
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_type_generic_parameter_required().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_type_generic_parameters_optional_and_following(self) -> BoundParser:
        @partial_parse
        def parse_following() -> BoundParser:
            p1 = self._parse_token(TokenType.TkComma).parse_once()
            p2 = self._parse_type_generic_parameters_optional_then_variadic().parse_once()
            return BoundParser(lambda x: x, self, [p1, p2])

        p3 = self._parse_type_generic_parameter_optional().parse_once()
        p4 = parse_following().parse_optional()
        return BoundParser(lambda x, y: [x] + y, self, [p3, p4])

    @partial_parse
    def _parse_type_generic_parameters_variadic_and_following(self) -> BoundParser:
        p1 = self._parse_type_generic_parameter_variadic().parse_once()
        return BoundParser(lambda x: [x], self, [p1])

    @partial_parse
    def _parse_type_generic_parameter_required(self) -> BoundParser:
        def parse_inline_constraint() -> BoundParser:
            p3 = self._parse_token(TokenType.TkColon).parse_once()
            p4 = self._parse_where_constraint_chain().parse_once()
            return BoundParser(lambda x: x, self, [p3, p4])

        p1 = self._parse_identifier().parse_once()
        p2 = parse_inline_constraint().parse_optional()
        return BoundParser(TypeGenericParameterAst_Required, self, [p1, p2])

    @partial_parse
    def _parse_type_generic_parameter_optional(self) -> BoundParser:
        p1 = self._parse_type_generic_parameter_required().parse_once()
        p2 = self._parse_token(TokenType.TkEqual).parse_once()
        p3 = self._parse_expression().parse_once()
        return BoundParser(TypeGenericParameterAst_Optional, self, [p1, p2, p3])

    @partial_parse
    def _parse_type_generic_parameter_variadic(self) -> BoundParser:
        p1 = self._parse_token(TokenType.TkTripleDot).parse_once()
        p2 = self._parse_type_generic_parameter_required().parse_once()
        return BoundParser(TypeGenericParameterAst_Variadic, self, [p1, p2])

    """[STATEMENTS]"""
    @partial_parse
    def _parse_statement_if(self) -> BoundParser:
        p1 = self._parse_statement_if_branch().parse_once()
        p5 = self._parse_statement_elif_branch().parse_zero_or_more()
        p6 = self._parse_statement_else_branch().parse_optional()
        return BoundParser(IfStatementAst, self, [p1, p5, p6])

    @partial_parse
    def _parse_statement_if_branch(self) -> BoundParser:
        def parse_inline_definitions() -> BoundParser:
            p5 = self._parse_statement_let().parse_once()
            p6 = self._parse_token(TokenType.TkComma).parse_once()
            return BoundParser(lambda x: x, self, [p5, p6])

        p1 = self._parse_token(TokenType.KwIf).parse_once()
        p2 = parse_inline_definitions().parse_zero_or_more()
        p3 = self._parse_expression().parse_once()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(IfStatementBranchAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_statement_elif_branch(self) -> BoundParser:
        def parse_inline_definitions() -> BoundParser:
            p7 = self._parse_statement_let().parse_once()
            p8 = self._parse_token(TokenType.TkComma).parse_once()
            return BoundParser(lambda x: x, self, [p7, p8])

        p1 = self._parse_token(TokenType.KwElif).parse_once()
        p2 = parse_inline_definitions().parse_zero_or_more()
        p3 = self._parse_expression().parse_once()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(IfStatementBranchAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_statement_else_branch(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwElse).parse_once()
        p2 = self._parse_statement_block().parse_once()
        return BoundParser(ElseStatementBranchAst, self, [p1, p2])

    @partial_parse
    def _parse_statement_while(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwWhile).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_statement_block().parse_once()
        return BoundParser(WhileStatementAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_statement_for(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwFor).parse_once()
        p2 = self._parse_local_variable_identifiers().parse_once()
        p3 = self._parse_token(TokenType.KwIn).parse_once()
        p4 = self._parse_expression().parse_once()
        p5 = self._parse_statement_block().parse_once()
        return BoundParser(ForStatementAst, self, [p1, p2, p3, p4, p5])

    @partial_parse
    def _parse_statement_do(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwDo).parse_once()
        p2 = self._parse_statement_block().parse_once()
        p3 = self._parse_token(TokenType.KwWhile).parse_once()
        p4 = self._parse_expression().parse_once()
        return BoundParser(DoWhileStatementAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_statement_match(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwMatch).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_statement_cases().parse_once()
        return BoundParser(MatchStatementAst, self, [p1, p2, p3])

    @partial_parse
    def _parse_statement_case(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwCase).parse_once()
        p2 = self._parse_expression().parse_once()
        p3 = self._parse_value_guard().parse_optional()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(CaseStatementAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_statement_case_default(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwCase).parse_once()
        p2 = self._parse_expression_placeholder().parse_once()
        p3 = self._parse_value_guard().parse_optional()
        p4 = self._parse_statement_block().parse_once()
        return BoundParser(CaseStatementAst, self, [p1, p2, p3, p4])

    @partial_parse
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

    @partial_parse
    def _parse_statement_return(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwReturn).parse_once()
        p2 = self._parse_expression().parse_optional()
        return BoundParser(ReturnStatementAst, self, [p1, p2])

    @partial_parse
    def _parse_statement_yield(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwYield).parse_once()
        p2 = self._parse_expression().parse_optional()
        return BoundParser(YieldStatementAst, self, [p1, p2])

    @partial_parse
    def _parse_statement_typedef(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwUse).parse_once()
        p2 = self._parse_generic_identifier().parse_once()
        p3 = self._parse_token(TokenType.KwAs).parse_once()
        p4 = self._parse_type_identifier().parse_once()
        return BoundParser(TypedefStatementAst, self, [p1, p2, p3, p4])

    @partial_parse
    def _parse_statement_break(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwBreak).parse_once()
        p2 = self._parse_statement_loop_tag().parse_optional()
        return BoundParser(BreakStatementAst, self, [p1, p2])

    @partial_parse
    def _parse_statement_continue(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwContinue).parse_once()
        p2 = self._parse_statement_loop_tag().parse_optional()
        return BoundParser(ContinueStatementAst, self, [p1, p2])

    @partial_parse
    def _parse_statement_loop_tag(self) -> BoundParser:
        p1 = self._parse_token(TokenType.KwAs).parse_once()
        p2 = self._parse_tag_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1, p2])

    @partial_parse
    def _parse_tag_identifier(self) -> BoundParser:
        p1 = self._parse_identifier().parse_once()
        return BoundParser(lambda x: x, self, [p1])

    @partial_parse
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


    @partial_parse
    def _parse_token(self, token: TokenType) -> BoundParser:
        if token != TokenType.TkNewLine: self._skip(TokenType.TkNewLine)
        if token != TokenType.TkWhitespace: self._skip(TokenType.TkWhitespace)

        current_token = self._tokens[self._current].token_type
        if current_token != token:
            raise ParseError(f"Expected {token}, got <{current_token}>")
        self._current += 1
        return BoundParser(lambda t: TokenAst(t, None), self, [])

    @partial_parse
    def _parse_dot_scoped_identifier(self) -> BoundParser:
        return BoundParser(IdentifierAst, self, [])

    def _skip(self, token: TokenType):
        while self._current < len(self._tokens) and self._tokens[self._current].token_type == token:
            self._current += 1
