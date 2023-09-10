from __future__ import annotations

import hashlib
from typing import Optional
from dataclasses import dataclass, field

from src.LexicalAnalysis.Tokens import Token, TokenType

# TODO : Default ._tok to -1
# TODO : Rename ._tok to .pos
# TODO : Add a parent access?


@dataclass
class ProgramAst:
    module: ModulePrototypeAst
    eof: TokenAst
    _tok: int

    def __str__(self):
        s = str(self.module)
        s += "\n\n### END OF FILE ###\n\n"
        return s

@dataclass
class TokenAst:
    tok: Token
    _tok: int

    def __str__(self):
        return self.tok.token_metadata

    def __hash__(self):
        return hash(self.tok.token_type)

@dataclass
class ParameterPassingConventionReferenceAst:
    is_mutable: bool
    _tok: int

    def __eq__(self, other):
        return isinstance(other, ParameterPassingConventionReferenceAst) and self.is_mutable == other.is_mutable

    def __str__(self):
        return "&" + ("mut " if self.is_mutable else "")

    def __hash__(self):
        return hash(BoolLiteralAst(self.is_mutable, self._tok))

@dataclass
class IdentifierAst:
    identifier: str
    _tok: int

    def __init__(self, identifier, tok):
        self.identifier = identifier
        self._tok = tok

    def __hash__(self):
        h = hashlib.md5(self.identifier.encode()).digest()
        return int.from_bytes(h, "big")

    def __eq__(self, other):
        return isinstance(other, IdentifierAst) and self.identifier == other.identifier

    def __str__(self):
        return self.identifier

    def __add__(self, other: str) -> IdentifierAst:
        return IdentifierAst(self.identifier + other, self._tok)

    def __radd__(self, other: str) -> IdentifierAst:
        return IdentifierAst(other + self.identifier, self._tok)

    def to_generic_identifier(self) -> GenericIdentifierAst:
        return GenericIdentifierAst(self.identifier, [], self._tok)

    def is_special(self):
        return self.identifier.startswith("__") and self.identifier.endswith("__")

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
        return self.identifier + ("[" + ", ".join([str(arg) for arg in self.generic_arguments]) + "]" if self.generic_arguments else "")

    def to_identifier(self) -> IdentifierAst:
        return IdentifierAst(self.identifier, self._tok)

# @dataclass
# class SelfTypeAst:
#     _tok: int
#     identifier: str
#
#     def __init__(self, _tok: int):
#         self._tok = _tok
#         self.identifier = "Self"
#
#     def __eq__(self, other):
#         return isinstance(other, SelfTypeAst)
#
#     def __str__(self):
#         return "Self"
#
#     def __hash__(self):
#         return hash(IdentifierAst("Self", self._tok))

@dataclass
class ImportTypeAst:
    imported_type: IdentifierAst
    alias: Optional[IdentifierAst]
    _tok: int

    def __str__(self):
        s = str(self.imported_type)
        s += " as " + str(self.alias) if self.alias else ""
        return s

@dataclass
class ImportTypesAst:
    individual_types: list[ImportTypeAst]
    import_all: bool
    _tok: int

    def __str__(self):
        s = ""
        s += "*" if self.import_all else ""
        s += "{" + ", ".join([str(individual_type) for individual_type in self.individual_types]) + "}" if len(self.individual_types) > 1 else str(self.individual_types[0])
        return s

def ImportTypesAllAst(_tok: int):
    return ImportTypesAst([], True, _tok)

def ImportTypesIndividualAst(individual_types: list[ImportTypeAst], _tok: int):
    return ImportTypesAst(individual_types, False, _tok)

@dataclass
class ImportStatementAst:
    module: ImportIdentifierAst
    what_to_import: ImportTypesAst
    _tok: int

    def __str__(self):
        s = "use " + str(self.module) + "."
        s += str(self.what_to_import)
        return s

@dataclass
class ImportIdentifierAst:
    parts: list[IdentifierAst]
    _tok: int

    def __str__(self):
        return "/".join([str(part) for part in self.parts])

    def __hash__(self):
        return hash(tuple(self.parts)) if len(self.parts) else hash(self.parts[0])

    def __eq__(self, other):
        return isinstance(other, ImportIdentifierAst) and self.parts == other.parts

    def remove_last(self):
        return ImportIdentifierAst(self.parts[:-1], self._tok)

@dataclass
class ImportBlockAst:
    imports: list[ImportStatementAst]
    _tok: int

    def __str__(self):
        s = "\n".join([str(i) for i in self.imports])
        return s

@dataclass
class ModuleImplementationAst:
    import_block: ImportBlockAst
    members: list[ModuleMemberAst]
    _tok: int

    def __str__(self):
        s = str(self.import_block) + "\n" if self.import_block else ""
        s += "\n".join([str(member) for member in self.members])
        return s

@dataclass
class ModulePrototypeAst:
    decorators: list[DecoratorAst]
    identifier: ModuleIdentifierAst
    body: ModuleImplementationAst
    _tok: int

    def __str__(self):
        s = "\n".join([str(dec) for dec in self.decorators]) + "\n" if self.decorators else ""
        s += "mod " + str(self.identifier) + "\n"
        s += str(self.body)
        return s

@dataclass
class ClassAttributeAst:
    decorators: list[DecoratorAst]
    identifier: IdentifierAst
    type_annotation: TypeAst
    _tok: int

    def __str__(self):
        s = "\n".join([str(dec) for dec in self.decorators]) + "\n" if self.decorators else ""
        s += str(self.identifier) + ": "
        s += str(self.type_annotation)
        return s

@dataclass
class ClassImplementationAst:
    members: list[ClassAttributeAst]
    _tok: int

    def __str__(self):
        return "\n".join([str(member) for member in self.members])

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
        s = "\n".join([str(dec) for dec in self.decorators]) + "\n" if self.decorators else ""
        s += "cls " + self.identifier.identifier
        s += ("[" + ", ".join([str(param) for param in self.generic_parameters]) + "]" if self.generic_parameters else "")
        s += str(self.where_block) + "\n" if self.where_block else ""
        s += "{" + str(self.body) + "}\n"

        return s

    def to_type(self) -> TypeAst:
        return TypeSingleAst([GenericIdentifierAst(self.identifier.identifier, [None for x in range(len(self.generic_parameters))], self.identifier._tok)], self._tok)

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
        s = repr(self)
        return s

    def __repr__(self):
        s = "fn " if not self.is_coro else "gn "
        s += str(self.identifier)
        s += ("[" + ", ".join([str(param) for param in self.generic_parameters]) + "]" if self.generic_parameters else "")
        s += "(" + ", ".join([str(param) for param in self.parameters]) + ")"
        s += (" -> " + str(self.return_type) if self.return_type else "")
        s += str(self.body)
        return s

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

    def __hash__(self):
        return hash((self.identifier, self.calling_convention, self.value, self.unpack))

def FunctionArgumentNamedAst(identifier: IdentifierAst, convention: Optional[TokenAst], value: ExpressionAst, _tok: int):
    return FunctionArgumentAst(identifier, value, convention, False, _tok)

def FunctionArgumentNormalAst(convention: Optional[TokenAst], value: ExpressionAst, unpack: bool, _tok: int):
    return FunctionArgumentAst(None, value, convention, unpack, _tok)

@dataclass
class FunctionParameterAst:
    is_self: bool
    is_mutable: bool
    identifier: IdentifierAst
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    type_annotation: TypeAst
    default_value: Optional[ExpressionAst]
    is_variadic: bool
    _tok: int

    def __str__(self):
        s = "mut " if self.is_mutable else ""
        s += str(self.identifier) + ": "
        s += str(self.calling_convention) if self.calling_convention else ""
        s += str(self.type_annotation)
        s += (" = " + str(self.default_value)) if self.default_value else ""
        return s

def FunctionParameterSelfAst(calling_convention: Optional[ParameterPassingConventionReferenceAst] | TokenAst, _tok: int):
    self_type = TypeSingleAst([GenericIdentifierAst("Self", [], _tok)], _tok)
    param = None
    match calling_convention:
        case TokenAst(): param =  FunctionParameterAst(True, True, IdentifierAst("self", _tok), None, self_type, None, False, _tok)
        case _: param = FunctionParameterAst(True, False, IdentifierAst("self", _tok), calling_convention, self_type, None, False, _tok)
    return param


def FunctionParameterRequiredAst(is_mutable: bool, identifier: IdentifierAst, calling_convention: Optional[TokenAst], type_annotation: TypeAst, _tok: int):
    return FunctionParameterAst(False, is_mutable, identifier, calling_convention, type_annotation, None, False, _tok)

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

    def __str__(self):
        s = "{\n" + ("\n".join(["" + str(statement) for statement in self.statements]) if self.statements else "") + "}\n"
        return s

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

    def __str__(self):
        s = "@" + str(self.identifier)
        s += ("[" + ", ".join([str(arg) for arg in self.generic_arguments]) + "]" if self.generic_arguments else "")
        s += "(" + ", ".join([str(arg) for arg in self.arguments]) + ")"
        return s

@dataclass
class BinaryExpressionAst:
    lhs: ExpressionAst
    op: TokenAst
    rhs: ExpressionAst
    _tok: int

    def __str__(self):
        return str(self.lhs) + " " + str(self.op) + " " + str(self.rhs)

@dataclass
class AssignmentExpressionAst:
    lhs: list[ExpressionAst]
    op: TokenAst # always "=", just to store token position
    rhs: ExpressionAst
    _tok: int

    def __str__(self):
        return ", ".join([str(lhs) for lhs in self.lhs]) + " = " + str(self.rhs)

@dataclass
class PostfixExpressionAst:
    lhs: ExpressionAst
    op: PostfixOperationAst
    _tok: int

    def __str__(self):
        s = str(self.lhs)
        s += str(self.op)
        return s

    def __hash__(self):
        return hash(self.lhs) + hash(self.op)
    
    def __eq__(self, other):
        return isinstance(other, PostfixExpressionAst) and self.lhs == other.lhs and self.op == other.op

@dataclass
class PlaceholderAst:
    _tok: int

    def __str__(self):
        return "_"

@dataclass
class LambdaParameterAst:
    is_mutable: bool
    identifier: IdentifierAst
    _tok: int

    def __str__(self):
        s = "mut " if self.is_mutable else ""
        s += str(self.identifier)
        return s

@dataclass
class LambdaCaptureItemAst:
    identifier: Optional[IdentifierAst]
    calling_convention: Optional[ParameterPassingConventionReferenceAst]
    capture: IdentifierAst
    _tok: int

    def __str__(self):
        s = (str(self.identifier) + " = ") if self.identifier else ""
        s += str(self.calling_convention) if self.calling_convention else ""
        s += str(self.capture)
        return s

@dataclass
class LambdaAst:
    captures: list[LambdaCaptureItemAst]
    parameters: list[LambdaParameterAst]
    body: list[StatementAst]
    _tok: int

    def __str__(self):
        s = "[" + ", ".join([str(capture) for capture in self.captures]) + "]" if self.captures else ""
        s += "(" + ", ".join([str(param) for param in self.parameters]) + ") -> "
        s += "{" + "\n".join([str(statement) for statement in self.body]) + "}\n"
        return s

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
        return ("..." if self.is_variadic else "") + self.identifier.identifier

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        return isinstance(other, TypeGenericParameterAst) and self.identifier == other.identifier and self.constraints == other.constraints and self.is_variadic == other.is_variadic

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
    parts: list[GenericIdentifierAst | int]
    _tok: int

    def __eq__(self, other):
        return isinstance(other, TypeSingleAst) and self.parts == other.parts

    def __hash__(self):
        return hash(tuple(self.parts))

    def __str__(self):
        return ".".join([str(part) for part in self.parts])

    def to_identifier(self):
        s = ".".join([part.to_identifier().identifier for part in self.parts])
        return IdentifierAst(s, self._tok)

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

    def __str__(self):
        s = "if "
        s += str(self.condition) + " {\n"
        s += " " + str(self.comparison_op) + " " if self.comparison_op else " "
        s += "\n".join([str(branch) for branch in self.branches]) + "}\n"
        return s

    def __hash__(self):
        return hash((self.condition, *self.branches))

@dataclass
class PatternStatementAst:
    comparison_op: Optional[TokenAst]
    patterns: list[PatternAst]
    guard: Optional[ExpressionAst]
    body: list[StatementAst]
    _tok: int

    def __str__(self):
        s = str(self.comparison_op) if self.comparison_op else ""
        s += ", ".join([str(pattern) for pattern in self.patterns])
        s += (" && " + str(self.guard)) if self.guard else ""
        s += " { " + "\n".join([str(statement) for statement in self.body]) + " }"
        return s

    def __hash__(self):
        return hash((*self.patterns, self.guard))

@dataclass
class PatternAst:
    value: ExpressionAst
    _tok: int

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value)

@dataclass
class WhileStatementAst:
    condition: ExpressionAst
    body: list[StatementAst]
    else_: Optional[InnerScopeAst]
    _tok: int

    def __str__(self):
        s = "while "
        s += str(self.condition) + " {\n"
        s += "\n".join([str(statement) for statement in self.body]) + "}"
        s += (" else { " + str(self.else_) + " }") if self.else_ else "\n"
        return s

@dataclass
class WithStatementAst:
    value: ExpressionAst
    alias: Optional[LocalVariableAst]
    body: list[StatementAst]
    _tok: int

    def __str__(self):
        s = "with "
        s += str(self.value)
        s += ((" as " + str(self.alias)) if self.alias else "") + " {\n"
        s += "\n".join([str(statement) for statement in self.body]) + "}\n"
        return s

@dataclass
class ReturnStatementAst:
    value: Optional[ExpressionAst]
    _tok: int

    def __str__(self):
        s = "return "
        s += str(self.value) if self.value else ""
        return s

@dataclass
class YieldStatementAst:
    convention: Optional[ParameterPassingConventionReferenceAst]
    value: Optional[ExpressionAst]
    _tok: int

    def __str__(self):
        s = "yield "
        s += str(self.convention) if self.convention else ""
        s += str(self.value) if self.value else ""
        return s

@dataclass
class TypedefStatementAst:
    new_type: TypeAst
    old_type: TypeAst
    _tok: int

    def __str__(self):
        s = "use "
        s += str(self.new_type) + " as " + str(self.old_type)
        return s

@dataclass
class LetStatementAst:
    variables: list[LocalVariableAst]
    value: Optional[ExpressionAst]
    type_annotation: Optional[TypeAst]
    if_null: Optional[InnerScopeAst]
    _tok: int

    def __str__(self):
        s = "let "
        s += ", ".join([str(var) for var in self.variables])
        s += " = " if self.value else ": "
        s += str(self.value) if self.value else str(self.type_annotation)
        s += " else { " + str(self.if_null) + " }" if self.if_null else ""
        return s

@dataclass
class InnerScopeAst:
    body: list[StatementAst]
    _tok: int

    def __str__(self):
        s = "{\n"
        s += "\n".join([str(statement) for statement in self.body]) + "}\n"
        return s

@dataclass
class LocalVariableAst:
    is_mutable: bool
    identifier: IdentifierAst
    _tok: int

    def __str__(self):
        s = "mut " if self.is_mutable else ""
        s += str(self.identifier)
        return s

@dataclass
class SupImplementationAst:
    members: list[SupMemberAst]
    _tok: int

    def __str__(self):
        return " {\n" + "\n".join([str(member) for member in self.members]) + "\n}\n"

@dataclass
class SupPrototypeNormalAst:
    generic_parameters: list[TypeGenericParameterAst]
    identifier: TypeAst
    where_block: Optional[WhereBlockAst]
    body: SupImplementationAst
    _tok: int

    def __str__(self):
        s = "sup "
        s += ("[" + ", ".join([str(param) for param in self.generic_parameters]) + "]" if self.generic_parameters else "")
        s += str(self.identifier)
        s += str(self.where_block) + "\n" if self.where_block else ""
        s += str(self.body)
        return s

    def to_type(self):
        return self.identifier

@dataclass
class SupPrototypeInheritanceAst(SupPrototypeNormalAst):
    super_class: TypeAst
    _tok: int

    def __str__(self):
        s = "sup "
        s += ("[" + ", ".join([str(param) for param in self.generic_parameters]) + "]" if self.generic_parameters else "")
        s += str(self.super_class) + " for "
        s += str(self.identifier)
        s += str(self.where_block) + "\n" if self.where_block else ""
        s += str(self.body)
        return s

@dataclass
class SupMethodPrototypeAst(FunctionPrototypeAst):
    _tok: int

    def __str__(self):
        return super().__repr__()

@dataclass
class SupTypedefAst(TypedefStatementAst):
    decorators: list[DecoratorAst]

@dataclass
class PostfixFunctionCallAst:
    type_arguments: list[TypeGenericArgumentAst]
    arguments: list[FunctionArgumentAst]
    _tok: int
    generic_map: dict[IdentifierAst, TypeAst] = field(default_factory=dict)

    def __str__(self):
        s = "[" + ", ".join([str(arg) for arg in self.type_arguments]) + "]" if self.type_arguments else ""
        s += "(" + ", ".join([str(arg) for arg in self.arguments]) + ")"
        return s

    def __hash__(self):
        return hash(tuple(self.type_arguments)) + hash(tuple(self.arguments))

    def __eq__(self, other):
        return isinstance(other, PostfixFunctionCallAst) and self.type_arguments == other.type_arguments and self.arguments == other.arguments

@dataclass
class PostfixMemberAccessAst:
    identifier: IdentifierAst | int
    _tok: int
    generic_map: dict[IdentifierAst, TypeAst] = field(default_factory=dict)

    def __str__(self):
        return "." + str(self.identifier)

    def __hash__(self):
        return hash(self.identifier)
    
    def __eq__(self, other):
        return isinstance(other, PostfixMemberAccessAst) and self.identifier == other.identifier

@dataclass
class PostfixStructInitializerAst:
    fields: list[PostfixStructInitializerFieldAst]
    _tok: int
    generic_map: dict[IdentifierAst, TypeAst] = field(default_factory=dict)

    def __str__(self):
        s = "{" + ", ".join([str(field) for field in self.fields]) + "}"
        return s

    def __hash__(self):
        return hash(tuple(self.fields))

    def __eq__(self, other):
        return isinstance(other, PostfixStructInitializerAst) and self.fields == other.fields

@dataclass
class PostfixStructInitializerFieldAst:
    identifier: IdentifierAst | TokenAst
    value: Optional[ExpressionAst]
    _tok: int

    def __str__(self):
        s = str(self.identifier)
        s += ("=" + str(self.value)) if self.value else ""
        return s

    def __hash__(self):
        return hash(self.identifier)

    def __eq__(self, other):
        return isinstance(other, PostfixStructInitializerFieldAst) and self.identifier == other.identifier and self.value == other.value

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

    def __hash__(self):
        return hash(IdentifierAst((self.integer or "") + (self.decimal or ""), self._tok))

@dataclass
class NumberLiteralBase16Ast:
    value: str
    _tok: int

    def __str__(self):
        return self.value

@dataclass
class NumberLiteralBase02Ast:
    value: str
    _tok: int

    def __str__(self):
        return self.value

@dataclass
class NumberExponentAst:
    sign: Optional[TokenAst]
    value: str
    _tok: int

    def __str__(self):
        s = self.sign.tok.token_metadata if self.sign else ""
        s += self.value
        return s

@dataclass
class StringLiteralAst:
    value: str
    _tok: int

    def __str__(self):
        return self.value

    def __hash__(self):
        return hash(IdentifierAst(self.value, self._tok))

@dataclass
class ArrayLiteralAst:
    values: list[ExpressionAst]
    _tok: int

    def __str__(self):
        return "[" + ", ".join([str(value) for value in self.values]) + "]"

    def __hash__(self):
        return hash(tuple(self.values))

@dataclass
class BoolLiteralAst:
    value: bool
    _tok: int

    def __str__(self):
        return "true" if self.value else "false"

    def __hash__(self):
        return hash(IdentifierAst(str(self), self._tok))

@dataclass
class RegexLiteralAst:
    value: str
    _tok: int

    def __str__(self):
        return self.value

    def __hash__(self):
        return hash(IdentifierAst(self.value, self._tok))

@dataclass
class TupleLiteralAst:
    values: list[ExpressionAst]
    _tok: int

    def __str__(self):
        return "(" + ", ".join([str(value) for value in self.values]) + ")"

    def __hash__(self):
        return hash(tuple(self.values))


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
