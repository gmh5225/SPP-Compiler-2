# Coroutines
- A coroutine is a function that can be paused and resumed.
- A coroutine is not necessarily asynchronous.

## Define a coroutine
- As seen in [**defining an asynchronous function**](./functions.md#asynchronous-functions), use the `gn` keyword to define a coroutine.
- The return type doesn't have to super-impose `Async`
- Asynchronous return types are returned immediately, and can be interacted with using the `yield` keyword.
- Non-asynchronous return types are returned with the `yield` keyword.

## Commonly seen coroutines
### Generators
- Return a `Gen[Yield, Return, Send]` generator object.
- Can be yielded into multiple times, and receive values sent back into the generator.
- Can send values back into the generator with `gen.next(value)`, and `let x = yield 5`.

### Async functions
- Return a `Fut[T]` future object.
- Can be yielded into only once (yielding multiple times is allowed but won't do anything).
- Remove the need for `await/async` syntax: just call `fut.await()` to block.

### Other
- Other types that super-impose `Async` will always be returned immediately.
- The `Async` type has a function for handling yielding and receiving.
- For example, both `Gen[T]` and `Fut[T]` super-impose `Async`, so they will always return immediately.

```s++
cls Async[Yield, Return, Send] {}

sup[Yield, Return, Send] Async[Yield, Return, Send] {
    fn yield(value: Yield) -> Void {}
    fn return(value: Return) -> Void {}
    fn send(value: Send) -> Void {}
}
```

## Yielding
- The special property of yielding is that it is *guaranteed* that control will return to the caller.
- This means that yielding references out of a function is safe, and doesn't violate second-class reference rules.
- The return type will remain just be the type the reference corresponds to, so `yield &5` would `yield` a `Num` object.
- All yield statements must use the same convention (`&`, `&mut`, or no convention ie move).

## Why "`gn`"?
- Because the `coroutines` are technically stackless, they are more like "generators".
- Generators can be abbreviated to `gn`, anf follows from `fn` nicely.