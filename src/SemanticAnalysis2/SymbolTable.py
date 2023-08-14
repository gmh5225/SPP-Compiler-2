from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Hashable, Optional, TypeVar, Callable
from src.SyntacticAnalysis import Ast


T = TypeVar("T")


class VariableSymbolMemoryStatus:
    is_borrowed_ref: bool
    is_borrowed_mut: bool
    is_initialized: bool

    def __init__(self):
        self.is_borrowed_ref = False
        self.is_borrowed_mut = False
        self.is_initialized = False

    def is_borrowed(self):
        return self.is_borrowed_ref or self.is_borrowed_mut


class SymbolTypes:
    @dataclass
    class Symbol(ABC):
        name: Any
        meta_data: dict[str, Any]

        @abstractmethod
        def json(self) -> dict:
            ...

    class VariableSymbol(Symbol):
        name: Ast.IdentifierAst
        type: Ast.TypeAst
        mem_info: VariableSymbolMemoryStatus
        is_mutable: bool

        def __init__(self, name: Ast.IdentifierAst, type: Ast.TypeAst, **kwargs):
            self.name = name
            self.type = type
            self.mem_info = VariableSymbolMemoryStatus()
            self.is_mutable = kwargs.get("is_mutable", False)
            self.meta_data = {}

            self.mem_info.is_initialized = kwargs.get("is_initialized", False)

        def json(self) -> dict:
            return {
                "name": str(self.name),
                "type": str(self.type),
                "is_mutable": self.is_mutable
            }

    @dataclass
    class TypeSymbol(Symbol):
        name: Ast.IdentifierAst
        type: Ast.ClassPrototypeAst

        def __init__(self, name: Ast.IdentifierAst, type: Ast.ClassPrototypeAst, **kwargs):
            self.name = name
            self.type = type
            self.meta_data = {}

        def json(self) -> dict:
            return {
                "name": str(self.name)
            }

    @dataclass
    class GenericSymbol(Symbol):
        name: Ast.IdentifierAst
        type: Ast.TypeAst

        def json(self) -> dict:
            return {
                "name": str(self.name),
                "type": str(self.type)
            }


class SymbolTable:
    symbols: dict[int, SymbolTypes.Symbol]

    def __init__(self):
        self.symbols = {}

    def add(self, symbol: SymbolTypes.Symbol):
        self.symbols[hash(symbol.name)] = symbol

    def get(self, name: Hashable, expected_sym_type: type) -> SymbolTypes.Symbol | list[SymbolTypes.Symbol]:
        symbols = {k: v for k, v in self.symbols.items() if isinstance(v, expected_sym_type)}

        match expected_sym_type.__name__:
            case "VariableSymbol": return symbols[hash(name)]
            case "TypeSymbol": return symbols[hash(name)]
            case "GenericSymbol": return symbols[hash(name)]
            case _: raise SystemExit(f"Unknown symbol type '{expected_sym_type.__name__}'.")

    def has(self, name: Hashable, expected_sym_type: type) -> bool:
        return hash(name) in self.symbols and isinstance(self.symbols[hash(name)], expected_sym_type)


class Scope:
    id: int
    parent: Optional[Scope]
    symbol_table: SymbolTable
    children: list[Scope]
    sup_scopes: list[Scope]

    visited: bool
    hidden: bool

    def __init__(self, id: Hashable, parent: Optional[Scope], hidden: bool = False):
        self.name = id
        self.id = hash(id)
        self.parent = parent
        self.symbol_table = SymbolTable()
        self.children = []
        self.sup_scopes = []

        self.visited = False
        self.hidden = hidden

        if parent is not None:
            parent.children.append(self)

    def add_symbol(self, symbol: SymbolTypes.Symbol):
        self.symbol_table.add(symbol)

    def get_symbol(self, name: Hashable, expected_sym_type: type[T], error=True) -> T:
        # combine this, sup-scopes and parents (recursively) into one symbol table
        combined_symbol_tables = SymbolTable()
        combined_symbol_tables.symbols = {**self.symbol_table.symbols}
        for sup_scope in self.sup_scopes:
            combined_symbol_tables.symbols = {**combined_symbol_tables.symbols, **sup_scope.symbol_table.symbols}

        sym = None
        try:
            sym = combined_symbol_tables.get(name, expected_sym_type)
        except KeyError:
            if self.parent:
                sym = self.parent.get_symbol(name, expected_sym_type, error=False)
        if not sym and error:
            raise Exception(f"Could not find {expected_sym_type.__name__} '{name}'.")
        return sym


        # try:
        #     sym = self.symbol_table.get(name, expected_sym_type)
        # except:
        #     sym = None
        # if not sym and self.sup_scopes:
        #     for sup_scope in self.sup_scopes:
        #         sym = sup_scope.get_symbol(name, expected_sym_type, error=False)
        #         if sym:
        #             break
        # if not sym and self.parent:
        #     sym = self.parent.get_symbol(name, expected_sym_type, error=False)
        # if not sym:
        #     raise Exception(f"Could not find {expected_sym_type.__name__} '{name}'.")
        # return sym

    def get_symbol_exclusive(self, name: Hashable, expected_sym_type: type[T], error=True) -> T | list[T]:
        combined_symbol_tables = SymbolTable()
        combined_symbol_tables.symbols = {**self.symbol_table.symbols}
        for sup_scope in self.sup_scopes:
            combined_symbol_tables.symbols = {**combined_symbol_tables.symbols, **sup_scope.symbol_table.symbols}

        try:
            return combined_symbol_tables.get(name, expected_sym_type)
        except KeyError as e:
            if error:
                raise e
            else:
                return None

    def has_symbol(self, name: Hashable, expected_sym_type: type) -> bool:
        found = self.has_symbol_exclusive(name, expected_sym_type)
        if not found and self.parent:
            found = self.parent.has_symbol(name, expected_sym_type)
        if not found and expected_sym_type == SymbolTypes.TypeSymbol and not name.identifier.startswith("__MOCK_"):
            found = self.has_symbol("__MOCK_" + name, expected_sym_type)
        return found

    def has_symbol_exclusive(self, name: Hashable, expected_sym_type: type) -> bool:
        combined_symbol_tables = SymbolTable()
        combined_symbol_tables.symbols = {**self.symbol_table.symbols}
        for sup_scope in self.sup_scopes:
            combined_symbol_tables.symbols = {**combined_symbol_tables.symbols, **sup_scope.symbol_table.symbols}

        t = combined_symbol_tables.has(name, expected_sym_type)
        return t

    def all_symbols(self, expected_sym_type: type) -> list[SymbolTypes.Symbol]:
        syms = self.all_symbols_exclusive(expected_sym_type)
        if self.parent:
            syms += self.parent.all_symbols(expected_sym_type)
        return syms

    def all_symbols_exclusive(self, expected_sym_type: type) -> list[SymbolTypes.Symbol]:
        combined_symbol_tables = SymbolTable()
        combined_symbol_tables.symbols = {**self.symbol_table.symbols}
        for sup_scope in self.sup_scopes:
            combined_symbol_tables.symbols = {**combined_symbol_tables.symbols, **sup_scope.symbol_table.symbols}
        return [sym for sym in combined_symbol_tables.symbols.values() if isinstance(sym, expected_sym_type)]

    def all_symbols_exclusive_no_fn(self, expected_sym_type: type) -> list[SymbolTypes.Symbol]:
        syms = self.all_symbols_exclusive(expected_sym_type)
        syms = [s for s in syms if s.type.parts[-1].identifier != "FnRef"]
        return syms

    def get_child_scope(self, id: Hashable) -> Optional[Scope]:
        # sup_children = []
        # for sup_scope in self.sup_scopes:
        #     sup_children.extend(sup_scope.children)
        # children = self.children + sup_children
        # matches = (c for c in children if c.id == hash(id))

        # matches = (c for c in self.children if c.id == hash(id))
        # return next(matches, None)

        matches = [c for c in self.children if c.id == hash(id)]
        if not any(matches):
            for c in self.children:
                match = c.get_child_scope(id)
                if match:
                    return match
        else:
            return matches[0]


class ScopeHandler:
    global_scope: Scope
    current_scope: Scope

    def __init__(self):
        self.global_scope  = Scope(Ast.IdentifierAst("Global", -1), None)
        self.current_scope = self.global_scope

    def enter_scope(self, name: Hashable, hidden: bool = False) -> None:
        self.current_scope = Scope(name, self.current_scope, hidden=hidden)

    def exit_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def next_scope(self) -> None:
        if any([not scope.visited for scope in self.current_scope.children]):
            unvisited_scopes = [scope for scope in self.current_scope.children if not scope.visited]
            next_scope = unvisited_scopes[0]
            next_scope.visited = True
            self.current_scope = next_scope

        else:
            raise Exception("No unvisited scopes")

    def prev_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def skip_scope(self) -> None:
        self.next_scope()
        self.prev_scope()

    def switch_to_global_scope(self) -> None:
        self.current_scope = self.global_scope
        self.visit_every_scope(lambda scope: setattr(scope, "visited", False))

    def visit_every_scope(self, func: Callable) -> None:
        # Apply some function to every scope, starting from the current scope and recursively visiting children
        def visit_every_scope_helper(scope: Scope, func: Callable) -> None:
            func(scope)
            for child in scope.children:
                visit_every_scope_helper(child, func)

        current_scope = self.current_scope
        visit_every_scope_helper(current_scope, func)

    def json(self) -> dict:
        def scope_to_json(scope: Scope) -> dict:
            return {
                "id": scope.id,
                "name": str(scope.name),
                "parent": scope.parent.id if scope.parent is not None else None,
                "symbol_table": {
                    "symbols": {str(v.name): v.json() for k, v in scope.symbol_table.symbols.items()}
                },
                "scope-id": scope.id,
                "children": [scope_to_json(child) for child in scope.children]
            }

        return scope_to_json(self.global_scope)
