from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from multimethod import multimethod

from src.SyntacticAnalysis import Ast


@dataclass
class SymbolTableEntry:
    """
    A symbol table entry contains the name, type and address of the symbol. Modelled as a dataclass because there is no
    need for any methods, it is just a group of data representing a symbol being used in the program. There is no value
    associated with the symbol, as the semantic analysis phase does not need to know the value of the symbol, only it
    exists and what type it is.
    """
    name: str
    type: str
    addr: int


class SymbolTable:
    """
    A symbol table is a dictionary of symbol table entries, where the key is the name of the symbol, and the value is
    the symbol table entry. This is a simple implementation of a symbol table, where the symbol table is just a
    dictionary. The symbol table is used to store the symbols that are declared in the program, and is used to check
    that the symbols are declared before they are used, and that the types of the symbols are correct.
    """
    _symbols: dict[str, SymbolTableEntry]

    def __init__(self):
        self._symbols = dict()

    def add_symbol(self, name: str, type: str, addr: int):
        self._symbols[name] = SymbolTableEntry(name, type, addr)

    def lookup(self, name: str) -> Optional[SymbolTableEntry]:
        return self._symbols.get(name, None)


class Scope:
    """
    A scope is a virtual representation of a scope in the program. The scope is a region of the program where a symbol
    is declared. A scope can be nested inside another scope, and the scope can be exited to return to the parent scope.
    """
    _symbol_table: SymbolTable
    _parent_scope: Optional[Scope]

    def __init__(self, parent=None):
        self._symbol_table = SymbolTable()
        self._parent_scope = parent

    @property
    def parent_scope(self) -> Optional[Scope]:
        return self._parent_scope

    @property
    def symbol_table(self) -> SymbolTable:
        return self._symbol_table


class SymbolTableManager:
    """
    The symbol table manager is used to manage the symbol tables for each scope. It is used to enter and exit scopes,
    and to add symbols to the current scope. It is also used to lookup symbols in the current scope and parent scopes.
    """
    _global_scope: Scope
    _current_scope: Scope

    def __init__(self):
        self._global_scope = Scope()
        self._current_scope = self._global_scope

    def enter_scope(self):
        next_scope = Scope(self._current_scope)
        self._current_scope = next_scope

    def exit_scope(self):
        self._current_scope = self._current_scope.parent_scope or self._current_scope

    def add_symbol(self, name: str, type: str, addr: int):
        self._current_scope.symbol_table.add_symbol(name, type, addr)

    def lookup_symbol(self, name: str) -> Optional[SymbolTableEntry]:
        # look in this and parent scopes for the symbol
        scope = self._current_scope
        while scope:
            symbol = scope.symbol_table.lookup(name)
            if symbol:
                return symbol
            scope = scope.parent_scope
        return None


def nest_next_scope(func: callable):
    def inner(ast, manager):
        manager.enter_scope()
        func(ast, manager)
        manager.exit_scope()
    return inner


class SymbolTableGenerator:
    """
    Generate a symbol table for each scope. This is used for type checking and variable declaration checking. For each
    statement that can introduce a scope, a new symbol table is created. This symbol table is then attached to the
    parent symbol statement, to allow for upwards searching of symbols.
    """

    @staticmethod
    @multimethod
    @nest_next_scope
    def analyse(ast: Ast.ProgramAst, manager: SymbolTableManager) -> None:
        for statement in ast.module.body.members:
            SymbolTableGenerator.analyse(statement, manager)

    @staticmethod
    @multimethod
    @nest_next_scope
    def analyse(ast: Ast.FunctionPrototypeAst, manager: SymbolTableManager) -> None:
        for parameter in ast.parameters:
            SymbolTableGenerator.analyse(parameter, manager)



