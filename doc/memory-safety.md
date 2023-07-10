# Memory safety
- Memory safety is a core feature of the language.
- Compile time memory checks are ran to prevent any runtime memory issues.


## Ownership
- Every object is uniquely owned
- Borrows to objects can only occur at function call sites
- Allows for a simple lifetime & borrow-checking model

### Borrows
- Cannot be returned
- Cannot be stored in a data structure
- Can only be created at function call sites
  - `let a = b` is a move
  - `let a = &b;` is an immutable borrow
  - `let a = &mut b;` is a mutable borrow
- Can only be received by a function parameter
  - `fn foo(a: A) -> Void {...}` receives an owned object
  - `fn foo(a: &A) -> Void {...}` receives an immutable borrow
  - `fn foo(a: &mut A) -> Void {...}` receives a mutable borrow

### Borrow checker rules to enforce safety
- The value being borrowed must be owned, not uninitialized or moved
- Only 1 mutable borrow can exist at a time
- Mutable and immutable borrows cannot exist at the same time


## Common issues mitigated
### Null pointer dereference
- No concept of "pointers" -- abstracted away into owned objects and borrows (safer concepts).
- Ownership tracking ensures that uninitialized or moved objects aren't used.
- Borrows are always valid because they are only taken at function call sites.
- Inadvertently prevents pointer arithmetic from being possible either (dangerous operation).

<BR>

### Use after free, double free & dangling borrows
- A "freed object" is moved into something else => memory enforcer recognizes this as a non-owned object.
- Cannot use a non-owned object -> ownership tracking ensures that objects are not used after they are "freed".
- References are only taken at call-sites, so it isn't possible for teh underlying object to be freed.

<BR>

### Out-of-bounds access & buffer underflow / overflow
- All low level memory access is bound checked in the `std::mem_seq<T>` class (from `std::allocator<T>`)
- Bound checks can result in errors -> return `std::result<T, std::mem_error>` type

<BR>

### Memory leaks
- Objects are uniquely owned => falls out of scope, then it is automatically freed after destructor is called.
- Memory leaks cannot occur, as the object will automatically be de-allocated upon destruction.
- Impossible to create a memory leak with borrows, as they are borrowed and never invalidated.
- Once the borrow falls out of scope, it is automatically freed, and the object is still valid.
- When the object falls out of scope, there will never be any active borrows to it.

<BR>

### Use uninitialized variables
- Variables that are uninitialized are not usable -- memory enforcer, models uninitialized variables as "non-owned".
- Until variables are assigned some value, they cannot be used.
- At construction, all class attributes must be initialized (from the struct initialization).

<BR>

### Type casting
- Requires a method on the target class to cast to the target type.
- For example, `let a = "123".to_int();` is the `std::Num` cast method.
- Some common casts are in classes to super-impose, ie `std::ToString`, which contains the method `.to_string()`.

<BR>

### Data races
- Only 1 mutable borrow can ever be active per owned object at 1 time
- Temporary ownership can be transferred with a mutable borrow.
- Any number of const borrows can be taken, because read-only objects/borrows are thread-safe.
- Cannot take a mutable and immutable borrow to the same object at the same time.
- Once the mutable borrow falls out of scope, another mutable borrow can be taken.

<BR>

### Deadlocks
TODO: explain how this is mitigated

<BR>


### Stack overflow
<s>
- There are certain optimizations that can be made to mitigate stack overflow, such as tail call optimization which
are used to reduce the strain on the stack. However, the memory enforcer also ensures that the stack is never
overflowed by tracking the size of the stack, and ensuring that it is never exceeded. The `std::allocator`
returns an `std::result` type, which can be checked at runtime to ensure that the stack is not exceeded.
- If the stack does exceed at runtime, then there will be a runtime error, because the device simply cannot allocate
any more memory. This is a fatal error, and the program will crash. However, before this happens, a number of
actions will take place to try and prevent this from happening.
- References are stored on the stack, unless they are moved into an attribute for example, to extend their lifetime,
in which case they are stored on the heap. This means that the stack is only used for local variables, and so the
stack size is only ever as large as the number of local variables in a function, allowing for the stack to rarely
overflow.
</s>

<BR>

### Heap overflow
<s>
TODO: explain how this is mitigated
</s>

<BR>

## TODO
#### Immutable Borrow - `&object`
<s>
- Immutable borrows are thread-safe, and can be used to share data across threads.
    - Immutable borrows are read-only
    - For an immutable borrow to exist, there must be no active mutable borrows => no writing can happen
- Immutable borrows can come from owned objects or immutable borrows.
    - Immutable borrows to an immutable borrow are allowed, and borrow from the owned object.
    - So the owned object's borrow count increments; borrows don't have their own borrow count.
- Immutable borrows invalidate previously declared mutable borrows to the owned object.
    - Cannot use the mutable reference to mutate the object while an immutable borrow exists.
    - Creates the thread-safe aspect of having N immutable borrows at any 1 time.
- Immutable borrows do not invalidate previously declared immutable borrows to the owned object.
    - Allows for N active immutable borrows to an object or its attributes at any 1 time.
    - Immutable borrows are read-only, so they do not interfere with each other.
- Immutable borrows cannot be used to mutate, only read, the owned object or its attributes.
    - Read-only access to the owned object or its attributes is allowed.
    - Prevents a number of memory-related errors from ever occurring at runtime.
- Immutable borrows to an immutable borrow are allowed, and borrow from the owned object.
    - Allow for a borrow to be duplicated, whilst leaving the original borrow valid.
    - Increments the owned object's borrow count.
- Immutable borrows cannot be takes from a partially moved object.
    - Prevents a number of memory-related errors from ever occurring at runtime.
</s>

<BR>

#### Mutable Borrow - `&mut object`
<s>
- Mutable borrows are not thread-safe, and cannot be used to share data across threads.
- Mutable borrows can only come from owned objects.
- Mutable borrows invalidate all previously declared borrows to the owned object.
- Mutable borrows can be used to mutate or read from the owned object or its attributes.
- Mutable borrows to an immutable borrow are not allowed.
- Mutable borrows to a mutable borrow are not allowed.
- Mutable borrows cannot be takes from a partially moved object.
</s>

#### For loop - ITERATION IS TODO
<s>
- `for i in a` consumes `a` and iterates over it.
    - `i` is an owned value => $\textcolor{green}{\textsf{allowed}}$
    - no point immutably borrowing `i` when it's container is moved => $\textcolor{red}{\textsf{not allowed}}$
    - no point mutably borrowing `i` when it's container is moved => $\textcolor{red}{\textsf{not allowed}}$
- `for i in &a` borrows `a` and iterates over it.
    - `i` is an immutable reference to the current element => $\textcolor{green}{\textsf{allowed}}$
    - `i` cannot be an owned object (cannot move from a borrowed context) => $\textcolor{red}{\textsf{not allowed}}$
    - `i` cannot be a mutable reference (cannot mutate an immutable container => `for mut i in &a` => $\textcolor{red}{\textsf{not allowed}}$)
- `for i in &mut a` mutably borrows `a` and iterates over it.
    - `i` is an immutable reference to the current element => $\textcolor{green}{\textsf{allowed}}$
    - `i` cannot be an owned object (cannot move from a borrowed context) => $\textcolor{red}{\textsf{not allowed}}$
- `for mut i in &mut a` mutably borrows `a` and iterates over it.
    - `i` is a mutable reference to the current element => $\textcolor{green}{\textsf{allowed}}$
    - `i` cannot be an owned object (cannot move from a borrowed context) => $\textcolor{red}{\textsf{not allowed}}$
</s>
