# Super-imposition
- Implement methods or another class onto a given class.
- Alternative to class inheritance.
- A more organised way of combining class behaviour.
- Allows for multiple inheritance.

## Example (super-impose methods onto a class)
```s++
cls Foo {
    a: Num
    b: Num
}

sup Foo {
    fn foo(self: &Self) { ... }
    fn bar(self: &Self) { ... }
    fn baz(self: &Self) { ... }
}
```
- Methods can be declared in a `sup` block.
- Methods that don't contain statement bodies are "abstract".
- When super-imposing a class onto another class, "abstract" method _must_ be overridden.

## Example (super-impose classes onto another class)
```s++
cls Copy {}

sup Add for Num {
    fn add(self: &Self, other: Num) -> Num { ... }
}

sup Copy for Num {
    fn copy(self: &Self) -> Self { ... }
}

sup Default for Num {
    fn default(self: &Self) -> Self { ... }
}
```
- Only the methods in the base-class can be overridden in a given `sup` block.
- Attributes are also inherited into the super-imposed class, allowing "state" to be inherited.


