from __future__ import annotations

import hashlib
from typing import Optional
from dataclasses import dataclass

from src.LexicalAnalysis.Tokens import Token, TokenType


@dataclass
class ProgramAst:
    module: ModulePrototypeAst
    _tok: int

@dataclass
class TokenAst:
    tok: Token
    _tok: int

@dataclass
class ParameterPassingConventionReferenceAst:
    is_mutable: bool
    _tok: int

    def __str__(self):
        return "&" + ("mut " if self.is_mutable else "")


@dataclass
class IdentifierAst:
    identifier: str
    _tok: int

    def __hash__(self):
        h = hashlib.md5(self.identifier.encode()).digest()
        return int.from_bytes(h, "big")

    def __eq__(self, other):
        return isinstance(other, IdentifierAst) and self.identifier == other.identifier

    def __str__(self):
        return self.identifier

@dataclass
class ModuleIdentifierAst:
    parts: list[IdentifierAst]
    _tok: int

    def __str__(self):
        return ".".join([str(part) for part in self.parts])

@dataclass
class GenericIdentifierAst:
    identifier: str
    generic_arguments: list[TypeGenericArgumentAst]
    _tok: int

    def __eq__(self, other):
        return isinstance(other, GenericIdentifierAst) and self.identifier == other.identifier and self.generic_arguments == other.generic_arguments

    def __hash__(self):
        return hash(IdentifierAst(self.identifier, self._tok))

    def __str__(self):
        return self.identifier + ("[" + ",".join([str(arg) for arg in self.generic_arguments]) + "]" if self.generic_arguments else "")

    def to_identifier(self) -> IdentifierAst:
        return IdentifierAst(self.identifier, self._tok)

# @dataclass
class SelfTypeAst:
    _tok: int
    identifier: str

    def __init__(self, _tok: int):
        self._tok = _tok
        self.identifier = "Self"

    def __eq__(self, other):
        return isinstance(other, SelfTypeAst)

    def __str__(self):
        return "Self"

    def __hash__(self):
        return hash(IdentifierAst("Self", self._tok))

@dataclass
class ImportTypeAst:
    imported_type: IdentifierAst
    alias: Optional[IdentifierAst]
    _tok: int

@dataclass
class ImportTypesAst:
    individual_types: list[ImportTypeAst]
    import_all: bool
    _tok: int

def ImportTypesAllAst(_tok: int):
    return ImportTypesAst([], True, _tok)

def ImportTypesIndividualAst(individual_types: list[ImportTypeAst], _tok: int):
    return ImportTypesAst(individual_types, False, _tok)

@dataclass
class ImportStatementAst:
    module: ImportIdentifierAst
    what_to_import: ImportTypesAst
    _tok: int

@dataclass
class ImportIdentifierAst:
    parts: list[IdentifierAst]
    _tok: int

    def __str__(self):
        return "/".join([str(part) for part in self.parts])

@dataclass
class ImportBlockAst:
    imports: list[ImportStatementAst]
    _tok: int

@dataclass
class ModuleImplementationAst:
    import_block: ImportBlockAst
    members: list[ModuleMemberAst]
    _tok: int

@dataclass
class ModulePrototypeAst:
    decorators: list[DecoratorAst]
    identifier: ModuleIdentifierAst
    body: ModuleImplementationAst
    _tok: int

@dataclass
class ClassAttributeAst:
    decorators: list[DecoratorAst]
    identifier: IdentifierAst
    type_annotation: TypeAst
    _tok: int

@dataclass
class ClassImplementationAst:
    members: list[ClassAttributeAst]
    _tok: int

@dataclass
class ClassPrototypeAst:
    decorators: list[DecoratorAst]
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    where_block: Optional[WhereBlockAst]
    body: ClassImplementationAst
    _tok: int

    def __hash__(self):
        return hash(self.identifier)

    def __str__(self):
        return self.identifier.identifier + ("[" + ",".join([str(param) for param in self.generic_parameters]) + "]" if self.generic_parameters else "")

@dataclass
class FunctionPrototypeAst:
    decorators: list[DecoratorAst]
    is_coro: bool
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    parameters: list[FunctionParameterAst]
    return_type: TypeAst
    where_block: Optional[WhereBlockAst]
    body: FunctionImplementationAst
    _tok: int

    def __str__(self):
        return self.identifier.identifier\
            + ("[" + ",".join([str(param) for param in self.generic_parameters]) + "]" if self.generic_parameters else "")\
            + "(" + ",".join([str(param) for param in self.parameters]) + ")"\
            + (" -> " + str(self.return_type) if self.return_type else "")

@dataclass
class FunctionArgumentAst:
    identifier: Optional[IdentifierAst]
    value: ExpressionAst
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    unpack: bool
    _tok: int

    def __str__(self):
        s = str(self.calling_convention) if self.calling_convention else ""
        s += str(self.value)
        return s

def FunctionArgumentNamedAst(identifier: IdentifierAst, convention: Optional[TokenAst], value: ExpressionAst, _tok: int):
    return FunctionArgumentAst(identifier, value, convention, False, _tok)

def FunctionArgumentNormalAst(convention: Optional[TokenAst], value: ExpressionAst, unpack: bool, _tok: int):
    return FunctionArgumentAst(None, value, convention, unpack, _tok)

@dataclass
class FunctionParameterAst:
    is_mutable: bool
    identifier: IdentifierAst
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    type_annotation: TypeAst
    default_value: Optional[ExpressionAst]
    is_variadic: bool
    _tok: int

    def __str__(self):
        return ("mut" if self.is_mutable else "")\
            + (str(self.calling_convention) if self.calling_convention else "")\
            + str(self.identifier) + ": " + str(self.type_annotation)

def FunctionParameterRequiredAst(is_mutable: bool, identifier: IdentifierAst, calling_convention: Optional[TokenAst], type_annotation: TypeAst, _tok: int):
    return FunctionParameterAst(is_mutable, identifier, calling_convention, type_annotation, None, False, _tok)

def FunctionParameterOptionalAst(parameter: FunctionParameterAst, default_value: ExpressionAst):
    parameter.default_value = default_value
    return parameter

def FunctionParameterVariadicAst(parameter: FunctionParameterAst):
    parameter.is_variadic = True
    return parameter

@dataclass
class FunctionImplementationAst:
    statements: list[StatementAst]
    _tok: int

@dataclass
class EnumMemberAst:
    identifier: IdentifierAst
    value: Optional[ExpressionAst]
    _tok: int

@dataclass
class EnumImplementationAst:
    members: list[EnumMemberAst]
    _tok: int

@dataclass
class EnumPrototypeAst:
    decorators: list[DecoratorAst]
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    where_block: Optional[WhereBlockAst]
    body: EnumImplementationAst
    _tok: int

@dataclass
class WhereBlockAst:
    constraints: list[WhereConstraintAst]
    _tok: int

@dataclass
class WhereConstraintAst:
    types_to_constrain: list[TypeAst]
    constraints: list[TypeAst]
    _tok: int

@dataclass
class DecoratorAst:
    identifier: ModuleIdentifierAst
    generic_arguments: list[TypeGenericArgumentAst]
    arguments: list[FunctionArgumentAst]
    _tok: int

@dataclass
class BinaryExpressionAst:
    lhs: ExpressionAst
    op: TokenAst
    rhs: ExpressionAst
    _tok: int

@dataclass
class AssignmentExpressionAst:
    lhs: list[ExpressionAst]
    op: TokenAst # always "=", just to store token position
    rhs: ExpressionAst
    _tok: int

@dataclass
class PostfixExpressionAst:
    lhs: ExpressionAst
    op: PostfixOperationAst
    _tok: int

    def __str__(self):
        s = str(self.lhs)
        s += str(self.op)
        return s

@dataclass
class PlaceholderAst:
    _tok: int

@dataclass
class LambdaParameterAst:
    is_mutable: bool
    identifier: IdentifierAst
    _tok: int

@dataclass
class LambdaCaptureItemAst:
    identifier: Optional[IdentifierAst]
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    capture: IdentifierAst
    _tok: int

@dataclass
class LambdaAst:
    captures: list[LambdaCaptureItemAst]
    parameters: list[LambdaParameterAst]
    body: ExpressionAst
    _tok: int

@dataclass
class TypeGenericParameterAst:
    identifier: IdentifierAst
    constraints: list[TypeAst]
    default: Optional[TypeAst]
    is_variadic: bool
    _tok: int

    def as_type(self) -> TypeAst:
        return TypeSingleAst([GenericIdentifierAst(self.identifier.identifier, [], self.identifier._tok)], self.identifier._tok)

    def __str__(self):
        return self.identifier.identifier

def TypeGenericParameterRequiredAst(identifier: IdentifierAst, constraints: list[TypeAst], _tok: int):
    return TypeGenericParameterAst(identifier, constraints, None, False, _tok)

def TypeGenericParameterOptionalAst(parameter: TypeGenericParameterAst, default: TypeAst):
    parameter.default = default
    return parameter

def TypeGenericParameterVariadicAst(parameter: TypeGenericParameterAst):
    parameter.is_variadic = True
    return parameter

@dataclass
class TypeGenericArgumentAst:
    identifier: Optional[IdentifierAst]
    value: TypeAst
    _tok: int

    def __eq__(self, other):
        return isinstance(other, TypeGenericArgumentAst) and self.identifier == other.identifier and self.value == other.value

    def __str__(self):
        return (str(self.identifier) + ": ") if self.identifier else "" + str(self.value)

    def __hash__(self):
        return hash(self.value)

def TypeGenericArgumentNamedAst(identifier: IdentifierAst, value: TypeAst, _tok: int):
    return TypeGenericArgumentAst(identifier, value, _tok)

def TypeGenericArgumentNormalAst(value: TypeAst, _tok: int):
    return TypeGenericArgumentAst(None, value, _tok)

@dataclass
class TypeSingleAst:
    parts: list[SelfTypeAst | GenericIdentifierAst | int]
    _tok: int

    def __eq__(self, other):
        return isinstance(other, TypeSingleAst) and self.parts == other.parts

    def __hash__(self):
        return hash(tuple(self.parts))

    def __str__(self):
        return ".".join([str(part) for part in self.parts])

@dataclass
class TypeTupleAst:
    types: list[TypeAst]
    _tok: int

    def __eq__(self, other):
        return isinstance(other, TypeTupleAst) and self.types == other.types

    def __str__(self):
        return "(" + ", ".join([str(t) for t in self.types]) + ")"

@dataclass
class IfStatementAst:
    condition: ExpressionAst
    comparison_op: Optional[TokenAst]
    branches: list[PatternStatementAst]
    _tok: int

@dataclass
class PatternStatementAst:
    comparison_op: Optional[TokenAst]
    patterns: list[PatternAst]
    guard: Optional[ExpressionAst]
    body: list[StatementAst]
    _tok: int

@dataclass
class PatternAst:
    value: ExpressionAst
    _tok: int

@dataclass
class WhileStatementAst:
    condition: ExpressionAst
    body: list[StatementAst]
    else_: Optional[InnerScopeAst]
    _tok: int

@dataclass
class WithStatementAst:
    value: ExpressionAst
    alias: Optional[LocalVariableAst]
    body: list[StatementAst]
    _tok: int

@dataclass
class ReturnStatementAst:
    value: list[ExpressionAst]
    _tok: int

    def __str__(self):
        return "ReturnStatementAst"

@dataclass
class YieldStatementAst:
    convention: Optional[ParameterPassingConventionReferenceAst]
    value: list[ExpressionAst]
    _tok: int

@dataclass
class TypedefStatementAst:
    new_type: TypeAst
    old_type: TypeAst
    _tok: int

@dataclass
class LetStatementAst:
    variables: list[LocalVariableAst]
    value: Optional[ExpressionAst]
    type_annotation: Optional[TypeAst]
    if_null: Optional[InnerScopeAst]
    _tok: int

@dataclass
class InnerScopeAst:
    body: list[StatementAst]
    _tok: int

@dataclass
class LocalVariableAst:
    is_mutable: bool
    identifier: IdentifierAst
    _tok: int

@dataclass
class SupImplementationAst:
    members: list[SupMemberAst]
    _tok: int

@dataclass
class SupPrototypeNormalAst:
    generic_parameters: list[TypeGenericParameterAst]
    identifier: TypeAst
    where_block: Optional[WhereBlockAst]
    body: SupImplementationAst
    _tok: int

@dataclass
class SupPrototypeInheritanceAst(SupPrototypeNormalAst):
    super_class: TypeAst
    _tok: int

@dataclass
class SupMethodPrototypeAst(FunctionPrototypeAst):
    _tok: int

@dataclass
class SupTypedefAst(TypedefStatementAst):
    decorators: list[DecoratorAst]

@dataclass
class PostfixFunctionCallAst:
    type_arguments: list[TypeGenericArgumentAst]
    arguments: list[FunctionArgumentAst]
    _tok: int

    def __str__(self):
        s = "[" + ", ".join([str(arg) for arg in self.type_arguments]) + "]" if self.type_arguments else ""
        s += "(" + ", ".join([str(arg) for arg in self.arguments]) + ")"
        return s

@dataclass
class PostfixMemberAccessAst:
    identifier: IdentifierAst | int
    _tok: int

    def __str__(self):
        return "." + str(self.identifier)

@dataclass
class PostfixStructInitializerAst:
    fields: list[PostfixStructInitializerFieldAst]
    _tok: int

    def __str__(self):
        s = "{" + ", ".join([str(field) for field in self.fields]) + "}"
        return s

@dataclass
class PostfixStructInitializerFieldAst:
    identifier: IdentifierAst | TokenAst
    value: Optional[ExpressionAst]
    _tok: int

    def __str__(self):
        s = str(self.identifier)
        s += ("=" + str(self.value)) if self.value else ""
        return s

@dataclass
class NumberLiteralBase10Ast:
    sign: Optional[TokenAst]
    integer: str
    decimal: str
    exponent: Optional[NumberExponentAst]
    is_imaginary: bool
    _tok: int

    def __str__(self):
        s = self.sign.tok.token_metadata if self.sign else ""
        s += self.integer
        s += "." + self.decimal if self.decimal else ""
        s += str(self.exponent) if self.exponent else ""
        s += "i" if self.is_imaginary else ""
        return s

@dataclass
class NumberLiteralBase16Ast:
    value: str
    _tok: int

@dataclass
class NumberLiteralBase02Ast:
    value: str
    _tok: int

@dataclass
class NumberExponentAst:
    sign: Optional[TokenAst]
    value: str
    _tok: int

    def __str__(self):
        s = self.sign.tok.token_metadata + self.value
        return s

@dataclass
class StringLiteralAst:
    value: str
    _tok: int

@dataclass
class ArrayLiteralAst:
    values: list[ExpressionAst]
    _tok: int

@dataclass
class BoolLiteralAst:
    value: bool
    _tok: int

@dataclass
class RegexLiteralAst:
    value: str
    _tok: int

@dataclass
class TupleLiteralAst:
    values: list[ExpressionAst]
    _tok: int


PostfixOperationAst = PostfixFunctionCallAst | PostfixMemberAccessAst | PostfixStructInitializerAst | TokenAst
NumberLiteralAst = NumberLiteralBase10Ast | NumberLiteralBase16Ast | NumberLiteralBase02Ast
LiteralAst = NumberLiteralAst | StringLiteralAst | ArrayLiteralAst | BoolLiteralAst | RegexLiteralAst | TupleLiteralAst
TypeAst = TypeSingleAst | TypeTupleAst
PrimaryExpressionAst = LiteralAst | IdentifierAst | LambdaAst | PlaceholderAst | TypeSingleAst | IfStatementAst | WhileStatementAst | YieldStatementAst | InnerScopeAst | WithStatementAst | TokenAst
ExpressionAst = BinaryExpressionAst | PostfixExpressionAst | AssignmentExpressionAst | PrimaryExpressionAst | TokenAst
StatementAst = TypedefStatementAst | ReturnStatementAst | LetStatementAst | ExpressionAst | FunctionPrototypeAst
ModuleMemberAst = EnumPrototypeAst | ClassPrototypeAst | FunctionPrototypeAst | SupPrototypeNormalAst | SupPrototypeInheritanceAst
SupMemberAst = SupMethodPrototypeAst | SupTypedefAst
SupPrototypeAst = SupPrototypeNormalAst | SupPrototypeInheritanceAst


BIN_FN = {
    TokenType.TkAdd: "add",
    TokenType.TkSub: "sub",
    TokenType.TkMul: "mul",
    TokenType.TkDiv: "div",
    TokenType.TkRem: "mod",

    TokenType.TkDoubleAmpersand: "and",
    TokenType.TkDoublePipe: "or",
    TokenType.TkAmpersand: "bit_and",
    TokenType.TkPipe: "bit_or",
    TokenType.TkCaret: "bit_xor",

    TokenType.TkEq : "eq",
    TokenType.TkNe: "ne",
    TokenType.TkLt: "lt",
    TokenType.TkLe: "le",
    TokenType.TkGt: "gt",
    TokenType.TkGe: "ge",
    TokenType.TkSs : "cmp",


    TokenType.TkAddEq: "add_eq",
    TokenType.TkSubEq: "sub_eq",
    TokenType.TkMulEq: "mul_eq",
    TokenType.TkDivEq: "div_eq",
    TokenType.TkRemEq: "mod_eq",

    TokenType.TkDoubleAmpersandEquals: "and_eq",
    TokenType.TkDoublePipeEquals: "or_eq",
    TokenType.TkAmpersandEquals: "bit_and_eq",
    TokenType.TkPipeEquals: "bit_or_eq",
    TokenType.TkCaretEquals: "bit_xor_eq",
}
