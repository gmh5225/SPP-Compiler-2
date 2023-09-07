# Blocks -- Looping
- The `while` statement is the only looping block in S++.
- The `for` statement is emulated using the [**streams API**](./streams.md).

## Structure
- The `while` statement is modelled as an expression, but cannot be used for assignment -- semantic analysis prohibits this..
- After the `while` keyword, a condition is required, which **must** evaluate to the `Bool` type -- [**no implicit casting**](casting.md).
- Inside the braces is where the statements making up the loop's body are placed.
- An optional residual block is allowed after the `while` block, in an `else` block.

```s++
let x = 0
while x < 100 {
    x = x + 1
}
```

## Infinite loops
### Detection
- If the variables in the condition don't change in the loop's body, then the loop is **infinite**.
- If the variables acting as parameters in _pure_ function calls in the condition don't change in the loop's body, then the loop is **infinite**.
- If _non-pure_ functions are called in the condition, then the loop is un-analyzable, and is assumed to be **finite**.

## Residual action
- Use the `else` keyword to specify a residual action.
- This only executes if the loop never executes, ie the condition is false from the start.

### Why include a residual action block?
- It shortens code: instead of doing an `if` check then a `while` loop with the same condition, only the `while` loop is required.
- The `else` block then executes the code that would have been executed had the `if` condition resulted in `false`.

###### Original
```s++
if x {
    < 100 {
        while x < 100 {
            x = x + 1
        }
    }
    else {
        print("x is already > 100")
    }
}
```

###### Shortened

```s++
while x < 100 {
    x = x + 1
}
else {
    print("x is already > 100")
}
```

## Control flow
- No `break` or `continue` statements, as this disrupts the flow of the code within a block.
- Therefore, whilst `while` loops are modelled as expressions, they cannot be used for assignment results.


## Design decisions
- Almost had no looping statements as recursion can emulate looping.
- Looping statements abstract over recursion, and heavily simplify the code.
