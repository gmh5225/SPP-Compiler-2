# Structs

## Classes vs Structs
- S++ "classes" are technically structs, ie they contain a list of fields.
- Used in a similar way to classes in other languages.
- Support a range of OOP features, including inheritance (via "super-imposition"), polymorphism, and encapsulation.
- The `cls` keyword is used to define a class.

## Overview of a class prototype
- Access modifier -> `pub`, `prot`, `priv`, determines where the class can be accessed from
- Classes can have [decorators](#decorators), that wrap the function in extra behaviour
- Classes can have [generic parameters & constraints](./6%20-%20generics%20&%20constraints.md)
- Classes have an implementation

### Access modifier
- `pub`: exported out the module, any module can import it
- `prot`: exported out the module, only sibling and child modules can import it
- `priv`: not exported out the module, only the module it is defined in can use it

### Decorators
- Additional behaviour after a class has been created
- See [decorating a class](./7%20-%20functions.md#defining-a-decorator-for-a-class)

### Generic parameters & constraints
- Classes can have generic parameters, defined after the class name
- Generic types of a class are available to all methods and attributes of the class
- Generic types can have constraints, defined after the generic type name, or in a `where` block
- Optional and variadic generic types can be defined

### Where block
- Optional clause to specify additional constraints on generic parameters
- See [Where clause]() for more information

## Overview of class implementation
### Implementation must be provided
- Attributes
- Static attributes

### Attributes
- Defined by an access modifier, an identifier and a type
- Attributes are defined with a type (no value), and must be initialized in the struct initializer
- Attributes can be accessed by name, and can be given in any order to the struct initializer
- Attributes, from inside the class, must be accessed with `self` or whatever the instance parameter is

### Static attributes
- Define in the same way as an [attribute](#attributes), but with a value, not a type (inferred)
- Static attributes must be accessed by the class name, even from inside the class

Example
```s++
cls Foo {
    pub a: std::Num;
    pub b: std::Num;
    pub c: std::Num;
    
    pub x = 2; # static
}
```

## Super-imposition
#### Concept
- Super-imposition relates to the implementation of methods, or other classes, in a class
- Super-imposition is the process of "imposing" something on top of the current class
- The class being imposed on must have be defined with the `cls` keyword in the file

### Methods
#### Implement the class directly, listing the methods
- Methods are defined in the same way as functions
- Methods can be defined in any order
- Methods can be defined in multiple implementations of the same class

```s++
sup Foo {
    pub fn foo() -> Void {}
    pub fn bar() -> Void {}
}

sup Foo {
    pub fn baz() -> Void {}
}
```

#### Compile-time conditionally enable functions with type-constraints
- Functions can be conditionally enabled based on the type of the generic parameters
- Enable certain functions if the constraints of the generic parameters are satisfied

```s++
sup Foo<T> {
    pub fn foo() -> Void {}
    pub fn bar() -> Void {}
    pub fn baz() -> Void {}
}

sup Foo<T: std::Default> {
    pub fn def() -> Void {}
}
```

### Classes ("inheritance")
- Works in a similar way to methods
- Allow super-imposing an entire class on top of the current class, acting as a super-class
- Allow functions to be overridden

#### Override methods from the super-class
- Required to give explicit control over which methods can be overridden
- Methods must be decorated with `@std::virtual` in the super-class to allow a sub-class to override

```s++
sup Bar {
    @std::virtual pub fn foo(self: &Self) -> Void {}
    @std::virtual pub fn bar(self: &Self) -> Void {}
}

sup Bar for Foo {
    pub fn foo(self: &Self) -> Void {...}
    pub fn bar(self: &Self) -> Void {...}
}
```

#### Compile-time conditionally enable classes with type-constraints
- Classes can be conditionally enabled based on the type of the generic parameters
- Enable certain classes if the constraints of the generic parameters are satisfied
- Any type-constraints on the base class must also be on the `sup` definitions when inheriting it
  - For example if `sup Bar<T: std::Default>` was the `sup` definition for `Bar`:
  - Then to inherit it as below, it would have to be `sup Bar<T: std::Default & std::Copy> for Foo`

```s++
sup Bar<T> {
    @std::virtual pub fn foo(self: &Self) -> Void {}
    @std::virtual pub fn bar(self: &Self) -> Void {}
    @std::virtual pub fn baz(self: &Self) -> Void {}
}

sup Bar<T: std::Copy> for Foo {
    pub fn foo(self: &Self) -> Void {...}
    pub fn bar(self: &Self) -> Void {...}
    pub fn baz(self: &Self) -> Void {...}
}
```

## Class instantiation
#### No constructors
- Classes do not support constructors
- Static methods exist and do the same thing => remove multiple ways to do the same thing

#### Struct initialization
- Raw initialization where each attribute must be given a value
- Order of initialization doesn't matter
- Shorthand allows the variable name to be omitted if the variable name is the same as the attribute name
- Class name is always required
- Base class instantiation should follow the `sup` keyword in the `{...}`
- It is possible to specify some fields, and then use another object to fill in the rest of the fields, with `else`
- This is the **ONLY** way to instantiate a class

```s++
let foo = Foo {a: 1, b: 2, c: 3}; # specify all fields
let foo = Foo {a, b, c}; # where a, b, and c are defined local variables
let bar = Foo {a: 3, else: foo}; # specify some fields, and fill in the rest with another object
```

- If `Foo` super-imposes `std::Default`, then `let baz = Foo{a: 3, else: Foo::default()}` allows for defaulting the variables and adjusting only the required ones
- Works because the `::default()` will construct the `Foo` object and therefore all fields will be specified
- An object in the `else` clause will be destructively moved, as any other assignment / [function call with no `&`] would

#### Static methods
- Static methods can return instances of the class
- Wrap the struct initialization in a function, providing some default values if desired
- Multiple static methods fine-tune the initialization process - `new`, `new_capa`, etc
- Convention is to use `new` for the default initialization

```s++
let foo = Foo::new(1, 2, 3);
```

## self and Self
#### `self`
- Not a keyword - allows for flexibility in naming, for example `this`
- The current instance of the class
- Can be used to access attributes and methods of the current instance
- Can be used to call other methods of the current instance
- Cannot be used to access/call static attributes or methods
- Followed by the `.` runtime access operator

#### `self`'s type in methods
- `self: &Self` -- an immutable reference to the current instance
- `self: &mut Self` -- a mutable reference to the current instance
- `self: Self` -- the current instance is moved into the method, and is no longer accessible outside the method
- `mut self: Self` -- the current instance is moved into the method, and is no longer accessible outside the method,
  but the method can mutate the instance

#### `Self`
- Is a keyword
- The type of the current instance of the class
- Can be used to specify the parameter types or return type of a method
- Can be used to access/call static attributes or methods
- Followed by the `::` compile-time access operator


## Member access
#### Runtime access
- All member access is done at runtime, so the runtime access operator `.` is used.
- The runtime access operator is used to access attributes and methods of the current instance
- Applicable to any object, or `self`

#### Safe access
- Types super-imposing the `std::ops::Try` class can have the postfix `?` operator applied
- Mock safe access by combining the `?` with the `.` operator, ie access if the object is not null, otherwise return 
  the residual value

## Virtual, Abstract, Static
- The decorators show below apply mutations to the methods that another method in the basic meta-class can detect
- This metaclass enforces a number of rules to ensure that explicit control is given regarding overriding methods

#### Virtual classes
- For a class to be inheritable, it must have 1+ methods decorated with `@std::virtual_method`
- A class with 1 or more virtual methods means that the class is virtual
- Common to implement the `std::ops::DTor` class and decorate the `__del__` method as `@std::virtual`
- Virtual methods can, but do not have to be, implemented in the super-class

#### Abstract classes
- For a class to be abstract, it must have 1+ methods decorated with `@std::abstract_method`
- Abstract classes cannot be instantiated
- Abstract methods must be implemented in the super-class
- Abstract classes can contain non-absract methods as well as abstract methods

#### Static methods
- For a method to be static, it must be decorated with `@std::static_method`
- Static methods can be called without an instance of the class
- Static methods cannot be called with an instance of the class -- use `type::` instead of `self.`