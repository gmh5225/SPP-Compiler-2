# Iteration
- Read the [functions](functions.md) & [async](async.md) to understand `gn` functions.
- Main issue: 2nd-class references mean that borrows cannot be returned from functions.
- However, borrows can be _yielded_ from functions, because control must be passed back, invalidating the borrow.
- This means that iteration can be done with a generator function.

#### Example iteration methods for Vec[T]
```s++
sup[T] Iter for Vec[T] {
    gn iter_ref(self: &Self) -> Gen[T] {
        let mut i = 0
        do i < self.length {
            let at_index = self.data.take(i)
            yield &at_index
            self.data.put(i, at_index)
            i += 1
        }
        ret
    }
    
    gn iter_mut(self: &mut Self) -> Gen[T] {
        let mut i = 0
        do i < self.length {
            let at_index = self.data.take(i)
            yield &mut at_index
            self.data.put(i, at_index)
            i += 1
        }
        ret
    }
    
    gn iter_one(self: Self) -> Gen[T] {
        let mut i = 0
        do i < self.length {
            let at_index = self.data.take(i)
            yield at_index
            i += 1
        }
        ret
    }
}
```
- All 3 methods are marked `gn`, meaning that the `Gen[T]` object is returned immediately.
- Every time the generator is resumed, the currently yielded borrow is invalidated and control passed back to the `iter_...` function.
- Each `Gen[T].next()` produces the next borrow.