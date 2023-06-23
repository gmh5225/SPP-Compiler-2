from typing import Generic, TypeVar, Optional
from abc import ABC, abstractmethod
from src.Ast import *

T = TypeVar("T")

class Parser(ABC, Generic[T]):
    def parse_once(self) -> T:
        ...

    def parse_optional(self) -> Optional[T]:
        ...

    def parse_zero_or_more(self) -> list[T]:
        ...

    def parse_one_or_more(self) -> list[T]:
        ...

    def __or__(self, other):
        ...

    @abstractmethod
    def _parse(self) -> T:
        ...


class ParseProgram(Parser[ProgramAst]):
    def _parse(self) -> T:
        p1 = ParseModulePrototype().parse_once()
        p2 = ParseEOF().parse_once()
        return ProgramAst(p1)


class ParseEOF(Parser[TokenAst]):
    def _parse(self) -> T:
        p1 = ParseToken(TokenType.TkEOF).parse_once()
        return TokenAst(p1, None)


class ParseModulePrototype(Parser[ModulePrototypeAst]):
    def _parse(self) -> T:
        p1 = ParseAccessModifier().parse_optional()
        p2 = ParseToken(TokenType.KwMod).parse_once()
        p3 = ParseModuleIdentifier().parse_once()
        p4 = ParseToken(TokenType.TkSemicolon).parse_once()
        p5 = ParseModuleImplementation().parse_once()
        return ModulePrototypeAst(p1, p3, p5)


class ParseModuleImplementation(Parser[ModuleImplementationAst]):
    def _parse(self) -> T:
        p1 = ParseImportBlock().parse_optional()
        p2 = ParseModuleMember().parse_zero_or_more()
        return ModuleImplementationAst(p1, p2)


class ParseModuleIdentifier(Parser[ModuleIdentifierAst]):
    class ParseNext(Parser[IdentifierAst]):
        def _parse(self) -> T:
            p1 = ParseToken(TokenType.TkDot).parse_once()
            p2 = ParseIdentifier().parse_once()
            return p2

    def _parse(self) -> T:
        p1 = ParseIdentifier().parse_once()
        p2 = ParseNext().parse_zero_or_more()
        return ModuleIdentifierAst([p1] + p2)


class ParseModuleMember(Parser[ModuleMemberAst]):
    def _parse(self) -> T:
        p1 = ParseFunctionPrototype()
        p2 = ParseEnumPrototype()
        p3 = ParseClassPrototype()
        p4 = ParseSupPrototype()
        p5 = (p1 | p2 | p3 | p4).parse_once()
        return p5


class ParseImportBlock(Parser[ImportBlockAst]):
    def _parse(self) -> T:
        p1 = ParseToken(TokenType.KwUse).parse_once()
        p2 = ParseToken(TokenType.TkColon).parse_once()
        p3 = ParseIndent().parse_once()
        p3 = ParseImportDefinition.parse_one_or_more()
        p4 = ParseDedent().parse_once()
        return ImportBlockAst(p3)


class ParseImportDefinition(Parser[ImportDefinitionsAst]):
    def _parse(self) -> T:
        p1 = ParseToken(TokenType.TkDot).parse_zero_or_more()
        p2 = ParseModuleIdentifier().parse_once()
        p3 = ParseToken(TokenType.TkRightArrow).parse_once()
        p4 = ParseImportIdentifiers().parse_once()
        p5 = ParseToken(TokenType.TkSemicolon).parse_once()
        return ImportDefinitionsAst(len(p1), p2, p4)


class ParseImportIdentifiers(Parser[ImportTypesAst]):
    def _parse(self) -> T:
        p1 = ParseImportAllTypes()
        p2 = ParseImportIdentifiersRaw()
        p3 = (p1 | p2).parse_once()
        return p3


class ParseImportAllTypes(Parser[ImportTypesAst]):
    def _parse(self) -> T:
        p1 = ParseToken(TokenType.TkAsterisk).parse_once()
        return ImportTypesAst([], True)


class ParseImportIndividualTypes(Parser[ImportTypesAst]):
    class ParseNext(Parser[ImportTypeAst]):
        def _parse(self) -> T:
            p1 = ParseToken(TokenType.TkComma).parse_once()
            p2 = ParseImportIndividualType().parse_once()
            return p2

    def _parse(self) -> T:
        p1 = ParseImportIndividualType().parse_once()
        p2 = ParseNext().parse_zero_or_more()
        return ImportTypesAst([p1] + p2, False)


class ParseImportIndividualType(Parser[ImportTypeAst]):
    def _parse(self) -> T:
        p1 = ParseIdentifier().parse_once()
        p2 = ParseImportTypeAlias().parse_optional()
        return ImportTypeAst(p1, p2)


class ParseImportTypeAlias(Parser[IdentifierAst]):
    def _parse(self) -> T:
        p1 = ParseToken(TokenType.KwAs).parse_once()
        p2 = ParseIdentifier().parse_once()
        return p2
