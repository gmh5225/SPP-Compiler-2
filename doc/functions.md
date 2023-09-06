# Functions
- Functions are a first class type in S++.
- They are one of the [**3 function types**](#function-types) seen below.
- All functions, methods, and [**closures**](closures.md) are of one of these types.

## Function types:
| Function type | Description                                         |
|---------------|-----------------------------------------------------|
| `FnRef`       | A function that borrows its environment.            |
| `FnMut`       | A function that mutably borrows its environment.    |
| `FnOne`       | A function that takes ownership of its environment. |

### Methods
- A method's function type is determined by the `self` parameter of the method.

| Declaration of `self` | Type of method |
|-----------------------|----------------|
| `self: &Self`         | `FnRef`        |
| `self: &mut Self`     | `FnMut`        |
| `self: Self`          | `FnOne`        |
| `mut self: Self`      | `FnOne`        |

### Free functions
- These will always be `FnRef`, because there is no "environment" to capture.
- Static class methods are also `FnRef`, because they don't capture the class's environment.

### Closures
- See [**closures**](closures.md#function-type) for more information.
- Complicated by variable capture.

## Declaring functions
- Prior to the AST being semantically analysed, functions are transformed for "AST normalisation".
- This remodels functions to be variables that are callable, by super-imposing `Fn...` types over them.
- This shows how functions are transformed in `S++` before analysis:
```s++
# User code
fn a(x: Num) -> Num { ... }
fn a(x: Str) -> Str { ... }
```
```s++
# From the STL
cls FnRef[R, ...Ts] {
  fn call_ref(&self, ...xs: Ts) { ... }
}

# User code

cls __MOCK_A {}
sup FnRef[Num, Num] for A {
  fn call_ref(x: Num) -> Num { ... }
}
sup FnRef[Str, Str] for A {
  fn call_ref(x: Str) -> Str { ... }
}
let a = __MOCK_A{}
```
- This allows overloads to be defined, and for functions to be passed around as objects.
- Note that the only way to pass `fn`/`gn` non-closure functions as arguments is to use the `&` calling convention.
- Due to the `__` prefix of the mock classes, they (deliberately) cannot be used in user code.
- The function-variables (`let a`) are declared as immutable, to prevent mutable references.

## Parameters
- Every parameter must have a type-annotation (design decision).
- Parameters are passed by value, unless the `&`/`&mut` calling convention is used.
- Parameters can be made mutable by prefixing the parameter with `mut`, like in Rust.
- Parameters must be in the order: Required -> Optional -> Variadic.
```s++
fn add_all(x: Num, y: Num ...xs: Num) -> Num { ... }
fn add_all(x: Num, y: Num) -> Num { ... }
```
- Arguments with no calling convention are "moved" into the function.
- See the [**Copy**](move-vs-copy.md#copying) documentation for how to copy a value into a function.

### Calling conventions
| Symbol | Convention       | Description                                         |
|--------|------------------|-----------------------------------------------------|
| none   | Move (or copy)   | The value is moved, unless `Copy` is super-imposed. |
| `&`    | Immutable borrow | The value is borrowed, and cannot be mutated.       |
| `&mut` | Mutable borrow   | The value is borrowed, and can be mutated.          |
- The argument must match the calling convention exactly.
- The exception is that if a variable is from a parameter, it could already be a borrow, in which case, the borrow is either moved or borrowed from again into the function.
  - It should be noted that borrowing from a borrow **doesn't** create an `&&T` type, it just duplicates the borrow.

## Generic type parameters
- A function can have generic type parameters.
- Generic type parameters must be in the order: Required -> Optional -> Variadic.
- Type parameters are passed into a function inside the `[...]` brackets.

```s++
fn a[T, U](x: T, y: U) -> (T, U) { ... }
```
- See [**type-generics**](type-generics.md) for more information.

### Implicit type parameters
- Type parameters don't have to be specified if they are in - `T`:
  - Parameter type: `fn func[T](param: T) -> Void {}`
  - Inside the constraint of another type parameter: `fn func[T: Constraint[U]]() -> Void {}`
- Otherwise, the type parameter must be specified.

### Type parameter ordering
- As well as the order: Required -> Optional -> Variadic, there is an extra enforcement.
- All inferrable type parameters must **come after** non-inferrable / explicit type parameters.
- This means that inferrable type parameters cannot be filled by explicit type arguments; they must be inferred.

## Return types
- A return type must **always** be specified (design decision).
- A function that doesn't return a value must return the `Void` type.
- Returning `()` is allowed, but creates a new (emtpy) tuple object.

## Asynchronous functions (coroutines)
- See [**coroutines**](coroutines.md) for more information.
- Functions defined as `gn` rather than `fn` are asynchronous.
- This means that a value is `yielded` rather than `returned`.
- If the return type super-imposes `Async`, then the function will return immediately, and values will be yielded asynchronously.
- Otherwise, the function will yield a `T` object -- **TODO**
- Yielding conventions
  - Yielding borrows is allowed, as control is passed back to the caller.
  - However, all yield must use the same convention ie if 1 yield statement yields an immutable borrow, then all yield statements must yield an immutable borrow.
  - This allows the compiler to keep track of the type of yield taking place, and enforce the necessary memory safety rules.

## Recursion
- Recursion is allowed.
- All recursive functions are tail-call optimised.
  - Recursive functions that aren't tail-call recursive are re-written to be tail-call recursive.
  - This means that the stack will not overflow.
  - The stack will only ever contain a single frame for a recursive function.
  - Recursion is time-limited, not stack-limited.
