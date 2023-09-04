# Compiler Roadmap
### Language features for syntactic analysis
#### Function & argument related
- [ ] Overload selection with optional & variadic parameters.
- [ ] Named (type) parameters and arguments binding to the correct ones.
- [ ] Generic type substitution when checking return type is matched by final statement.

#### Lambdas/closures related
- [ ] Lambdas & capturing variables (apply the same borrow/move rules as parameters).

#### Variable related
- [ ] Destructuring (especially for `if-patterns` and `let` statements).

#### Actual compiler Python code
- [ ] Heavily extend errors to include their source declaration ie `let` statement etc.
- [ ] Check that `copy.deepcopy` is called on all types that require it (modifying local AST variable).
- [ ] Currently, types ignore their namespace -- fix this + nested types

#### Other
- [ ] Calling functions in `sup` scopes isn't working yet.
- [ ] Fix the `Self` type for analysis (throws errors at the moment).
- [ ] Statements that require a `\n` at the end shouldn't if it's a one-line statement.
- [ ] Assigning to attributes doesn't work yet because type-inference of the attribute doesn't work.