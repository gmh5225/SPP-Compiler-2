from __future__ import annotations
from typing import Optional
from src.SyntacticAnalysis import Ast


class Symbol:
    _name: str
    _type: str

    def __init__(self, name: str, type: str):
        self._name = name
        self._type = type

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type


class SymbolTable:
    def __init__(self, parent: SymbolTable = None):
        self._symbols = {}

    def define(self, symbol: Symbol):
        self._symbols[symbol.name] = symbol


class Scope:
    _symbol_table: SymbolTable
    _parent_scope: Optional[Scope]

    def __init__(self, parent_scope: Optional[Scope] = None):
        self._symbol_table = SymbolTable()
        self._parent_scope = parent_scope

    def lookup(self, name: str, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._symbol_table._symbols.get(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup(name)
        return None

    def lookup_function(self, name: Ast.IdentifierAst, parameter_types: list[Ast.FunctionParameterAst], type_parameters: list[Ast.TypeGenericParameterAst], current_scope_only=False) -> Symbol:
        ...


class ScopeManager:
    _global_scope: Scope
    _current_scope: Scope

    def __init__(self):
        self._global_scope = Scope()
        self._current_scope = self._global_scope

    def enter_scope(self):
        self._current_scope = Scope(self._current_scope)

    def exit_scope(self):
        self._current_scope = self._current_scope._parent_scope if self._current_scope._parent_scope is not None else self._global_scope
