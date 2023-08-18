import llvmlite.ir as ir
import llvmlite.binding as llvm
from ctypes import CFUNCTYPE


def main():
    m = ir.Module()
    func_ty = ir.FunctionType(ir.VoidType(), []) # func_ty is of type: () -> Void
    func = ir.Function(m, func_ty, name="printer") # the function with the signature: () -> Void
    builder = ir.IRBuilder(func.append_basic_block(name="entry")) # the builder for the function & its entry block

    fmt = "%s\n\0"
    c_fmt = ir.Constant(ir.ArrayType(ir.IntType(8), len(fmt)),
                        bytearray(fmt.encode("utf8")))
    global_fmt = ir.GlobalVariable(m, c_fmt.type, name="fstr")
    global_fmt.linkage = "internal"
    global_fmt.global_constant = True
    global_fmt.initializer = c_fmt

    arg = "Hello World\0"
    c_str_val = ir.Constant(ir.ArrayType(ir.IntType(8), len(arg)),
                            bytearray(arg.encode("utf8")))

    printf_ty = ir.FunctionType(ir.IntType(32), [], var_arg=True)
    printf = ir.Function(m, printf_ty, name="printf")

    c_str = builder.alloca(c_str_val.type)
    builder.store(c_str_val, c_str)

    voidptr_ty = ir.IntType(8).as_pointer()
    fmt_arg = builder.bitcast(global_fmt, voidptr_ty)
    builder.call(printf, [fmt_arg, c_str])
    builder.ret_void()

    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    print(str(m))
    llvm_module = llvm.parse_assembly(str(m))
    tm = llvm.Target.from_default_triple().create_target_machine()

    with llvm.create_mcjit_compiler(llvm_module, tm) as ee:
        ee.finalize_object()
        fptr = ee.get_function_address("printer")
        py_func = CFUNCTYPE(None)(fptr)
        py_func()

if __name__ == "__main__":
    main()
