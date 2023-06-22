from __future__ import annotations

from typing import Optional
from dataclasses import dataclass
from src.Tokens import Token

@dataclass
class ProgramAst:
    module: ModulePrototypeAst

@dataclass
class TokenAst:
    primary: Token
    modifier: Optional[Token]

@dataclass
class AccessModifierAst:
    modifier: TokenAst

@dataclass
class IdentifierAst:
    identifier: str
    separator: TokenAst

@dataclass
class GenericIdentifierAst:
    identifier: str
    generic: list[TypeGenericArgumentAst]

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

@dataclass
class ImportDefinitionsAst:
    parent_directories: int
    module: IdentifierAst
    what_to_import: ImportTypesAst

@dataclass
class ImportBlockAst:
    imports: list[ImportDefinitionsAst]

@dataclass
class ModuleImplementationAst:
    members: list[ModuleMemberAst]
    imports: ImportBlockAst

@dataclass
class ModulePrototypeAst:
    modifier: Optional[AccessModifierAst]
    identifier: IdentifierAst
    body: ModuleImplementationAst

@dataclass
class ClassInstanceAttributeAst:
    modifier: Optional[AccessModifierAst]
    mutable: bool
    identifier: IdentifierAst
    type_annotation: TypeAst

@dataclass
class ClassStaticAttributeAst:
    modifier: Optional[AccessModifierAst]
    mutable: bool
    identifier: IdentifierAst
    value: ExpressionAst

@dataclass
class ClassImplementationAst:
    members: list[ClassAttributeAst]

@dataclass
class ClassPrototypeAst:
    decorators: list[DecoratorAst]
    partial: bool
    modifier: Optional[AccessModifierAst]
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    where_block: Optional[WhereBlockAst]
    body: ClassImplementationAst

@dataclass
class FunctionPrototypeAst:
    decorators: list[DecoratorAst]
    modifier: Optional[AccessModifierAst]
    is_async: bool
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    parameters: list[FunctionParameterAst]
    return_type: Optional[TypeAst]
    where_block: Optional[WhereBlockAst]
    value_guard: Optional[ValueGuardAst]
    body: list[StatementAst]

@dataclass
class FunctionArgumentAst:
    identifier: Optional[IdentifierAst]
    value: ExpressionAst

@dataclass
class FunctionParameterAst:
    identifier: IdentifierAst
    type_annotation: TypeAst
    default_value: Optional[ExpressionAst]
    is_mutable: bool
    is_variadic: bool

@dataclass
class FunctionImplementationAst:
    body: list[StatementAst]

@dataclass
class EnumMemberAst:
    identifier: IdentifierAst
    value: Optional[ExpressionAst]

@dataclass
class EnumImplementationAst:
    members: list[EnumMemberAst]

@dataclass
class EnumPrototypeAst:
    modifier: Optional[AccessModifierAst]
    identifier: IdentifierAst
    body: EnumImplementationAst

@dataclass
class WhereBlockAst:
    constraints: list[WhereConstraintAst]

@dataclass
class WhereConstraintAst:
    types_to_constrain: list[GenericIdentifierAst]
    constraints: list[GenericIdentifierAst]

@dataclass
class ValueGuardAst:
    value: ExpressionAst

@dataclass
class DecoratorAst:
    identifier: IdentifierAst
    type_arguments: list[TypeGenericArgumentAst]
    arguments: list[FunctionArgumentAst]

@dataclass
class UnaryExpressionAst:
    op: TokenAst
    rhs: ExpressionAst

@dataclass
class BinaryExpressionAst:
    op: TokenAst
    lhs: ExpressionAst
    rhs: ExpressionAst

@dataclass
class MultiAssignmentExpressionAst:
    lhs: list[ExpressionAst]
    rhs: list[ExpressionAst]

@dataclass
class PostfixExpressionAst:
    op: TokenAst
    lhs: ExpressionAst

@dataclass
class ParenthesizedExpressionAst:
    expression: ExpressionAst

@dataclass
class LambdaParameterAst:
    is_mutable: bool
    identifier: IdentifierAst

@dataclass
class LambdaCaptureItemAst:
    identifier: Optional[IdentifierAst]
    expression: ExpressionAst

@dataclass
class LambdaAst:
    captures: list[LambdaCaptureItemAst]
    parameters: list[LambdaParameterAst]
    expression: ExpressionAst

@dataclass
class TypeGenericParameterAst:
    identifier: IdentifierAst
    constraints: list[GenericIdentifierAst]
    default: Optional[TypeAst]
    is_variadic: bool

@dataclass
class TypeGenericArgumentAst:
    identifier: Optional[IdentifierAst]
    value: TypeAst

@dataclass
class TypeAst:
    reference_type: TokenAst
    identifier: GenericIdentifierAst
    postfixes: list[TokenAst]
    next_variant: Optional[TypeAst]

@dataclass
class IfStatementBranchAst:
    definitions: list[LetStatementAst]
    condition: ExpressionAst
    body: list[StatementAst]

@dataclass
class IfStatementAst:
    branches: list[IfStatementBranchAst]

@dataclass
class WhileStatementAst:
    condition: ExpressionAst
    body: list[StatementAst]

@dataclass
class ForStatementAst:
    identifiers: list[LocalVariableAst]
    iterable: ExpressionAst
    body: list[StatementAst]

@dataclass
class DoWhileStatementAst:
    body: list[StatementAst]
    condition: ExpressionAst

@dataclass
class MatchStatementAst:
    value: ExpressionAst
    cases: list[CaseStatements]

@dataclass
class CaseStatements:
    pattern: ExpressionAst
    guard: Optional[ValueGuardAst]
    body: list[StatementAst]

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
class TypedefAst:
    new_type: GenericIdentifierAst
    old_type: TypeAst

@dataclass
class LetStatementAst:
    variables: list[LocalVariableAst]
    values: list[ExpressionAst]
    type_annotation: Optional[TypeAst]

@dataclass
class LocalVariableAst:
    identifier: IdentifierAst
    is_mutable: bool


@dataclass
class SupImplementationAst:
    members: list[SupMemberAst]

@dataclass
class SupPrototypeNormalAst:
    identifier: IdentifierAst
    generic_parameters: list[TypeGenericParameterAst]
    where_block: Optional[WhereBlockAst]
    body: SupImplementationAst

@dataclass
class SupPrototypeInheritanceAst(SupPrototypeNormalAst):
    super_class: GenericIdentifierAst

@dataclass
class SupMethodPrototypeAst(FunctionPrototypeAst):
    pass

@dataclass
class SupTypedefAst(TypedefAst):
    modifier: Optional[AccessModifierAst]

@dataclass
class PostfixFunctionCallAst:
    arguments: list[FunctionArgumentAst]
    is_variadic: bool

@dataclass
class PostfixMemberAccessAst:
    separator: TokenAst
    identifier: IdentifierAst

@dataclass
class PostfixIndexAccessAst:
    index: ExpressionAst

@dataclass
class PostfixSliceAccessAst:
    start: Optional[ExpressionAst]
    end: Optional[ExpressionAst]
    step: Optional[ExpressionAst]

@dataclass
class PostfixStructInitializerAst:
    fields: dict[IdentifierAst | TokenAst, ExpressionAst]

@dataclass
class PostfixCastAst:
    cast_type: TypeAst

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
class NumberLiteralBase2Ast:
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
class MapLiteralAst:
    fields: list[PairLiteralAst]

@dataclass
class PairLiteralAst:
    key: ExpressionAst
    value: ExpressionAst

@dataclass
class RegexLiteralAst:
    value: str

@dataclass
class TupleLiteralAst:
    values: list[ExpressionAst]

@dataclass
class IterableRangeAst:
    start: ExpressionAst
    end: Optional[ExpressionAst]
    step: Optional[ExpressionAst]

@dataclass
class IterableFixedAst:
    values: list[ExpressionAst]

@dataclass
class IterableComprehensionAst:
    expression: ExpressionAst
    variables: list[LocalVariableAst]
    iterating: ExpressionAst
    guard: Optional[ExpressionAst]


PostfixOperationAst = PostfixFunctionCallAst | PostfixMemberAccessAst | PostfixIndexAccessAst | PostfixSliceAccessAst | PostfixStructInitializerAst | PostfixCastAst | TokenAst
ListLiteralAst = IterableRangeAst | IterableFixedAst | IterableComprehensionAst
GeneratorLiteralAst = IterableRangeAst | IterableComprehensionAst
SetLiteralAst = IterableRangeAst | IterableFixedAst | IterableComprehensionAst
NumberLiteralAst = NumberLiteralBase10Ast | NumberLiteralBase16Ast | NumberLiteralBase2Ast
LiteralAst = NumberLiteralAst | StringLiteralAst | CharLiteralAst | BoolLiteralAst | ListLiteralAst | GeneratorLiteralAst | MapLiteralAst | SetLiteralAst | PairLiteralAst | RegexLiteralAst | TupleLiteralAst
PrimaryExpressionAst = LiteralAst | IdentifierAst | ParenthesizedExpressionAst | LambdaAst
ExpressionAst = UnaryExpressionAst | BinaryExpressionAst | PostfixExpressionAst | MultiAssignmentExpressionAst | PrimaryExpressionAst
StatementAst = IfStatementAst | WhileStatementAst | ForStatementAst | DoWhileStatementAst | MatchStatementAst | WithStatementAst | ReturnStatementAst | YieldStatementAst | TypedefAst | LetStatementAst | ExpressionAst
ModuleMemberAst = EnumPrototypeAst | ClassPrototypeAst | FunctionPrototypeAst | SupPrototypeNormalAst | SupPrototypeInheritanceAst
ClassAttributeAst = ClassInstanceAttributeAst | ClassStaticAttributeAst
SupMemberAst = SupMethodPrototypeAst | SupTypedefAst