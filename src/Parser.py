from __future__ import annotations

import functools
from typing import Optional, Generic, TypeVar, Callable, Any
from src.Ast import *
from src.Tokens import TokenType, Token

class ParseSyntaxError(Exception):
    ...

class ParserError(Exception):
    ...

Rule = Callable

FOLD = ""

FAILED_OPTIONAL_PARSE_MESSAGE = "\n########## Failed to Parse Alternative ##########\n"
FAILED_TO_PARSE_ONE_OF_MESSAGE = "\n########## Failed to Parse One Of ##########\n"
FAILED_OR = "\n########## Or ##########\n"

# todo
#   - only use .opt-err() following a .parse-optional/one-or-more/zero-or-more => remove otherwise
#   - if a parse ends with one of the above, add a dummy-parse call after it with .opt-err() to get the error


class ErrorFormatter:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def error(self, start_token_index: int) -> str:
        error_position = start_token_index
        while start_token_index > 0 and self._tokens[start_token_index].token_type != TokenType.TkNewLine:
            start_token_index -= 1

        end_token_index = start_token_index + 1
        while end_token_index < len(self._tokens) and self._tokens[end_token_index].token_type != TokenType.TkNewLine:
            end_token_index += 1

        tokens = self._tokens[start_token_index:end_token_index]
        current_line_string = "".join([token.token_metadata for token in tokens])

        spaces = 0
        for token in tokens[:error_position - start_token_index - 1]:
            spaces += len(token.token_metadata)

        error_length = len(self._tokens[error_position].token_metadata)
        error_line_string = "".join([" " * spaces, "^" * error_length]) + " <- "
        final_string = "\n".join(["", current_line_string, error_line_string])
        return final_string


class BoundParser:
    _opt_err = ""

    _ctor: Callable
    _rule: Rule
    _parser: Parser
    _delayed: bool
    _ast: Optional[Any]
    _err: str

    def __init__(self, parser: Parser, rule: Rule):
        self._rule = rule
        self._parser = parser
        self._delayed = False
        self._ast = None
        self._err = ""

    def add_err(self, error: str) -> BoundParser:
        self._err += FOLD + "- " + error
        return self

    def parse_once(self):
        # Try to parse the rule once. If there is an error whilst parsing the rule, then catch it, append the current
        # BoundParser's error to the error message, and re-raise the error. This allows for the error message to be
        # propagated up the call stack.
        try:
            results = self._rule()
            # current_index = max(0, next(reversed(BoundParser._opt_err.split("\n"))).count("\t") - 1)
            # BoundParser._opt_err = BoundParser._opt_err[:BoundParser._opt_err.rfind("\t" * current_index + "-")]
            print(len(BoundParser._opt_err.split("\n")))

        except ParseSyntaxError as parse_once_error:
            self._err += "\n" + str(parse_once_error)
            self._err += ("¦" + FAILED_OPTIONAL_PARSE_MESSAGE + BoundParser._opt_err) if BoundParser._opt_err else ""
            raise ParseSyntaxError(self._err)

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
        except ParseSyntaxError as parse_optional_error:
            self._parser._current = restore_index
            self._ast = None
            BoundParser._opt_err = str(parse_optional_error).rsplit("¦")[0]
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
            except ParseSyntaxError as parse_zero_or_more_error:
                self._parser._current = restore_index
                self._ast = results
                BoundParser._opt_err = str(parse_zero_or_more_error).rsplit("¦")[0]
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
                errors.append(str(e))

        new_indent = errors[0].split("\n")[-1].count("\t") + 1
        errors = [error.replace("\n", "\n" + "\t" * new_indent) for error in errors]

        # Guess the correct branch being used (most successful parses)
        # errors.sort(key=lambda error: error.count("\n"))
        # correct_branch = errors[0] #.split("\n")[0]

        # print(len(errors))
        raise ParseSyntaxError(FAILED_TO_PARSE_ONE_OF_MESSAGE + FAILED_OR.join(errors).replace("¦", "£") + "\n")

    def parse_one_or_more(self):
        results = [self.parse_once()]

        while True:
            restore_index = self._parser._current
            try:
                result = self.parse_once()
                results.append(result)
            except ParseSyntaxError as e:
                self._parser._current = restore_index
                break

        self._ast = results
        return self._ast


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
            p1 = self._parse_module_prototype().add_err("Error parsing <ModulePrototype> for <Program>").parse_once()
            p2 = self._parse_eof().add_err("Error parsing <EOF> for <Program>").parse_once()
            return ProgramAst(p1)
        return BoundParser(self, inner)

    def _parse_eof(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkEOF).add_err("Error parsing 'eof' for <EOF>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_module_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <ModulePrototype>").parse_optional()
            p2 = self._parse_token(TokenType.KwMod).add_err("Error parsing 'mod' for <ModulePrototype>").parse_once()
            p3 = self._parse_module_identifier().add_err("Error parsing <ModuleIdentifier> for <ModulePrototype>").parse_once()
            p4 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <ModulePrototype>").parse_once()
            p5 = self._parse_module_implementation().add_err("Error parsing <ModuleImplementation> for <ModulePrototype>").parse_once()
            return ModulePrototypeAst(p1, p3, p5)
        return BoundParser(self, inner)

    def _parse_module_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_block().add_err("Error parsing <ImportBlock> for <ModuleImplementation>").parse_optional()
            p2 = self._parse_module_member().add_err("Error parsing <ModuleMember>+ for <ModuleImplementation>").parse_zero_or_more()
            return ModuleImplementationAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_module_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <ModuleIdentifier>").parse_once()
            p2 = self._parse_module_identifier_next_part().add_err("Error parsing <ModuleIdentifierNextPart>* for <ModuleIdentifier>").parse_zero_or_more()
            return ModuleIdentifierAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_module_identifier_next_part(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).add_err("Error parsing '.' for <ModuleIdentifierNextPart>").parse_once()
            p2 = self._parse_identifier().add_err("Error parsing <Identifier> for <ModuleIdentifierNextPart>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_module_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_prototype().add_err("Error parsing ... | <FunctionPrototype> | ... for <ModuleMember>").delay_parse()
            p2 = self._parse_enum_prototype().add_err("Error parsing ... | <EnumPrototype> | ... for <ModuleMember>").delay_parse()
            p3 = self._parse_class_prototype().add_err("Error parsing ... | <ClassPrototype> | ... for <ModuleMember>").delay_parse()
            p4 = self._parse_sup_prototype().add_err("Error parsing ... | <SupPrototype> | ... for <ModuleMember>").delay_parse()
            p5 = (p1 | p2 | p3 | p4).add_err("Error parsing selection for <ModuleMember>:").parse_once()
            return p5
        return BoundParser(self, inner)

    # Imports

    def _parse_import_block(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwUse).add_err("Error parsing 'use' for <ImportBlock>").parse_once()
            p2 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <ImportBlock>").parse_once()
            p3 = self._parse_indent().add_err("Error parsing <Indent> for <ImportBlock>").parse_once()
            p4 = self._parse_import_definition().add_err("Error parsing <ImportDefinition>+ for <ImportBlock>").parse_one_or_more()
            p5 = self._parse_dedent().add_err("Error parsing <Dedent> for <ImportBlock>").parse_once()
            return ImportBlockAst(p4)
        return BoundParser(self, inner)

    def _parse_import_definition(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).add_err("Error parsing '.' for <ImportDefinition> (parent dir count)").parse_zero_or_more()
            p2 = self._parse_module_identifier().add_err("Error parsing <ModuleIdentifier> for <ImportDefinition>").parse_once()
            p3 = self._parse_token(TokenType.TkRightArrow).add_err("Error parsing '->' for <ImportDefinition>").parse_once()
            p4 = self._parse_import_identifiers().add_err("Error parsing <ImportIdentifiers> for <ImportDefinition>").parse_once()
            p5 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <ImportDefinition>").parse_once()
            return ImportDefinitionsAst(p1, p2, p4)
        return BoundParser(self, inner)

    def _parse_import_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_all_types().add_err("Error parsing ... | <ImportAllTypes> | ... for <ImportIdentifiers>").delay_parse()
            p2 = self._parse_import_individual_types().add_err("Error parsing ... | <ImportIndividualTypes> | ... for <ImportIdentifiers>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <ImportIdentifiers>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_import_all_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAsterisk).add_err("Error parsing '*' for <ImportAllTypes>").parse_once()
            return ImportTypesAllAst()
        return BoundParser(self, inner)

    def _parse_import_individual_types(self) -> BoundParser:
        def inner():
            p1 = self._parse_import_individual_type().add_err("Error parsing <ImportIndividualType> for <ImportIndividualTypes>").parse_once()
            p2 = self._parse_import_individual_type_next().add_err("Error parsing <ImportIndividualTypeNext>* for <ImportIndividualTypes>").parse_zero_or_more()
            return ImportTypesIndividualAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_import_individual_type_next(self):
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <ImportIndividualTypeNext>").parse_once()
            p2 = self._parse_import_individual_type().add_err("Error parsing <ImportIndividualType> for <ImportIndividualTypeNext>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_import_individual_type(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <ImportIndividualTypes>").parse_once()
            p2 = self._parse_import_individual_type_alias().add_err("Error parsing <ImportIndividualTypeAlias> for <ImportIndividualType>").parse_optional()
            return ImportTypeAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_import_individual_type_alias(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.KwAs).add_err("Error parsing 'as' for <ImportIndividualTypeAlias>").parse_once()
            p4 = self._parse_identifier().add_err("Error parsing <Identifier> for <ImportIndividualTypeAlias>").parse_once()
            return p4
        return BoundParser(self, inner)

    """CLASSES"""

    def _parse_access_modifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwPub).add_err("Error parsing ... | 'pub' | ... for <AccessModifier>").delay_parse()
            p2 = self._parse_token(TokenType.KwPriv).add_err("Error parsing  ... | 'priv' | ... for <AccessModifier>").delay_parse()
            p3 = self._parse_token(TokenType.KwProt).add_err("Error parsing ... | 'prot' | ... for <AccessModifier>").delay_parse()
            p4 = (p1 | p2 | p3).add_err("Error parsing selection for <AccessModifier>:").parse_optional()
            return p4
        return BoundParser(self, inner)

    def _parse_class_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorators().add_err("Error parsing <Decorators>? for <ClassPrototype>").parse_optional()
            p2 = self._parse_token(TokenType.KwPart).add_err("Error parsing 'part'? for <ClassPrototype>").parse_optional()
            p3 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <ClassPrototype>").parse_optional()
            p4 = self._parse_token(TokenType.KwCls).add_err("Error parsing 'cls' for <ClassPrototype>").parse_once()
            p5 = self._parse_class_identifier().add_err("Error parsing <ClassIdentifier> for <ClassPrototype>").parse_once()
            p6 = self._parse_type_generic_parameters().add_err("Error parsing <TypeGenericParameters>? for <ClassPrototype>").parse_optional()
            p7 = self._parse_where_block().add_err("Error parsing <WhereBlock>? for <ClassPrototype>").parse_optional()
            p8 = self._parse_class_or_empty_implementation().add_err("Error parsing <ClassOrEmptyImplementation> for <ClassPrototype>").parse_once()
            return ClassPrototypeAst(p1, p3, p5, p6, p6, p7, p8)
        return BoundParser(self, inner)

    def _parse_class_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_or_empty_implementation_empty_prep().add_err("Error parsing ... | <ClassOrEmptyImplementationEmptyPrep> | ... for <ClassOrEmptyImplementation>").delay_parse()
            p2 = self._parse_class_or_empty_implementation_non_empty_prep().add_err("Error parsing ... | <ClassOrEmptyImplementationNonEmptyPrep> | ... for <ClassOrEmptyImplementation>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <ClassOrEmptyImplementation>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_class_or_empty_implementation_empty_prep(self):
        def inner():
            p1 = self._parse_empty_implementation().add_err("Error parsing <EmptyImplementation> for <ClassOrEmptyImplementationEmptyPrep>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_or_empty_implementation_non_empty_prep(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <ClassOrEmptyImplementationNonEmptyPrep>").parse_once()
            p2 = self._parse_indent().add_err("Error parsing <Indent> for <ClassOrEmptyImplementationNonEmptyPrep>").parse_once()
            p3 = self._parse_class_implementation().add_err("Error parsing <ClassImplementation> for <ClassOrEmptyImplementationNonEmptyPrep>").parse_once()
            p4 = self._parse_dedent().add_err("Error parsing <Dedent> for <ClassOrEmptyImplementationNonEmptyPrep>").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_class_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_member().add_err("Error parsing <ClassMember>+ for <ClassImplementation>").parse_one_or_more()
            return ClassImplementationAst(p1)
        return BoundParser(self, inner)

    def _parse_class_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_class_attribute().add_err("Error parsing ... | <ClassAttribute> | ... for <ClassMember>").delay_parse()
            p2 = self._parse_class_attribute_static().add_err("Error parsing ... | <ClassAttributeStatic> | ... for <ClassMember>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <ClassMember>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_class_attribute(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <ClassAttribute>").parse_optional()
            p2 = self._parse_token(TokenType.KwMut).add_err("Error parsing 'mut'? for <ClassAttribute>").parse_optional()
            p3 = self._parse_class_attribute_identifier().add_err("Error parsing <ClassAttributeIdentifier> for <ClassAttribute>").parse_once()
            p4 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <ClassAttribute>").parse_once()
            p5 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <ClassAttribute>").parse_once()
            p6 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <ClassAttribute>").parse_once()
            return ClassInstanceAttributeAst(p1, p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_class_attribute_static(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <ClassAttributeStatic>").parse_optional()
            p2 = self._parse_token(TokenType.KwMut).add_err("Error parsing 'mut'? for <ClassAttributeStatic>").parse_optional()
            p3 = self._parse_class_attribute_static_identifier().add_err("Error parsing <ClassAttributeStaticIdentifier> for <ClassAttributeStatic>").parse_once()
            p4 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <ClassAttributeStatic>").parse_once()
            p5 = self._parse_expression().add_err("Error parsing <Expression> for <ClassAttributeStatic>").parse_once()
            p6 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <ClassAttributeStatic>").parse_once()
            return ClassStaticAttributeAst(p1, p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_class_attribute_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <ClassAttributeIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_attribute_static_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <ClassAttributeStaticIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_class_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <ClassIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    # Super-Impositions

    def _parse_sup_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwSup).add_err("Error parsing 'sup' for <SupPrototype>").parse_once()
            p2 = self._parse_sup_prototype_normal().add_err("Error parsing ... | <SupPrototypeNormal> | ... for <SupPrototype>").delay_parse()
            p3 = self._parse_sup_prototype_with_inherit().add_err("Error parsing ... | <SupPrototypeWithInherit> | ... for <SupPrototype>").delay_parse()
            p4 = (p2 | p3).add_err("Error parsing selection for <SupPrototype>:").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_sup_prototype_normal(self):
        def inner():
            p5 = self._parse_type_generic_parameters().add_err("Error parsing <TypeGenericParameters>? for <SupPrototypeNormal>").parse_optional()
            p6 = self._parse_sup_identifier().add_err("Error parsing <SupIdentifier> for <SupPrototypeNormal>").parse_once()
            p7 = self._parse_where_block().add_err("Error parsing <WhereBlock>? for <SupPrototypeNormal>").parse_optional()
            p8 = self._parse_sup_or_empty_implementation().add_err("Error parsing <SupOrEmptyImplementation> for <SupPrototypeNormal>").parse_once()
            return SupPrototypeNormalAst(p5, p6, p7, p8)
        return BoundParser(self, inner)

    def _parse_sup_prototype_with_inherit(self):
        def inner():
            p5 = self._parse_type_generic_parameters().add_err("Error parsing <TypeGenericParameters>? for <SupPrototypeWithInheritance>").parse_optional()
            p6 = self._parse_sup_identifier().add_err("Error parsing <SupIdentifier> for <SupPrototypeWithInheritance>").parse_once()
            p7 = self._parse_token(TokenType.KwFor).add_err("Error parsing 'for' for <SupPrototypeWithInheritance>").parse_once()
            p8 = self._parse_sup_identifier().add_err("Error parsing <SupIdentifier> for <SupPrototypeWithInheritance>").parse_once()
            p9 = self._parse_where_block().add_err("Error parsing <WhereBlock>? for <SupPrototypeWithInheritance>").parse_optional()
            p10 = self._parse_sup_or_empty_implementation().add_err("Error parsing <SupOrEmptyImplementation> for <SupPrototypeWithInheritance>").parse_once()
            return SupPrototypeInheritanceAst(p5, p6, p8, p9, p10)
        return BoundParser(self, inner)

    def _parse_sup_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_or_empty_implementation_empty_prep().add_err("Error parsing ... | <SupOrEmptyImplementationEmptyPrep> | ... for <SupOrEmptyImplementation>").delay_parse()
            p2 = self._parse_sup_or_empty_implementation_non_empty_prep().add_err("Error parsing ... | <SupOrEmptyImplementationNonEmptyPrep> | ... for <SupOrEmptyImplementation>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <SupOrEmptyImplementation>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_sup_or_empty_implementation_empty_prep(self):
        def inner():
            p1 = self._parse_empty_implementation().add_err("Error parsing <EmptyImplementation> for <SupOrEmptyImplementationEmptyPrep>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_or_empty_implementation_non_empty_prep(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <SupOrEmptyImplementationNonEmptyPrep>").parse_once()
            p2 = self._parse_indent().add_err("Error parsing <Indent> for <SupOrEmptyImplementationNonEmptyPrep>").parse_once()
            p3 = self._parse_sup_implementation().add_err("Error parsing <SupImplementation> for <SupOrEmptyImplementationNonEmptyPrep>").parse_once()
            p4 = self._parse_dedent().add_err("Error parsing <Dedent> for <SupOrEmptyImplementationNonEmptyPrep>").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_sup_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_member().add_err("Error parsing <SupImplementation>+ for <SupImplementation>").parse_one_or_more()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_sup_method_prototype().add_err("Error parsing ... | <SupMethodPrototype> | ... for <SupMember>").delay_parse()
            p2 = self._parse_sup_typedef().add_err("Error parsing ... | <SupTypedef> | ... for <SupMember>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <SupMember>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_sup_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_static_scoped_generic_identifier().add_err("Error parsing <StatisScopedGenericIdentifier> for <SupIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_sup_typedef(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <SupTypedef>").parse_optional()
            p2 = self._parse_statement_typedef().add_err("Error parsing <StatementTypedef> for <SupTypedef>").parse_once()
            return SupTypedefAst(p1, p2.old_type, p2.new_type)
        return BoundParser(self, inner)

    def _parse_sup_method_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_prototype().add_err("Error parsing <FunctionPrototype> for <SupMethodPrototype>").parse_once()
            return SupMethodPrototypeAst(p1) # todo
        return BoundParser(self, inner)

    """ENUMS"""

    def _parse_enum_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <EnumPrototype>").parse_optional()
            p2 = self._parse_token(TokenType.KwEnum).add_err("Error parsing 'enum' for <EnumPrototype>").parse_once()
            p3 = self._parse_enum_identifier().add_err("Error parsing <EnumIdentifier> for <EnumPrototype>").parse_once()
            p4 = self._parse_enum_or_empty_implementation().add_err("Error parsing <EnumOrEmptyImplementation> for <EnumPrototype>").parse_once()
            return EnumPrototypeAst(p1, p3, p4)
        return BoundParser(self, inner)

    def _parse_enum_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_or_empty_implementation_empty_prep().add_err("Error parsing ... | <EnumOrEmptyImplementationEmptyPrep> | ... for <EnumOrEmptyImplementation>").delay_parse()
            p2 = self._parse_enum_or_empty_implementation_non_empty_prep().add_err("Error parsing ... | <EnumOrEmptyImplementationNoneEmptyPrep | ... for <EnumOrEmptyImplementation>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <EnumOrEmptyImplementation>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_enum_or_empty_implementation_empty_prep(self):
        def inner():
            p1 = self._parse_empty_implementation().add_err("Error parsing <EmptyImplementation> for <EnumOrEmptyImplementationEmptyPrep>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_enum_or_empty_implementation_non_empty_prep(self):
        def inner():
            p1 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <EnumOrEmptyImplementationNonEmptyPrep>").parse_once()
            p2 = self._parse_indent().add_err("Error parsing <Indent> for <EnumOrEmptyImplementationNonEmptyPrep>").parse_once()
            p3 = self._parse_enum_implementation().add_err("Error parsing <EnumImplementation> for <EnumOrEmptyImplementationNonEmptyPrep>").parse_once()
            p4 = self._parse_dedent().add_err("Error parsing <Dedent> for <EnumOrEmptyImplementationNonEmptyPrep>").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_enum_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_member().add_err("Error parsing <EnumMember> for <EnumImplementation>").parse_once()
            p2 = self._parse_enum_member_next().add_err("Error parsing <EnumMemberNext>* for <EnumImplementation>").parse_zero_or_more()
            p3 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <EnumImplementation>").parse_once()
            return EnumImplementationAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_enum_member_next(self):
        def inner():
            p4 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <EnumMemberNext>").parse_once()
            p5 = self._parse_enum_member().add_err("Error parsing <EnumMember> for <EnumMemberNext>").parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_enum_member(self) -> BoundParser:
        def inner():
            p1 = self._parse_enum_member_identifier().add_err("Error parsing <EnumMemberIdentifier> for <EnumMember>").parse_once()
            p2 = self._parse_enum_member_value_wrapper().add_err("Error parsing <EnumMemberValueWrapper>? for <EnumMember>").parse_optional()
            return EnumMemberAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_enum_member_value_wrapper(self):
        def inner():
            p3 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <EnumMemberValueWrapper>").parse_once()
            p4 = self._parse_enum_member_value().add_err("Error parsing <EnumMemberValue> for <EnumMemberValueWrapper>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_enum_member_value(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().add_err("Error parsing <Expression> for <EnumMemberValue>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_enum_member_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <EnumMemberIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_enum_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <EnumIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    # Function Prototype & Implementation

    def _parse_function_prototype(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorators().add_err("Error parsing <Decorators>? for <FunctionPrototype>").parse_optional()
            p2 = self._parse_access_modifier().add_err("Error parsing <AccessModifier>? for <FunctionPrototype>").parse_optional()
            p3 = self._parse_token(TokenType.KwAsync).add_err("Error parsing 'async'? for <FunctionPrototype>").parse_optional()
            p4 = self._parse_token(TokenType.KwFun).add_err("Error parsing 'fun' for <FunctionPrototype>").parse_once()
            p5 = self._parse_function_identifier().add_err("Error parsing <FunctionIdentifier> for <FunctionPrototype>").parse_once()
            p6 = self._parse_type_generic_parameters().add_err("Error parsing <TypeGenericParameters>? for <FunctionPrototype>").parse_optional()
            p7 = self._parse_function_parameters().add_err("Error parsing <FunctionParameters> for <FunctionPrototype>").parse_once()
            p8 = self._parse_token(TokenType.TkRightArrow).add_err("Error parsing '->' for <FunctionPrototype>").parse_once()
            p9 = self._parse_type_identifiers().add_err("Error parsing <TypeIdentifiers> for <FunctionPrototype>").parse_once()
            p10 = self._parse_where_block().add_err("Error parsing <WhereBlock>? for <FunctionPrototype>").parse_optional()
            p11 = self._parse_value_guard().add_err("Error parsing <ValueGuard>? for <FunctionPrototype>").parse_optional()
            p12 = self._parse_function_or_empty_implementation().add_err("Error parsing <FunctionOrEmptyImplementation> for <FunctionPrototype>").parse_once()
            return FunctionPrototypeAst(p1, p2, p3, p5, p6, p7, p9, p10, p11, p12)
        return BoundParser(self, inner)

    def _parse_function_or_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_or_empty_implementation_empty_prep().add_err("Error parsing <FunctionOrEmptyImplementationEmptyPrep> for <FunctionOrEmptyImplementation>").delay_parse()
            p2 = self._parse_function_or_empty_implementation_non_empty_prep().add_err("Error parsing <FunctionOrEmptyImplementationNonEmptyPrep> for <FunctionOrEmptyImplementation>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <FunctionOrEmptyImplementation>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_or_empty_implementation_empty_prep(self):
        def inner():
            p4 = self._parse_empty_implementation().add_err("Error parsing <EmptyImplementation> for <FunctionOrEmptyImplementationPrep>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_function_or_empty_implementation_non_empty_prep(self):
        def inner():
            p4 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <FunctionOrEmptyImplementationNonEmptyPrep>").parse_once()
            p5 = self._parse_indent().add_err("Error parsing <Indent> for <FunctionOrEmptyImplementationNonEmptyPrep>").parse_once()
            p6 = self._parse_function_implementation().add_err("Error parsing <FunctionImplementation> for <FunctionOrEmptyImplementationNonEmptyPrep>").parse_once()
            p7 = self._parse_dedent().add_err("Error parsing <Dedent> for <FunctionOrEmptyImplementationNonEmptyPrep>").parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_function_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement().add_err("Error parsing <Statement>+ for <FunctionImplementation>").parse_one_or_more()
            return FunctionImplementationAst(p1)
        return BoundParser(self, inner)

    def _parse_function_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <FunctionIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    # Function Call Arguments

    def _parse_function_call_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).add_err("Error parsing '(' for <FunctionCallArguments>").parse_once()
            p2 = self._parse_function_call_arguments_normal_then_named().add_err("Error parsing <FunctionCallArgumentsNormalThenNamed>? for <FunctionCallArguments>").parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightParenthesis).add_err("Error parsing ')' for <FunctionCallArguments>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_arguments_normal_then_named(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_call_normal_arguments().add_err("Error parsing ... | <FunctionCallNormalArguments> | ... for <FunctionCallArgumentsNormalThenNamed>").delay_parse()
            p2 = self._parse_function_call_named_arguments().add_err("Error parsing ... | <FunctionCallNamedArguments> | ... for <FunctionCallArgumentsNormalThenNamed>").delay_parse()
            p3 = (p2 | p1).add_err("Error parsing selection for <FunctionCallArgumentsNormalThenNamed>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_call_normal_arguments(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_call_normal_argument().add_err("Error parsing <FunctionCallNormalArgument> for <FunctionCallNormalArguments>").parse_once()
            p4 = self._parse_function_call_rest_of_normal_arguments().add_err("Error parsing <FunctionCallRestOfNormalArguments>? for <FunctionCallNormalArguments>").parse_optional()
            return [p3, p4]
        return BoundParser(self, inner)

    def _parse_function_call_rest_of_normal_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <FunctionCallRestOfNormalArguments>").parse_once()
            p2 = self._parse_function_call_arguments_normal_then_named().add_err("Error parsing <FunctionCallArgumentsNormalThenNamed> for <FunctionCallRestOfNormalArguments>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_named_arguments(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_call_named_argument().add_err("Error parsing <FunctionCallNamedArgument> for <FunctionCallNamedArguments>").parse_once()
            p4 = self._parse_function_call_next_named_argument().add_err("Error parsing <FunctionCallNextNamedArgument>* for <FunctionCallNamedArguments>").parse_zero_or_more()
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_function_call_next_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <FunctionCallNextNamedArgument>").parse_once()
            p2 = self._parse_function_call_named_argument().add_err("Error parsing <FunctionCallNamedArgument> for <FunctionCallNextNamedArgument>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_call_normal_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().add_err("Error parsing <Expression> for <FunctionCallNormalArgument>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_function_call_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <FunctionCallNamedArgument>").parse_once()
            p2 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <FunctionCallNamedArgument>").parse_once()
            p3 = self._parse_expression().add_err("Error parsing <Expression> for <FunctionCallNamedArgument>").parse_once()
            return FunctionArgumentNamedAst(p1, p3)
        return BoundParser(self, inner)

    # Function Parameters

    def _parse_function_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).add_err("Error parsing '(' for <FunctionParameters>").parse_once()
            p2 = self._parse_function_parameters_required_then_optional().add_err("Error parsing <FunctionParametersRequiredThenOptional>? for <FunctionParameters>").parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightParenthesis).add_err("Error parsing ')' for <FunctionParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_parameters_required_then_optional(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_required_parameters().add_err("Error parsing ... | <FunctionRequiredParameters> | ... for <FunctionParametersRequiredThenOptional>").delay_parse()
            p2 = self._parse_function_optional_parameters().add_err("Error parsing ... | <FunctionOptionalParameters> | ... for <FunctionParametersRequiredThenOptional>").delay_parse()
            p3 = self._parse_function_variadic_parameter().add_err("Error parsing ... | <FunctionVariadicParameter> | ... for <FunctionParametersRequiredThenOptional>").delay_parse()
            p4 = (p3 | p2 | p1).add_err("Error parsing selection for <FunctionParametersRequiredThenOptional>:").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_function_parameters_optional_then_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_optional_parameters().add_err("Error parsing ... | <FunctionOptionalParameters> | ... for <FunctionParametersOptionalThenVariadic>").delay_parse()
            p2 = self._parse_function_variadic_parameter().add_err("Error parsing ... | <FunctionVariadicParameter> | ... for <FunctionParametersOptionalThenVariadic>").delay_parse()
            p3 = (p2 | p1).add_err("Error parsing selection for <FunctionParametersOptionalThenVariadic>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_function_required_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_required_parameter().add_err("Error parsing <FunctionRequiredParameter> for <FunctionRequiredParameters>").parse_once()
            p4 = self._parse_function_rest_of_required_parameters().add_err("Error parsing <FunctionRestOfRequiredParameters>? for <FunctionRequiredParameters>").parse_optional()
            return [p3, p4]
        return BoundParser(self, inner)

    def _parse_function_rest_of_required_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <FunctionRestOfRequiredParameters>").parse_once()
            p2 = self._parse_function_parameters_required_then_optional().add_err("Error parsing <FunctionParametersRequiredThenOptional> for <FunctionRestOfRequiredParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_optional_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_function_optional_parameter().add_err("Error parsing <FunctionOptionalParameter> for <FunctionOptionalParameters>").parse_once()
            p4 = self._parse_function_rest_of_optional_parameters().add_err("Error parsing <FunctionRestOfOptionalParameters>? for <FunctionOptionalParameters>").parse_optional()
            return [p3, p4]
        return BoundParser(self, inner)

    def _parse_function_rest_of_optional_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <FunctionRestOfOptionalParameters>").parse_once()
            p2 = self._parse_function_parameters_optional_then_variadic().add_err("Error parsing <FunctionParametersOptionalThenVariadic> for <FunctionRestOfOptionalParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_function_required_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMut).add_err("Error parsing 'mut'? for <FunctionRequiredParameter>").parse_optional()
            p2 = self._parse_function_parameter_identifier().add_err("Error parsing <FunctionParameterIdentifier> for <FunctionRequiredParameter>").parse_once()
            p3 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <FunctionRequiredParameter>").parse_once()
            p4 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <FunctionRequiredParameter>").parse_once()
            return FunctionParameterRequiredAst(p1 is not None, p2, p4)
        return BoundParser(self, inner)

    def _parse_function_optional_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_function_required_parameter().add_err("Error parsing <FunctionRequiredParameter> for <FunctionOptionalParameter>").parse_once()
            p2 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <FunctionOptionalParameter>").parse_once()
            p3 = self._parse_expression().add_err("Error parsing <Expression> for <FunctionOptionalParameter>").parse_once()
            return FunctionParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_function_variadic_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).add_err("Error parsing '...' for <FunctionVariadicParameter>").parse_once()
            p2 = self._parse_function_required_parameter().add_err("Error parsing <FunctionRequiredParameter> for <FunctionVariadicParameter>").parse_once()
            return FunctionParameterVariadicAst(p2)
        return BoundParser(self, inner)

    def _parse_function_parameter_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <FunctionParameterIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    # Type Constraints & Value Guard

    def _parse_where_block(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWhere).add_err("Error parsing 'where' for <WhereBlock>").parse_once()
            p2 = self._parse_token(TokenType.TkLeftBracket).add_err("Error parsing '[' for <WhereBlock>").parse_once()
            p3 = self._parse_where_constraints().add_err("Error parsing <WhereConstraints> for <WhereBlock>").parse_once()
            p4 = self._parse_token(TokenType.TkRightBracket).add_err("Error parsing ']' for <WhereBlock>").parse_once()
            return WhereBlockAst(p3)
        return BoundParser(self, inner)

    def _parse_where_constraints(self) -> BoundParser:
        def inner():
            p1 = self._parse_where_constraint().add_err("Error parsing <WhereConstraint> for <WhereConstraints>").parse_once()
            p2 = self._parse_where_constraint_next().add_err("Error parsing <WhereConstraintNext>* for <WhereConstraints>").parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_where_constraint_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <WhereConstraintNext>").parse_once()
            p4 = self._parse_where_constraint().add_err("Error parsing <WhereConstraint> for <WhereConstraintNext>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_where_constraint(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifiers().add_err("Error parsing <TypeIdentifiers> for <WhereConstraint>").parse_once()
            p2 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <WhereConstraint>").parse_once()
            p3 = self._parse_where_constraint_chain().add_err("Error parsing <WhereConstraintChain> for <WhereConstraint>").parse_once()
            return WhereConstraintAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_where_constraint_chain(self) -> BoundParser:
        def inner():
            p3 = self._parse_where_constraint_chain_element().add_err("Error parsing <WhereConstraintChainElement> for <WhereConstraintChain>").parse_once()
            p4 = self._parse_where_constraint_chain_element_next().add_err("Error parsing <WhereConstraintChainElementNext>* for <WhereConstraintChain>").parse_zero_or_more()
            return [p3, *p4]
        return BoundParser(self, inner)

    def _parse_where_constraint_chain_element_next(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkPlus).add_err("Error parsing '+' for <WhereConstraintChainElementNext>").parse_once()
            p2 = self._parse_where_constraint_chain_element().add_err("Error parsing <WhereConstraintChainElement> for <WhereConstraintChainElementNext>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_where_constraint_chain_element(self) -> BoundParser:
        def inner():
            p1 = self._parse_static_scoped_generic_identifier().add_err("Error parsing <StaticScopedGenericIdentifier> for <WhereConstraintChainElement>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_value_guard(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwIf).add_err("Error parsing 'if' for <ValueGuard>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <ValueGuard>").parse_once()
            return ValueGuardAst(p2)
        return BoundParser(self, inner)

    # Decorators

    def _parse_decorator(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAt).add_err("Error parsing '@' for <Decorator>").parse_once()
            p2 = self._parse_decorator_identifier().add_err("Error parsing <DecoratorIdentifier> for <Decorator>").parse_once()
            p3 = self._parse_type_generic_arguments().add_err("Error parsing <TypeGenericArguments>? for <Decorator>").parse_optional()
            p4 = self._parse_function_call_arguments().add_err("Error parsing <FunctionCallArguments>? for <Decorator>").parse_optional()
            return DecoratorAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_decorators(self) -> BoundParser:
        def inner():
            p1 = self._parse_decorator().add_err("Error parsing <Decorator> for <Decorators>").parse_once()
            p2 = self._parse_decorator_next().add_err("Error parsing <DecoratorNext>* for <Decorators>").parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_decorator_next(self):
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <DecoratorNext>").parse_once()
            p4 = self._parse_decorator().add_err("Error parsing <Decorator> for <DecoratorNext>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_decorator_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_static_scoped_generic_identifier().add_err("Error parsing <StaticScopedGenericIdentifier> for <DecoratorIdentifier>").parse_once()
            return p1
        return BoundParser(self, inner)

    # Expressions

    def _parse_expressions(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().add_err("Error parsing <Expression> for <Expressions>").parse_once()
            p2 = self._parse_expression_next().add_err("Error parsing <ExpressionNext>* for <Expressions>").parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_expression_next(self):
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <ExpressionNext>").parse_once()
            p4 = self._parse_expression().add_err("Error parsing <Expression> for <ExpressionNext>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_assignment_expression().add_err("Error parsing <AssignmentExpression> for <Expression>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_assignment_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_assignment_single().add_err("Error parsing ... | <AssignmentSingle> | ... for <AssignmentExpression>").delay_parse()
            p2 = self._parse_assignment_multiple().add_err("Error parsing ... | <AssignmentMultiple> | ... for <AssignmentExpression>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <AssignmentExpression>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_assignment_multiple(self) -> BoundParser:
        def inner():
            p4 = self._parse_null_coalescing_expression().add_err("Error parsing <NullCoalescingExpression> for <AssignmentMultiple>").parse_once()
            p5 = self._parse_assignment_multiple_lhs().add_err("Error parsing <AssignmentMultipleLhs>* for <AssignmentMultiple>").parse_zero_or_more()
            p6 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <AssignmentMultiple>").parse_once()
            p7 = self._parse_assignment_expression().add_err("Error parsing <AssignmentExpression> for <AssignmentMultiple>").parse_once()
            p8 = self._parse_assignment_multiple_rhs().add_err("Error parsing <AssignmentMultipleRhs>* for <AssignmentMultiple>").parse_zero_or_more()
            return MultiAssignmentExpressionAst([p4, *p5], [p7, *p8])
        return BoundParser(self, inner)

    def _parse_assignment_multiple_lhs(self) -> BoundParser:
        def inner():
            p9 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <AssignmentMultipleLhs>").parse_once()
            p10 = self._parse_null_coalescing_expression().add_err("Error parsing <NullCoalescingExpression> for <AssignmentMultipleLhs>").parse_once()
            return p10
        return BoundParser(self, inner)

    def _parse_assignment_multiple_rhs(self) -> BoundParser:
        def inner():
            p9 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <AssignmentMultipleRhs>").parse_once()
            p10 = self._parse_assignment_expression().add_err("Error parsing <AssignmentExpression> for <AssignmentMultipleRhs>").parse_once()
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
            p1 = self._parse_operator_identifier_unary().add_err("Error parsing <OperatorIdentifierUnary>* for <UnaryExpression>").parse_zero_or_more()
            p2 = self._parse_postfix_expression().add_err("Error parsing <PostfixExpression> for <UnaryExpression>").parse_once()
            for op in reversed(p1):
                p2 = UnaryExpressionAst(op, p2)
            return p2
        return BoundParser(self, inner)

    def _parse_postfix_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_primary_expression().add_err("Error parsing <PrimaryExpression> for <PostfixExpression>").parse_once()
            p2 = self._parse_operator_identifier_postfix().add_err("Error parsing <OperatorIdentifierPostfix>* for <PostfixExpression>").parse_zero_or_more()
            for op in p2:
                p1 = PostfixExpressionAst(p1, op)
            return p1
        return BoundParser(self, inner)

    def _parse_primary_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <PrimaryExpression>").delay_parse()
            p2 = self._parse_lambda().add_err("Error parsing <Lambda> for <PrimaryExpression>").delay_parse()
            p3 = self._parse_literal().add_err("Error parsing <Literal> for <PrimaryExpression>").delay_parse()
            p4 = self._parse_static_scoped_generic_identifier().add_err("Error parsing StaticScopedGenericIdentifier for <PrimaryExpression>").delay_parse()
            p5 = self._parse_parenthesized_expression().add_err("Error parsing <ParenthesizedExpression> for <PrimaryExpression>").delay_parse()
            p6 = self._parse_expression_placeholder().add_err("Error parsing <ExpressionPlaceholder> for <PrimaryExpression>").delay_parse()
            p7 = (p1 | p2 | p3 | p4 | p5 | p6).add_err("Error parsing selection for <PrimaryExpression>").parse_once()
            return p7
        return BoundParser(self, inner)

    def _parse_binary_expression(self, __lhs, __op, __rhs) -> BoundParser:
        def inner(lhs, op, rhs):
            p1 = lhs.add_err("Error parsing LHS of binary op").parse_once()
            p2 = self._parse_binary_expression_rhs(op, rhs).parse_optional()
            return p1 if p2 is None else BinaryExpressionAst(p1, p2[0], p2[1])
        return BoundParser(self, functools.partial(inner, __lhs, __op, __rhs))

    def _parse_binary_expression_rhs(self, __op, __rhs) -> BoundParser:
        def inner(op, rhs):
            p3 = op.add_err("Error parsing OP of binary op").parse_once()
            p4 = rhs().add_err("Error parsing RHS of binary op").parse_once()
            return p3, p4
        return BoundParser(self, functools.partial(inner, __op, __rhs))

    def _parse_parenthesized_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).add_err("Error parsing '(' for <ParenthesizedExpression>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <ParenthesizedExpression>").parse_once()
            p3 = self._parse_token(TokenType.TkRightParenthesis).add_err("Error parsing ')' for <ParenthesizedExpression>").parse_once()
            return ParenthesizedExpressionAst(p2)
        return BoundParser(self, inner)

    def _parse_expression_placeholder(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkUnderscore).add_err("Error parsing '_' for <ExpressionPlaceholder>").parse_once()
            return PlaceholderAst()
        return BoundParser(self, inner)

    # Lambda

    def _parse_lambda(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwAsync).add_err("Error parsing 'async'? for <Lambda>").parse_optional()
            p2 = self._parse_lambda_capture_list().add_err("Error parsing <LambdaCaptureList>? for <Lambda>").parse_optional()
            p3 = self._parse_lambda_parameters().add_err("Error parsing <LambdaParameters> for <Lambda>").parse_once()
            p4 = self._parse_token(TokenType.TkRightArrow).add_err("Error parsing '->' for <Lambda>").parse_once()
            p5 = self._parse_lambda_implementation().add_err("Error parsing <LambdaImplementation> for <Lambda>").parse_once()
            return LambdaAst(p1, p2, p3, p5)
        return BoundParser(self, inner)

    def _parse_lambda_capture_list(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).add_err("Error parsing '[' for <LambdaCaptureList>").parse_once()
            p2 = self._parse_lambda_capture_item().add_err("Error parsing <LambdaCaptureItem> for <LambdaCaptureList>").parse_once()
            p3 = self._parse_lambda_capture_item_next().add_err("Error parsing <LambdaCaptureItemNext>* for <LambdaCaptureList>").parse_zero_or_more()
            p4 = self._parse_token(TokenType.TkRightBracket).add_err("Error parsing ']' for <LambdaCaptureList>").parse_once()
            return [p2, *p3]
        return BoundParser(self, inner)

    def _parse_lambda_capture_item_next(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <LambdaCaptureItemNext>").parse_once()
            p6 = self._parse_lambda_capture_item().add_err("Error parsing <LambdaCaptureItem> for <LambdaCaptureItemNext>").parse_once()
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
            p1 = self._parse_unary_operator_reference().add_err("Error parsing <UnaryOperatorReference> for <TypeIdentifier>").parse_optional()
            p2 = self._parse_static_scoped_generic_identifier().add_err("Error parsing <StaticScopedGenericIdentifier> for <TypeIdentifier>").parse_once()
            return TypeAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_type_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <TypeIdentifiers>").parse_once()
            p2 = self._parse_type_identifier_next().add_err("Error parsing <TypeIdentifierNext>* for <TypeIdentifiers>").parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_identifier_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <TypeIdentifierNext>").parse_once()
            p4 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <TypeIdentifierNext>").parse_once()
            return p4
        return BoundParser(self, inner)

    # Type Generic Arguments

    def _parse_type_generic_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftAngleBracket).add_err("Error parsing '<' for <TypeGenericArguments>").parse_once()
            p2 = self._parse_type_generic_arguments_normal_then_named().add_err("Error parsing <TypeGenericArgumentsNormalThenNamed>? for <TypeGenericArguments>").parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightAngleBracket).add_err("Error parsing '>' for <TypeGenericArguments>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_arguments_normal_then_named(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_normal_arguments().add_err("Error parsing ... | <TypeGenericNormalArguments | ... for <TypeGenericArgumentsNormalThenNamed>").delay_parse()
            p2 = self._parse_type_generic_named_arguments().add_err("Error parsing ... | <TypeGenericNamedArguments | ... for <TypeGenericArgumentsNormThenNamed>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <TypeGenericArgumentsNormalThenNamed>").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_generic_normal_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_normal_argument().add_err("Error parsing <TypeGenericNormalArgument> for <TypeGenericNormalArguments>").parse_once()
            p2 = self._parse_type_generic_rest_of_normal_arguments().add_err("Error parsing <TypeGenericRestOfNormalArguments>? for <TypeGenericNormalArguments>").parse_optional()
            return [p1, p2]
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_normal_arguments(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <TypeGenericRestOfNormalArguments>").parse_once()
            p4 = self._parse_type_generic_arguments_normal_then_named().add_err("Error parsing <TypeGenericArgumentsNormalThenNamed> for <TypeGenericRestOfNormalArguments>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_named_arguments(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_named_argument().add_err("Error parsing <TypeGenericNamedArgument> for <TypeGenericNamedArguments>").parse_once()
            p2 = self._parse_type_generic_next_named_argument().add_err("Error parsing <TypeGenericNextNamedArgument>* for <TypeGenericNamedArguments>").parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_type_generic_next_named_argument(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <TypeGenericNextNamedArgument>").parse_once()
            p4 = self._parse_type_generic_named_argument().add_err("Error parsing <TypeGenericNamedArgument> for <TypeGenericNextNamedArgument>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_normal_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <TypeGenericNormalArgument>").parse_once()
            return TypeGenericArgumentNormalAst(p1)
        return BoundParser(self, inner)

    def _parse_type_generic_named_argument(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <TypeGenericNamedArgument>").parse_once()
            p2 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <TypeGenericNamedArgument>").parse_once()
            p3 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <TypeGenericNamedArgument>").parse_once()
            return TypeGenericArgumentNamedAst(p1, p3)
        return BoundParser(self, inner)

    # Type Generic Parameters

    def _parse_type_generic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftAngleBracket).add_err("Error parsing '<' for <TypeGenericParameters>").parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().add_err("Error parsing <TypeGenericParametersRequiredThenOptional> for <TypeGenericParameters>").parse_optional() or []
            p3 = self._parse_token(TokenType.TkRightAngleBracket).add_err("Error parsing '>' for <TypeGenericParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_parameters_required_then_optional(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_required_parameters().add_err("Error parsing ... | <TypeGenericRequiredParameters> | ... for <TypeGenericParametersRequiredThenOptional>").delay_parse()
            p2 = self._parse_type_generic_optional_parameters().add_err("Error parsing ... | <TypeGenericOptionalParameters> | ... for <TypeGenericParametersRequiredThenOptional>").delay_parse()
            p3 = self._parse_type_generic_variadic_parameters().add_err("Error parsing ... | <TypeGenericVariadicParameters> | ... for <TypeGenericParametersRequiredThenOptional>").delay_parse()
            p4 = (p3 | p2 | p1).add_err("Error parsing selection for <TypeGenericParametersRequiredThenOptional>:").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_type_generic_parameters_optional_then_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_optional_parameters().add_err("Error parsing ... | <TypeGenericOptionalParameters> | ... for <TypeGenericParametersOptionalThenVariadic>").delay_parse()
            p2 = self._parse_type_generic_variadic_parameters().add_err("Error parsing ... | <TypeGenericVariadicParameters> | ... for <TypeGenericParametersOptionalThenVariadic>").delay_parse()
            p3 = (p2 | p1).add_err("Error parsing selection for <TypeGenericParametersOptionalThenVariadic>:").parse_once()
            return p3
        return BoundParser(self, inner)

    def _parse_type_generic_required_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_type_generic_required_parameter().add_err("Error parsing <TypeGenericRequiredParameter> for <TypeGenericRequiredParameters>").parse_once()
            p4 = self._parse_type_generic_rest_of_required_parameters().add_err("Error parsing <TypeGenericRestOfRequiredParameters>? for <TypeGenericRequiredParameters>").parse_optional()
            return [p3, p4]
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_required_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <TypeGenericRestOfRequiredParameters>").parse_once()
            p2 = self._parse_type_generic_parameters_required_then_optional().add_err("Error parsing <TypeGenericParametersRequiredThenOptional> for <TypeGenericRestOfRequiredParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_optional_parameters(self) -> BoundParser:
        def inner():
            p3 = self._parse_type_generic_optional_parameter().add_err("Error parsing <TypeGenericOptionalParameter> for <TypeGenericOptionalParameters>").parse_once()
            p4 = self._parse_type_generic_rest_of_optional_parameters().add_err("Error parsing <TypeGenericRestOfOptionalParameters>? for <TypeGenericOptionalParameters>").parse_optional()
            return [p3, p4]
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_optional_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <TypeGenericRestOfOptionalParameters>").parse_once()
            p2 = self._parse_type_generic_parameters_optional_then_variadic().add_err("Error parsing <TypeGenericParametersOptionalThenVariadic> for <TypeGenericRestOfOptionalParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_required_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().add_err("Error parsing <Identifier> for <TypeGenericRequiredParameter>").parse_once()
            p2 = self._parse_type_generic_parameter_inline_constraint().add_err("Error parsing <TypeGenericParameterInlineConstraint>? for <TypeGenericRequiredParameter>").parse_optional()
            return TypeGenericParameterRequiredAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_type_generic_optional_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_required_parameter().add_err("Error parsing <TypeGenericRequiredParameter> for <TypeGenericOptionalParameter>").parse_once()
            p2 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <TypeGenericOptionalParameter>").parse_once()
            p3 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <TypeGenericOptionalParameter>").parse_once()
            return TypeGenericParameterOptionalAst(p1, p3)
        return BoundParser(self, inner)

    def _parse_type_generic_variadic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_type_generic_variadic_parameter().add_err("Error parsing <TypeGenericVariadicParameter> for <TypeGenericVariadicParameters>").parse_once()
            p2 = self._parse_type_generic_rest_of_variadic_parameters().add_err("Error parsing <TypeGenericRestOfVariadicParameters>? for <TypeGenericVariadicParameters>").parse_optional()
            return [p1, p2]
        return BoundParser(self, inner)

    def _parse_type_generic_variadic_parameter(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).add_err("Error parsing '...' for <TypeGenericVariadicParameter>").parse_once()
            p2 = self._parse_type_generic_required_parameter().add_err("Error parsing <TypeGenericRequiredParameter> for <TypeGenericVariadicParameter>").parse_once()
            return TypeGenericParameterVariadicAst(p2)
        return BoundParser(self, inner)

    def _parse_type_generic_rest_of_variadic_parameters(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <TypeGenericRestOfVariadicParameters>").parse_once()
            p2 = self._parse_type_generic_variadic_parameter().add_err("Error parsing <TypeGenericVariadicParameter> for <TypeGenericRestOfVariadicParameters>").parse_once()
            return p2
        return BoundParser(self, inner)

    def _parse_type_generic_parameter_inline_constraint(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <TypeGenericParameterInlineConstraint>").parse_once()
            p4 = self._parse_where_constraint_chain().add_err("Error parsing <WhereConstraintChain> for <TypeGenericParameterInlineConstraint>").parse_once()
            return p4
        return BoundParser(self, inner)

    # Statements

    def _parse_statement_inline_definitions(self) -> BoundParser:
        def inner():
            p5 = self._parse_statement_let().add_err("Error parsing <StatementLet> for <StatementInlineDefinitions>").parse_once()
            p6 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <StatementInlineDefinitions>").parse_once()
            return p5
        return BoundParser(self, inner)

    def _parse_statement_if(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_if_branch().add_err("Error parsing <StatementIfBranch> for <StatementIf>").parse_once()
            p5 = self._parse_statement_elif_branch().add_err("Error parsing <StatementElifBranch> for <StatementIf>").parse_zero_or_more()
            p6 = self._parse_statement_else_branch().add_err("Error parsing <StatementElseBranch> for <StatementIf>").parse_optional()
            return IfStatementAst(p1, p5, p6)
        return BoundParser(self, inner)

    def _parse_statement_if_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwIf).add_err("Error parsing 'if' for <StatementIfBranch>").parse_once()
            p2 = self._parse_statement_inline_definitions().add_err("Error parsing <StatementInlineDefinitions>* for <StatementIfBranch>").parse_zero_or_more()
            p3 = self._parse_expression().add_err("Error parsing <Expression> for <StatementIfBranch>").parse_once()
            p4 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementIfBranch>").parse_once()
            return IfStatementBranchAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_elif_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwElif).add_err("Error parsing 'elif' for <StatementElifBranch>").parse_once()
            p2 = self._parse_statement_inline_definitions().add_err("Error parsing <StatementInlineDefinitions>* for <StatementElifBranch>").parse_zero_or_more()
            p3 = self._parse_expression().add_err("Error parsing <Expression> for <StatementElifBranch>").parse_once()
            p4 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementElifBranch>").parse_once()
            return ElifStatementBranchAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_else_branch(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwElse).add_err("Error parsing 'else' for <StatementElseBranch>").parse_once()
            p2 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementElseBranch>").parse_once()
            return ElseStatementBranchAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_while(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWhile).add_err("Error parsing 'while' for <StatementWhileLoop>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <StatementWhileLoop>").parse_once()
            p3 = self._parse_statement_loop_tag().add_err("Error parsing <StatementLoopTag>? for <StatementWhile>").parse_optional()
            p4 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementWhile>").parse_once()
            return WhileStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_for(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwFor).add_err("Error parsing 'for' for <StatementFor>").parse_once()
            p2 = self._parse_local_variable_identifiers().add_err("Error parsing <LocalVariableIdentifiers> for <StatementFor>").parse_once()
            p3 = self._parse_token(TokenType.KwIn).add_err("Error parsing 'in' for <StatementFor>").parse_once()
            p4 = self._parse_expression().add_err("Error parsing <Expression> for <StatementFor>").parse_once()
            p5 = self._parse_statement_loop_tag().add_err("Error parsing <StatementLoopTag>? for <StatementFor>").parse_optional()
            p6 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementFor>").parse_once()
            return ForStatementAst(p2, p4, p5, p6)
        return BoundParser(self, inner)

    def _parse_statement_do(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwDo).add_err("Error parsing 'do' for <StatementDo>").parse_once()
            p2 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementDo>").parse_once()
            p3 = self._parse_token(TokenType.KwWhile).add_err("Error parsing 'while' for <StatementDo>").parse_once()
            p4 = self._parse_expression().add_err("Error parsing <Expression> for <StatementDo>").parse_once()
            p5 = self._parse_statement_loop_tag().add_err("Error parsing <StatementLoopTag>? for <StatementDo>").parse_optional()
            return DoWhileStatementAst(p2, p4, p5)
        return BoundParser(self, inner)

    def _parse_statement_match(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMatch).add_err("Error parsing 'match' for <StatementMatch>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <StatementMatch>").parse_once()
            p3 = self._parse_statement_cases().add_err("Error parsing <StatementCases> for <StatementMatch>").parse_once()
            return MatchStatementAst(p2, p3)
        return BoundParser(self, inner)

    def _parse_statement_case(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwCase).add_err("Error parsing 'case' for <StatementCase>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <StatementCase>").parse_once()
            p3 = self._parse_value_guard().add_err("Error parsing <ValueGuard>? for <StatementCase>").parse_optional()
            p4 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementCase>").parse_once()
            return CaseStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_case_default(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwCase).add_err("Error parsing 'case' for <StatementCaseDefault>").parse_once()
            p2 = self._parse_expression_placeholder().add_err("Error parsing <ExpressionPlaceholder> for <StatementCaseDefault>").parse_once()
            p3 = self._parse_value_guard().add_err("Error parsing <ValueGuard>? for <StatementCaseDefault>").parse_optional()
            p4 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementCaseDefault>").parse_once()
            return CaseStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_with(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwWith).add_err("Error parsing 'with' for <StatementWith>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <StatementWith>").parse_once()
            p3 = self._parse_statement_with_expression_alias().add_err("Error parsing <StatementWithExpressionAlias>? for <StatementWith>").parse_optional()
            p4 = self._parse_statement_block().add_err("Error parsing <StatementBlock> for <StatementWith>").parse_once()
            return WithStatementAst(p2, p3, p4)
        return BoundParser(self, inner)

    def _parse_statement_with_expression_alias(self) -> BoundParser:
        def inner():
            p5 = self._parse_token(TokenType.KwAs).add_err("Error parsing 'as' for <StatementWithExpressionAlias>").parse_once()
            p6 = self._parse_local_variable_identifier().add_err("Error parsing <LocalVariableIdentifier> for <StatementWithExpressionAlias>").parse_once()
            return p6
        return BoundParser(self, inner)

    def _parse_statement_return(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwReturn).add_err("Error parsing 'return' for <StatementReturn>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing <Expression> for <StatementReturn>").parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <StatmentReturn>").parse_once()
            return ReturnStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_yield(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwYield).add_err("Error parsing 'yield' for <StatementYield>").parse_once()
            p2 = self._parse_expression().add_err("Error parsing 'yield' for <StatementYield>").parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <StatementYield>").parse_once()
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
            p1 = self._parse_token(TokenType.KwBreak).add_err("Error parsing 'break' for <StatementBreak>").parse_once()
            p2 = self._parse_statement_loop_tag().add_err("Error parsing <StatementLoopTag>? for <StatementBreak>").parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';'? for <StatementBreak>").parse_once()
            return BreakStatementAst(p2)
        return BoundParser(self, inner)

    def _parse_statement_continue(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwContinue).add_err("Error parsing 'continue' for <StatementContinue>").parse_once()
            p2 = self._parse_statement_loop_tag().add_err("Error parsing <StatementLoopTag>? for <StatementContinue>").parse_optional()
            p3 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <StatementContinue>").parse_once()
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
            p1 = self._parse_token(TokenType.KwLet).add_err("Error parsing 'let' for <StatementLet>").parse_once()
            p2 = self._parse_local_variable_identifier().add_err("Error parsing <LocalVariableIdentifiers> for <StatementLet>").parse_once()
            p3 = self._parse_statement_let_type_annotation().add_err("Error parsing <StatementLetTypeAnnotation> for <StatementLet>").delay_parse()
            p4 = self._parse_statement_let_value().add_err("Error parsing <StatementLetValue> for <StatementLet>").delay_parse()
            p5 = (p3 | p4).add_err("Error parsing selection for <StatementLet>").parse_once()
            return LetStatementAst(p2, [], p5) if isinstance(p5, TypeAst) else LetStatementAst(p2, p5, None)
        return BoundParser(self, inner)

    def _parse_statement_let_value(self) -> BoundParser:
        def inner():
            p6 = self._parse_token(TokenType.TkEqual).add_err("Error parsing '=' for <StatementLetValue>").parse_once()
            p7 = self._parse_expressions().add_err("Error parsing <Expressions> for <StatementLetValue>").parse_once()
            return p7
        return BoundParser(self, inner)

    def _parse_statement_let_type_annotation(self) -> BoundParser:
        def inner():
            p6 = self._parse_token(TokenType.TkColon).add_err("Error parsing ':' for <StatementLetTypeAnnotation>").parse_once()
            p7 = self._parse_type_identifier().add_err("Error parsing <TypeIdentifier> for <StatementLetTypeAnnotation>").parse_once()
            return p7
        return BoundParser(self, inner)

    def _parse_local_variable_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwMut).add_err("Error parsing 'mut'? for <LocalVariableIdentifier>").parse_optional()
            p2 = self._parse_identifier().add_err("Error parsing <Identifier> for <LocalVariableIdentifier>").parse_once()
            return LocalVariableAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_local_variable_identifiers(self) -> BoundParser:
        def inner():
            p1 = self._parse_local_variable_identifier().add_err("Error parsing <LocalVariableIdentifier> for <LocalVariableIdentifiers>").parse_once()
            p2 = self._parse_local_variable_identifier_next().add_err("Error parsing <LocalVariableIdentifierNext>* for <LocalVariableIdentifiers>").parse_zero_or_more()
            return [p1, *p2]
        return BoundParser(self, inner)

    def _parse_local_variable_identifier_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkComma).add_err("Error parsing ',' for <LocalVariableIdentifierNext>").parse_once()
            p4 = self._parse_local_variable_identifier().add_err("Error parsing <LocalVariableIdentifier> for <LocalVariableIdentifierNext>").parse_once()
            return p4
        return BoundParser(self, inner)

    def _parse_statement_expression(self) -> BoundParser:
        def inner():
            p1 = self._parse_expression().add_err("Error parsing <Expression> for <StatementExpression>").parse_once()
            p2 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <StatementExpression>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_statement(self) -> BoundParser:
        def inner():
            p1 = self._parse_statement_if().add_err("Error parsing <StatementIf> for <Statement>").delay_parse()
            p2 = self._parse_statement_while().add_err("Error parsing <StatementWhile> for <Statement>").delay_parse()
            p3 = self._parse_statement_for().add_err("Error parsing <StatementFor> for <Statement>").delay_parse()
            p4 = self._parse_statement_do().add_err("Error parsing <StatementDo> for <Statement>").delay_parse()
            p5 = self._parse_statement_match().add_err("Error parsing <StatementMatch> for <Statement>").delay_parse()
            p6 = self._parse_statement_with().add_err("Error parsing <StatementWith> for <Statement>").delay_parse()
            p7 = self._parse_statement_typedef().add_err("Error parsing <StatementTypedef> for <Statement>").delay_parse()
            p8 = self._parse_statement_return().add_err("Error parsing <StatementReturn> for <Statement>").delay_parse()
            p9 = self._parse_statement_yield().add_err("Error parsing <StatementYield> for <Statement>").delay_parse()
            p10 = self._parse_statement_break().add_err("Error parsing <StatementBreak> for <Statement>").delay_parse()
            p11 = self._parse_statement_continue().add_err("Error parsing <StatementContinue> for <Statement>").delay_parse()
            p12 = self._parse_statement_let().add_err("Error parsing <StatementLet> for <Statement>").delay_parse()
            p13 = self._parse_statement_expression().add_err("Error parsing <StatementExpression> for <Statement>").delay_parse()
            # p14 = self._parse_function_prototype().delay_parse()
            p15 = (p1 | p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11 | p12 | p13).add_err("Error parsing selection for <Statement>").parse_once()
            return p15
        return BoundParser(self, inner)

    # Identifiers

    def _parse_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxIdentifier).add_err("Error parsing <Lexeme> for <Identifier>").parse_once()
            return IdentifierAst(p1)
        return BoundParser(self, inner)

    def _parse_generic_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxIdentifier).add_err("Error parsing <Lexeme> for <GenericIdentifier>").parse_once()
            p2 = self._parse_type_generic_arguments().add_err("Error parsing <TypeGenericArguments> for <GenericIdentifier>").parse_optional()
            return GenericIdentifierAst(p1, p2)
        return BoundParser(self, inner)

    def _parse_static_scoped_generic_identifier(self) -> BoundParser:
        def inner():
            p1 = self._parse_generic_identifier().add_err("Error parsing <GenericIdentifier> for <StaticScopedGenericIdentifier>").parse_once()
            p2 = self._parse_static_scoped_generic_identifier_next().add_err("Error parsing <StaticScopedGenericIdentifierNext>* for <StaticScopedGenericIdentifier>").parse_zero_or_more()
            return ScopedGenericIdentifierAst([p1, *p2])
        return BoundParser(self, inner)

    def _parse_static_scoped_generic_identifier_next(self) -> BoundParser:
        def inner():
            p3 = self._parse_token(TokenType.TkDoubleColon).add_err("Error parsing '::' for <StaticScopedGenericIdentifierNext>").parse_once()
            p4 = self._parse_generic_identifier().add_err("Error parsing <GenericIdentifier> for <StaticScopedGenericIdentifierNext>").parse_once()
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
            p1 = self._parse_token(TokenType.TkPlus).add_err("Error parsing ... | '+' | ... for <OperatorIdentifierUnary>").delay_parse()
            p2 = self._parse_token(TokenType.TkHyphen).add_err("Error parsing ... | '-' | ... for <OperatorIdentifierUnary>").delay_parse()
            p3 = self._parse_token(TokenType.TkTilde).add_err("Error parsing ... | '~' | ... for <OperatorIdentifierUnary>").delay_parse()
            p4 = self._parse_token(TokenType.TkExclamation).add_err("Error parsing ... | '!' | ... for <OperatorIdentifierUnary>").delay_parse()
            p5 = self._parse_unary_operator_reference().add_err("Error parsing ... | <UnaryOperatorReference> | ... for <OperatorIdentifierUnary>").delay_parse()
            p6 = self._parse_operator_identifier_variadic().add_err("Error parsing ... | <OperatorIdentifierVariadic> | ... for <OperatorIdentifierUnary>").delay_parse()
            p7 = self._parse_token(TokenType.KwAwait).add_err("Error parsing ... | 'await' | ... for <OperatorIdentifierUnary>").delay_parse()
            p8 = (p1 | p2 | p3 | p4 | p5 | p6 | p7).add_err("Error parsing selection for <OperatorIdentifierUnary>").parse_once()
            return p8
        return BoundParser(self, inner)

    def _parse_unary_operator_reference(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkAmpersand).add_err("Error parsing '&' for <UnaryOperatorReference>").parse_once()
            p2 = self._parse_token(TokenType.KwMut).add_err("Error parsing 'mut'? for <UnaryOperatorReference").parse_optional() is not None
            return TokenAst(p1.primary, p2 is not None)
        return BoundParser(self, inner)

    def _parse_operator_identifier_variadic(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkTripleDot).add_err("Error parsing '...' for <OperatorIdentiferVariadic>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_operator_identifier_member_access(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkDot).add_err("Error parsing '.' for <OperatorIdentifierMemberAccess>").parse_once()
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

    """[LITERALS]"""

    def _parse_literal(self) -> BoundParser:
        def inner():
            p1 = self._parse_literal_number().add_err("Error parsing <LiteralNumber> for <Literal>").delay_parse()
            p2 = self._parse_literal_string().add_err("Error parsing <LiteralString> for <Literal>").delay_parse()
            p3 = self._parse_literal_char().add_err("Error parsing <LiteralChar> for <Literal>").delay_parse()
            p4 = self._parse_literal_boolean().add_err("Error parsing <LiteralBoolean> for <Literal>").delay_parse()
            p5 = self._parse_literal_list().add_err("Error parsing <LiteralList> for <Literal>").delay_parse()
            p6 = self._parse_literal_map().add_err("Error parsing <LiteralMap> for <Literal>").delay_parse()
            p7 = self._parse_literal_set().add_err("Error parsing <LiteralSet> for <Literal>").delay_parse()
            p8 = self._parse_literal_pair().add_err("Error parsing <LiteralPair> for <Literal>").delay_parse()
            p9 = self._parse_literal_tuple().add_err("Error parsing <LiteralTuple> for <Literal>").delay_parse()
            p10 = self._parse_literal_regex().add_err("Error parsing <LiteralRegex> for <Literal>").delay_parse()
            p11 = self._parse_literal_generator().add_err("Error parsing <LiteralGenerator> for <Literal>").delay_parse()
            p12 = (p2 | p3 | p4 | p5 | p6 | p7 | p8 | p9 | p10 | p11).parse_once()
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
            p1 = self._parse_lexeme(TokenType.LxDoubleQuoteStr).add_err("Error parsing <Lexeme> for <LiteralString>").parse_once()
            return StringLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_char(self) -> BoundParser:
        def inner():
            p1 = self._parse_lexeme(TokenType.LxSingleQuoteChr).add_err("Error parsing <Lexeme> for <LiteralChar>").parse_once()
            return CharLiteralAst(p1)
        return BoundParser(self, inner)

    def _parse_literal_boolean(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.KwTrue).add_err("Error parsing 'true' for <LiteralBoolean>").delay_parse()
            p2 = self._parse_token(TokenType.KwFalse).add_err("Error parsing 'false' for <LiteralBoolean>").delay_parse()
            p3 = (p1 | p2).add_err("Error parsing selection for <LiteralBoolean>").parse_once()
            return BoolLiteralAst(p3 == TokenType.KwTrue)
        return BoundParser(self, inner)

    def _parse_literal_list(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBracket).parse_once()
            p2 = self._parse_build_container_from_range().delay_parse()
            p3 = self._parse_build_container_from_expressions().delay_parse()
            p4 = self._parse_build_container_from_comprehension().delay_parse()
            p5 = (p2 | p3 | p4).parse_once()
            p6 = self._parse_token(TokenType.TkRightBracket).parse_once()
            return ListLiteralAst(p5)
        return BoundParser(self, inner)

    def _parse_literal_generator(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftParenthesis).parse_once()
            p2 = self._parse_build_container_from_range().delay_parse()
            p3 = self._parse_build_container_from_comprehension().delay_parse()
            p4 = (p2 | p3).parse_once()
            p5 = self._parse_token(TokenType.TkRightParenthesis).parse_once()
            return GeneratorLiteralAst(p4)
        return BoundParser(self, inner)

    def _parse_literal_set(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkLeftBrace).parse_once()
            p2 = self._parse_build_container_from_range().delay_parse()
            p3 = self._parse_build_container_from_expressions().delay_parse()
            p4 = self._parse_build_container_from_comprehension().delay_parse()
            p5 = (p2 | p3 | p4).parse_once()
            p6 = self._parse_token(TokenType.TkRightBrace).parse_once()
            return SetLiteralAst(p5)
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
            p1 = self._parse_lexeme(TokenType.LxRegex).add_err("Error parsing <Lexeme> for <LiteralRegex>").parse_once()
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

    """[CONTAINER BUILDING]"""
    def _parse_build_container_from_range(self):
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_token(TokenType.TkDoubleDot).parse_once()
            p3 = self._parse_expression().parse_once()
            p4 = self._parse_iterable_step().parse_optional()
            return IterableRangeAst(p1, p3, p4)
        return BoundParser(self, inner)

    def _parse_build_container_from_expressions(self):
        def inner():
            p1 = self._parse_expressions().parse_optional()
            return p1
        return BoundParser(self, inner)

    def _parse_build_container_from_comprehension(self):
        def inner():
            p1 = self._parse_expression().parse_once()
            p2 = self._parse_token(TokenType.KwFor).parse_once()
            p3 = self._parse_local_variable_identifiers().parse_once()
            p5 = self._parse_expression().parse_once()
            p4 = self._parse_token(TokenType.KwIn).parse_once()
            p6 = self._parse_value_guard().parse_optional()
            return IterableComprehensionAst(p1, p3, p5, p6)
        return BoundParser(self, inner)

    """[NUMBER]"""

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
                raise ParseSyntaxError(f"Expected <{token}>, got <EOF>")

            current_token = self._tokens[self._current]
            if current_token.token_type != token:

                error = ParseSyntaxError(
                    # ErrorFormatter(self._tokens).error(self._current) +
                    FOLD + f"- Expected <{token}>, got: <{current_token.token_type}> => '{current_token.token_metadata}'\n")
                raise error

            self._current += 1

            return TokenAst(self._tokens[self._current - 1], None)
        return BoundParser(self, inner)

    def _parse_lexeme(self, lexeme: TokenType) -> BoundParser:
        def inner():
            p1 = self._parse_token(lexeme).add_err("Error parsing <Token> for <Lexeme>").parse_once()
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
            p1 = self._parse_indented_whitespace().add_err("Error parsing '    '*n for <Indent>").parse_once()
            if self._tokens[self._current].token_type == TokenType.TkWhitespace:
                raise ParseSyntaxError("Unexpected whitespace")

        return BoundParser(self, inner)

    def _parse_indented_whitespace(self) -> BoundParser:
        def inner():
            for i in range(self._indent):
                self._parse_token(TokenType.TkWhitespace).add_err("Error parsing ' ' for '    '*n").parse_once()
        return BoundParser(self, inner)

    def _parse_dedent(self) -> BoundParser:
        def inner():
            self._indent -= 4
            self._dedents_expected = max(self._dedents_expected - 1, 0)
        return BoundParser(self, inner)

    def _parse_empty_implementation(self) -> BoundParser:
        def inner():
            p1 = self._parse_token(TokenType.TkSemicolon).add_err("Error parsing ';' for <EmptyImplementation>").parse_once()
            return p1
        return BoundParser(self, inner)

    def _parse_character(self, character: str) -> BoundParser:
        def inner():
            p1 = self._parse_identifier().parse_once()
            if p1.identifier != character:
                raise ParseSyntaxError(f"Expected {character}, got {p1.value}")
            return p1
        return BoundParser(self, inner)
