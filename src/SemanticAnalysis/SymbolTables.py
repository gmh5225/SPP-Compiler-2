from __future__ import annotations

import pprint
from dataclasses import dataclass
from typing import Any, Optional
from multimethod import multimethod

from src.SyntacticAnalysis import Ast


def type_string(type: Optional[Ast.TypeAst]) -> str:
    string = ""
    if type is None:
        return ""
    for part in type.parts:
        string += "::" + part.identifier
        if len(part.generic):
            string += "<"
            string += ", ".join([generic.identifier.identifier for generic in part.generic])
            string += ">"
    return string[2:]

@dataclass
class SymbolTableEntry:
    """
    A symbol table entry contains the name, type and address of the symbol. Modelled as a dataclass because there is no
    need for any methods, it is just a group of data representing a symbol being used in the program. There is no value
    associated with the symbol, as the semantic analysis phase does not need to know the value of the symbol, only it
    exists and what type it is.
    """
    name: str
    type: Ast.TypeAst


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

    def add_symbol(self, name: str, type: Ast.TypeAst):
        self._symbols[name] = SymbolTableEntry(name, type)

    def lookup(self, name: str) -> Optional[SymbolTableEntry]:
        return self._symbols.get(name, None)

    @property
    def symbols(self) -> dict[str, SymbolTableEntry]:
        return self._symbols

    def __repr__(self):
        return f"SymbolTable({', '.join([name + ': ' + type_string(type.type) for name, type in self._symbols.items()])})"


class Scope:
    """
    A scope is a virtual representation of a scope in the program. The scope is a region of the program where a symbol
    is declared. A scope can be nested inside another scope, and the scope can be exited to return to the parent scope.
    """
    _symbol_table: SymbolTable
    _type_table: SymbolTable
    _parent_scope: Optional[Scope]
    _child_scopes: list[Scope]

    def __init__(self, parent=None):
        self._symbol_table = SymbolTable()
        self._type_table = SymbolTable()
        self._parent_scope = parent
        self._child_scopes = []

        if parent:
            parent.child_scopes.append(self)

    @property
    def parent_scope(self) -> Optional[Scope]:
        return self._parent_scope

    @property
    def symbol_table(self) -> SymbolTable:
        return self._symbol_table

    @property
    def type_table(self) -> SymbolTable:
        return self._type_table

    @property
    def child_scopes(self) -> list[Scope]:
        return self._child_scopes

    def __repr__(self):
        string = f"Scope ({self._symbol_table})"
        return string


class GlobalScope(Scope):
    _scope_name: Optional[Ast.ModuleIdentifierAst]

    def __init__(self):
        super().__init__()
        self._parent_scope = None
        self._scope_name = None

    @property
    def scope_name(self) -> Ast.ModuleIdentifierAst:
        return self._scope_name

    @scope_name.setter
    def scope_name(self, value: Ast.ModuleIdentifierAst):
        assert self._scope_name is not None
        self._scope_name = value


class SymbolTableManager:
    """
    The symbol table manager is used to manage the symbol tables for each scope. It is used to enter and exit scopes,
    and to add symbols to the current scope. It is also used to lookup symbols in the current scope and parent scopes.
    """
    _global_scope: GlobalScope
    _current_scope: Scope

    def __init__(self):
        self._global_scope = GlobalScope()
        self._current_scope = self._global_scope

    def enter_scope(self):
        next_scope = Scope(self._current_scope)
        self._current_scope = next_scope

    def exit_scope(self):
        self._current_scope = self._current_scope.parent_scope or self._current_scope

    def add_symbol(self, name: str, type: Ast.TypeAst):
        self._current_scope.symbol_table.add_symbol(name, type)

    def add_type(self, name: str, type: Ast.TypeAst):
        self._current_scope.type_table.add_symbol(name, type)

    def lookup_symbol(self, name: str) -> Optional[SymbolTableEntry]:
        # look in this and parent scopes for the symbol
        return self._lookup(lambda scope: scope.symbol_table.lookup(name))

    def lookup_type(self, name: str) -> Optional[SymbolTableEntry]:
        return self._lookup(lambda scope: scope.type_table.lookup(name))

    def _lookup(self, func: callable) -> Optional[SymbolTableEntry]:
        # look in this and parent scopes for the symbol
        scope = self._current_scope
        while scope:
            symbol = func(scope)
            if symbol:
                return symbol
            scope = scope.parent_scope
        return None

    def __repr__(self):
        # Print all scopes, their child scopes, and all the symbols in every scope
        def inner_print(scope: Scope, indent: int):
            string = f"{' ' * indent}{scope}\n"
            for child_scope in scope.child_scopes:
                string += inner_print(child_scope, indent + 2)
            return string
        return inner_print(self._global_scope, 0)

    @property
    def global_scope(self) -> GlobalScope:
        return self._global_scope

    @property
    def current_scope(self) -> Scope:
        return self._current_scope



def nest_next_scope(func: callable):
    def inner(ast, manager):
        manager.enter_scope() # "".join(list(map(lambda x: x.title(), func.__name__.split("_")[2:]))))
        func(ast, manager)
        manager.exit_scope()
    return inner


class SymbolTableGenerator:
    """
    Generate a symbol table for each scope. This is used for type checking and variable declaration checking. For each
    statement that can introduce a scope, a new symbol table is created. This symbol table is then attached to the
    parent symbol statement, to allow for upwards searching of symbols. This class just manages the symbols, not
    checking if types or loop tags actually exist. No analysis happens here, just the building of the symbol tables.
    """

    @staticmethod
    @nest_next_scope
    def build_symbols_program(ast: Ast.ProgramAst, manager: SymbolTableManager) -> None:
        manager.global_scope.scope_name = ast.module.identifier
        for statement in ast.module.body.members:
            SymbolTableGenerator.build_symbols_module_member(statement, manager)

    @staticmethod
    def build_symbols_module_member(ast: Ast.ModuleMemberAst, manager: SymbolTableManager) -> None:
        match ast:
            case Ast.FunctionPrototypeAst(): SymbolTableGenerator.build_symbols_function(ast, manager)
            case Ast.MetaPrototypeAst(): raise NotImplementedError("MetaPrototypeAst not implemented")
            case Ast.SupPrototypeNormalAst(): raise NotImplementedError("SupPrototypeNormalAst not implemented")
            case Ast.SupPrototypeInheritanceAst(): raise NotImplementedError("SupPrototypeInheritanceAst not implemented")
            case Ast.ClassPrototypeAst(): SymbolTableGenerator.build_symbols_class(ast, manager)
            case Ast.EnumPrototypeAst(): raise NotImplementedError("EnumPrototypeAst not implemented")
            case _: raise NotImplementedError(f"Unknown module member: {ast.__class__.__name__}")

    @staticmethod
    @nest_next_scope
    def build_symbols_function(ast: Ast.FunctionPrototypeAst, manager: SymbolTableManager) -> None:
        for parameter in ast.parameters:
            SymbolTableGenerator.build_symbols_parameters(parameter, manager)
        for statement in ast.body.statements:
            SymbolTableGenerator.build_symbols_statement(statement, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_class(ast: Ast.ClassPrototypeAst, manager: SymbolTableManager) -> None:
        manager.add_type(ast.identifier.identifier)
        for statement in ast.body.members:
            SymbolTableGenerator.build_symbols_class_attribute(statement, manager)

    @staticmethod
    def build_symbols_class_attribute(ast: Ast.ClassAttributeAst, manager: SymbolTableManager) -> None:
        match ast:
            case Ast.ClassInstanceAttributeAst(): SymbolTableGenerator.build_symbols_class_instance_attribute(ast, manager)
            case Ast.ClassStaticAttributeAst(): SymbolTableGenerator.build_symbols_class_static_attribute(ast, manager)
            case _: raise NotImplementedError(f"Unknown class attribute: {ast.__class__.__name__}")

    @staticmethod
    def build_symbols_class_instance_attribute(ast: Ast.ClassInstanceAttributeAst, manager: SymbolTableManager) -> None:
        manager.add_symbol(ast.identifier.identifier, ast.type_annotation)

    @staticmethod
    def build_symbols_class_static_attribute(ast: Ast.ClassStaticAttributeAst, manager: SymbolTableManager) -> None:
        manager.add_symbol(ast.identifier.identifier, TypeInference.infer_type(ast.value))

    @staticmethod
    def build_symbols_parameters(ast: Ast.FunctionParameterAst, manager: SymbolTableManager) -> None:
        manager.add_symbol(ast.identifier.identifier, ast.type_annotation)

    @staticmethod
    def build_symbols_statement(ast: Ast.StatementAst, manager: SymbolTableManager) -> None:
        match ast:
            case Ast.IfStatementAst(): SymbolTableGenerator.build_symbols_if_statement(ast, manager)
            case Ast.ForStatementAst(): raise NotImplementedError("ForStatementAst not implemented")
            case Ast.WhileStatementAst(): SymbolTableGenerator.build_symbols_while_statement(ast, manager)
            case Ast.DoWhileStatementAst(): SymbolTableGenerator.build_symbols_do_while_statement(ast, manager)
            case Ast.MatchStatementAst(): SymbolTableGenerator.build_symbols_match_statement(ast, manager)
            case Ast.CaseStatementAst(): SymbolTableGenerator.build_symbols_case_statement(ast, manager)
            case Ast.WithStatementAst(): raise NotImplementedError("WithStatementAst not implemented")
            case Ast.InnerScopeAst(): SymbolTableGenerator.build_symbols_inner_scope(ast, manager)
            case Ast.LetStatementAst(): SymbolTableGenerator.build_symbols_let_statement(ast, manager)
            case Ast.FunctionPrototypeAst(): SymbolTableGenerator.build_symbols_function(ast, manager)
            case _: raise NotImplementedError(f"Unknown Statement {ast.__class__.__name__}")

    @staticmethod
    def build_symbols_if_statement(ast: Ast.IfStatementAst, manager: SymbolTableManager) -> None:
        # No @nest_next_scope because the branches themselves are new scopes, not this wrapper that contains each branch
        for branch in [ast.if_branch, *ast.elif_branches, ast.else_branch]:
            SymbolTableGenerator.build_symbols_if_statement_branch(branch, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_if_statement_branch(ast: Ast.IfStatementBranchAst, manager: SymbolTableManager) -> None:
        if not ast: return

        # Else branch will never have any definitions (parser forces this)
        for definition in ast.definitions:
            SymbolTableGenerator.build_symbols_let_statement(definition, manager)
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_while_statement(ast: Ast.WhileStatementAst, manager: SymbolTableManager) -> None:
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, manager)

    # @staticmethod
    # @nest_next_scope
    # def build_symbols_for_statement(ast: Ast.ForStatementAst, manager: SymbolTableManager) -> None:
    #     for identifier in ast.identifiers:
    #         SymbolTableGenerator.build_symbols_for_statement_identifiers(identifier, ast.iterable, manager)
    #     for statement in ast.body:
    #         SymbolTableGenerator.build_symbols_statement(statement, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_do_while_statement(ast: Ast.DoWhileStatementAst, manager: SymbolTableManager) -> None:
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_match_statement(ast: Ast.MatchStatementAst, manager: SymbolTableManager) -> None:
        for case in ast.cases:
            SymbolTableGenerator.build_symbols_case_statement(case, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_case_statement(ast: Ast.CaseStatementAst, manager: SymbolTableManager) -> None:
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, manager)

    # @staticmethod
    # @nest_next_scope
    # def build_symbols_with_statement(ast: Ast.WithStatementAst, manager: SymbolTableManager) -> None:
    #     SymbolTableGenerator.build_symbols(ast.alias, manager)
    #     for statement in ast.body:
    #         SymbolTableGenerator.build_symbols_statement(statement, manager)

    @staticmethod
    @nest_next_scope
    def build_symbols_inner_scope(ast: Ast.InnerScopeAst, manager: SymbolTableManager) -> None:
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, manager)

    @staticmethod
    def build_symbols_let_statement(ast: Ast.LetStatementAst, manager: SymbolTableManager) -> None:
        # Nested into this function, but not a new scope => no need to enter/exit scope, so no @nest_next_scope
        for variable, value in zip(ast.variables, ast.values):
            manager.add_symbol(variable.identifier.identifier, ast.type_annotation) # or TypeInference.infer(value))
