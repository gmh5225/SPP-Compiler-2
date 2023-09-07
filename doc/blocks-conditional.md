# Blocks (Conditional)
- Special `if` and pattern statements.
- Quite different to other language's `if` statements.
- They are technically expressions too (can be on RHS of a binary expression etc).

## Structure
- The `if` keyword is followed by an expression.
- This expression doesn't have to be a boolean expression.
- The expression can be followed by an operator.
- Each branch is applied against the operator if it exists.
- Each branches' application against the condition **must** evaluate to a `Bool` type.

## Examples
### Simple `==` comparison
```s++
let my_number = 1
let str = if my_number == {
    1 { "one" }
    2 { "two" }
    3 { "three" }
    else { "unknown" }
}
```
- This allows each branch's pattern to be applied to the `==` operator of the `Num` class.
- The result of the operator functions must be `Bool` types.

### Different comparison operators
```s++
let my_number = 1
let str = if my_number {
    < 1 { "less than one" }
    > 1 { "greater than one" }
    else { "one" }
}
```
- Allows for different comparison operators to be used.
- The result of the operator functions must be `Bool` types.

### Extending operators to methods and attributes
```s++
let my_number = 1
let str = if my_number {
    .is_even() { "even" }
    .is_odd() { "odd" }
    else { "unknown" }
}
```
- Allows for methods and attributes to be used in the pattern.
- Operators ie `my_numbers == 1` are just syntactic sugar for `my_number.eq(1)`.
- The method results / attributes must be `Bool` types.

### Allowing for multiple matches on a pattern-branch
```s++
let my_number = 1
let str = if my_number == {
    1 | 2 | 3 { "one, two or three" }
    4 | 5 | 6 { "four, five or six" }
    7 | 8 | 9 { "seven, eight or nine" }
    else { "unknown" }
}
```
- Each pattern is separated by the `|` operator.
- Each pattern is then applied to the operator per branch.
- For self-consuming methods, multiple patterns can't be used (unless `Copy` is super-imposed).

### Pattern-branch guards
```s++
let my_number = 1
let str = if my_number == {
    1 && some_func() { "one and some_func() is true" }
    2 && some_func() { "two and some_func() is true" }
    else { "error" }
}
```
- Each pattern can be _guarded_ by a boolean expression, placed after a `&&` token.
- The boolean expression is evaluated after the pattern is matched.
- The boolean expression must evaluate to a `Bool` type.

## Assignment from `if` statements
- Each branch must return a value.
- The last statement of each branch is the return statement.
- Each branch's returning statement must be the same type.
- The `if` statement returns the value of the branch that was executed.
- The `else` branch is required for assignment.