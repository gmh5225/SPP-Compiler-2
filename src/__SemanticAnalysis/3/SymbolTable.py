from __future__ import annotations
from typing import Optional
from src.SyntacticAnalysis import Ast


class Symbol:
    _name: list[Ast.IdentifierAst]
    _type: Ast.TypeAst

    def __init__(self, name: list[Ast.IdentifierAst], type: Ast.TypeAst):
        self._name = name
        self._type = type

    @property
    def name(self) -> list[Ast.IdentifierAst]:
        return self._name

    @property
    def type(self) -> Ast.TypeAst:
        return self._type

    @property
    def pretty_name(self) -> str:
        ...


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

    def lookup_function(self, name: Ast.IdentifierAst, parameter_types: list[Ast.FunctionParameterAst], type_parameters: list[Ast.TypeGenericParameterAst], current_scope_only=False) -> Ast.FunctionPrototypeAst:
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

    def define(self, symbol: Symbol):
        self._current_scope._symbol_table.define(symbol)


class SymbolTableBuilder:
    @staticmethod
    def build_symbol_table(ast: Ast.ProgramAst, scope_manager: ScopeManager) -> None:
        map(lambda m: SymbolTableBuilder._symbolize_module_member(m, scope_manager), ast.module.body.members)

    @staticmethod
    def _symbolize_module_member(ast: Ast.ModuleMemberAst, scope_manager: ScopeManager) -> None:
        match ast:
            case Ast.FunctionPrototypeAst: SymbolTableBuilder._symbolize_function_prototype(ast, scope_manager)
            case _: raise NotImplementedError(f"Symbolizing {ast.__class__.__name__} is not implemented")

    @staticmethod
    def _symbolize_function_prototype(ast: Ast.FunctionPrototypeAst, scope_manager: ScopeManager) -> None:
        scope_manager.define(Symbol(Utils.function_name(ast.identifier, scope_manager), Utils.function_type(ast)))
        scope_manager.enter_scope()
        map(lambda p: scope_manager.define(Symbol(p.identifier, p.type)), ast.parameters)


class Utils:
    @staticmethod
    def function_type(ast: Ast.FunctionPrototypeAst) -> Ast.TypeAst:
        ...

    @staticmethod
    def function_name(ast: Ast.IdentifierAst, scope_manager: ScopeManager) -> list[Ast.IdentifierAst]:
        ...
