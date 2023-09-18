# Streaming
- Streaming is the S++ alternative to the `for` loop.
- Allows for "interior" iteration, ie iteration without a counter.

## Example
- C++ vs S++:
```c++
// C++
std::vector<int> vec(100)
std::iota(vec.begin(), vec.end(), 0);
for (auto i : vec) {
    if (i % 3 == 0) {
        std::cout << i << std::endl;
    }
}
```

```s++
# S++
Vec.new_range(0, 100)
    .filter((i) -> { i % 3 == 0 })
    .map(func)
    .for_each(print)
    
# shorthand for .map((i) -> { func(i) })
# shorthand for .for_each((i) -> { print(i) })
```
