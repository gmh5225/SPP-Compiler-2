"""
Semantic analysis module
- Type checking
    - Type inference in "let" statements => only place where type-inference is used
    - Check argument types match function parameter types
- Local variable declaration and scope
    - Check variable exists in the current scope
- Function declaration and analysis
    - Check function exists in the current scope
    - Check number of arguments match function parameter count
- Method declaration and analysis
    - Encapsulation
- Attribute declaration and analysis
    - Encapsulation
- Control-flow statements
    - Check conditions are all boolean expression types
    - Check Continue/Break tags exist
- Const variable declaration / assignment
    - Check const variables are only assigned to once
- Operators
    - Check operator classes are implemented
- Type generics
    - Check constraints to decide which type to use
- Memory analysis
    - No mutable and immutable references to the same object at the same time
    - Max 1 mutable reference to an object at a time
"""

from __future__ import annotations

from dataclasses import dataclass

from multimethod import multimethod
from typing import Optional
from src.SyntacticAnalysis import Ast


class SemanticAnalyser:
    _ast: Ast.ProgramAst

    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast


class UninitializedSymbol:
    pass


@dataclass
class SymbolTableEntry:
    name: str
    type: str
    addr: int

class SymbolTable:
    _symbols: dict[str, SymbolTableEntry]

    def __init__(self):
        self._symbols = dict()

    def add_symbol(self, name: str, type: str, addr: int):
        self._symbols[name] = SymbolTableEntry(name, type, addr)

    def lookup(self, name: str) -> Optional[SymbolTableEntry]:
        return self._symbols.get(name, None)

class Scope:
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

class SymbolTableGenerator:
    """
    Generate a symbol table for each scope. This is used for type checking and variable declaration checking. For each
    statement that can introduce a scope, a new symbol table is created. This symbol table is then attached to the
    parent symbol statement, to allow for upwards searching of symbols.
    """

    @staticmethod
    @multimethod
    def analyse(ast: Ast.ProgramAst, program_table: SymbolTable) -> None:
        for statement in ast.module.body.members:
            SymbolTableGenerator.analyse(statement, program_table)

    @staticmethod
    @multimethod
    def analyse(ast: Ast.FunctionPrototypeAst) -> None:
        function_table = SymbolTable()
        for parameter in ast.parameters:
            function_table.add_symbol(parameter.identifier, UninitializedSymbol(), parameter.type)

