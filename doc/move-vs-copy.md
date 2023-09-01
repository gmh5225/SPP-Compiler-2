# Move vs Copy
- By default, all assignment and argument passing is done by "moving".
- Moving is destructive and changes the ownership of the object.
- To copy an object, super-impose the `Copy` trait onto the type.

## Copying
- Super-impose the `Copy` trait onto a type to allow it to be copied.
- This causes _all_ assignment and argument passing to be done by copying.
- Makes it a lot easier than having to write `let x = y.clone()` everywhere for numbers etc.
