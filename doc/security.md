# Security
## Stack security
#### Stack canaries / cookies / guards
- Each stack frame has a canary value that is checked before the function returns.
- Each canary value is unique to the function, and randomly generated.
- Check the canary value before returning.

#### Shadow stacks
- Maintain a shadow stack that is used to store return addresses.
- When a function returns, the return address is checked against the shadow stack.
- Check return address before returning.

#### Stack isolation
- Thread-local stacks are used to isolate threads from each other.
- Each thread has its own stack, and cannot access the stack of another thread.
- Check the thread ID before accessing the stack.

#### Stack protectors
- Check stack pointers before accessing the stack.
- TODO

## Heap security
- Heap canaries
- Heap isolation
- Heap hardening
- Non-Executable Heap

## Flow control
- Control flow integrity
- Control flow enforcement technology
- Control flow guard

## Binary hardening
- Address space layout randomization
- Position independent executable
- Data execution prevention
- Executable space protection

## Code security
- Code signing
- Privilege separation

## Hardware interaction
#### NX bit

## C code
