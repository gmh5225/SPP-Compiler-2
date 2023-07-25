1. Symbol generation: create the table of symbols for each scope.
   - `let` declarations create a new symbol in the current scope.
   - `fun` declarations create a new symbol in the current scope.
   - `cls` declarations create a new symbol in the current scope.
2. Symbol checking: check that each symbol exists.
3. Type inference: using all the known symbols, infer the type of each expression.
4. Type checking: check that the type of each expression matches the expected type.
5. Mutability checking: check that the mutability of each expression matches the expected mutability.
6. Visibility checking: check that each symbol is visible from its use.
7. Memory checking: check law of exclusivity and that each symbol is initialized before use.
8. Code generation: generate the LLVM IR code.
