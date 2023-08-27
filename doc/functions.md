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
- Parameters must be in the order:
  - Required parameters
  - Optional parameters
  - Variadic parameter
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

## Generic type parameters
- A function can have generic type parameters.
- Generic type parameters must be in the order:
  - Required type parameters
  - Optional type parameters
  - Variadic type parameters
- Type parameters are passed into a function inside the `[...]` brackets.

```s++
fn a[T, U](x: T, y: U) -> (T, U) { ... }
```

### Implicit type parameters
- Type parameters don't have to be specified if they are in - `T`:
  - Parameter type: `fn func(param: T) -> Void {}`
  - Inside the constraint of another type parameter: `fn func[T: Constraint[U]]() -> Void {}`
- Otherwise, the type parameter must be specified.

## Return types
- A return type must **always** be specified.
- A function that doesn't return a value must return `Void`.
- Returning `()` is allowed, but creates a new tuple object.

## Asynchronous functions
- Functions defined as `gn` rather than `fn` are asynchronous.
- This means that a value is `yielded` rather than `returned`.
- If the return type super-imposes `Async`, then the function will return immediately, and values will be yielded asynchronously.
- Otherwise, the function will yield a `T` object -- **TODO**
- Yielding conventions
  - Yielding borrows is allowed, as control is passed back to the caller.
  - However, all yield must use the same convention ie if 1 yield statement yields an immutable borrow, then all yield statements must yield an immutable borrow.
  - This allows the compiler to keep track of the type of yield taking place, and enforce the necessary memory safety rules.

## Recursion
- Recursion is allowed
- All recursive functions are tail-call optimised.
  - Recursive functions that aren't tail-call recursive are re-written to be tail-call recursive.
- This means that the stack will not overflow.
- The stack will only ever contain a single frame for a recursive function.

## Examples:
### Fibonacci
```s++
fn fib(n: Num) -> Num {
  return if n == {
    0 | 1 { n }
    else { fib(n - 1) + fib(n - 2) }
  }
}