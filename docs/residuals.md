# Residuals
#### Examples:
- `std::Option<T>`
- `std::Result<T, E>`

### Early return
#### Shorthand
- Use the postfix `?` operator to return early if the result is the residual error value
- The `?` operator can be used on any object that super-imposes the `std::ops::Try` class

#### Else clause
- The `else` clause can be added to a `let` statement to specify a block of code to execute if the value is the residual error value
- Allows for a more complex early return, for example, to return a different error value

#### The null-coalescing operator
- The `??` operator can be used as shorthand to select a different value if the current one is the residual error value
- For example: `let a = some_function() ?? 0;` will call `some_function`, unwrap the value if it is valid, otherwise return `0`
- The `??` operator can be used on any object that super-imposes the `std::ops::Try` class
- Acts the same as `std::Option::unwrap_or`, but is more concise - is an operator for classes that don't have an `unwrap_or()`
