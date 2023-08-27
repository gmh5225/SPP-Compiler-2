# Classes
- Separate state and behaviour.
- Allows for extensions.
- Super-imposition allows to define behaviour.
- Classes are types -> require an titlecase name.

## Class definition
- Use the `cls` keyword.
- Generics can exist on the class, and can be constrained by a `where` block.
- Every member must have a type-annotation.
- No default values.

### Example
```s++
cls Point {
    x: Num
    y: Num
}
```

## Instantiation
- There are no constructors in S++, because static methods do the same thing.
- Struct initialization required every member to be specified in braces.
  - The `else` keyword can allow a default object to fill in the missing values.
  - The `sup` keyword is required for base classes (in a tuple).
    - Only base classes that are not stateless or super-impose `Default` are required.

## Class methods
- See [super-imposition](super-imposition.md) for more information.
