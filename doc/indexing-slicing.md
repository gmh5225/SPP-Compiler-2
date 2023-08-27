# Indexing & Slicing
- First read the [iteration](iteration.md) page to understand how iteration works in S++.
- Indexing and slicing work by yielding borrows to the data.
- A generator is not required, as the borrows are yielded immediately.
- Instead, a `Fut[T]` future object is returned, which can be awaited on for the result.

## Indexing
- Indexing is done with the `get_ref` or `get_mut` methods.
- These methods return a `Fut[T]` object, which can be awaited on for the result.
- The `Fut[T]` object will return a `&T` or `&mut T` object, depending on the calling convention.
- The `Gen[T]` object passes control of the borrow back to the caller after the `.next()` call.

### Example
```s++
let vec = Vec.new(1, 2, 3)
let x = vec.get_ref(1).await()
std.io.print(x) # prints 2
```