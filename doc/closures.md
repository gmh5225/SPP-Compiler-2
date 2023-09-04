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
