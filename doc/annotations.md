# Annotations
- Similar to `Rust` attributes.
- Defined by using the `@` symbol.
- They operate at compile time, allowing for the token stream to be edited.
- The `std.ast` module provides wrapper methods for common annotation operations.
  - Wrapping functions, injecting tokens, etc.

## Defining an annotation
- The signature of an annotation is constricted as follows
  - The annotation must be a function.
  - The first parameter must have a `Vec<Token>` type.
  - The return type must be `Vec<Token>`.
- Any number of parameters after the first one are allowed, as they can be passed in on definition.
- The scope of a annotation is the scope 1 outside the function being decorated.
- Chaining annotations means that the output token stream on the inner annotation becomes the input token stream on the outer annotation.

## Added to the compiler
- Annotations won't be added until the compiler is self-hosting, because they require the `std.ast` module, and access to their own token stream.
