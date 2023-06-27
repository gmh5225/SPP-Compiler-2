"""
Semantic analysis module
- Type checking
    - Type inference in "let" statements => only place where type-inference is used
    - Check argument types match function parameter types
- Local variable declaration and scope
    - Check variable exists in the current scope
- Function declaration and analysis
    - Check function exists in the current scope
    - Check number of arguments match function parameter count
- Attribute declaration and analysis
- Control-flow statements
    - Check conditions are all boolean expression types
    - Check Continue/Break tags exist
- Const variable declaration / assignment
    - Check const variables are only assigned to once
- Operators
    - Check operator classes are implemented
- Type generics
    - Check constraints to decide which type to use
- Memory analysis
"""