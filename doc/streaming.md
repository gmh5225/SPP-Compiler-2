# Streaming
- Streaming is the S++ alternative to the `for` loop.
- Allows for "interior" iteration, ie iteration without a counter.

## Example
- Rust vs S++:
```rust
RUST
for i in 0..100 {
    if i % 2 == 0 {
        println!("{}", func(i));
    }
}
```

```s++
S++
Vec.new_range(0, 100)
    .filter((i) -> { i % 3 == 0 })
    .map(func)       # shorthand for .map((i) -> { func(i) })
    .for_each(print) # shorthand for .for_each((i) -> { print(i) })
```
