# Literals
- There aren't a lot of literals in the language.
- Reduces syntactic noise, and more complex types (maps, sets) have their own constructing methods.

## Language literals
#### Base 10 number literal
- Has an integer part
- Can have a fractional part
- Can have an exponent part
- Can be marked as imaginary
- Creates a `Num` object

#### Base 2 number literal
- Prefix with `0b`
- Has an integer part
- Creates a `Num` object

#### Base 16 number literal
- Prefix with `0x`
- Has an integer part
- Creates a `Num` object

#### String literal
- Surrounded by double quotes
- Can contain escape sequences
- Can contain interpolation sequences with the `${...}` groupings
- Creates a `Str` object

#### Array literal
- Surrounded by square brackets
- Every element must be of the same type
- Creates an `Arr[T]` object

## Common literals not in S++
#### Character literal
- Instead, single character strings are used.
- No need to have a separate type for a single character.
- Reduces syntactic noise.

#### Base 8 number literal
- Base 8 is not used often enough to warrant a separate literal.
- Use other number literal types.

#### Map, Set, Vec etc
- Use the class' construction methods ie `.new(...)`
- Because variadic parameters are supported, this is not a problem, and doesn't require macros.
