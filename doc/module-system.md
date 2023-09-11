# Module system
- Every `mod` tagged `.spp` file is a module, and included in the compilation graph.
- The module name must follow the directory structure from, and including, the `src` folder.

## Absolute vs relative imports
- Absolute imports are from the `src` folder, and must include `src` at the beginning of the `use` statement.
- Relative imports use `sup` to go up a level.
- 3rd part imports are the same as absolute imports, but `src` is replaced with the module name.

## Level of namespacing
- Namespaces reflect module names which in turn reflect directory structure.
- However, the _file name_ is not included in the namespace.
- The `Num` class is in the file `std/num.spp`, and the module is `std.num`. But the `Num` class is not accessed as `std.num.Num`, it is accessed as `std.Num`

| Module name | File name     | Class name |
|-------------|---------------|------------|
| `std.num`   | `std/num.spp` | `std.Num`  |

- This choice was made to that functions that create object, ie `std.[some|none|pass|fail]` didnt become `std.residual.[some|none|pass|fail]`.

## Importing modules
- Every (public) module in the graph is imported, as usable via its fully qualified name.
- The `use ...` statement can perform namespace reduction, importing a type _directly_.
- Using `use std.num.Num` will import `Num` into the current scope, rather than having to use `std.Num`.
