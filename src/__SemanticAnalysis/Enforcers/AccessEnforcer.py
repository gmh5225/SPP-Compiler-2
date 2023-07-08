"""
Access modifiers are used to control the access of class members [class members]
- Public: Accessible from anywhere
- Protected: Accessible from the class and subclasses
- Private: Accessible only from the class

Access modifiers also dictate the visibility of a member of a module [module members]
- Public: Can be imported into any module
- Protected: Can be imported into a sibling or child module (directory structure)
- Private: Can only be used in the module - not importable into other modules

Access modifiers also dictate the visibility of a module [module]
- Public: Accessible from any module
- Protected: Accessible from a sibling or child module (directory structure)
- Private: Not accessible from any other module

Places where access modifiers have to be checked
- Class members: member access postfix expression - check the access modifier of the member
- Module members: import statement - check the access modifier of the module member
- Module: import statement - check the access modifier of the module
"""