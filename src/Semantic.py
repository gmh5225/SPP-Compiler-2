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
"""

from __future__ import annotations
from multimethod import multimethod
from src import Ast


class UninitializedSymbol:
    pass

class SymbolTable:
    _symbols: dict[Ast.LocalVariableAst, (Ast.ExpressionAst, Ast.TypeAst)]
    _child_tables: list[SymbolTable]
    _parent: SymbolTable

    def __init__(self, parent: SymbolTable):
        self._symbols = {}
        self._child_tables = []
        self._parent = parent
        self._parent._child_tables.append(self)

    def add_symbol(self, symbol: Ast.LocalVariableAst, value: Ast.ExpressionAst, type: Ast.TypeAst):
        self._symbols[symbol] = (value, type)


class SemanticAnalyser:
    _ast: Ast.ProgramAst

    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast

    @multimethod
    def analyse(self, stmt: Ast.LetStatementAst, scope: SymbolTable):
        if stmt.type_annotation is None:
            for variable, value in stmt.variables, stmt.values:
                scope.add_symbol(variable, value, self._infer_type(value))
        else:
            for variable in stmt.variables:
                scope.add_symbol(variable, UninitializedSymbol(), stmt.type_annotation)

    def _infer_type(self, expr: Ast.ExpressionAst):
        # move left to right
        match expr:
            case Ast.BinaryExpressionAst(left, op, right):
                function_type = self._lookup_operator_function(op)
                matched_functions = self._scan_symbol_table(function_type)
                matched_signature_functions = filter(lambda fn: self._mach_signature(fn, left, right), matched_functions)
                matched_signature_function = next(matched_signature_functions)
                return_type = matched_signature_function.return_type


    def _lookup_operator_function(self, op: Ast.TokenAst) -> Ast.FunctionPrototypeAst:
        pass

    def _scan_symbol_table(self): ...

