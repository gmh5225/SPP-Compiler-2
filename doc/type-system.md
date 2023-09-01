# Type System
- Everything is an object, even numbers, booleans etc.
- Every super-imposition adds a new type to the sup-types in the symbol table.
- Constraints are therefore based on the types being super-imposed.

## Static type system
- All types must be known at compile time.

## Case
- All types must begin with an upper-case character.
- This allows the parser to easily tell the difference between a type and a variable.
