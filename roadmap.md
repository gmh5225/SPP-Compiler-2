# Compiler Roadmap
### Language features for syntactic analysis
#### Function & argument related
- [ ] Overload selection with variadic parameters
- [ ] Named (type) parameters and arguments binding to the correct ones.
- [ ] All things type-constraints.

#### Memory
- [ ] Reassigning to moved _attributes_ makes the object no longer partially moved.
- [ ] Can still assign to attributes of a moved object -- should not be allowed.

#### Lambdas/closures related
- [ ] Type analysis (infer return type, what about param types?).
- [ ] Lambdas & capturing variables (apply the same borrow/move rules as parameters).

#### Variable related
- [ ] Destructuring (especially for `if-patterns` and `let` statements).
- [ ] Struct initialization: require stateful, non-default sub-classes in `sup=`
- [ ] Would be nice to have assignment mutability check _before_ type check.
- [ ] Most things concerning tuples need fixing -- `(...) vs Tup[...]`.

#### Types
- [ ] Non-final return statements must return the correct type.
- [ ] Variadics & variadic generics.

#### Operators
- [ ] Operator chaining: allow, like Python, for ` a < b < c` to be `a < b && b < c`.
- [ ] Allow `a == b == b` to become `a == b && b == c`.

#### Actual compiler Python code
- [ ] Heavily extend errors to include their source declaration ie `let` statement etc.
- [ ] Redo all error types regarding `SystemExit` etc.
- [ ] Work out all error codes (will have to finish syntactic analysis first).
- [ ] Change the error handler to receive the extra string as a parameter for multiline support (not just `... + "..."` )
- [ ] Check that `copy.deepcopy` is called on all types that require it (modifying local AST variable).
- [ ] Error messages from imported files don't use the correct token stream after the symbol generation stage.

#### Type system
- [ ] All things `nested types / typedefs`
- [ ] Maybe split `Num` to `U8`, `U16`, `U32`, `U64`, `I8`, `I16`, `I32`, `I64`, `F32`, `F64`?
  - [ ] Then add `Num` as a `BigNum` type that can be used for all arithmetic.
  - [ ] Then add `Dec` like Python's `decimal.Decimal` class?
- [ ] Change the typedef to allow "type reductions" from namespaced types too.
- [ ] Allow typedefs as top-level module members too.
- [ ] Currenly FQN is always needed, even in file of definition - should just be able to use class name in same file.

#### Statements
- [ ] Currently no borrow checking on returning or yielding from a function.
- [ ] Change `for` to `on` for super-imposition based inheritance.

#### Other
- [ ] All things `yield` / coroutines
- [ ] Fold expressions (requires variadic implementation).
- [ ] Disallow duplicate inheritance super-impositions onto a class (recursive sup-scope analysis).
- [ ] Postfix member access doesn't work with function calls in the middle ie `a.func().b` fails on `func()`.
- [ ] Check tuple indexing ie `let x = tup.0` marks the object as partially moved.
- [ ] Error needs to be thrown for unreachable code after a `return` statement.
- [ ] Make some classes non-instantiable (operators etc)

#### Imports
- [ ] Relative imports using the `sup` keyword.

#### Ideas that probably won't happen
- [ ] Keyword renaming: `while` -> `do`, `else` -> `or` (matches 2 letter nature of `if`).