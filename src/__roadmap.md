# Compiler Roadmap
### Language features for syntactic analysis
#### Function & argument related
- [ ] Overload selection with optional & variadic parameters (+ most constraining chosen first).
- [ ] Named (type) parameters and arguments binding to the correct ones.
- [ ] Generic type substitution when checking return type is matched by final statement.
- [ ] All things type-constraints.

#### Memory
- [ ] Reassigning to moves _attributes_ makes the object no longer partially moved.

#### Lambdas/closures related
- [ ] Lambdas & capturing variables (apply the same borrow/move rules as parameters).

#### Variable related
- [ ] Destructuring (especially for `if-patterns` and `let` statements).

#### Actual compiler Python code
- [ ] Heavily extend errors to include their source declaration ie `let` statement etc.
- [ ] Check that `copy.deepcopy` is called on all types that require it (modifying local AST variable).
- [ ] Currently, types ignore their namespace -- fix this + nested types => imports
- [ ] Redo all error types regarding `SystemExit` etc
- [ ] Work out all error codes (will have to finish syntactic analysis first).

#### Other
- [ ] Statements that require a `\n` at the end shouldn't if it's a one-line statement.
- [ ] Assigning to attributes doesn't work yet because type-inference of the attribute doesn't work.
- [ ] All thing `yield`
- [ ] Allow subtyping in the type-comparison algorithm.