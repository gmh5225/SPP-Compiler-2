# Functions
## Overview of functions
- Functions can have an access modifier
- Functions can have a calling convention - `async` or nothing
- Functions can have [decorators](), that wrap the function in extra behaviour
- Functions can have [generic parameters & constraints]()
- Functions can have [parameters]()
- Functions have a return type
- Functions can have a [where block]()
- Functions can have a [value guard]()
- Functions have a body

### Access modifier
#### Free function
- `pub`: exported out the module, any module can import it
- `prot`: exported out the module, only sibling and child modules can import it
- `priv`: not exported out the module, only the module it is defined in can use it

#### Class method
- `pub`: exported out the class, any class' methods and free functions can use it
- `prot`: only the class it is defined in can use it, and any sub-classes can use it
- `priv`: only the class it is defined in can use it

### Calling convention
- Currently either nothing is specified, or `async`
- Functions marked `async` must return a `std::Promise<T>` type

### Generic parameters & constraints
- Functions can have generic parameters, defined after the function name
- Generic types must not shadow enclosing an enclosing class's generic type names
- Generic types can have constraints, defined after the generic type name, or in a `where` block
- Optional and variadic generic types can be defined

### Decorators
- See [decorating a method]()

### Parameters
#### Required parameters
- Parameters are listed with their name and type
- These are parameters that must be given when calling the function
- Parameters can access other parameters defined before them

#### Optional parameters
- Parameters can be optional, and have a default value (type is still required)
- Optional parameters must be defined after all required parameters
- Optional parameters can be accessed by name, and can be given in any order

#### Variadic parameters
- There can be a single variadic parameter, which must be the last parameter
- It can either have a variadic type (all types can be different, or a single type that they all must be)
- `<T>(...args: std::Number)` -> `args` is a variadic parameter of type `std::Number` ie n `std::Number` parameters
- `<T>(...args: T)` -> `args` is a variadic parameter of type `T` ie n `T` parameters
- `<...Ts>(...args: Ts)` -> `args` is a variadic parameter of type `Ts` ie n parameters of different types
- Effectively the same as Python's `*args`, just replace `*` with `...`

#### Parameter passing modes
- Parameters can be passed by value, reference, or mutable reference
- Passing by value is the default (destructive move)
- Passing by reference is specified with `&`
- Passing by mutable reference is specified with `&mut`

### Return type
- Functions must have a return type
- Returning nothing must return `std::Void`

### Where block
- Additional constraints to generic parameters can be specified in a where clause
- Compile time function selection is based on the where clause & other constraints
- Where clause is optional, and follows the `return` type
- Where clause is specified in brackets
- See [Where block type constraints]() for more information

#### Example:
```s++
fn foo<T, U>(a: T, b: U) -> std::Num where [T: std::Num, U: std::Num] {}
```

### Value guard
- A value guard are optional, and follow the where clause
- A value guard allows for runtime selection based on the value of parameters
- A value guard is specified as a simplified if-statement
- If a value guard is used, there must be an unguarded equivalent function
- All functions with the same signature and different value guards must return the same type

#### Example:
```s++
fn foo<T, U>(a: T, b: U) -> std::Num if a > b {}
```

## Function types
- 3 function types in the STL - `std::FunRef`, `std::FunMut`, `std::FunOnce` (same as Rust)
- `std::FunRef` is the default function type -> `self` is an immutable reference: `self: &Self`
- `std::FunMut` -> `self` is a mutable reference: `self: &mut Self`
- `std::FunOnce` -> `self` is moved into the function (self-consuming)
- Free function / static method -> `self` is not defined => use `std::FnRef` as it takes no ownership of `self`

## Function overloading
### Function overload variations
- Number of parameters
- Types of parameters
- Number of generic type parameters
- Constraints on generic type parameters
- Value guard on functions

### Function overload non-variations (ie don't overload)
- Return type
- Access modifier
- Calling convention
- Decorators
- Generic type parameter names
- Parameter names

### Overload conflict resolution (compile time)
- Compile time checks for unknown function resolution
  - 2 functions with the same name and signature
  - 2 functions with the same name and different return type
  - 2 functions with same parameters, one with extra optional parameters
  - TODO

## Partial functions
- Automatic currying allows for simple partial functions
- Use the placeholder - `_` - to reserve a parameter for later
- Reserve the variadic slot parameter with a single `_` too -- the compiler knows when variadics are being filled /
  reserved

```s++
pub fun add(a: std::Number, b: std::Number, c: std::Number, d: std::Number = 0) -> std::Number:
    return a + b + c;
    
pub fun main():
    let a = add(1, 2, _);
    std::io::println(a(3)); # 6
    
    let b = add(_, 2, _, _);
    std::io::println(b(1, 3, 1)); # 7
```

## Variadic function, parameter packs
### Variadic function call
Take the following functions:
```s++
function func_variadic_helper_0<T>(...a: T) -> std::void:
    ...
    
function func_variadic_helper_1<T>(a: T) -> std::void:
    ...
    
function func_variadic_helper_2<T>(a: T, b: T) -> std::void:
    ...
```

They can be called in the following ways:
- `func_variadic_helper_0(...a);` -> calls `func_variadic_helper_0` with a single parameter pack
- `func_variadic_helper_0(a);` -> calls `func_variadic_helper_0` with a single tuple type
- `func_variadic_helper_1(a)...;` -> calls `func_variadic_helper_1` multiple times, once for each element in `a`
- `func_variadic_helper_2(a)...;` -> calls `func_variadic_helper_2` multiple times, pairs are pulled out the tuple
  (with overlap)

## Decorators
### Defining a decorator for a function
- Changes `my_method` to `decorator1(&my_method, 123)`
- Add functionality before and after the function is called
```s++
pub fun decorator1<F: std::FunRef>(func: &F, a: std::Number) -> F::RetType:
    std::io::println("decorator1 called - before function");
    let val = func();
    std::io::println("decorator1 called - after function");
    return val + a;

@decorator1(123)
pub fun my_method(a: std::Number) -> std::Number:
    return a + 1;
```

### Defining chained decorators for a function
- Changes `my_method` to `decorator1(decorator2(&my_method, 456), 123)`
- Add functionality before and after the function is called
```s++
pub fun decorator1<F: std::FunRef>(func: &F, a: std::Number) -> F::return_type:
    std::io::println("decorator1 called - before function");
    let val = func();
    std::io::println("decorator1 called - after function");
    return val + a;

pub fun decorator2<F: std::FunRef>(func: &F, a: std::Number) -> F::return_type:
    std::io::println("decorator2 called - before function");
    let val = func();
    std::io::println("decorator2 called - after function");
    return val + a;

@decorator1(123), @decorator2(456)
pub fun my_method(self: &self_t, a: std::Number) -> std::Number:
    return a + 1;
```

### Defining a decorator for a class
- Changes `Foo{attr: 1}` to `decorator1(Foo{attr: 1}, 123)`
- Accept an already created class, and add functionality after the class is created
- For a normal class, the decorator will return the instance of the class it received
```s++
pub fun decorator1<T>(class: T, a: std::Number) -> T:
    class.attr = a;
    std::io::println("decorator1 called");
    return class;
    
@decorator1(123)
pub cls Foo:
    pub attr: std::Number;
```

## Other information
#### Entry point to a program
```s++
fn main() -> Void {}
```

#### Declaration vs definition
- Functions are never declared, only defined
- Implementation must be provided
- Order of definition doesn't matter in a module

#### Function calling (TODO : expand?)
- Function calls are specified by the function name followed by parentheses
- Function arguments can ave a parameter passing convention (none, &, or &mut)
- Normal arguments must be specified in order before anything else
- Optional parameters can be in any order, as long as they are "named"
- If there are required, optional and variadic parameters, then optional arguments must all be specified, unnamed, 
  before the variadic arguments

#### Base class resolution
- If two base classes have the same signature for a method, and these classes are inherited into a sub-class, that 
  doesn't override the method, then there is an ambiguity issue
- Any attempt to call the method will result in a compile time error
- 2 ways to resolve:
  - Override the method in the sub-class
  - Upcast the class to the correct super-type, and call the method on that => `std::upcast<A>(c).foo(1)`


## Other function features
- [Struct methods]()
- [Closure expressions]()
