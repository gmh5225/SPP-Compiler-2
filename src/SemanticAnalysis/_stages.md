#### DONE
1. Symbol generation: create the table of symbols for each scope.
   - `let` declarations create a new symbol in the current scope.
   - `fun` declarations create a new symbol in the current scope.
   - `cls` declarations create a new symbol in the current scope.
2. Symbol checking: check that each symbol exists.

<BR>

#### WIP
1. Type inference: using all the known symbols, infer the type of each expression.

<BR>

#### TODO
1. Type checking: check that the type of each expression matches the expected type.
2. Mutability checking: check that the mutability of each expression matches the expected mutability.
3. Visibility checking: check that each symbol is visible from its use.
4. Memory checking: check law of exclusivity and that each symbol is initialized before use.
5. Code generation: generate the LLVM IR code.
