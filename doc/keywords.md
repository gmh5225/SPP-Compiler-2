# Keywords

#### mod
- The `mod` keyword declared a module.
- It must be present at the top of the file for it to be included in the compilation.
- The module name must follow the directory structure from, and including, the `src` folder.
- A module identifier might look like: `mod src.foo.bar`
- Modules can be _annotated_, with specifiers like `@protected` etc.

#### use
- The `use` keyword imports a module, or declares a type-alias.
- Importing from a module allows imported types to enter the global namespace.

#### enum
- TODO

#### fn
- Declare a "subroutine" function.
- A subroutine identifier might look like: `fn foo(a: Num) -> Num {...}`

#### gn
- Declare a "coroutine" function.
- A coroutine identifier might look like: `gn foo(a: Num) -> Gen[Num] {...}`
- A coroutine is a function that can be paused and resumed.

#### mut
- Declare a `let` statement as mutable, or used when taking a mutable reference.
- To declare a mutable variable, use `let mut x = 2`.
- To create a mutable reference, use `foo(&mut x)`.
- To declare a mutable parameter, use `fn foo(self: Self, mut x: Num) {...}`.
- The parameter's type can be a mutable reference too: `fn foo(self: Self, mut x: &mut Num) {...}`.
- Tuples require `mut` _per variable_ being assigned to: `let mut x, y = (1, 2)`.

#### let
- Declare a variable, or a tuple of variables.
- A variable identifier might look like: `let x = 2`.
- See [**mut**](#mut) for more information on declaring _mutable_ variables.
- A tuple identifier might look like: `let x, y = (1, 2)`.

#### if
- Declare an if statement, or a "conditional jump".

#### else
- Declare an `else` branch for an `if` statement.
- Declare a default object to be moved from in a struct-initializer.
- Declare a residual action for `let` statements.

#### while
- Declare a while loop, or a "conditional loop".
- A while loop identifier might look like: `while x < 10 {...}`.

#### ret
- Return a value from a function.
- A return statement might look like: `ret 2`.

#### yield
- Yield a value out of a coroutine.
- Can assign from the `yield` statement to receive a value being sent back to the coroutine.
- A yield statement might look like: `let x = yield 2`.

#### cls
- Declare a class.
- A class identifier might look like: `cls Foo {...}`.
- Only class attributes can be included in the class body.
- Separation of state and behaviour.

#### where
- Declare a where clause.
- Constrain generic types to a list of other types that the generic type must super-impose.
- A where clause might look like: `where [T, U: Str + Copy + Default]`, etc.

#### true / false
- Declare a boolean true or false.
- A boolean literal might look like: `true`.
- Will refer to singleton instantiations of the `Bool` class.
- The `Bool` object type has some special compiler behaviour.

#### as
- Alias imported types, ie `use src.foo.{bar as FooBar, baz as FooBaz}`.
- Alias an expression for a `with` clause.
- **Not** used to type casting - declare static method or `sup` common converter classes.

#### sup
- Super-impose methods or another class onto a class.
- Super-impose methods onto a class: `sup Foo {...}`.
- Super-impose another class onto a class: `sup Bar for Foo {...}`.
- Can override methods when super-imposing a class onto a class.

#### with
- Declare a context block, the same way as a `with` statement in Python.
- A context block might look like: `with foo.bar() as bar {...}`.
- The created type must super-impose the `std.ops.Ctx` class.
- The `std.ops.Ctx` class has some special compiler behaviour.

#### for (TODO - will probably change)
- Currently used for super-imposes a class onto another class.
- Currently used as `sup Copy for Num` etc.
- Will change to a different more applicable name in the future.

#### Self
- Refer to the current type of the enclosing class.
- Can be used in generics referring to the class itself.
