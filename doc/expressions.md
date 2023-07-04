# Expressions

## Literals
| Literal         | Example         | Description        | Default Type |
|-----------------|-----------------|--------------------|--------------|
| `Base02 Number` | `0b101010`      | Binary number      | `std::Num`   |
| `Base16 Number` | `0xa2`          | Hexadecimal number | `std::Num`   |
| `Base10 Number` | `42.4e+10`      | Decimal number     | `std::Num`   |
| `String`        | `"Hello"`       | String             | `std::Str`   |
| `Char`          | `'a'`           | Character          | `std::Char`  |
| `Bool`          | `true`, `false` | Boolean            | `std::Bool`  |
| `Vector`        | `[1, 2, 3]`     | Vector             | `std::Vec`   |
| `Tuple`         | `(1, 2, 3)`     | Tuple              | `std::Tup`   |
| `Map`           | `{1: 2, 3: 4}`  | Map                | `std::Map`   |
| `Set`           | `{1, 2, 3}`     | Set                | `std::Set`   |
| `Range`         | `1..10`         | Range              | `std::Range` |

## Primary Expressions
| Primary Expression        | Description                                        | Example        |
|---------------------------|----------------------------------------------------|----------------|
| `Identifier`              | Some variable/function or type                     | `variable_a`   |
| `Literal`                 | Create a new instance of a type using shorthand    | `[0, 1, 2]`    |
| `ScopedGenericIdentifier` | Will be a namespaced type / function               | `std::Str`     |
| `Lambda`                  | Closure function allowing an expression            | `(x) -> x + 1` |
| `Parenthesized`           | Contain an expression to execute first             | `(1 + 2)`      |
| `Placeholder`             | Placeholders for match/case, partial functions etc | `_`            |
| `IfStatement`             |                                                    |                |
| `MatchStatement`          |                                                    |                |
| `WhileStatement`          |                                                    |                |
| `ForStatement`            |                                                    |                |

## Operators
### Operator Tables
#### Binary operators: apply to two arguments that are mapped into the \_\_fn__'s parameters
| Binary Operator | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `=`             | Assignment - Assign right expression to left expression                     |
| `??`, `??=`     | Null coalescing - Return left expression if not null, else right            |
| `?:`, `?:=`     | Elvis operator - Return right expression if not null, else left             |
| `&&`, `&&=`     | Logical AND - Logical AND of two expressions                                |
| `\|\|`, `\|\|=` | Logical OR - Logical OR of two expressions                                  |
| `&`, `&=`       | Bitwise AND - Bitwise AND of two expressions                                |
| `\|`, `\|=`     | Bitwise OR - Bitwise OR of two expressions                                  |
| `^`, `^=`       | Bitwise XOR - Bitwise XOR of two expressions                                |
| `<<`, `<<=`     | Bitwise left shift - Bitwise left shift of two expressions                  |
| `>>`, `>>=`     | Bitwise right shift - Bitwise right shift of two expressions                |
| `<<<`, `<<<=`   | Bitwise left rotate - Bitwise left rotate of two expressions                |
| `>>>`, `>>>=`   | Bitwise right rotate - Bitwise right rotate of two expressions              |
| `<=>`           | Comparison - Compare two expressions                                        |
| `==`            | Equality - Check if two expressions are equal                               |
| `!=`            | Inequality - Check if two expressions are not equal                         |
| `<`             | Less than - Check if left expression is less than right expression          |
| `>`             | Greater than - Check if left expression is greater than right               |
| `<=`            | Less than or equal - Check if left expression is less than or equal         |
| `>=`            | Greater than or equal - Check if left expression is greater than or         |
| `+`, `+=`       | Addition - Add two expressions                                              |
| `-`, `-=`       | Subtraction - Subtract two expressions                                      |
| `*`, `*=`       | Multiplication - Multiply two expressions                                   |
| `/`, `/=`       | Division - Divide two expressions                                           |
| `%`, `%=`       | Modulo - Modulo of two expressions                                          |
| `//`, `//=`     | Integer division - Divide two expressions                                   |
| `**`, `**=`     | Exponentiation - Exponentiate two expressions                               |
| `\|>`           | Pipe function operator - Pipe the left expression into the right expression |

<BR>

#### Unary operators: apply to one argument that is mapped into the \_\_fn__'s parameter
| Unary Operator | Description                                         |
|----------------|-----------------------------------------------------|
| `~`            | Bitwise NOT - Bitwise NOT of an expression          |
| `!`            | Logical NOT - Logical NOT of an expression          |
| `&` \| `&mut`  | Reference to - Take a reference to an owning object |
| `+`            | Absolute - Take the absolute value                  |
| `-`            | Negate - Negate the current value                   |

<BR>

#### Postfix operators: apply to one argument that is mapped into the \_\_fn__'s parameter
| Postfix Operator | Description                                                      |
|------------------|------------------------------------------------------------------|
| `()`             | Function call - Call a function with the given arguments         |
| `[]`             | Index - Index into a collection with the given index             |
| `{}`             | Initialize a class with the given arguments                      |
| `.`              | Member access - Access a member of an object                     |
| `?`              | Force unwrap - Unwrap an optional object (return error if error) |


### Overloading operators
- Operators can be overloaded by implementing the corresponding class containing the magic methods
- Only the reference operator `&[mut]?` cannot be overloaded for a type
- The function pipe operator must be implemented on the receiving type, not the argument type

| Class                    | Magic methods                       | Description                      |
|--------------------------|-------------------------------------|----------------------------------|
| `std::ops::Add`          | `__add__`, `__add_assign__`         | Binary `+`                       |
| `std::ops::Sub`          | `__sub__`, `__sub_assign__`         | Binary `-`                       |
| `std::ops::Mul`          | `__mul__`, `__mul_assign__`         | Binary `*`                       |
| `std::ops::Div`          | `__div__`, `__div_assign__`         | Binary `/`                       |
| `std::ops::Pow`          | `__pow__`, `__pow_assign__`         | Binary `**`                      |
| `std::ops::Flo`          | `__flo__`, `__flo_assign__`         | Binary `//`                      |
| `std::ops::Mod`          | `__mod__`, `__mod_assign__`         | Binary `%`                       |
| `std::ops::Not`          | `__not__`                           | Unary `!`                        |
| `std::ops::And`          | `__and__`, `__and_assign__`         | Binary `&&`                      |
| `std::ops::Or`           | `__or__`, `__or_assign__`           | Binary `\|\|`                    |
| `std::ops::BitNot`       | `__bit_not__`, `__bit_not_assign__` | Unary `~`                        |
| `std::ops::BitAnd`       | `__bit_and__`, `__bit_and_assign__` | Binary `&`                       |
| `std::ops::BitOr`        | `__bit_or__`, `__bit_or_assign__`   | Binary `\|`                      |
| `std::ops::BitXor`       | `__bit_xor__`, `__bit_xor_assign__` | Binary `^`                       |
| `std::ops::BitShfitL`    | `__bit_shl__`, `__bit_shl_assign__` | Binary `<<`                      |
| `std::ops::BitShiftR`    | `__bit_shr__`, `__bit_shr_assign__` | Binary `>>`                      |
| `std::ops::BitRotateL`   | `__bit_rol__`, `__bit_rol_assign__` | Binary `<<<`                     |
| `std::ops::BitRotateR`   | `__bit_ror__`, `__bit_ror_assign__` | Binary `>>>`                     |
| `std::ops::Eq`           | `__eq__`                            | Binary `==`                      |
| `std::ops::Ne`           | `__ne__`                            | Binary `!=`                      |
| `std::ops::Lt`           | `__lt__`                            | Binary `<`                       |
| `std::ops::Le`           | `__le__`                            | Binary `<=`                      |
| `std::ops::Gt`           | `__gt__`                            | Binary `>`                       |
| `std::ops::Ge`           | `__ge__`                            | Binary `>=`                      |
| `std::ops::Cmp`          | `__cmp__`                           | Binary `<=>`                     |
| `std::ops::NullCoalesce` | `__nlc__`, `__nlc_assign__`         | Binary `??`                      |
| `std::ops::Pipe`         | `__pip__`                           | Binary `\|>`                     |
| `std::ops::Neg`          | `__neg__`                           | Unary `-`                        |
| `std::ops::Abs`          | `__abs__`                           | Unary `+`                        |
| `std::ops::Variadic`     | `__pack__`, `__unpack__`            | Pack/unpack to/from type         |
| `std::func::FunOnce`     | `__call_once__`                     | Postfix call                     |
| `std::func::FunRef`      | `__call_ref__`                      | Postfix call                     |
| `std::func::FunMut`      | `__call_mut__`                      | Postfix call                     |
| `std::ops::IndexRef`     | `__index_ref__`                     | Postfix subscript                |
| `std::ops::IndexMut`     | `__index_mut__`                     | Postfix subscript                |
| `std::ops::SliceRef`     | `__slice_ref__`                     | Postfix slice                    |
| `std::ops::SliceMut`     | `__slice_mut__`                     | Postfix slice                    |
| `std::ops::Try<T, E>`    | `__try__`                           | Postfix `?`                      |
| `std::ops::Del`          | `__del__`                           | Destructor                       |
| `std::ops::With`         | `__enter__`, `__exit__`             | For the `with` statement         |
| `std::ops::Rng`          | `__next__`                          | For the range literal ie `0..10` |

