import llvmlite.ir as llvm

from src.Ast import *


class CodeGen:
    def __init__(self):
        self.context = llvm.Context()
        self.module = llvm.Module(name="main", context=self.context)
        self.builder = llvm.IRBuilder(self.context)

    def generate_function(self, llvm_function: FunctionPrototypeAst) -> llvm.FunctionType:
        llvm_function_type = llvm.FunctionType(self.generate_type(llvm_function.return_type), self.generate_parameters(llvm_function.parameters), llvm_function.parameters[-1].is_variadic)
        llvm_function = llvm.Function(self.module, llvm_function_type, name=llvm_function.identifier)

        block = llvm_function.append_basic_block(name="entry")
        self.builder.position_at_end(block)


