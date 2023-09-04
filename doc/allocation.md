# Allocation
- Allocators can provide **safe** low-level memory management.
- Allocators are objects that super-impose the `Alloc` class.
- Allocator APIs allow memory allocation, reallocation, and deallocation.
- Some collections take an `[A: Alloc]` generic parameter.

## Allocators
- The `Alloc` class is defined as:
```s++
cls Alloc[T] {
    use Item = T

    @static fn alloc(size: Num) -> Ret[Arr[T], AllocErr] { ... }
    @static fn realloc(arr: Arr[T], size: Num) -> Ret[Arr[T], AllocErr] { ... }
    @static fn dealloc(arr: Arr[T]) -> Ret[Void, AllocErr] { ... }
    
    @static fn alloc_zero(size: Num) -> Ret[Arr[T], AllocErr] { ... }
    ...
}
```
- Allocators aren't initialized for use, rather their methods are called statically.
- Custom allocators can be defined by super-imposing the `Alloc` class.

#### Alloc.alloc
- Allocates a new array of size `size` and returns it.
- The `Ret` type is used to return either the allocated array or an error from C.

#### Alloc.realloc
- Reallocates the array `arr` to size `size` and returns it.
- Has to take ownership of the memory, extend and return it.

#### Alloc.dealloc
- Deallocates the array `arr` and returns `Ret[Void, ...]`.
- Has to take ownership of the memory, free it and return.