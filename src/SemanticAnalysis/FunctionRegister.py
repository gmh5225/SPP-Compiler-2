"""
Register the signature of functions, and provide the infrastructure to request the correct function based on the
type-constraints, parameter types, and number of arguments.

Sup-functions:
- Take the method, and turn it into a function
- Append the fully-qualified class name to the function name
- Any call to the function applies the "self", with the correct calling convention (ie auto-borrowing)
    - Checks to make sure the required borrow is possible takes place in the memory-analysis phase
    - Memory analysis phase is the last check to happen, so functions are already prepared

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
- foo_A(self: &A, x: std::Num) -> std::Num;
- bar_A(self: &A, x: std::Str) -> std::Str;
- baz_A(self: &A, x: std::Num) -> std::Num;
- qux_A(self: &A, x: std::Str) -> std::Str;

Already existed:
- foo_B(self: &B, x: std::Num) -> std::Num;
- bar_B(self: &B, x: std::Str) -> std::Str;

Match by super-class:
- Matching by the super-class first ensures that the correct instance of the function is called
- If a A class has been upcasted to a B class, then the A class's method is still called
    - Internally, the true type is available, so the correct function is called
"""

from src.SyntacticAnalysis import Ast

class FunctionRegister:
    REGISTRY: dict[Ast.IdentifierAst, list[Ast.FunctionPrototypeAst]] = dict()

    @staticmethod
    def register_function(function_prototype: Ast.FunctionPrototypeAst):
        fn_name = function_prototype.identifier
        FunctionRegister.REGISTRY[fn_name] = FunctionRegister.REGISTRY.get(fn_name, []) + [function_prototype]
