# Iteration, Indexing & Slicing
## Iteration
- The `std::ops::Iter` classes are used or iterate over a collection (and therefore index & slice).
- The class is compiler-known, to that non-owning views are achievable.
- The `for` loop's identifier's reference is dictated by the type of object being iterated over.
- Any `.iter()` method, or variant, will return the `std::Iter<T>` class (or a subclass).
- The `std::Iter<T>` is compiler-known, and the `for` loop is called with the correct reference type.

#### Immutable reference iteration
- `for x in [0, 1, 2, 3].iter() {}`
- `x` is a reference to the value in the array, so `x` is of type `&std::Num`.

#### Mutable reference iteration
- `for x in [0, 1, 2, 3].iter_mut() {}`
- `x` is a mutable reference to the value in the array, so `x` is of type `&mut std::Num`.

#### Self-consuming iteration
- `for x in [0, 1, 2, 3].iter_once() {}`
- `x` is the value in the array, so `x` is of type `std::Num`.

#### Notes
- The mutability of the iterator variable `x` can be set to be mutable by using `mut x` 
