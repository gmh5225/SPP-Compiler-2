"""
Construct symbol tables for each scope in the program, including the global scope.
"""

from __future__ import annotations
from src.SyntacticAnalysis import Ast
from typing import Generic, Optional, TypeVar

T = TypeVar('T')


class SymbolName(Generic[T]):
    _module_name: Ast.ModuleIdentifierAst
    _symbol_name: T

    def __init__(self, symbol_name: T, module_name: Ast.ModuleIdentifierAst = None):
        self._module_name = module_name
        self._symbol_name = symbol_name

    def __eq__(self, that):
        return self._module_name == that.module_name and self._symbol_name == that.symbol_name

    def pretty_name(self) -> str:
        return f"{'::'.join([p.identifier for p in self._module_name.parts])}::{self._symbol_name}"

    @property
    def module_name(self) -> Ast.ModuleIdentifierAst:
        return self._module_name

    @property
    def symbol_name(self) -> T:
        return self._symbol_name


class SymbolType:
    _type: Ast.TypeAst

    def __init__(self, type: Ast.TypeAst):
        self._type = type

    @property
    def type(self) -> Ast.TypeAst:
        return self._type


class Symbol(Generic[T]):
    _name: SymbolName[T]
    _type: SymbolType

    def __init__(self, name: SymbolName[T], type: Optional[SymbolType]):
        self._name = name
        self._type = type

    @property
    def name(self) -> SymbolName[T]:
        return self._name

    @property
    def type(self) -> SymbolType:
        return self._type


class SymbolTable(Generic[T]):
    _symbols: dict[SymbolName[T], Symbol]

    def __init__(self):
        self._symbols = {}

    def define(self, symbol: Symbol):
        self._symbols[symbol.name] = symbol

    def lookup(self, name: SymbolName[T]) -> Optional[Symbol]:
        return self._symbols.get(name)


class Scope:
    _symbol_table: SymbolTable[Ast.IdentifierAst]
    _type_table: SymbolTable[Ast.TypeAst]
    _tag_table: SymbolTable[Ast.TagIdentifierAst]

    _parent_scope: Optional[Scope]

    def __init__(self, parent_scope: Optional[Scope] = None):
        self._symbol_table = SymbolTable()
        self._type_table = SymbolTable()
        self._parent_scope = parent_scope

    def define_symbol(self, symbol: Symbol):
        self._symbol_table.define(symbol)

    def define_type(self, symbol: Symbol):
        self._type_table.define(symbol)

    def define_tag(self, symbol: Symbol):
        self._tag_table.define(symbol)

    def lookup_symbol(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._symbol_table.lookup(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup_symbol(name)
        return None

    def lookup_type(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._type_table.lookup(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup_type(name)
        return None

    def lookup_tag(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._tag_table.lookup(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup_tag(name)
        return None

    @property
    def parent_scope(self) -> Optional[Scope]:
        return self._parent_scope


class GlobalScope(Scope):
    _module_name: Ast.ModuleIdentifierAst

    def __init__(self, module_name: Ast.ModuleIdentifierAst):
        Scope.__init__(self)
        self._module_name = module_name

    @property
    def module_name(self) -> Ast.ModuleIdentifierAst:
        return self._module_name


class ScopeManager:
    _global_scope: GlobalScope
    _current_scope: Scope

    def __init__(self, module_name: Ast.ModuleIdentifierAst):
        self._global_scope = GlobalScope(module_name)
        self._current_scope = self._global_scope

    def define_symbol(self, symbol: Symbol):
        self._current_scope.define_symbol(symbol)

    def define_type(self, symbol: Symbol):
        self._current_scope.define_type(symbol)

    def define_tag(self, symbol: Symbol):
        self._current_scope.define_tag(symbol)

    def lookup_symbol(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        return self._current_scope.lookup_symbol(name, current_scope_only)

    def lookup_type(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        return self._current_scope.lookup_type(name, current_scope_only)

    def lookup_tag(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        return self._current_scope.lookup_tag(name, current_scope_only)

    def enter_scope(self):
        self._current_scope = Scope(self._current_scope)

    def exit_scope(self):
        self._current_scope = self._current_scope.parent_scope

    @property
    def current_scope(self) -> Scope:
        return self._current_scope

    @property
    def global_scope(self) -> Scope:
        return self._global_scope


class SymbolTableBuilder:
    @staticmethod
    def build_program(ast: Ast.ProgramAst, s: ScopeManager) -> None:
        for member in ast.module.body.members: SymbolTableBuilder._build_module_member(member, s)

    @staticmethod
    def _build_module_member(ast: Ast.ModuleMemberAst, s: ScopeManager) -> None:
        match ast:
            case Ast.FunctionPrototypeAst: SymbolTableBuilder._build_function_prototype(ast, s)
            case Ast.ClassPrototypeAst: SymbolTableBuilder._build_class_prototype(ast, s)
            case Ast.EnumPrototypeAst: SymbolTableBuilder._build_enum_prototype(ast, s)
            case Ast.SupPrototypeNormalAst: SymbolTableBuilder._build_sup_prototype_normal(ast, s)
            case Ast.SupPrototypeInheritanceAst: SymbolTableBuilder._build_sup_prototype_inheritance(ast, s)
            case _: raise NotImplementedError(f"Unknown module member type: {ast}")

    @staticmethod
    def _build_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeManager) -> None:
        s.define_symbol(Symbol(SymbolName(ast.identifier), SymbolType(Utils.extract_function_type(ast))))
        s.enter_scope()
        for parameter in ast.parameters: SymbolTableBuilder._build_function_parameter(parameter, s)
        for generic_p in ast.generic_parameters: SymbolTableBuilder._build_generic_parameter(generic_p, s)
        for statement in ast.body.statements: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_function_parameter(ast: Ast.FunctionParameterAst, s: ScopeManager) -> None:
        s.define_symbol(Symbol(SymbolName(ast.identifier), SymbolType(ast.type_annotation)))

    @staticmethod
    def _build_generic_parameter(ast: Ast.TypeGenericParameterAst, s: ScopeManager) -> None:
        s.define_type(Symbol(SymbolName(ast.identifier), SymbolType(ast)))

    @staticmethod
    def _build_statement(ast: Ast.StatementAst, s: ScopeManager) -> None:
        match ast:
            case Ast.IfStatementAst: SymbolTableBuilder._build_if_statement(ast, s)
            case Ast.WhileStatementAst: SymbolTableBuilder._build_while_statement(ast, s)
            case Ast.ForStatementAst: SymbolTableBuilder._build_for_statement(ast, s)
            case Ast.DoWhileStatementAst: SymbolTableBuilder._build_do_while_statement(ast, s)
            case Ast.MatchStatementAst: SymbolTableBuilder._build_match_statement(ast, s)
            case Ast.WithStatementAst: SymbolTableBuilder._build_with_statement(ast, s)
            case Ast.ReturnStatementAst: SymbolTableBuilder._build_return_statement(ast, s)
            case Ast.YieldStatementAst: SymbolTableBuilder._build_yield_statement(ast, s)
            case Ast.TypedefStatementAst: SymbolTableBuilder._build_typedef_statement(ast, s)
            case Ast.LetStatementAst: SymbolTableBuilder._build_let_statement(ast, s)
            case Ast.ExpressionAst: SymbolTableBuilder._build_expression(ast, s)
            case _: raise NotImplementedError(f"Unknown statement type: {ast}")

    @staticmethod
    def _build_if_statement(ast: Ast.IfStatementAst, s: ScopeManager) -> None:
        SymbolTableBuilder._build_if_branch(ast.if_branch, s)
        for elif_branch in ast.elif_branches: SymbolTableBuilder._build_if_branch(elif_branch, s)
        if ast.else_branch is not None: SymbolTableBuilder._build_statement(ast.else_branch, s)

    @staticmethod
    def _build_if_branch(ast: Ast.IfStatementBranchAst, s: ScopeManager) -> None:
        for inline_definition in ast.definitions: SymbolTableBuilder._build_let_statement(inline_definition, s)
        s.enter_scope()
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_while_statement(ast: Ast.WhileStatementAst, s: ScopeManager) -> None:
        s.define_tag(Symbol(SymbolName(ast.tag), None))
        s.enter_scope()
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_for_statement(ast: Ast.ForStatementAst, s: ScopeManager) -> None:
        s.define_tag(Symbol(SymbolName(ast.tag), None))
        s.enter_scope()
        iterable_type = Utils.force_tuple(TypeInference.infer_type(ast.iterable, s))
        for identifier in ast.identifiers: s.define_symbol(Symbol(SymbolName(identifier), next(iterable_type)))
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_do_while_statement(ast: Ast.DoWhileStatementAst, s: ScopeManager) -> None:
        s.define_tag(Symbol(SymbolName(ast.tag), None))
        s.enter_scope()
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

class Utils:
    @staticmethod
    def extract_function_type(ast: Ast.FunctionPrototypeAst) -> Ast.TypeAst:
        ...
