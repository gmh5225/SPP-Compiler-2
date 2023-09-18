# S++ Compiler

S++ is a systems programming language that aims to be a safe and simple language to use. It can be used for all levels
of programming, from low level systems programming to high level application programming. It has a number of memory
safety features ensuring that a program runs without errors, and is easy to reason about. All these checks are performed
at compile time, so there is no overhead at runtime.

----

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
- The `SPP` repo is used for docs -- the BNF file is not upto date.
