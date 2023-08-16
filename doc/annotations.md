# Annotations
- Similar to `Rust` attributes.
- Defined by using the `@` symbol.
- They operate at compile time, allowing for the token stream to be edited.
- The `std.ast` module provides wrapper methods for common annotation operations.
  - Wrapping functions, injecting tokens, etc.

# Commonly used annotations
- Access modifiers: `@public`, `@private`, `@protected`
- Function modifiers: `@staticmethod`, `@virtualmethod`, `@abstractmethod`
