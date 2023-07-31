# S++ Compiler

#### Progress
- [x] Lexer
- [x] Parser
- [ ] Semantic Analyzer -- WIP
- [ ] Code Generator
- [ ] Standard Library


## Notes
- Compiler written in Python for now -- easy to model, uses LLVM so generated code is same speed as if the compiler were written in C++/Rust.
- Once the compiler in Python is complete, I will either rewrite it in Rust, or do the STL and self-host the compiler.
- Semantic Analyzer is horrible at the moment, written awfully, duplicated code etc -- will rewrite once all the features and checks are in place.
- Importing currently imports into global namespace like Python, but in the end it will import as its qualified name.