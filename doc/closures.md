# Closures
- Explicit capture list, with optional conventions per capture


## Memory safety
### Capturing borrows
- If a closure captures a borrow, it must be used before the borrow is dropped.
- This means that the closure can be passed between functions, as long as it is before the owning values are moved.
- The closure cannot be set as a class attribute because the closure will outlive the owning values.

### Capturing moves
- If a closure captures a move, the object is moved into the closure's scope.
- If the closure consumes the object, it can only be called once.

## Function type
- Capturing variables is done explicitly using the `with` keyword.
- The captured variables can be captured with an optional convention -- `&` or `&mut`.
- The captured variables are passed as fixed arguments to the function.

### Which function type is implemented by the closure?
- If 1+ variables are consumed by the closure, then the function type is `FnOne`.
- If 1+ variables are captured as a mutable borrow, then the function type is `FnMut`.
- Otherwise, the function type is `FnRef`.
