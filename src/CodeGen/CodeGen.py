import llvmlite.ir as ll
import llvmlite.binding as llvm

from src.SyntacticAnalysis.Ast import *


class CodeGen:
    def __init__(self):
        self.context = ll.Context()
        self.module = ll.Module(name="main", context=self.context)
        self.builder = ll.IRBuilder(self.context)

        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

    def _generate_llvm_function(self, ast: FunctionPrototypeAst) -> ll.Function:
        is_variadic = len(ast.parameters) and ast.parameters[-1].is_variadic
        llvm_function_return_type = self._generate_llvm_type(ast.return_type)
        llvm_function_parameter_types = self._generate_parameter_types(ast.parameters)
        llvm_function_type = ll.FunctionType(llvm_function_return_type, llvm_function_parameter_types, is_variadic)

        llvm_function = ll.Function(self.module, llvm_function_type, name=ast.identifier)
        llvm_function.linkage = self._generate_llvm_linkage(ast.access_modifier)

        llvm_basic_block_entry = llvm_function.append_basic_block(name="entry")
        llvm_builder = ll.IRBuilder()
        llvm_builder.position_at_end(llvm_basic_block_entry)
        llvm_basic_blocks_body = [self._generate_llvm_block_from_statement(llvm_builder, statement) for statement in ast.body]
        llvm_basic_block_exit = llvm_builder.append_basic_block(name="exit")
        llvm_builder.position_at_end(llvm_basic_block_exit)

        return llvm_function
