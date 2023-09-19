# Operators
- S++ strips down the number of operators to the bare minimum.
- This is to reduce syntactic noise, and to make the language easier to learn.
- There are no unary operators in the language at all
- There are a reduced number of binary operators
- There are no ternary operators


## Binary operators
- There are some operators that don't have equivalent symbols (empty `Symbol` cell)

| Symbol  | Name                        | Description                                                                   | Class                | CPU instruction |
|---------|-----------------------------|-------------------------------------------------------------------------------|----------------------|-----------------|
| `=`     | Assignment                  | Assigns the value of the right hand side to the left hand side.               |                      |
| `+=`    | Addition assignment         | Adds the right value to the left value, and assigns the result to it.         | `std.ops.AddAssign`  |
| `-=`    | Subtraction assignment      | Subtracts the right value from the left value, and assigns the result to it.  | `std.ops.SubAssign`  |
| `*=`    | Multiplication assignment   | Multiplies the left value by the right value, and assigns the result to it.   | `std.ops.MulAssign`  |
| `/=`    | Division assignment         | Divides the left value by the right value, and assigns the result to it.      | `std.ops.DivAssign`  |
| `%=`    | Remainder assignment        | Takes the remainder of two values, and assigns the result to it               | `std.ops.RemAssign`  |
| `\|\|=` | Or assignment               | Takes the logical OR of two values, and assigns the result to it              | `std.ops.OrAssign`   |
| `\|= `  | Bitwise or assignment       | Takes the bitwise OR of two values, and assigns the result to it              | `std.ops.BOrAssign`  |
| `&&=`   | And assignment              | Takes the logical AND of two values, and assigns the result to it             | `std.ops.AndAssign`  |
| `&=`    | Bitwise and assignment      | Takes the bitwise AND of two values, and assigns the result to it             | `std.ops.BAndAssign` |
| `^=`    | Bitwise xor assignment      | Takes the bitwise XOR of two values, and assigns the result to it             | `std.ops.BXorAssign` |
| `<<=`   | Bit shift left assignment   | Shifts the left value left by the right value, and assigns the result to it   | `std.ops.ShlAssign`  |
| `>>=`   | Bit shift right assignment  | Shifts the left value right by the right value, and assigns the result to it  | `std.ops.ShrAssign`  |
| `<<<=`  | Bit rotate left assignment  | Rotates the left value left by the right value, and assigns the result to it  | `std.ops.RolAssign`  |
| `>>>=`  | Bit rotate right assignment | Rotates the left value right by the right value, and assigns the result to it | `std.ops.RorAssign`  |
| `+`     | Addition                    | Adds the right value to the left value.                                       | `std.ops.Add`        | `ADD`           |
| `-`     | Subtraction                 | Subtracts the right value from the left value.                                | `std.ops.Sub`        | `SBB`           |
| `*`     | Multiplication              | Multiplies the left value by the right value.                                 | `std.ops.Mul`        | `MUL`           |
| `/`     | Division                    | Divides the left value by the right value.                                    | `std.ops.Div`        | `DIV`           |
| `%`     | Remainder                   | Takes the remainder of two values                                             | `std.ops.Rem`        |
| `\|\|`  | Or                          | Takes the logical OR of two values                                            | `std.ops.Or`         | `OR`            |
| `&&`    | And                         | Takes the logical AND of two values                                           | `std.ops.And`        | `AND`           |
| `\|`    | Bitwise or                  | Takes the bitwise OR of two values                                            | `std.ops.BOr`        |
| `&`     | Bitwise and                 | Takes the bitwise AND of two values                                           | `std.ops.BAnd`       |
| `^`     | Bitwise xor                 | Takes the bitwise XOR of two values                                           | `std.ops.BXor`       |
| `<<`    | Bit shift left              | Shifts the left value left by the right value                                 | `std.ops.Shl`        | `SHL`           |
| `>>`    | Bit shift right             | Shifts the left value right by the right value                                | `std.ops.Shr`        | `SHR`           |
| `<<<`   | Bit rotate left             | Rotates the left value left by the right value                                | `std.ops.Rol`        | `ROL`           |
| `>>>`   | Bit rotate right            | Rotates the left value right by the right value                               | `std.ops.Ror`        | `ROR`           |
| `==`    | Equals                      | Checks if two values are equal                                                | `std.ops.Eq`         |
| `!=`    | Not equals                  | Checks if two values are not equal                                            | `std.ops.Ne`         |
| `<`     | Less than                   | Checks if the left value is less than the right value                         | `std.ops.Lt`         |
| `<=`    | Less than or equal to       | Checks if the left value is less than or equal to the right value             | `std.ops.Le`         |
| `>`     | Greater than                | Checks if the left value is greater than the right value                      | `std.ops.Gt`         |
| `>=`    | Greater than or equal to    | Checks if the left value is greater than or equal to the right value          | `std.ops.Ge`         |
| `<=>`   | Compare                     | Compares two values                                                           | `std.ops.Cmp`        |
|         | Modulo                      | Takes the modulo of two values                                                | `std.ops.Mod`        |
|         | Power                       | Raises the left value to the power of the right value                         | `std.ops.Pow`        |
- Modulo might get the `%%` operator.
- Power might get the `**` operator.


### Precedence
| Precedence | Type                           | Operators                                                                                          |
|------------|--------------------------------|----------------------------------------------------------------------------------------------------|
| 0          | Assignment                     | `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `\|\|=`, `\|=`, `&&=`, `&=`, `^=`, `<<=`, `>>=`, `<<<=`, `>>>=` | 
| 1          | Logical or                     | `\|\|`                                                                                             |
| 2          | Logical and                    | `&&`                                                                                               |
| 3          | Comparisons                    | `==`, `!=`, `<`, `<=`, `>`, `>=`, `<=>`                                                            |
| 4          | Bit shifting                   | `<<`, `>>`, `<<<`, `>>>`                                                                           |
| 5          | Math & bitwise additives       | `+`, `-`, `\|`, `^`                                                                                |
| 6          | Math & bitwise multiplicatives | `*`, `/`, `%`, `&`                                                                                 |

### Operator overloading
- Super-impose the corresponding class onto the type to overload the operator.
- For example, to overload the `+` operator, super-impose the `Add` class onto the type.
```s++
cls Add[Rhs, Output=Self] {
    use Rhs as Rhs
    use Output as Output
}

sup[Rhs, Output=Self] Add[Rhs, Output] {
    fn add(self, that: Rhs) -> Output { ... }
}

sup Add[Num] for Num {
    fn add(self, that: Num) -> Self { ... }
}
```
- Because `Num` also implements the `Copy` trait, the RHS isn't consumed in the addition operation.

### Operator chaining
- Identical comparative operators can be chained, like Python, to simplify multi-comparisons.
- There are no _constraints_ on which comparative operators are compatible with each other -> they are all chained.

| S++           | Converted to       |
|---------------|--------------------|
| `a < b <= c`  | `a < b && b <= c`  |
| `a == b == c` | `a == b && b == c` |

### Other common binary operators not in S++
- `++` and `--` are not in S++. Instead, use the `+=` and `-=` operators.
- `?:` is not in S++. Instead, use the `if`/`else` expression.
- `**` is not an operator, as there is no dedicated CPU instruction for exponentiation.

---

## Unary operators
- There are no unary operators in `S++`
- Instead, super-impose the corresponding class.
- Call the method associated with the operator.

| Symbol  | Name                        | Description                                                                   | Class                | CPU instruction |
|---------|-----------------------------|-------------------------------------------------------------------------------|----------------------|-----------------|
|         | Not                         | Takes the logical NOT of a value                                              | `std.ops.Not`        | `NOT`           |
|         | Bitwise not                 | Takes the bitwise NOT of a value                                              | `std.ops.BNot`       | `NEG`           |

---

## Postfix operators
- There are only 3 postfix operators in `S++`
- Functions are split into 3 different operators, based on context.
- See [**functions**](./functions.md#function-types).

| Symbol  | Name                  | Description                                     | Class           |
|---------|-----------------------|-------------------------------------------------|-----------------|
| `(...)` | `FnRef`               | Call a function in a immutably borrowed context | `std.ops.FnRef` |
| `(...)` | `FnMut`               | Call a function in a mutably borrowed context   | `std.ops.FnMut` |
| `(...)` | `FnOne`               | Call a function in a moved context              | `std.ops.FnOne` |
| `{...}` | Struct initialization | Initialize a struct will all its fields         |                 |
| `.`     | Member access         | Access a member of a struct                     |                 |