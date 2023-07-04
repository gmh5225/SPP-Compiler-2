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
