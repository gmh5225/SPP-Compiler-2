from __future__ import annotations

from typing import Optional
from dataclasses import dataclass
from src.LexicalAnalysis.Tokens import Token, TokenType


@dataclass
class ProgramAst:
    module: ModulePrototypeAst

@dataclass
class TokenAst:
    tok: Token

@dataclass
class ParameterPassingConventionReferenceAst:
    mutable: bool

@dataclass
class IdentifierAst:
    identifier: str

@dataclass
class TagIdentifierAst:
    identifier: str

@dataclass
class ModuleIdentifierAst:
    parts: list[IdentifierAst]

@dataclass
class GenericIdentifierAst:
    identifier: str
    generic: list[TypeGenericArgumentAst]

@dataclass
class SelfTypeAst:
    pass

@dataclass
class MemberAccessAst:
    separator: TokenAst
    member: GenericIdentifierAst

@dataclass
class ImportTypeAst:
    imported_type: IdentifierAst
    alias: Optional[IdentifierAst]

@dataclass
class ImportTypesAst:
    individual_types: list[ImportTypeAst]
    import_all: bool

def ImportTypesAllAst():
    return ImportTypesAst([], True)

def ImportTypesIndividualAst(individual_types: list[ImportTypeAst]):
    return ImportTypesAst(individual_types, False)

@dataclass
class ImportStatementAst:
    module: ImportIdentifierAst
    what_to_import: ImportTypesAst

@dataclass
class ImportIdentifierAst:
    parts: list[IdentifierAst]

@dataclass
class ImportBlockAst:
    imports: list[ImportStatementAst]

@dataclass
class ModuleImplementationAst:
    imports: ImportBlockAst
    members: list[ModuleMemberAst]

@dataclass
class ModulePrototypeAst:
    decorators: list[DecoratorAst]
    identifier: ModuleIdentifierAst
    body: ModuleImplementationAst

@dataclass
class ClassAttributeAst:
    decorators: list[DecoratorAst]
    mutable: bool
    identifier: IdentifierAst
    type_annotation: TypeAst

@dataclass
class ClassImplementationAst:
    members: list[ClassAttributeAst]

@dataclass
class ClassPrototypeAst:
    decorators: list[DecoratorAst]
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    where_block: Optional[WhereBlockAst]
    body: ClassImplementationAst

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

@dataclass
class FunctionArgumentAst:
    identifier: Optional[IdentifierAst]
    value: ExpressionAst
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    unpack: bool

def FunctionArgumentNamedAst(identifier: IdentifierAst, convention: Optional[TokenAst], value: ExpressionAst):
    return FunctionArgumentAst(identifier, value, convention, False)

def FunctionArgumentNormalAst(convention: Optional[TokenAst], value: ExpressionAst, unpack: bool):
    return FunctionArgumentAst(None, value, convention, unpack)

@dataclass
class FunctionParameterAst:
    is_mutable: bool
    identifier: IdentifierAst
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    type_annotation: TypeAst
    default_value: Optional[ExpressionAst]
    is_variadic: bool

def FunctionParameterRequiredAst(is_mutable: bool, identifier: IdentifierAst, calling_convention: Optional[TokenAst], type_annotation: TypeAst):
    return FunctionParameterAst(is_mutable, identifier, calling_convention, type_annotation, None, False)

def FunctionParameterOptionalAst(parameter: FunctionParameterAst, default_value: ExpressionAst):
    parameter.default_value = default_value
    return parameter

def FunctionParameterVariadicAst(parameter: FunctionParameterAst):
    parameter.is_variadic = True
    return parameter

@dataclass
class FunctionImplementationAst:
    statements: list[StatementAst]

@dataclass
class EnumMemberAst:
    identifier: IdentifierAst
    value: Optional[ExpressionAst]

@dataclass
class EnumImplementationAst:
    members: list[EnumMemberAst]

@dataclass
class EnumPrototypeAst:
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    where_block: Optional[WhereBlockAst]
    body: EnumImplementationAst

@dataclass
class WhereBlockAst:
    constraints: list[WhereConstraintAst]

@dataclass
class WhereConstraintAst:
    types_to_constrain: list[TypeAst]
    constraints: list[TypeAst]

@dataclass
class ValueGuardAst:
    value: ExpressionAst

@dataclass
class DecoratorAst:
    identifier: TypeAst # can be namespaced and generic
    generic_arguments: list[TypeGenericArgumentAst]
    arguments: list[FunctionArgumentAst]

@dataclass
class BinaryExpressionAst:
    lhs: ExpressionAst
    op: TokenAst
    rhs: ExpressionAst

@dataclass
class AssignmentExpressionAst:
    lhs: list[ExpressionAst]
    rhs: ExpressionAst

@dataclass
class PostfixExpressionAst:
    lhs: ExpressionAst
    op: PostfixOperationAst

@dataclass
class PlaceholderAst:
    ...

@dataclass
class LambdaParameterAst:
    is_mutable: bool
    identifier: IdentifierAst

@dataclass
class LambdaCaptureItemAst:
    identifier: Optional[IdentifierAst]
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    capture: IdentifierAst

@dataclass
class LambdaAst:
    captures: list[LambdaCaptureItemAst]
    parameters: list[LambdaParameterAst]
    body: list[StatementAst]

@dataclass
class TypeGenericParameterAst:
    identifier: IdentifierAst
    constraints: list[GenericIdentifierAst]
    default: Optional[TypeAst]
    is_variadic: bool

def TypeGenericParameterRequiredAst(identifier: IdentifierAst, constraints: list[GenericIdentifierAst]):
    return TypeGenericParameterAst(identifier, constraints, None, False)

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

def TypeGenericArgumentNamedAst(identifier: IdentifierAst, value: TypeAst):
    return TypeGenericArgumentAst(identifier, value)

def TypeGenericArgumentNormalAst(value: TypeAst):
    return TypeGenericArgumentAst(None, value)

@dataclass
class TypeSingleAst:
    parts: list[SelfTypeAst | GenericIdentifierAst | int]

@dataclass
class TypeTupleAst:
    types: list[TypeAst]

@dataclass
class IfStatementAst:
    expression: ExpressionAst
    comparison_op: TokenAst
    branches: list[PatternStatementAst]

@dataclass
class PatternStatementAst:
    comparison_op: Optional[TokenAst]
    patterns: list[PatternAst]
    guard: Optional[ValueGuardAst]
    body: list[StatementAst]

@dataclass
class PatternAst:
    value: ExpressionAst

@dataclass
class WhileStatementAst:
    condition: ExpressionAst
    tag: Optional[TagIdentifierAst]
    body: InnerScopeAst
    else_: Optional[InnerScopeAst]

@dataclass
class ForStatementAst:
    identifiers: list[LocalVariableAst]
    iterable: ExpressionAst
    tag: Optional[TagIdentifierAst]
    body: InnerScopeAst
    else_: Optional[InnerScopeAst]

@dataclass
class DoWhileStatementAst:
    condition: ExpressionAst
    tag: Optional[TagIdentifierAst]
    body: InnerScopeAst
    else_: Optional[InnerScopeAst]

@dataclass
class WithStatementAst:
    value: ExpressionAst
    alias: Optional[LocalVariableAst]
    body: list[StatementAst]

@dataclass
class ReturnStatementAst:
    value: list[ExpressionAst]

@dataclass
class YieldStatementAst:
    value: list[ExpressionAst]

@dataclass
class TypedefStatementAst:
    new_type: TypeAst
    old_type: TypeAst

@dataclass
class BreakStatementAst:
    loop_tag: Optional[TagIdentifierAst]
    returning_expressions: list[ExpressionAst]

@dataclass
class ContinueStatementAst:
    loop_tag: Optional[TagIdentifierAst]

@dataclass
class LetStatementAst:
    variables: list[LocalVariableAst]
    value: Optional[ExpressionAst]
    type_annotation: Optional[TypeAst]
    if_null: Optional[InnerScopeAst]

@dataclass
class InnerScopeAst:
    body: list[StatementAst]

@dataclass
class LocalVariableAst:
    is_mutable: bool
    identifier: IdentifierAst

@dataclass
class SupImplementationAst:
    members: list[SupMemberAst]

@dataclass
class SupPrototypeNormalAst:
    generic_parameters: list[TypeGenericParameterAst]
    identifier: TypeAst
    where_block: Optional[WhereBlockAst]
    body: SupImplementationAst

@dataclass
class SupPrototypeInheritanceAst(SupPrototypeNormalAst):
    super_class: TypeAst

@dataclass
class SupMethodPrototypeAst(FunctionPrototypeAst):
    pass

@dataclass
class SupTypedefAst(TypedefStatementAst):
    decorators: list[DecoratorAst]

@dataclass
class PostfixFunctionCallAst:
    arguments: list[FunctionArgumentAst]

@dataclass
class PostfixMemberAccessAst:
    separator: TokenAst
    identifier: IdentifierAst | int

@dataclass
class PostfixStructInitializerAst:
    fields: list[PostfixStructInitializerFieldAst]

@dataclass
class PostfixStructInitializerFieldAst:
    identifier: IdentifierAst | TokenAst
    value: Optional[ExpressionAst]

@dataclass
class NumberLiteralBase10Ast:
    integer: str
    decimal: str
    exponent: Optional[NumberExponentAst]
    is_imaginary: bool

@dataclass
class NumberLiteralBase16Ast:
    value: str

@dataclass
class NumberLiteralBase02Ast:
    value: str

@dataclass
class NumberExponentAst:
    sign: Optional[TokenAst]
    value: str

@dataclass
class StringLiteralAst:
    value: str

@dataclass
class CharLiteralAst:
    value: str

@dataclass
class BoolLiteralAst:
    value: bool

@dataclass
class RegexLiteralAst:
    value: str

@dataclass
class TupleLiteralAst:
    values: list[ExpressionAst]

@dataclass
class RangeLiteralAst:
    start: Optional[ExpressionAst]
    end: Optional[ExpressionAst]


PostfixOperationAst = PostfixFunctionCallAst | PostfixMemberAccessAst | PostfixStructInitializerAst | TokenAst
NumberLiteralAst = NumberLiteralBase10Ast | NumberLiteralBase16Ast | NumberLiteralBase02Ast
LiteralAst = NumberLiteralAst | StringLiteralAst | CharLiteralAst | BoolLiteralAst | RegexLiteralAst | TupleLiteralAst
TypeAst = TypeSingleAst | TypeTupleAst
PrimaryExpressionAst = LiteralAst | IdentifierAst | GenericIdentifierAst | LambdaAst | PlaceholderAst | TypeSingleAst | IfStatementAst | WhileStatementAst | ForStatementAst | DoWhileStatementAst | YieldStatementAst | InnerScopeAst | WithStatementAst
ExpressionAst = BinaryExpressionAst | PostfixExpressionAst | AssignmentExpressionAst | PrimaryExpressionAst | TokenAst  # todo: separate AST for "..."?
StatementAst = IfStatementAst | WhileStatementAst | ForStatementAst | DoWhileStatementAst | WithStatementAst | ReturnStatementAst | YieldStatementAst | TypedefStatementAst | LetStatementAst | ExpressionAst
ModuleMemberAst = EnumPrototypeAst | ClassPrototypeAst | FunctionPrototypeAst | SupPrototypeNormalAst | SupPrototypeInheritanceAst
SupMemberAst = SupMethodPrototypeAst | SupTypedefAst
