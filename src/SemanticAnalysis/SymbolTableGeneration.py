from __future__ import annotations
from typing import Generic, Optional, TypeVar
from inflection import camelize

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

    def to_json(self) -> dict:
        return {name: str(symbol) for name, symbol in self._symbols.items()}


class FunctionRegistry(SymbolTable[Ast.FunctionPrototypeAst]):
    def get_symbol(self, name: str, type_generics: list[Ast.TypeAst] = [], argument_types: list[Ast.TypeAst] = []) -> Optional[Ast.FunctionPrototypeAst]:
        ...

class Scope:
    _name: str
    _symbol_table: SymbolTable[Ast.TypeAst]
    _type_table: SymbolTable[Ast.TypeAst]
    _function_registry: FunctionRegistry
    _loop_tag_table: SymbolTable[None]

    _parent_scope: Optional[Scope]
    _child_scopes: list[Scope]

    def __init__(self, name: str, parent_scope: Optional[Scope] = None):
        self._name = name
        self._parent_scope = parent_scope
        self._parent_scope._child_scopes.append(self) if self._parent_scope is not None else None
        self._child_scopes = []

        self._symbol_table = SymbolTable()
        self._type_table = SymbolTable()
        self._function_registry = FunctionRegistry()
        self._loop_tag_table = SymbolTable()

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

    def to_json(self) -> dict:
        # Convert the symbol table, type table, function registry, and loop tag table to JSON
        # Add the child scopes as json in a list, named "child_scopes"
        # Return the JSON string
        return {
            "name": self._name,
            "symbol_table": self._symbol_table.to_json(),
            "type_table": self._type_table.to_json(),
            "function_registry": self._function_registry.to_json(),
            "loop_tag_table": self._loop_tag_table.to_json(),
            "child_scopes": [scope.to_json() for scope in self._child_scopes]
        }


class ScopeManager:
    _global_scope: Scope
    _current_scope: Scope

    def __init__(self):
        self._global_scope = Scope("Global")
        self._current_scope = self._global_scope

    def enter_scope(self, name: str):
        self._current_scope = Scope(name, self._current_scope)

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
            s.enter_scope(camelize(function.__name__.replace("build_symbols_", "")))
            function(ast, s)
            s.exit_scope()
        return inner

    @staticmethod
    def is_parameter_required(parameter: Ast.FunctionParameterAst) -> bool:
        return parameter.default_value is None and not parameter.is_variadic


class SymbolTableGenerator:
    @staticmethod
    @Utils.new_scope
    def build_symbols_program(ast: Ast.ProgramAst, s: ScopeManager) -> None:
        for member in ast.module.body.members:
            SymbolTableGenerator.build_symbols_module_member(member, s)

        # execute all deferred type inference now that all the symbols are available
        SymbolTableGenerator.infer_types(s)

    @staticmethod
    def infer_types(s: ScopeManager) -> None:
        scope = s.global_scope
        while True:
            for i in range(len(scope.symbol_table._symbols.values())):
                symbol = list(scope.symbol_table._symbols.values())[i]
                if callable(symbol):
                    scope.symbol_table._symbols[list(scope.symbol_table._symbols.keys())[i]] = symbol()
            if scope.child_scopes:
                scope = scope.child_scopes[0]
            else:
                cur_index = scope.parent_scope.child_scopes.index(scope)
                if cur_index + 1 < len(scope.parent_scope.child_scopes):
                    scope = scope.parent_scope.child_scopes[cur_index + 1]
                else:
                    scope = scope.parent_scope
                    if scope == s.global_scope:
                        break


    @staticmethod
    def build_symbols_module_member(ast: Ast.ModuleMemberAst, s: ScopeManager) -> None:
        match ast:
            case Ast.FunctionPrototypeAst(): SymbolTableGenerator.build_symbols_function_prototype(ast, s)
            case Ast.ClassPrototypeAst(): SymbolTableGenerator.build_symbols_class_prototype(ast, s)
            case Ast.EnumPrototypeAst(): SymbolTableGenerator.build_symbols_enum_prototype(ast, s)
            case _: raise NotImplementedError(f"Unknown module member type: {ast.__class__.__name__}")

    @staticmethod
    def build_symbols_if_statement(ast: Ast.IfStatementAst, s: ScopeManager) -> None:
        branches = [ast.if_branch, *ast.elif_branches, ast.else_branch]
        for branch in branches:
            SymbolTableGenerator.build_symbols_if_branch(branch, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_if_branch(ast: Ast.IfStatementBranchAst, s: ScopeManager) -> None:
        for definition in ast.definitions:
            SymbolTableGenerator.build_symbols_let_statement(definition, s)
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_while_statement(ast: Ast.WhileStatementAst, s: ScopeManager) -> None:
        if ast.tag:
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
        from src.SemanticAnalysis.TypeInference import TypeInference

        s.current_scope.symbol_table.add_symbol(ast.alias.identifier.identifier, lambda: TypeInference.infer_type_from_expression(ast.value, s))
        for statement in ast.body:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    def build_symbols_typedef_statement(ast: Ast.TypedefStatementAst, s: ScopeManager) -> None:
        s.current_scope.type_table.add_symbol(ast.new_type.parts[-1].identifier, ast.old_type) # todo

    @staticmethod
    def build_symbols_let_statement(ast: Ast.LetStatementAst, s: ScopeManager) -> None:
        from src.SemanticAnalysis.TypeInference import TypeInference

        for variable in ast.variables: # todo : unpack value
            s.current_scope.symbol_table.add_symbol(variable.identifier.identifier, lambda: TypeInference.infer_type_from_expression(ast.value, s) if ast.value else ast.type_annotation)

    @staticmethod
    @Utils.new_scope
    def build_symbols_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeManager) -> None:
        s.current_scope.parent_scope.function_registry.add_symbol(ast.identifier.identifier, ast)
        for parameter in ast.parameters:
            s.current_scope.symbol_table.add_symbol(parameter.identifier.identifier, parameter.type_annotation)
        for type_parameter in ast.generic_parameters:
            s.current_scope.type_table.add_symbol(type_parameter.identifier.identifier, type_parameter) # todo -> replaced by true type on function call
        for statement in ast.body.statements:
            SymbolTableGenerator.build_symbols_statement(statement, s)

    @staticmethod
    @Utils.new_scope
    def build_symbols_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeManager) -> None:
        s.current_scope.parent_scope.type_table.add_symbol(ast.identifier.identifier, ast)
        for type_parameter in ast.generic_parameters:
            s.current_scope.type_table.add_symbol(type_parameter.identifier.identifier, type_parameter)
        for attribute in ast.body.members:
            s.current_scope.symbol_table.add_symbol(attribute.identifier.identifier, attribute.type_annotation)


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
            case Ast.FunctionPrototypeAst(): SymbolTableGenerator.build_symbols_function_prototype(ast, s)
            case True if type(ast) in Ast.ExpressionAst.__args__: SymbolTableGenerator.build_symbols_expression_statement(ast, s)
            case _: raise NotImplementedError(f"Statement {ast} not implemented")


