# Reflection
- Reflection is supported by leveraging the AST library, to allow AST inspection at runtime.
- Getting and setting attributes is supported.
- Method invocation is supported.

### Getting, Setting, Has and Removing Attributes
- Use the reflection library's `get_attr`, `set_attr`, `has_attr` functions.
- No `del_attr` function is provided, as it would require changing the memory layout of the object.

#### Example: get_attr:
```s++
let obj = Foo();
let attr = "a";
let val = std::rx::get_attr(obj, attr);
```

#### Example: set_attr:
```s++
let obj = Foo();
let attr = "a";
let val = 2;
std::rx::set_attr(obj, attr, val);
```

#### Example: has_attr:
```s++
let obj = Foo();
let attr = "a";
let val = std::rx::has_attr(obj, attr);
```

### Invoking Methods
- Use the reflection library's `call` function.
- The `call` function takes the object, the method name, and the arguments to pass to the method.
- The `call` function returns the result of the method invocation.
- The `call` function supports generic methods, and the generic parameters must be specified.
- The `call` function supports methods with a `self` parameter, and the object must be passed as the first argument.

#### Example: call:
```s++
let obj = Foo();
let method = "foo";
let args = (,);
let result = std::rx::call(obj, method, ...args);
```
