# Compiler Roadmap
### Language features for syntactic analysis
#### Function & argument related
- [ ] Overload selection with optional & variadic parameters (+ most constraining chosen first).
- [ ] Named (type) parameters and arguments binding to the correct ones.
- [ ] Generic type substitution when checking return type is matched by final statement.
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

#### Statements
- [ ] Non-final return statements must return the correct type.

#### Operators
- [ ] Re-introduce `<<`, `>>` bit shifts
- [ ] Look at bit-rotate operators `<<<`, `>>>`
- [ ] Any new operators need to be integrated into the precedence table.

#### Actual compiler Python code
- [ ] Heavily extend errors to include their source declaration ie `let` statement etc.
- [ ] Check that `copy.deepcopy` is called on all types that require it (modifying local AST variable).
- [ ] Redo all error types regarding `SystemExit` etc.
- [ ] Work out all error codes (will have to finish syntactic analysis first).

#### Parser
- [ ] Statements that require a `\n` at the end shouldn't if it's a one-line statement.
- [ ] Sometimes multiple newlines in spp code causes error?
- [ ] Remove requirement of newlines completely?
- [ ] Semantic analysis for `self` in postfix expression.
- [ ] Change the type rules to allow `Self` anywhere in upper-case type identifier.
  - [ ] Use semantic analysis to ensure correct positioning 

#### Type system
- [ ] All things `nested types / typedefs`
- [ ] Maybe split `Num` to `U8`, `U16`, `U32`, `U64`, `I8`, `I16`, `I32`, `I64`, `F32`, `F64`?
  - [ ] Then add `Num` as a `BigNum` type that can be used for all arithmetic.
  - [ ] Then add `Dec` like Python's `decimal.Decimal` class?

#### Other
- [ ] All things `yield` / coroutines
- [ ] Fold expressions (requires variadic implementation).
- [ ] Disallow duplicate inheritance super-impositions onto a class (recursive sup-scope analysis).
- [ ] Postfix member access doesn't work with function calls in the middle ie `a.func().b` fails on `func()`.
- [ ] Check tuple indexing ie `let x = tup.0` marks the object as partially moved.

#### Imports
- [ ] Relative imports using the `sup` keyword.
- [ ] Fix
###### Fix imports
- By default, "import" all spp files with a `mod` declaration into the `main.spp` file, forcing use of FQN.
- Using a `use` statement allows "namespace reduction" ie `use std.num.Num` => `Num` in scope.
  - Perform reduction by adding the child scope (scope of the imported type) to the current scope.
- Allow the `ImportStatement` parsing rule to be used as a regular statement, like the typedef.
  - Allows reductions to be only applied to the current scope, not the entire file.


#### Ideas that probably won't happen
- [ ] Keyword renaming: `while` -> `do`, `else` -> `or` (matches 2 letter nature of `if`).