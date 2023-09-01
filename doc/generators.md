# Generators
- Special type of coroutine that can `yield` multiple times.
- Use the return type `Gen[Yield, Return, Send]`, and yield to it.

## The `Gen` type
- The `Gen` type super-imposed `Async` so that it can be returned immediately.
- The `Gen` type has a `next` function that can be used to send values back into the generator.

### Type parameters
- `Yield` is the type that is yielded to the generator.
- `Return` is the type that is returned from the generator.
- `Send` is the type that is sent back into the generator.