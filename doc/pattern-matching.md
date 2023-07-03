## Pattern Matching
### Iterable sequence matching
```s++
let result = match ...command {
    "add", x, y => {x + y;}
    "sub", x, y => {x - y;}
    "mul", x, y => {x * y;}
    "div", x, y => {x / y;}
}.to_string();

# the std::Map<K, V>::iter() returns list of paris -> unpack
let result = match data {
    [("text": text, "value": value)] => {...}
    _ => {"Invalid data";}
}
```

### Iterable matching with variable grouping
```s++
let result = match command {
    ["add", ...args] => {std::ops::Add::__add__(...args)...;}
    ["sub", ...args] => {std::ops::Sub::__sub__(...args)...;}
    ["mul", ...args] => {std::ops::Mul::__mul__(...args)...;}
    ["div", ...args] => {std::ops::Div::__div__(...args)...;}
}.to_string();
```

### Wildcard case
```s++
let result = match command {
    ["c1", ...rest] => {...}
    ["c2", ...rest] => {...}
    ["c3", ...rest] => {...}
    _ => {"Invalid command".to_string();}
};
```

### Or pattern composition
```s++
let result = match command {
    ["add", x, y] | ["sub", x, y] => {"Additive";}
    ["mul", x, y] | ["div", x, y] => {"Multiplicative";}
    _ => {"Invalid operation";}
};
```
- The binding must be the same in each case (same name and type required)

### Subpattern matching
```s++
let result = match command {
    ["go", ("north" | "south" | "east" | "west")] => {...}
    ["go", direction] => {"Invalid direction";}
```

### Subpattern matching with variable binding
```s++
let result = match command {
    ["go", ("north" | "south" | "east" | "west") as direction] => {...}
    ["go", direction] => {"Invalid direction";}
```

### Value guards
```s++
let result = match command {
    ["go", direction] if ["north", "south", "east", "west"].contains(direction) => {...}
    ["go", direction] => {"Invalid direction";}
    _ => {"Invalid command";}
};
```

### Attribute matching
```s++
let result = match point {
    Point {x: 100, y, z} if z < 0 {...}
    Point {x, y, _} if z < 0 {...}
    _ => {...}
};
```

### Enum matching
```s++
let result = match direction {
    Direction::North => {...}
    Direction::South => {...}
    Direction::East => {...}
    Direction::West => {...}
};
```
- Default case is not required if the enum cases are exhaustive


### Range based matching
```s++
let result = match number {
    ..0 => {...}
    00..10 => {...}
    10..20 => {...}
    20..30 => {...}
    _ => {...}
};
```
}
```

