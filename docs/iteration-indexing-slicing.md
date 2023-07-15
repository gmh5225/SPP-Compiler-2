# Iteration, Indexing & Slicing
## Iteration
- 2nd class references mean that references cannot be returned, posing a difficulty for iteration.
- Iteration is possible by passing a closure or function to the `iter` method
- The `for` loop is syntactic sugar for iteration
- Example:
```s++
for x, y, z in some_collection.iter() {
    // do something with x, y, z
}
```
- Is actually:
```s++
some_collection.iter((x, y, z) => {
    // do something with x, y, z
});
```