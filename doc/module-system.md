# Module system
- Every `mod` tagged `.spp` file is a module, and included in the compilation graph.
- The module name must follow the directory structure from, and including, the `src` folder.

## Absolute vs relative imports
- Absolute imports are from the `src` folder, and must include `src` at the beginning of the `use` statement.
- Relative imports use `sup` to go up a level.
- 3rd part imports are the same as absolute imports, but `src` is replaced with the module name.