# Allocation
- Allocators can provide **safe** low-level memory management.
- Allocators are objects that implement the `Alloc` class.
- Allocator APIs allow memory allocation, reallocation, and deallocation.
- Collections take a `A: Alloc` generic parameter.

## Allocators
- The `Alloc` class is defined as:
```s++
cls Alloc[T] {
    use Item = T

    @static @virtual
    fn alloc(size: Num) -> Ret[Arr[T], AllocErr] { ... }
    
    @static @virtual
    fn realloc(arr: Arr[T], size: Num) -> Ret[Arr[T], AllocErr] { ... }
    
    @static @virtual
    fn dealloc(arr: Arr[T]) -> Ret[Void, AllocErr] { ... }
}
```
- Allocators aren't initialized for use, rather their methods are called statically.
- Custom allocators can be defined by super-imposing the `Alloc` class.