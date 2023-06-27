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

from multimethod import multimethod
from src import Ast


class SemanticAnalyser:
    _ast: Ast.ProgramAst

    def __init__(self, ast: Ast.ProgramAst):
        self._ast = ast

    def _analyse_program(self, ast: Ast.ProgramAst):
        self._analyse_module_prototype(ast.module)

    def _analyse_module_prototype(self, ast: Ast.ModulePrototypeAst):
        self._register_module_name(ast.identifier, ast.modifier)
        self._analyse_module_implementation(ast.body, ast)

    def _analyse_module_implementation(self, ast: Ast.ModuleImplementationAst, module_prototype: Ast.ModulePrototypeAst):
        self._analyse_import_block(ast.imports)
        self._analyse_module_members(ast.members, module_prototype)

    def _analyse_import_block(self, ast: Ast.ImportBlockAst):
        for import_statement in ast.imports:
            self._load_module(import_statement.module, import_statement.parent_directories)
            self._load_module_members(import_statement.module, import_statement.what_to_import)

    def _analyse_module_member(self, ast: Ast.ModuleMemberAst, module_prototype: Ast.ModulePrototypeAst):
        match ast:
            case Ast.FunctionPrototypeAst(): self._analyse_function_prototype(ast)
            case Ast.ClassPrototypeAst(): self._analyse_class_prototype(ast)
            case Ast.EnumPrototypeAst(): self._analyse_enum_prototype(ast)
            case Ast.SupPrototypeNormalAst(): self._analyse_sup_prototype_normal(ast)
            case Ast.SupPrototypeInheritanceAst(): self._analyse_sup_prototype_inheritance(ast)

    def _analyse_function_prototype(self, ast: Ast.FunctionPrototypeAst, module: Ast.ModulePrototypeAst):
        self._register_function_name(ast.identifier, ast.modifier)
        self._analyse_function_parameters(ast.parameters)
        self._analyse_function_return_type(ast.return_type)

