from __future__ import annotations
from typing import Any, Callable, Optional

from src.SyntacticAnalysis import Ast


class Sym:
    module: Optional[Ast.ModuleIdentifierAst]
    name: Ast.IdentifierAst
    type: Optional[Ast.TypeAst]
    bases: list[Scope]

    def __init__(self, module: Optional[Ast.ModuleIdentifierAst], name: Ast.IdentifierAst, type: Optional[Ast.TypeAst] = None):
        self.module = module
        self.name = name
        self.type = type
        self.bases = []

    def json(self) -> dict[str, Any]:
        return {
            "module": self.module.to_string() if self.module else "",
            "name": self.name.to_string(),
            "type": self.type.to_string() if self.type else ""
        }

class SymTbl:
    symbols: dict[tuple[Ast.ModuleIdentifierAst, Ast.IdentifierAst], Sym]

    def add(self, sym: Sym) -> None:
        self.symbols[(sym.module, sym.name)] = sym

    def get(self, name: Ast.IdentifierAst, module: Optional[Ast.ModuleIdentifierAst] = None) -> Optional[Sym]:
        return self.symbols.get((module, name))

    def has(self, name: Ast.IdentifierAst, module: Optional[Ast.ModuleIdentifierAst] = None) -> bool:
        return (module, name) in self.symbols

    def json(self) -> list[dict[str, Any]]:
        return [sym.json() for sym in self.symbols.values()]


class Scope:
    parent: Optional[Scope]
    children: list[Scope]
    symtbl: SymTbl
    visited: bool

    def __init__(self, parent: Optional[Scope] = None):
        self.parent = parent
        self.parent.children.append(self) if self.parent else None

        self.symtbl = SymTbl()
        self.tytbl = SymTbl()

        self.children = []
        self.visited = False

    def add_sym(self, sym: Sym) -> None:
        self.symtbl.add(sym)

    def get_sym(self, name: Ast.IdentifierAst, module: Optional[Ast.ModuleIdentifierAst] = None) -> Optional[Sym]:
        if self.symtbl.has(name):
            return self.symtbl.get(name)
        elif self.parent:
            return self.parent.get_sym(name, module)
        else:
            raise Exception(f"Symbol {name} not found")

    def has_sym(self, name: Ast.IdentifierAst, module: Optional[Ast.ModuleIdentifierAst] = None) -> bool:
        return self.symtbl.has(name) or (self.parent and self.parent.has_sym(name, module))

    def json(self) -> dict[str, Any]:
        return {
            "symtbl": self.symtbl.json(),
            "children": [child.json() for child in self.children]
        }


class ScopeHandler:
    global_scope: Scope
    current_scope: Scope

    def __init__(self):
        self.global_scope = Scope()
        self.current_scope = self.global_scope

    def enter_scope(self) -> None:
        self.current_scope = Scope(self.current_scope)

    def exit_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def next_scope(self):
        if any([not scope.visited for scope in self.current_scope.children]):
            unvisited_scopes = [scope for scope in self.current_scope.children if not scope.visited]
            next_scope = unvisited_scopes[0]
            next_scope.visited = True
            self.current_scope = next_scope

        else:
            raise Exception("No unvisited scopes")

    def prev_scope(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
        else:
            raise Exception("No parent scope")

    def switch_to_global_scope(self) -> None:
        self.current_scope = self.global_scope
        self.visit_every_scope(lambda scope: setattr(scope, "visited", False))

    def visit_every_scope(self, func: Callable) -> None:
        def visit_every_scope_helper(scope: Scope, func: Callable) -> None:
            func(scope)
            for child in scope.children:
                visit_every_scope_helper(child, func)

        current_scope = self.current_scope
        visit_every_scope_helper(current_scope, func)

    def json(self) -> dict[str, any]:
        return self.global_scope.json()
