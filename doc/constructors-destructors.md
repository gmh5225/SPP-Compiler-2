# Constructors
- Struct initialization can be used to instantiate a class, initializing every attribute.
- There are no constructors for classes, because static methods can do the same thing.
- Static methods typically wrap struct initialization.

## Struct initialization
- Struct initialization is a special syntax for initializing structs.
- It is used to instantiate classes, and is the only way to instantiate structs.

```s++
cls Point {
    x: Num
    y: Num
}

fn main() -> Void {
    let p = Point { x=5, y=10 }  # initialize a Point object with x=5 and y=10
    let q = Point { x=8, y=16 }  # initialize a Point object with x=8 and y=16
}
```

### Wrap struct initialization in a static method
```s++
sup Point {
    fn new(x: Num, y: Num) -> Point {
        return Point { x=x, y=y }
    }
}

fn main() -> Void {
    let p = Point.new(5, 10)  # initialize a Point object with x=5 and y=10
    let q = Point.new(8, 16)  # initialize a Point object with x=8 and y=16
}
```
- This can be used to fill default arguments, or call other methods.
- Seen in `Vec[T].new()` and `Vec[T].with_capacity()`.


# Destructors
- Destruction is an "operation", so the special `Del` class can be super-imposed.
- All code in `Del.del(...)` is executed when the object is destroyed.
- Objects can be destructed early by calling `.del()` on them, as the method is self-consuming.
- All initialized objects are destructed when they go out of scope (no double free).