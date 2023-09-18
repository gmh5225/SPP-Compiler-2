# Why use S++


## Issues solved
#### Optional block delimiters
- Blocks must be delimited by `{` and `}`.
- This is to avoid the dangling `else` problem.

#### Bitwise operator precedence
- See the [**precedence table**](operators.md#precedence).
- Bitwise operators on the same side of `=` as the mathematical operators.
- Breaks away from typical `C/C++/Java` etc precedence.

#### Negative modulo
- The `%` operator is the remainder operator, not the modulo operator.
- This holds that `0 <= a % b <= b.abs()`
- Separate `std.ops.Rem` and `std.math.Mod` classes that can be super-imposed separately.
- The `%` operator will always call `std.ops.Rem`

#### C-style for loops
- There are no for loops at all.
- Use the [**Streams API**](streaming.md) instead (internal iteration).

#### C-style switch statements
- No default fallthrough for if-pattern statements.
- No `switch/match` -- see the [**if-pattern statement**](blocks-conditional.md).

#### Type-first
- All cases where types are _required_ are places _after_ the variable name: `x: Num`.

| Lang  | Example                                                                                                                                                                             |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `C++` | `extern const volatile std::unordered_map<unsigned long long int, std::unordered_map<const long double * const, const std::vector<std::basic_string<char>>::const_iterator>> foo;`  |
| `S++` | `foo: Vol[Map[U64, Map[F64, Vec[Str]]::Iter]]`                                                                                                                                      |


#### Weak typing
- No implicit conversions _between types_.
- See the [**type system**](type-system.md#strong-type-system).

#### Increment & Decrement
- No `++` or `--` operators.
- Use `+= 1` and `-= 1` instead.
- Forces 1 way to do things, and reduces syntactic noise.

#### Unary operators
- No unary operators at all.
- Use the postfix function calls ie `some_func().not()`
- Clearer to see from a long condition expression what is happening.

#### Multiple returns
- Return a tuple + automatic destructure.
- _Can_ use in-out parameters as mutable references as long as borrow rules are followed.
- Prefer returning tuples -- a lot cleaner.

#### Errors
- No exceptions.
- Use the `Ret[T, E]` type instead.
- Forces the programmer to handle errors, and makes it clear where they can occur.

#### Nulls
- No nulls.
- Use the `Opt[T]` type instead.
- Forces the programmer to handle nulls.

#### Assignment as an expression
- Assignment returns `Void`.
- Assignment cannot be used in conditions

#### Initialization
- C++ has several ways to initialize objects
- S++ has one way to initialize objects: struct initialization.
- Static methods can wrap struct initialization to provide more complex initialization.

#### Memory safety
- 2nd class references + borrow rules.
- Impossible to have memory leaks, dangling pointers, use-after-free etc.
- No pointers => no pointer arithmetic.
- Bounds checking on arrays to prevent buffer overflows.
- See the [**memory safety**](memory-safety.md) section.

#### Name-hiding
- Inner scopes can use an outer scope's variable name.
- Inner scopes can re-declare a variable name.
- On returning to the outer scope, the variable will be restored if it was redeclared in the inner scope.
- See the [**shadowing**](blocks.md#shadowing) section.

#### Mutability
- All variables are immutable by default.
- Use the `mut` keyword to make a variable mutable.
- Fields' mutability determined by outer scope's mutability.

#### Context free grammar
- The grammar is context free.
- This means that the parser can be written in a single pass.
- See the [**parser.py**](../src/SyntacticAnalysis/Parser.py) file.

#### Functions vs function pointers
- No function pointers.
- All methods, functions & closures are objects -- one from `[FnRef, FnMut, FnOne]`.
- Return type and parameter types are the generic type parameters of the function object.

#### First class tuples
- The tuple is a compiler known special object.
- It maps to the language type `std.Tup` for compatibility with types.

#### No primitives
- All types are objects.
- Simplifies the language, and makes it more consistent.
- Compiler is a lot simpler.

#### Casting
- All casts are explicit and done with a static method.
- No special cast keyword, because a static method can do the same thing.
- Force 1 way to do things, and reduces syntactic noise.

#### Top-level functions
- There are very few top-level functions.
- Almost everything is a method on an object.
- This makes the language more consistent.
- Less to remember.
