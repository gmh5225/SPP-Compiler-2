from __future__ import annotations

import builtins
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Hashable, Optional, TypeVar, Callable

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import ErrFmt


T = TypeVar("T")


class VariableSymbolMemoryStatus:
    is_borrowed_ref: bool
    is_borrowed_mut: bool
    is_initialized: bool
    is_partially_moved: bool

    consume_ast: Any
    borrow_ast: Any
    initialization_ast: Any
    partially_moved_asts: list


    def __init__(self):
        self.is_borrowed_ref = False
        self.is_borrowed_mut = False
        self.is_initialized = False
        self.is_partially_moved = False

        self.consume_ast = None
        self.borrow_ast = None
        self.initialization_ast = None
        self.partially_moved_asts = []

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
        is_comptime: bool

        def __init__(self, name: Ast.IdentifierAst, type: Ast.TypeAst, **kwargs):
            self.name = name
            self.type = type
            self.mem_info = VariableSymbolMemoryStatus()
            self.is_mutable = kwargs.get("is_mutable", False)
            self.is_comptime = kwargs.get("is_comptime", False)
            self.meta_data = {}

            self.mem_info.is_initialized = kwargs.get("is_initialized", False)

        def json(self) -> dict:
            return {
                "name": str(self.name),
                "type": str(self.type),
                "is_mutable": self.is_mutable
            }

        def __str__(self):
            return f"Variable Symbol({self.name}: {self.type})"

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
    is_mod: bool

    visited: bool
    hidden: bool

    def __init__(self, id: Hashable, parent: Optional[Scope], hidden: bool = False, is_mod: bool = False):
        self.name = id
        self.id = hash(id)
        self.parent = parent
        self.symbol_table = SymbolTable()
        self.children = []
        self.sup_scopes = []
        self.is_mod = is_mod

        self.visited = False
        self.hidden = hidden

        if parent is not None:
            parent.children.append(self)

    def level_of_sup_scope(self, other: Scope) -> int:
        def inner(s: Scope, t: Scope, level: int) -> int:

            if s == t: return level
            if not s.sup_scopes: return -1

            for sup_scope in [sc for sc in s.sup_scopes if not isinstance(sc.name, str)]:
                l = inner(sup_scope, t, level + 1)
                if l != -1: return l
            return -1

        return inner(self, other, 0)

    def where_to_look(self, name: Hashable, expected_sym_type: type[T], error=True) -> tuple[Optional[Scope], Optional[Hashable]]:
        if expected_sym_type == SymbolTypes.TypeSymbol and "." in str(name):
            where = self
            while where.parent:
                where = where.parent

            parts = name.identifier.split(".")
            i = 0
            while parts[i].islower():
                p = parts[i]
                where = [c for c in where.children if str(c.name).replace("/", ".") == p]
                if len(where) == 0:
                    if error:
                        raise SystemExit(
                            f"Could not find module-part/namespace '{p}'." +
                            ErrFmt.err(name._tok) + f"Symbol '{p}' used here")
                    else:
                        return None, None
                where = where[0]
                i += 1
            return where, Ast.IdentifierAst(".".join(parts[i:]), name._tok)
        return self, name

    def add_symbol(self, symbol: SymbolTypes.Symbol):
        if self.symbol_table.has(symbol.name, SymbolTypes.TypeSymbol):
            raise SystemExit(f"Symbol '{symbol.name}' already exists." +
                ErrFmt.err(self.symbol_table.get(symbol.name, SymbolTypes.TypeSymbol).type.identifier._tok) + "Symbol defined here\n..." +
                ErrFmt.err(symbol.type.identifier._tok) + "Symbol redefined here")
        self.symbol_table.add(symbol)

    def get_symbol(self, name: Hashable, expected_sym_type: type[T], error=True) -> T:
        where, name = self.where_to_look(name, expected_sym_type, error=error)

        # combine this, sup-scopes and parents (recursively) into one symbol table
        combined_symbol_tables = SymbolTable()
        combined_symbol_tables.symbols = {**where.symbol_table.symbols}
        for sup_scope in where.sup_scopes:
            combined_symbol_tables.symbols = {**combined_symbol_tables.symbols, **sup_scope.symbol_table.symbols}

        sym = None
        try:
            sym = combined_symbol_tables.get(name, expected_sym_type)
        except KeyError:
            if where.parent and where == self:
                sym = where.parent.get_symbol(name, expected_sym_type, error=False)
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
        where, name = self.where_to_look(name, expected_sym_type, error=error)

        combined_symbol_tables = SymbolTable()
        combined_symbol_tables.symbols = {**where.symbol_table.symbols}
        for sup_scope in where.sup_scopes:
            combined_symbol_tables.symbols = {**combined_symbol_tables.symbols, **sup_scope.symbol_table.symbols}

        try:
            return combined_symbol_tables.get(name, expected_sym_type)
        except KeyError as e:
            if error:
                raise e
            else:
                return None

    def has_symbol(self, name: Hashable, expected_sym_type: type[T]) -> bool:
        where, name = self.where_to_look(name, expected_sym_type, error=False)

        found = where.has_symbol_exclusive(name, expected_sym_type)
        if not found and where.parent and where == self:
            found = where.parent.has_symbol(name, expected_sym_type)
        # if not found and expected_sym_type == SymbolTypes.TypeSymbol and not name.identifier.startswith("__MOCK_"):
        #     found = self.has_symbol("__MOCK_" + name, expected_sym_type)
        return found

    def has_symbol_exclusive(self, name: Hashable, expected_sym_type: type[T]) -> bool:#
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

    def all_symbols_names(self, expected_sym_type: type) -> list[str]:
        syms = self.all_symbols(expected_sym_type)
        return [str(s.name) for s in syms]

    def all_symbols_exclusive(self, expected_sym_type: type, **kwargs) -> list[SymbolTypes.Symbol]:
        combined_symbol_tables = [a for a in self.symbol_table.symbols.values() if isinstance(a, expected_sym_type)]
        if kwargs.get("sup", True):
            for sup_scope in self.sup_scopes:
                combined_symbol_tables += [a for a in sup_scope.symbol_table.symbols.values() if isinstance(a, expected_sym_type)]
        return combined_symbol_tables

    def all_symbols_exclusive_no_fn(self, expected_sym_type: type) -> list[SymbolTypes.Symbol]:
        syms = self.all_symbols_exclusive(expected_sym_type)
        syms = [s for s in syms if s.type.identifier.identifier not in ["FnRef", "FnMut", "FnOne"]]
        return syms

    def get_child_scope(self, id: Hashable) -> Optional[Scope]:

        def inner(part, scope):
            print(part, scope.name)
            all_scopes_to_check = [scope] + scope.sup_scopes
            children = []
            for sc in all_scopes_to_check:
                children += sc.children
            matches = [c for c in children if c.id == hash(part)]
            return matches[0] if matches else None

        if isinstance(id, Ast.TypeSingleAst):
            current = self

            # For each part of the namespace, ie std.a.b.C, we want to find the scope for std, then a, then b, as these
            # are all just nested scopes. Move in a scope for each part of the namespace, and if we can't find a scope
            # for a part, then we know that the namespace is invalid.
            for p in [q for q in str(id).split(".") if q[0].islower()]:
                current = inner(Ast.IdentifierAst(p, id._tok), current)
                if not current: return None # todo : error?

            # Get the class from the last part of the namespace, ie std.a.b.C. If there was no namespace, then it is
            # just the type in the global namespace, ie the scope will be the global scope, so works in the same way.
            # todo : are branches below duplicate code?
            if len(id.parts) > 1 and id.parts[-1].identifier[0].isupper():
                final_type = Ast.TypeSingleAst([id.parts[-1]], -1)
                final_type = final_type.without_generics()
                print(current.name, final_type)
                return inner(final_type, current)
            return inner(id.without_generics(), current)
        else:
            return inner(id, self)



class ScopeHandler:
    global_scope: Scope
    current_scope: Scope

    def __init__(self):
        self.global_scope  = Scope(Ast.IdentifierAst("Global", -1), None)
        self.current_scope = self.global_scope

    def enter_scope(self, name: Hashable, hidden: bool = False, is_mod: bool = False) -> None:
        self.current_scope = Scope(name, self.current_scope, hidden=hidden, is_mod=is_mod)

    def exit_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def next_scope(self) -> None:
        if any([not scope.visited for scope in self.current_scope.children]):
            unvisited_scopes = [scope for scope in self.current_scope.children if not scope.visited]
            next_scope = unvisited_scopes[0]

            if next_scope.is_mod:
                self.current_scope = next_scope
                self.next_scope()

            else:
                next_scope.visited = True
                self.current_scope = next_scope

            # next_scope.visited = True
            # self.current_scope = next_scope

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
                "children": [scope_to_json(child) for child in scope.children],
                "sup-scopes": [str(sup_scope.name) for sup_scope in scope.sup_scopes]
            }

        return scope_to_json(self.global_scope)
