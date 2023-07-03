# Modules & importing
## Module definition

The `mod` keyword is used at the top of a `.spp` file, in order to mark it as a module that can be
imported into the program's module system. The name of the module must follow the directory structure from the `src`
folder of the program. For example, if the module is in the `src\com\example\module` folder, the module name would be
`src.com.example.module`. The module name must be unique, and cannot be the same as any other module in the program.

Modules can be public, protected or private. A public module can be imported by any other module in the program. A
private module can only be imported by modules in the same directory. A protected module can only be imported by
modules in the same directory, or any subdirectory. A visibility must be specified.

Tools in IDEs such as Intellij will automatically fill in this module name as a file template, so it is not
necessary for the programmer to type it out. Further to this, the file systems of most operating systems force every
directory to have a unique name, so it is not possible to have two modules with the same name. If a module is
not desired to be imported, the `mod` identifier can be commented out.

<BR>

## Importing
- Import block is defined under the `mod` keyword, if desired.
- It is used to import modules from other locations into the current module.
- The `use` keyword is followed by the module path and then types / functions to import
- Use `sup` to import from the super module (parent directory)
- Use `src` to refer to the root of the `src` folder
```s++
mod src.com.example.module1;

# Import local structures.
use src::data_structures::my_struct;
use sup::utils::vector_tools -> vector_tools;

# Import the vector and optional class from the standard library.
use std::vector::vector;
use std::optional::{optional, ok, some};

# Import minecraft data structures from GitHub S++ project (cached locally).
use vcs::minecraft::models::block::{block, block_state};
use vcs::minecraft::particles::{particle, particle_type};
use vcs::minecraft::models::entity::{entity, entity_type};

# Import the lockers library from the lib folder.
use lib::lockers::lockers;
```
- The automatic namespacing of types follows the module path, **but NOT including the filename**

### What can be imported
#### Single type - one of:
- Import one type from a module by extending the `use` with another `::Type;`
- Import one type inside a group of imports: `::{Type};`

#### Multiple types:
- Import multiple types inside an import group: `::{Type1, Type2};`

#### All types:
- Import all types from a module: `::*;`

### Import locations
| Folder tag | Description                                                             |
|------------|-------------------------------------------------------------------------|
| `src`      | The `src` folder of the program, root of all 2nd party content          |
| `lib`      | The `lib` folder of the program, root of all 3rd party static content   |
| `std`      | The `std` folder of the S++ standard library (1st party code)           |
| `vcs`      | The `vcs` folder of the program, cache of all 3rd party dynamic content |
| `sup`      | The super module (parent directory)                                     |

<BR>

#### src
- Root folder of the program, root of all 2nd party content
- Only folder that can contain user-defined modules
- Enforced by the compiler - the `main.spp` will be in at the root of the `src` folder

#### lib
- Root folder of the program, root of all 3rd party static content
- Download static 3rd party content, where it is not hosted on a vcs
- Prefer to use vcs over lib, as it allows for automatic updates of the code

#### std
- Root folder of the S++ standard library (1st party code)
- Contains all the standard library modules
- Simple structure to optimize imports

#### vcs
- Root folder of the program, cache of all 3rd party dynamic content
- Allows importing directly from a vcs, such as GitHub or GitLab
- Allows for automatic updates of the code
- The `config.toml` file defines the URLs for each project to get from vcs

To use non common version control systems, the user can add a config file to the `vcs` folder. The config file must
follow the following specification (github example), so that the compiler knows how to download the code from the
vcs - it's a very simple system, and can be easily extended to support any vcs system:
```toml
[meta]
name = "github"
prefix = "gh"
url = "https://github.com/<user>/<repo>/blob/<branch>"

[commands]
clone = "git clone"
fetch = "git fetch"
pull  = "git pull"
```

Here is the GitLab example:
```toml
[meta]
name = "gitlab"
prefix = "gl"
url = "https://gitlab.com/<user>/<repo>/blob/<branch>"

[commands]
clone = "git clone"
fetch = "git fetch"
pull  = "git pull"
```

To register the project to import from vcs:
```toml
[vcs]
minecraft = "https://.../minecraft.git"
```
The correct VCS is used based on the URl regex comparison to known VCS URLs.

<BR>

## Exporting
There is no `export` keyword -- instead, top level structs of a module have an access modifier, which determines the
importability of the struct. The access modifiers are: `pub`, `priv`, `prot`, and for classes, enums and
modules, the `part` keyword is also available to extend partial types.
