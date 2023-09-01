# Operators
- S++ strips down the number of operators to the bare minimum.
- This is to reduce syntactic noise, and to make the language easier to learn.
- There are no unary operators in the language at all
- There are a reduced number of binary operators
- There are no ternary operators


## Binary operators
| Symbol | Name                      | Description                                                                  | Class                |
|--------|---------------------------|------------------------------------------------------------------------------|----------------------|
| `=`    | Assignment                | Assigns the value of the right hand side to the left hand side.              |                      |
| `+=`   | Addition assignment       | Adds the right value to the left value, and assigns the result to it         | `std.ops.AddAssign`  |
| `-=`   | Subtraction assignment    | Subtracts the right value from the left value, and assigns the result to it. | `std.ops.SubAssign`  |
| `*=`   | Multiplication assignment | Multiplies the left value by the right value, and assigns the result to it.  | `std.ops.MulAssign`  |
| `/=`   | Division assignment       | Divides the left value by the right value, and assigns the result to it.     | `std.ops.DivAssign`  |
| `\|=`  | Or assignment             | Takes the logical OR of two values, and assigns the result to it             | `std.ops.OrAssign`   |
| `&&=`  | And assignment            | Takes the logical AND of two values, and assigns the result to it            | `std.ops.AndAssign`  |
| `&=`   | Bitwise and assignment    | Takes the bitwise AND of two values, and assigns the result to it            | `std.ops.BAndAssign` |
| `^=`   | Bitwise xor assignment    | Takes the bitwise XOR of two values, and assigns the result to it            | `std.ops.BXorAssign` |
| `+`    | Addition                  | Adds the right value to the left value.                                      | `std.ops.Add`        |
| `-`    | Subtraction               | Subtracts the right value from the left value.                               | `std.ops.Sub`        |
| `*`    | Multiplication            | Multiplies the left value by the right value.                                | `std.ops.Mul`        |
| `/`    | Division                  | Divides the left value by the right value.                                   | `std.ops.Div`        |
| `\|\|` | Or                        | Takes the logical OR of two values                                           | `std.ops.Or`         |
| `&&`   | And                       | Takes the logical AND of two values                                          | `std.ops.And`        |
| `\|`   | Bitwise or                | Takes the bitwise OR of two values                                           | `std.ops.BOr`        |
| `\|= ` | Bitwise or assignment     | Takes the bitwise OR of two values, and assigns the result to it             | `std.ops.BOrAssign`  |
| `&`    | Bitwise and               | Takes the bitwise AND of two values                                          | `std.ops.BAnd`       |
| `^`    | Bitwise xor               | Takes the bitwise XOR of two values                                          | `std.ops.BXor`       |
| `==`   | Equals                    | Checks if two values are equal                                               | `std.ops.Eq`         |
| `!=`   | Not equals                | Checks if two values are not equal                                           | `std.ops.Ne`         |
| `<`    | Less than                 | Checks if the left value is less than the right value                        | `std.ops.Lt`         |
| `<=`   | Less than or equal to     | Checks if the left value is less than or equal to the right value            | `std.ops.Le`         |
| `>`    | Greater than              | Checks if the left value is greater than the right value                     | `std.ops.Gt`         |
| `>=`   | Greater than or equal to  | Checks if the left value is greater than or equal to the right value         | `std.ops.Ge`         |
| `<=>`  | Compare                   | Compares two values                                                          | `std.ops.Cmp`        |

### Precedence
| Precedence | Operators                               |
|------------|-----------------------------------------|
| 1          | `=`                                     |
| 2          | `\|\|`                                  |
| 3          | `&&`                                    |
| 4          | `==`, `!=`, `<`, `<=`, `>`, `>=`, `<=>` |
| 5          | `+`, `-`, `\|`, `^`                     |
| 6          | `*`, `/`, `&`                           |

### Operator overloading
- Super-impose the corresponding class onto the type to overload the operator.
- For example, to overload the `+` operator, super-impose the `Add` class onto the type.
```s++
cls Add[Rhs, Output=Self] {
    use Rhs as Rhs
    use Output as Output

    fn add(self: &Self, other: T) -> Output { ... }
}

sup Add[Num] for Num {
    fn add(self: &Num, other: Num) -> Num { ... }
}
```
- Because `Num` also implements the `Copy` trait, the RHS isn't consumed in the addition operation.

### Other common binary operators not in S++
- `<<` and `>>` are not in S++. Instead, use the `std.bit` module.
- `++` and `--` are not in S++. Instead, use the `+=` and `-=` operators.
- `?:` is not in S++. Instead, use the `if`/`else` expression.
