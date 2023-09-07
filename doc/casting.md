# Casting
- There is no implicit casting, keeping the type-system simple and safe.
- There is no special casting syntax, because methods can do the same thing.
- To normalize all casts, however, there is the `To[T]` class, that can be super-imposed.
- The `To[T]` class has a single method, `to`, that consumes the object and returns a `T`.

```s++
cls To[T] {}
sup[T] To[T] {
    fn to(self) -> T { ... }
}

sup To[Str] for Num {
    fn to(self) -> Str { ... }
}

sup To[Bool] for Num {
    fn to(self) -> Bool { ... }
}

fn main() -> Void {
    let x = 5.to[Str]()   # x is a Str object
    let y = 5.to[Bool]()  # y is a Bool object
}
```
- Because the generic parameter `T` isn't inferrable, it must be explicitly specified.
- This makes it easy to determine what type the object is being cast to.
- Because types cannot be specified unless the object is uninitialized, this is the only way to cast.
