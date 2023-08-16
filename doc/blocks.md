# Blocks
- Used to group statements together in a new scope.
- Blocks follow `if`, `while`, function definitions etc.

## Where can blocks be used?
- The `if` statement requires a block of pattern statements.
- The pattern statement requires a block for its body.
- The `while` statement requires a block of statements.
- The `while-else` statement requires a block of statements.
- The `fn`/`gn` statement requires a block of statements.
- The `let` statement can be followed by a block of statements.
- The `let-else` statement can be followed by a block of statements.
- Inner scopes can be created with blocks.

## Returning from blocks
- Because blocks are effectively expressions, the final statement in a block is returned, if the block is being used for assignment.
- If the block is not being used for assignment, the final statement is not returned.
```s++
let x = {
    let y = fn_call_1()
    let z = fn_call_2()
    y | z
}
```
- `X` will be assigned the value of `y | z`.

## Shadowing
- Inner blocks that re-define a variable name will shadow the outer variable.
- The inner definition is used until the end of the block.
- If an inner block doesn't redefine the variable, assignment falls to the outer definition.
- Follows the same rules as Rust.
```s++
fn function() -> Void {
    let x = 5
    let y = {
        let x = 6
        x # At this point, x is 6
    }
    # At this point, x is 5
}
```

```s++
fn function() -> Void {
    let x = 5
    let y = {
        x = 6
        x # At this point, x is 6
    }
    # At this point, x is 6
}
```
