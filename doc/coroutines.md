# Coroutines
- A lot of overlap with the [**async**](./async.md) section.
- A coroutine is a function that can be paused and resumed.
- A coroutine is not necessarily asynchronous.

## Define a coroutine
- As seen in [**defining an asynchronous function**](./functions.md#asynchronous-functions), use the `gn` keyword to define a coroutine.
- The return type doesn't have to super-impose `std.Async`
- Asynchronous return types are returned immediately, and can be interacted with using the `yield` keyword.
- Non-asynchronous return types are returned with the `yield` keyword.

### The `gn` keyword
- Because the `coroutines` are technically stackless, they are more like "generators".
- Generators can be abbreviated to `gn`, anf follows from `fn` more nicely.