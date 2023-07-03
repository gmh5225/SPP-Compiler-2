# Type System
## Overview of the type system
- Strong typing => no implicit type casting
- Static typing => type checking at compile time
- Every value is type-inferred
- Explicit type annotations have to be used for uninitialized variables

## Primitives vs Objects
- No primitives in S++
- Everything inherits from `std::Obj` - this is never explicitly stated in code
- Primitive numbers -> `std::Num`
- Primitive booleans -> `std::Bool`
- Primitive strings -> `std::Str`

## Type inference / annotations
- Every value is type-inferred
- Any assignment that has an RHS is always type-inferred, and therefore a type annotation is not allowed
- Any assignment that does not have an RHS must have a type annotation
- Parameter and return types for functions must be annotated
- Class attributes are the same as variables: if they are initialized, they are type-inferred, otherwise they must be annotated

## Supertypes as function parameters
- A class will automatically cast to a super-type if the super-type is used as a parameter type
- Within the function, `std::down_cast<T>` can be used to downcast the parameter to the original type

## Type casting and conversion
- Implement methods specific to each type
- The class `std::ToString` is used to convert any type to a string

## Hierarchy casts
#### Upcasting
- Compile time check to make sure that the target class is a base class of the variable type.
- Always yields a valid object => return type is `T`.
- Use `std::up_cast<T>(...)` to upcast a variable: `let a = std::upcast<T>(b)`

#### Downcasting
- Compile time check to make sure that the target class is a derived class of the variable type.
- Returns a `std::result<T, std::CastErr>` type (could be a different derived class).
- Use `std::down_cast<T>(...)` to downcast a variable: `let a = std::downcast<T>(b)?` (use `?` to handle the error)

#### Cross-casting
- Compile time check to make sure that the target class is a base class of the >0 derived class of the variable type.
- Returns a `std::result<T, std::CastErr>` type (could be a different derived class).
- Use `std::cross_cast<T>(...)` to cross-cast a variable: `let a = std::crosscast<T>(b)?` (use `?` to handle the error)

## Variadic types
- A generic looks like `<...Ts>`, then it is a variadic type - the pack using this type must be variadic ie `...args: Ts`
- A variadic parameter must use this type - a single requires or optional parameter cannot be a variadic type

### Not allowed
- A non-variadic parameter can not be denoted with a type declared as variadic (makes no sense)
```s++
function func_variadic_3<...Ts>(a: Ts):
    std::print(a);
```


### Accessing nth type of a pack
There is a very simple way to access the nth type of a parameter pack, using the index after `::`. For example:
```s++
function func_variadic_4<...Ts>(...a: Ts):
    other_func<Ts::0>(1);
```

## Special types
####  `std::Void`
- The "nothing" type
- Cannot be the type of a variable / attribute
- Can be used as a return type for a function
- Can be used as a generic type argument ie `std::Result<std::Void, std::String>`
- Cannot be instantiated