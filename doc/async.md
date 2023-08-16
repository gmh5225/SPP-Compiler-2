# Async
- Asynchronous functions are defined with the `gn` keyword rather than the standard `fn` keyword.
- `gn` functions return immediately, ie the `Gen[T]` or `Fut[T]` object.
- The rest of the function can execute and interact with the `Gen[T]` or `Fut[T]` object with the `yield` keyword.

## Commonly seen
### Generators
- Return a `Gen[T]` object.
- Can `yield` multiple times.
- Can send values back into the generator with `gen.next(value)`, and `let x = yield 5`.

### Async functions
- Return a `Fut[T]` object.
- Can yield only once.
- Remove the need for `await/async` syntax: just call `fut.await()`.

### Other
- Objects that super-impose `Async` will always be returned immediately.
- For example, both `Gen[T]` and `Fut[T]` super-impose `Async`, so they will always return immediately.

## Yielding
- The special property of yielding is that it is *guaranteed* that control will return to the caller.
- This means that yielding references out of a function is safe, and doesn't violate second-class reference rules.
- The return type will remain just be the type the reference corresponds to, so `yield &5` would `yield` a `Num` object.
- 
