from __future__ import annotations
from typing import Optional

from src.SyntacticAnalysis import Ast


class Symbol:
    name: str
    type: Optional[Ast.TypeAst]
    value: Optional[Ast.ExpressionAst]

    # optional metadata
    index: int
    bases: list[Ast.TypeAst]

    def __init__(self, name: str, type_: Optional[Ast.TypeAst], value: Optional[Ast.ExpressionAst], index: int = 0):
        self.name = name
        self.type = type_
        self.value = value
        self.index = index
        self.bases = []

    def json(self) -> dict[str, any]:
        d = {
            "Name": self.name,
            "Type": repr(self.type),
            "Value": repr(self.value),
            "Index": self.index,
        }

        if self.bases:
            d["Bases"] = [repr(b) for b in self.bases]

        return d


class SymbolTable:
    symbols: dict[str, Symbol]

    def __init__(self):
        self.symbols = {}

    def add(self, symbol: Symbol):
        self.symbols[symbol.name] = symbol

    def set(self, name: str, value: Ast.ExpressionAst):
        self.symbols[name].value = value

    def get(self, name: str) -> Symbol:
        return self.symbols[name]

    def has(self, name: str) -> bool:
        return name in self.symbols

    def rem(self, name: str):
        del self.symbols[name]

    def json(self) -> dict[str, any]:
        d = {}
        for k, v in self.symbols.items():
            d[repr(k)] = repr(v.type)
        return d

class Scope:
    name: str
    symbols: SymbolTable
    types: SymbolTable
    parent: Optional[Scope]
    children: list[Scope]

    def __init__(self, name: str, parent: Optional[Scope] = None):
        self.name = name
        self.symbols = SymbolTable()
        self.types = SymbolTable()

        self.parent = parent
        self.children = []
        if self.parent is not None:
            self.parent.children.append(self)

    def add_symbol(self, symbol: Symbol):
        self.symbols.add(symbol)

    def add_type(self, symbol: Symbol):
        self.types.add(symbol)

    def set_symbol(self, name: str, value: Ast.ExpressionAst):
        self.symbols.set(name, value)

    def set_type(self, name: str, value: Ast.ExpressionAst):
        self.types.set(name, value)

    def get_symbol(self, name: str) -> Symbol:
        current = self
        while current is not None:
            if current.symbols.has(name):
                return current.symbols.get(name)
            current = current.parent

        raise Exception(f"Symbol '{name}' not found")

    def get_type(self, name: str) -> Symbol:
        current = self
        while current is not None:
            if current.types.has(name):
                return current.types.get(name)
            current = current.parent

        raise Exception(f"Type '{name}' not found")

    def has_symbol(self, name: str) -> bool:
        current = self
        while current is not None:
            if current.symbols.has(name):
                return True
            current = current.parent

        return False

    def has_type(self, name: str) -> bool:
        current = self
        while current is not None:
            if current.types.has(name):
                return True
            current = current.parent

        return False

    def rem_symbol(self, name: str):
        self.symbols.rem(name)

    def rem_type(self, name: str):
        self.types.rem(name)

    def json(self) -> dict[str, any]:
        return {
            "Name": self.name,
            "Symbols": self.symbols.json(),
            "Types": self.types.json(),
            "ChildScopes": [s.json() for s in self.children]
        }


class ScopeHandler:
    global_scope: Scope
    current_scope: Scope

    def __init__(self):
        self.global_scope = Scope("Global")
        self.current_scope = self.global_scope

    def enter_scope(self, name: str) -> None:
        self.current_scope = Scope(name, self.current_scope)

    def exit_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def json(self) -> dict[str, any]:
        return self.global_scope.json()


class SymbolTableBuilder:
    @staticmethod
    def build(ast: Ast.ProgramAst) -> ScopeHandler:
        s = ScopeHandler()
        SymbolTableBuilder.build_program_symbols(ast, s)
        return s

    @staticmethod
    def build_program_symbols(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        for module_member in ast.module.body.members:
            match module_member:
                case Ast.FunctionPrototypeAst(): SymbolTableBuilder.build_function_prototype_symbols(module_member, s)
                case Ast.ClassPrototypeAst(): SymbolTableBuilder.build_class_prototype_symbols(module_member, s)
                case Ast.EnumPrototypeAst(): SymbolTableBuilder.build_enum_prototype_symbols(module_member, s)
                case Ast.SupPrototypeNormalAst(): SymbolTableBuilder.build_sup_prototype_symbols(module_member, s)
                case Ast.SupPrototypeInheritanceAst(): SymbolTableBuilder.build_sup_prototype_symbols(module_member, s)

    @staticmethod
    def build_function_prototype_symbols(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        s.current_scope.add_symbol(Symbol(convert_identifier_to_string(ast.identifier), get_function_type(ast), None))
        s.enter_scope("FnPrototype")

        for param in ast.parameters:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(param.identifier), param.type_annotation, None))
        for generic in ast.generic_parameters:
            s.current_scope.add_type(Symbol(convert_identifier_to_string(generic.identifier), None, None))
        for statement in ast.body.statements:
            SymbolTableBuilder.build_statement_symbol(statement, s)

        s.exit_scope()

    @staticmethod
    def build_statement_symbol(ast: Ast.StatementAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.TypedefStatementAst(): SymbolTableBuilder.build_typedef_statement_symbols(ast, s)
            case Ast.ReturnStatementAst(): pass
            case Ast.LetStatementAst(): SymbolTableBuilder.build_let_statement_symbols(ast, s)
            case Ast.FunctionPrototypeAst(): SymbolTableBuilder.build_function_prototype_symbols(ast, s)
            case _: SymbolTableBuilder.build_expression_symbols(ast, s)

    @staticmethod
    def build_typedef_statement_symbols(ast: Ast.TypedefStatementAst, s: ScopeHandler) -> None:
        s.current_scope.add_type(Symbol(convert_identifier_to_string(ast.new_type), ast.old_type, None))

    @staticmethod
    def build_let_statement_symbols(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        for i, variable in enumerate(ast.variables):
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(variable.identifier), ast.type_annotation, ast.value, i))

    @staticmethod
    def build_expression_symbols(ast: Ast.ExpressionAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.BinaryExpressionAst(): pass
            case Ast.PostfixExpressionAst(): pass
            case Ast.AssignmentExpressionAst(): pass
            case Ast.IdentifierAst(): pass
            case Ast.LambdaAst(): SymbolTableBuilder.build_lambda_symbols(ast, s)
            case Ast.PlaceholderAst(): pass
            case Ast.TypeSingleAst(): pass
            case Ast.IfStatementAst(): SymbolTableBuilder.build_if_statement_symbols(ast, s)
            case Ast.WhileStatementAst(): SymbolTableBuilder.build_while_statement_symbols(ast, s)
            case Ast.YieldStatementAst(): pass
            case Ast.InnerScopeAst(): SymbolTableBuilder.build_inner_scope_symbols(ast, s)
            case Ast.WithStatementAst(): SymbolTableBuilder.build_with_statement_symbols(ast, s)
            case Ast.TokenAst(): pass
            case _ :
                if type(ast) in Ast.LiteralAst.__args__: return
                if type(ast) in Ast.NumberLiteralAst.__args__: return
                raise NotImplementedError(f"ExpressionAst {ast} not implemented")

    @staticmethod
    def build_lambda_symbols(ast: Ast.LambdaAst, s: ScopeHandler) -> None:
        s.enter_scope("Lambda")
        for param in ast.parameters:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(param.identifier), None, None))
        SymbolTableBuilder.build_expression_symbols(ast.body, s)
        s.exit_scope()

    @staticmethod
    def build_if_statement_symbols(ast: Ast.IfStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("IfStatement")
        for branch in ast.branches:
            SymbolTableBuilder.build_if_branch_symbols(branch, s)
        s.exit_scope()

    @staticmethod
    def build_if_branch_symbols(ast: Ast.PatternStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("PatternBranch")
        SymbolTableBuilder.build_expression_symbols(ast.body, s)
        s.exit_scope()

    @staticmethod
    def build_while_statement_symbols(ast: Ast.WhileStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("WhileStatement")
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbol(statement, s)
        s.exit_scope()

    @staticmethod
    def build_inner_scope_symbols(ast: Ast.InnerScopeAst, s: ScopeHandler) -> None:
        s.enter_scope("InnerScope")
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbol(statement, s)
        s.exit_scope()

    @staticmethod
    def build_with_statement_symbols(ast: Ast.WithStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("WithStatement")
        s.current_scope.add_symbol(Symbol(convert_identifier_to_string(ast.alias.identifier), None, None))
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbol(statement, s)
        s.exit_scope()

    @staticmethod
    def build_class_prototype_symbols(ast: Ast.ClassPrototypeAst, s: ScopeHandler) -> None:
        s.current_scope.add_type(Symbol(convert_identifier_to_string(ast.identifier), None, None))
        s.enter_scope("ClassPrototype")
        for member in ast.body.members:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(member.identifier), member.type_annotation, None))
        s.exit_scope()

    @staticmethod
    def build_enum_prototype_symbols(ast: Ast.EnumPrototypeAst, s: ScopeHandler) -> None:
        s.current_scope.add_type(Symbol(convert_identifier_to_string(ast.identifier), None, None))
        s.enter_scope("EnumPrototype")
        for member in ast.body.members:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(member.identifier), None, None))
        s.exit_scope()

    @staticmethod
    def build_sup_prototype_symbols(ast: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, s: ScopeHandler) -> None:
        if isinstance(ast, Ast.SupPrototypeInheritanceAst):
            s.global_scope.get_type(convert_identifier_to_string(ast.identifier)).bases.append(ast.super_class)

        s.enter_scope("SupPrototype")
        for typedef in filter(lambda member: isinstance(member, Ast.SupTypedefAst), ast.body.members):
            s.current_scope.add_type(Symbol(convert_identifier_to_string(typedef.identifier), typedef.type_annotation, None))
        for method in filter(lambda member: isinstance(member, Ast.SupMethodPrototypeAst), ast.body.members):
            s.global_scope.add_symbol(Symbol(convert_identifier_to_string(method.identifier), get_function_type(method), None))
        s.exit_scope()


def convert_identifier_to_string(ast: Ast.IdentifierAst) -> str:
    return ast.identifier

def get_function_type(ast: Ast.FunctionPrototypeAst) -> Ast.TypeAst:
    return "TODO"
