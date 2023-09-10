import llvmlite.ir as ll
import llvmlite.binding as llvm

from src.SyntacticAnalysis import Ast


class CodeGen:
    @staticmethod
    def generate(ast: Ast.ProgramAst):
        # todo : LLVM initialization boilerplate code here
        # todo : call generation for each type of ast
        ...
