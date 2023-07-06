"""
Register the signature of functions, and provide the infrastructure to request the correct function based on the
type-constraints, parameter types, and number of arguments.

Sup-functions:
-- Take the method, and turn it into a function.
-- Append the fully-qualified class name to the function name.
-- Any call to the function applies the "self", with the correct calling convention (ie auto-borrowing).
    -- The checks that ensure the required borrow is possible, take place in the memory-analysis phase.
    -- Memory analysis phase is the last check to happen, so functions are already prepared.

- Example:
struct A {
    a: std::Num;
    b: std::Str;
}

sup A {
    fn foo(self: &Self, x: std::Num) -> std::Num {}
    fn bar(self: &Self, x: std::Str) -> std::Str {}
}

sup B for A {
    fn baz(self: &Self, x: std::Num) -> std::Num {}
    fn qux(self: &Self, x: std::Str) -> std::Str {}
}

Will create the functions:
-- foo_A(self: &A, x: std::Num) -> std::Num;
-- bar_A(self: &A, x: std::Str) -> std::Str;
-- baz_A(self: &A, x: std::Num) -> std::Num;
-- qux_A(self: &A, x: std::Str) -> std::Str;

Already existed:
-- foo_B(self: &B, x: std::Num) -> std::Num;
-- bar_B(self: &B, x: std::Str) -> std::Str;

Match by super-class:
-- Matching by the super-class first ensures that the correct instance of the function is called.
-- If an `A` class has been upcast to a `B` class, then the `A` class's method is still called.
    -- Internally, the true type is available, so the correct function is called.

Conflicting base class methods
sup A {
    fn foo(self: &Self, x: std::Num) -> std::Num {}
}

sup B {
    fn foo(self: &Self, x: std::Str) -> std::Str {}
}

sup A for C {}
sup B for C {}

-- C now has two versions of the foo(&C, std::Num) -> std::Num function.
-- An error is thrown if the function is called, as the correct function cannot be determined.
-- To manually specify the correct function either:
    -- Override the method in the sub-class and call it directly.
    -- Upcast the class to the correct super-class, and call the method on the super-class => std::upcast<A>(c).foo(1);
"""

from src.SyntacticAnalysis import Ast

class FunctionRegister:
    REGISTRY: dict[Ast.TypeAst, list[Ast.FunctionPrototypeAst]] = dict()

    @staticmethod
    def register_function(fq_fn_name: Ast.TypeAst, function_prototype: Ast.FunctionPrototypeAst):
        FunctionRegister.REGISTRY[fq_fn_name] = FunctionRegister.REGISTRY.get(fq_fn_name, []) + [function_prototype]
