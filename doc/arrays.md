# Arrays
- Arrays are the lowest level collection in S++.
- Represented by the `Arr[T]` class.
- They abstract over a C array.

## Creating arrays
- Use the array literal syntax: `[1, 2, 3]`.
- Use the `Arr[T].new()` static method.
- Because generics must be defined on type creation, `[]` cannot be used for the `let` statement.

## The array object
- Arrays are objects, so they have methods and attributes.
- The `Arr[T]` is a fixed size array, so it has a `length` attribute.
- Bounds access is checked at runtime, so a `Ret[T]` is returned.