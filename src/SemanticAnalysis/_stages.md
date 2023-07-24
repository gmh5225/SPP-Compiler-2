1. Symbol generation: create the table of symbols for each scope.
   - `let` declarations create a new symbol in the current scope.
   - `fun` declarations create a new symbol in the current scope.
   - `cls` declarations create a new symbol in the current scope.

2. Type inference: using all the known symbols, infer the type of each expression.
3. Type checking: check that the type of each expression matches the expected type.
4. Mutability checking: check that the mutability of each expression matches the expected mutability.
5. Visibility checking: check that each symbol is visible from its use.
6. Memory checking: check law of exclusivity and that each symbol is initialized before use.
7. Code generation: generate the LLVM IR code.
