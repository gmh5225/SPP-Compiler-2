from __future__ import annotations
from typing import Callable, Optional
import base64, pickle

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
            "Type": convert_type_to_string(self.type),  # base64.b64encode(pickle.dumps(self.type)).decode(),
            # "Value": 1,  # base64.b64encode(pickle.dumps(self.value)).decode(),
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
        return {name: symbol.json() for name, symbol in self.symbols.items()}

class Scope:
    name: str
    symbols: SymbolTable
    types: SymbolTable
    parent: Optional[Scope]
    children: list[Scope]
    visited: bool

    def __init__(self, name: str, parent: Optional[Scope] = None):
        self.name = name
        self.symbols = SymbolTable()
        self.types = SymbolTable()

        self.parent = parent
        self.children = []
        if self.parent is not None:
            self.parent.children.append(self)

        self.visited = False

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

    def all_symbols(self) -> list[str]:
        current = self
        symbols = []
        while current is not None:
            symbols += current.symbols.symbols.keys()
            current = current.parent
        return symbols

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

    def next_scope(self) -> None:
        # Use the Scope.visited flag to keep track of which scopes have been visited.

        # First check if any children are unvisited, and visit the first one
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
        # switch to global and "un-visit" every scope
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

    def json(self) -> dict[str, any]:
        return self.global_scope.json()


class SymbolTableBuilder:
    @staticmethod
    def build(ast: Ast.ProgramAst) -> ScopeHandler:
        s = ScopeHandler()
        SymbolTableBuilder.build_program_symbols(ast, s)
        s.switch_to_global_scope()
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
        s.enter_scope(f"FnPrototype__{convert_identifier_to_string(ast.identifier)}")

        for param in ast.parameters:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(param.identifier), param.type_annotation, None))
        for generic in ast.generic_parameters:
            s.current_scope.add_type(Symbol(convert_identifier_to_string(generic.identifier), None, None))
        for statement in ast.body.statements:
            SymbolTableBuilder.build_statement_symbols(statement, s)

        s.exit_scope()

    @staticmethod
    def build_statement_symbols(ast: Ast.StatementAst, s: ScopeHandler) -> None:
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
            SymbolTableBuilder.build_expression_symbols(ast.value, s)

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
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_inner_scope_symbols(ast: Ast.InnerScopeAst, s: ScopeHandler) -> None:
        s.enter_scope("InnerScope")
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_with_statement_symbols(ast: Ast.WithStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("WithStatement")
        s.current_scope.add_symbol(Symbol(convert_identifier_to_string(ast.alias.identifier), None, None))
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_class_prototype_symbols(ast: Ast.ClassPrototypeAst, s: ScopeHandler) -> None:
        s.current_scope.add_type(Symbol(convert_identifier_to_string(ast.identifier), None, None))
        s.enter_scope(f"ClassPrototype{convert_identifier_to_string(ast.identifier)}")
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
            s.global_scope.get_type(convert_identifier_to_string_no_generics(ast.identifier)).bases.append(convert_identifier_to_string(ast.super_class))

        s.enter_scope("SupPrototype")
        for typedef in filter(lambda member: isinstance(member, Ast.SupTypedefAst), ast.body.members):
            s.current_scope.add_type(Symbol(convert_identifier_to_string(typedef.identifier), typedef.type_annotation, None))
        for method in filter(lambda member: isinstance(member, Ast.SupMethodPrototypeAst), ast.body.members):
            s.global_scope.add_symbol(Symbol(convert_identifier_to_string(method.identifier), get_function_type(method), None))
        s.exit_scope()


def convert_identifier_to_string(ast: Ast.IdentifierAst | Ast.GenericIdentifierAst) -> str:
    x = ast.identifier
    if type(ast) == Ast.GenericIdentifierAst:
        return x + f"[{', '.join(map(lambda y: convert_identifier_to_string(y.identifier), ast.generic_arguments))}]"
    return x

def convert_type_to_string(ast: Ast.TypeAst) -> str:
    if isinstance(ast, Ast.TypeSingleAst):
        s = ""
        for p in ast.parts:
            s += p.identifier
            if p.generic_arguments:
                generics = list(map(lambda y: convert_type_to_string(y), p.generic_arguments))
                joined_generics = ", ".join(generics)
                s += f"[{joined_generics}]"
            s += "::"
        return s[:-2]
    elif isinstance(ast, Ast.TypeTupleAst):
        s = "("
        for p in ast.types:
            s += convert_type_to_string(p) + ", "
        return (s[:-2] if len(s) > 1 else s) + ")"
    elif isinstance(ast, str):
        return ast # temp (for type: "TODO") etc
    elif ast is None:
        return ""
    else:
        raise NotImplementedError(f"TypeAst {ast} not implemented")

def convert_identifier_to_string_no_generics(ast: Ast.IdentifierAst | Ast.GenericIdentifierAst) -> str:
    return ast.identifier

def get_function_type(ast: Ast.FunctionPrototypeAst) -> Ast.TypeAst:
    """
    Determine the type of a function. The function types are either std::FnRef, std::FnMut, or std::Fn. The generics of
    the function type are the return type, followed by the arguments as a tuple. For example, a function accepting two
    numbers and returning a string would have the type std::FnRef[String, (Num, Num)]. Steps:
    1. Determine the type of the function => free functions are FnRef, methods are determined by the Self type
    2. Determine the generics of the function => return type, followed by the arguments as a tuple

    @param ast:
    @return:
    """
    return_type = Ast.TypeGenericArgumentAst(None, ast.return_type, -1)
    param_types = Ast.TypeGenericArgumentAst(None, Ast.TypeTupleAst([a.type_annotation for a in ast.parameters], -1), -1)

    return Ast.TypeSingleAst([
        Ast.GenericIdentifierAst("std", [], -1),
        Ast.GenericIdentifierAst("FnRef", [return_type, param_types], -1)], -1)
