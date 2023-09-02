# Compiler Roadmap
#### Language features for syntactic analysis
- [ ] Overload selection with optional & variadic parameters.
- [ ] Generic type substitution when checking return type is matched by final statement.
- [ ] Final statement shouldn't be compared against return-type if the return type should be `Void`.
- [ ] Partial moves for owned objects (memory analysis etc).
- [ ] Lambdas & capturing variables (apply the same borrow/move rules as parameters).
- [ ] Named (type) parameters and arguments binding to the correct ones.
- [ ] Destructuring (especially for `if-patterns` and `let` statements).
- [ ] Heavily extend errors to include their source declaration ie `let` statement etc.
- [ ] Check that `copy.deepcopy` is called on all types that require it (modifying local AST variable).