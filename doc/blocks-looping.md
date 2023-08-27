# Blocks (looping)
- The `do` statement is the only looping block in S++.
- The `for` statement is emulated using the **streams API**
- Almost had no looping statements as recursion can emulate looping.
- Looping statements abstract over recursion, and heavily simplify the code.

## Example
- The below code is a simple loop

```s++
let x = 0
do x < 100 {
    x = x + 1
}
```

## Residual action
- Use the `else` keyword to specify a residual action.
- This only executes if the loop never executes, ie the condition is false from the start.

```s++
do x < 100 {
    x = x + 1
}
else {
    print("x is already 100")
}
```

## Control
- No `break` or `continue`
- Therefore, whilst `do` loops are modelled as expressions, they cannot be used for assignment results.
