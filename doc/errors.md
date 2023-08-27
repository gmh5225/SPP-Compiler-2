# Errors / Exceptions
- There are no errors or exceptions in S++.
- There is no `try/catch/finally/throw/throws` etc.
- Return residual-encompassing types such as `Opt[T]` or `Ret[T, E]` instead.

## Example:
```s++
cls Err {
    message: Str
    metadata: Map[Str, Str]
}

fn main() -> Void {
    let err = Err {
        message: "Something went wrong",
        metadata: Map.new()
    }
    let ret = std.err[Str, Err](err)
}
```

## The `?` postfix operator
- The `?` operator is used to perform an "early return".
- The value being unwrapped must super-impose the `std.ops.Try` class.
