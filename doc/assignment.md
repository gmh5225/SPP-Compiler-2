# Assignment
- Simple `=` expression
- Automatic destructuring
- Multi-assignment is supported

## Example
```s++
let x = 123  # x is a Num
let y = 456  # y is a Num
```
### Single assignment:
```s++
x = 1
y = 2
```

### Multi-assignment:
- There can only be 1 element on the RHS, so make it a tuple.
- Tuples are first-class language structures, so destructuring is automatic.
- The following is equivalent to the above:
```s++
x, y = (1, 2)
```
