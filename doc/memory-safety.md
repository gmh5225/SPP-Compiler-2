# Memory safety
- 2nd-class references make lifetime analysis trivial.
- Law of exclusivity is enforced by the compiler.
- No need for a garbage collector.

## 2nd-class references
- References can only be created at function call sites.
- References cannot be stored in objects.
- References cannot be returned from functions.
- This means they can be stored on the _stack_, for better performance.

## Lifetime analysis
- Due to 2nd-class references, lifetime analysis is trivial.
- The lifetime of a reference is the lifetime of the function call.
- This is always less than the lifetime of the object being referenced.

## Law of exclusivity
- There can be `n` immutable references to an object.
- There can be `1` mutable reference to an object.
- Mutable and immutable references cannot exist at the same time.

## Mitigated errors:
| Error                     | Mitigation                                                                                                                                                                |
|---------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Nullptr deference         | There are no concepts of pointers in S++. Reference's are non-nullable, as they are always takes from an owned object. Therefore, nullptr de-referencing can never happen |
| Dangling pointers         | References are 2nd-class, meaning they are taken at function call sites. This means that the reference cannot outlive the object it is referencing.                       |
| Buffer overflow           | All array access operations are bounds checked.                                                                                                                           |
| Buffer underflow          | This would require using `Arr.set` with a negative index. This is checked in the method.                                                                                  |
| Memory leaks              | Unique ownership means that at the end of the scope, the object is immediately freed.                                                                                     |
| Double-free               | Object's cannot manually be freed. They are freed at the end of the scope.                                                                                                |
| Use-after-free            | The compiler checks that an object is owned (ie not uninitialized) before every operation involving it.                                                                   |
| Stack overflow            | ?                                                                                                                                                                         |
| Heap fragmentation        | ?                                                                                                                                                                         |
| Uninitialized variables   | A variable whose contents in "moved" to another variable is modelled as uninitialized, meaning the same techniques as preventing `use-after-free` are applied             |
| Pointer Arithmetic        | Not possible, as there are no concept of pointers in S++                                                                                                                  |
| Memory Corruption         | A combination of techniques including: bounds checking, prebuilt-containers, no c-arrays etc protect this. **TODO**                                                       |
| Type-Conversions          | All type conversions are explicit, and require some method to be called on the object.                                                                                    |
| Alignment Errors          | ?                                                                                                                                                                         |
| Race-conditions           | Unique ownership + Shared ownership wrapper + Mutexes force all concurrency to be safe.                                                                                   |
| Deadlocks                 | Mutexes are not re-entrant, and are not allowed to be locked twice. (?) **TODO**                                                                                          |
| Static & Global variables | Neither are allowed in S++.                                                                                                                                               |