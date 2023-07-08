from __future__ import annotations
from typing import Generic, Optional, TypeVar

from src.SyntacticAnalysis import Ast


T = TypeVar("T")


class SymbolTable(Generic[T]):
    _symbols: dict[str, T]

    def __init__(self):
        self._symbols = {}

    def add_symbol(self, name: str, symbol: T):
        self._symbols[name] = symbol

    def get_symbol(self, name: str) -> Optional[T]:
        return self._symbols.get(name, None)

    def __repr__(self):
        return f"SymbolTable({self._symbols})"


class FunctionRegistry(SymbolTable[Ast.FunctionPrototypeAst]):
    def get_symbol(self, name: str, type_generics: list[Ast.TypeAst] = [], argument_types: list[Ast.TypeAst] = []) -> Optional[Ast.FunctionPrototypeAst]:
        ...


class Scope:
    _symbol_table: SymbolTable[Ast.TypeAst]
    _type_table: SymbolTable[Ast.TypeAst]
    _function_registry: FunctionRegistry
    _loop_tag_table: SymbolTable[None]

    _parent_scope: Optional[Scope]
    _child_scopes: list[Scope]

    def __init__(self, parent_scope: Optional[Scope] = None):
        self._parent_scope = parent_scope
        self._parent_scope._child_scopes.append(self) if self._parent_scope is not None else None
        self._child_scopes = []

        self._symbol_table = SymbolTable()
        self._type_table = SymbolTable()
        self._function_registry = SymbolTable()

    @property
    def parent_scope(self) -> Optional[Scope]:
        return self._parent_scope

    @property
    def child_scopes(self) -> list[Scope]:
        return self._child_scopes

    @property
    def symbol_table(self) -> SymbolTable[Ast.TypeAst]:
        return self._symbol_table

    @property
    def type_table(self) -> SymbolTable[Ast.TypeAst]:
        return self._type_table

    @property
    def function_registry(self) -> FunctionRegistry:
        return self._function_registry

    @property
    def loop_tag_table(self) -> SymbolTable[None]:
        return self._loop_tag_table


class ScopeManager:
    _global_scope: Scope
    _current_scope: Scope

    def enter_scope(self):
        self._current_scope = Scope(self._current_scope)

    def exit_scope(self):
        assert self._current_scope != self._global_scope
        assert self._current_scope.parent_scope is not None
        self._current_scope = self._current_scope.parent_scope

    @property
    def current_scope(self) -> Scope:
        return self._current_scope

    @property
    def global_scope(self) -> Scope:
        return self._global_scope


class Utils:
    @staticmethod
    def new_scope(function: callable) -> callable:
        def inner(ast, s: ScopeManager):
            s.enter_scope()
            function(ast, s)
            s.exit_scope()
        return inner

    @staticmethod
    def is_parameter_required(parameter: Ast.FunctionParameterAst) -> bool:
        return parameter.default_value is None and not parameter.is_variadic


class SymbolTableGenerator:
    @staticmethod
    def build_symbols_if_statement(ast: Ast.IfStatementAst, s: ScopeManager) -> None:
        branches = [ast.if_branch, *ast.elif_branches, ast.else_branch]
        for branch in branches:
            SymbolTableGenerator.build_symbols_if_branch(branch, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_if_branch(ast: Ast.IfStatementBranchAst, s: ScopeManager) -> None:
        for definition in ast.definitions:
            SymbolTableGenerator.build_variable_declaration(definition, s)
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_while_statement(ast: Ast.WhileStatementAst, s: ScopeManager) -> None:
        s.current_scope.loop_tag_table.add_symbol(ast.tag.identifier, None)
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_do_while_statement(ast: Ast.DoWhileStatementAst, s: ScopeManager) -> None:
        s.current_scope.loop_tag_table.add_symbol(ast.tag.identifier, None)
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_match_statement(ast: Ast.MatchStatementAst, s: ScopeManager) -> None:
        for case in ast.cases:
            SymbolTableGenerator.build_symbols_case_statement(case, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_case_statement(ast: Ast.CaseStatementAst, s: ScopeManager) -> None:
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_with_statement(ast: Ast.WithStatementAst, s: ScopeManager) -> None:
        s.current_scope.symbol_table.add_symbol(ast.alias.identifier.identifier, TypeInference.infer_type(ast.value, s))
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    def build_symbols_typedef_statement(ast: Ast.TypedefStatementAst, s: ScopeManager) -> None:
        s.current_scope.type_table.add_symbol(ast.new_type.parts[-1].identifier, ast.old_type) # todo

    @staticmethod
    def build_symbols_let_statement(ast: Ast.LetStatementAst, s: ScopeManager) -> None:
        for variable, value in zip(ast.variables, ast.values):
            s.current_scope.symbol_table.add_symbol(variable.identifier.identifier, TypeInference.infer_type(value, s) if value else ast.type_annotation)



    @staticmethod
    def build_symbols_statement(ast: Ast.StatementAst, s: ScopeManager) -> None:
        match ast:
            case Ast.IfStatementAst(): SymbolTableGenerator.build_symbols_if_statement(ast, s)
            case Ast.WhileStatementAst(): SymbolTableGenerator.build_symbols_while_statement(ast, s)
            case Ast.ForStatementAst(): SymbolTableGenerator.build_symbols_for_statement(ast, s)
            case Ast.DoWhileStatementAst(): SymbolTableGenerator.build_symbols_do_while_statement(ast, s)
            case Ast.MatchStatementAst(): SymbolTableGenerator.build_symbols_match_statement(ast, s)
            case Ast.WithStatementAst(): SymbolTableGenerator.build_symbols_with_statement(ast, s)
            case Ast.TypedefStatementAst(): SymbolTableGenerator.build_symbols_typedef_statement(ast, s)
            case Ast.LetStatementAst(): SymbolTableGenerator.build_symbols_let_statement(ast, s)
            case Ast.ExpressionAst(): SymbolTableGenerator.build_symbols_expression_statement(ast, s)
            case Ast.FunctionPrototypeAst(): SymbolTableGenerator.build_symbols_function_prototype(ast, s)
            case _: raise NotImplementedError(f"Statement {ast} not implemented")


