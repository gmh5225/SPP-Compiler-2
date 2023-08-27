# Residual Types
- Must super-impose `std.ops.Try`
- Commonly seen in the STL: `Opt[T]` and `Ret[T, E]`

## The optional type
- The `Opt[T]` has a nullable state.
- The `Opt[T]` is constructed with `std.some[T](val: T)` and `std.none[T]()`.
- Unwrapping a `Opt[T]` that is in the `none` state will panic.

## The result type
- The `Ret[T, E]` has a success state and an error state.
- The `Ret[T, E]` is constructed with `std.pass[T, E](val: T)` and `std.fail[T, E](err: E)`.
- Unwrapping a `Ret[T, E]` that is in the `fail` state will panic.

## The `?` operator
- Requires the type to super-impose `std.ops.Try`.
- If the type is in the `fail` state, the function will return the failed value immediately.
- Otherwise, the value will be unwrapped.

## Residual `let` statements
- The `let` statement can have an `else` block that is executed if the value is in the `none` or `fail` state.
