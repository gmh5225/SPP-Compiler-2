from __future__ import annotations

from typing import Optional
from dataclasses import dataclass

from src.LexicalAnalysis.Tokens import Token


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
    mutable: bool
    _tok: int


@dataclass
class IdentifierAst:
    identifier: str
    _tok: int

@dataclass
class ModuleIdentifierAst:
    parts: list[IdentifierAst]
    _tok: int

@dataclass
class GenericIdentifierAst:
    identifier: str
    generic_arguments: list[TypeGenericArgumentAst]
    _tok: int

@dataclass
class SelfTypeAst:
    _tok: int

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
    mutable: bool
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

@dataclass
class FunctionPrototypeAst:
    decorators: list[DecoratorAst]
    is_coro: bool
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    parameters: list[FunctionParameterAst]
    return_type: TypeAst
    where_block: Optional[WhereBlockAst]
    value_guard: Optional[ValueGuardAst]
    body: FunctionImplementationAst
    _tok: int

@dataclass
class FunctionArgumentAst:
    identifier: Optional[IdentifierAst]
    value: ExpressionAst
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    unpack: bool
    _tok: int

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
class ValueGuardAst:
    value: ExpressionAst
    _tok: int

@dataclass
class DecoratorAst:
    identifier: TypeAst # can be namespaced and generic
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

def TypeGenericArgumentNamedAst(identifier: IdentifierAst, value: TypeAst, _tok: int):
    return TypeGenericArgumentAst(identifier, value, _tok)

def TypeGenericArgumentNormalAst(value: TypeAst, _tok: int):
    return TypeGenericArgumentAst(None, value, _tok)

@dataclass
class TypeSingleAst:
    parts: list[SelfTypeAst | GenericIdentifierAst | int]
    _tok: int

@dataclass
class TypeTupleAst:
    types: list[TypeAst]
    _tok: int

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
    guard: Optional[ValueGuardAst]
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

@dataclass
class PostfixMemberAccessAst:
    separator: TokenAst
    identifier: IdentifierAst | int
    _tok: int

@dataclass
class PostfixStructInitializerAst:
    fields: list[PostfixStructInitializerFieldAst]
    _tok: int

@dataclass
class PostfixStructInitializerFieldAst:
    identifier: IdentifierAst | TokenAst
    value: Optional[ExpressionAst]
    _tok: int

@dataclass
class NumberLiteralBase10Ast:
    sign: Optional[TokenAst]
    integer: str
    decimal: str
    exponent: Optional[NumberExponentAst]
    is_imaginary: bool
    _tok: int

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

@dataclass
class StringLiteralAst:
    value: str
    _tok: int

@dataclass
class CharLiteralAst:
    value: str
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
LiteralAst = NumberLiteralAst | StringLiteralAst | CharLiteralAst | BoolLiteralAst | RegexLiteralAst | TupleLiteralAst
TypeAst = TypeSingleAst | TypeTupleAst
PrimaryExpressionAst = LiteralAst | IdentifierAst | LambdaAst | PlaceholderAst | TypeSingleAst | IfStatementAst | WhileStatementAst | YieldStatementAst | InnerScopeAst | WithStatementAst | TokenAst
ExpressionAst = BinaryExpressionAst | PostfixExpressionAst | AssignmentExpressionAst | PrimaryExpressionAst | TokenAst
StatementAst = TypedefStatementAst | ReturnStatementAst | LetStatementAst | ExpressionAst | FunctionPrototypeAst
ModuleMemberAst = EnumPrototypeAst | ClassPrototypeAst | FunctionPrototypeAst | SupPrototypeNormalAst | SupPrototypeInheritanceAst
SupMemberAst = SupMethodPrototypeAst | SupTypedefAst
