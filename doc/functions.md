# Functions
- First class `Fun[R, ...Args]` type.

## Declaring functions
- This shows how functions are registered in `S++`:
```s++
fn a(x: Num) -> Num { ... }
fn a(x: Str) -> Str { ... }
```
```s++
cls Fn[R, ...Ts] {
  fn call(...xs: Ts) { ... }
}

cls __MOCK_A {}
sup Fn[Num, Num] for A {
  fn call(x: Num) -> Num { ... }
}
sup Fn[Str, Str] for A {
  fn call(x: Str) -> Str { ... }
}
let a = __MOCK_A{}
```
- This allows overloads to be defined, and for functions to be passed around as objects.
- Note that the only way to pass `fn`/`gn` functions is to use the `&Fn` calling convention.

## Parameters
- Every parameter must have a type-annotation (design decision).
- Parameters are passed by value, unless the `&`/`&mut` calling convention is used.
- Parameters can be made mutable by prefixing the parameter with `mut`, like in Rust.
- Required parameters can be followed by optional parameters.
- Optional parameters can be followed by a variadic parameter.
```s++
fn add_all(x: Num, y: Num ...xs: Num) -> Num { ... }
fn add_all(x: Num, y: Num) -> Num { ... }
```
- Arguments with no calling convention are "moved" into the function.
- Super-impose the `Copy` class onto the type to allow the previous value to be used after the function call.

### Calling conventions
| Symbol | Convention       | Description                                         |
|--------|------------------|-----------------------------------------------------|
| ` `    | Move (or copy)   | The value is moved, unless `Copy` is super-imposed. |
| `&`    | Immutable borrow | The value is borrowed, and cannot be mutated.       |
| `&mut` | Mutable borrow   | The value is borrowed, and can be mutated.          |
- The argument must match the calling convention exactly.
- The exception is that if a variable is from a parameter, it could already be a borrow, in which case, the borrow is either moved or borrowed from again into the function.
  - It should be noted that borrowing from a borrow **doesn't** create an `&&T` type, it just duplicates the borrow.