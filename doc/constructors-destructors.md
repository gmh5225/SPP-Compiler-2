# Constructors
- Struct initialization can be used to create a class, initializing every attribute.
- There are no constructors for classes, because static methods can do the same thing.
- Static methods typically wrap struct initialization.

# Destructors
- Destruction is an "operation", so the special `Del` class can be super-imposed.
- All code in `Del.del(...)` is executed when the object is destroyed.
