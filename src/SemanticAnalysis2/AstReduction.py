"""
The AstReduction module is responsible to manipulating the AST before Syntactic Analysis is performed. There are a few
key operations that take place in this module:

1. Function overload merging:
Generate a class per unique function name, and then super-impose Fn[...] per overload of that function. A single
immutable variable is then generated from this class. For example:

    fn a(x: Num) -> Num { ... }
    fn a(x: Str) -> Str { ... }

becomes:
    cls __MOCK_a {}
    sup Fn[Num, Num] for __MOCK_a {
      fn call_ref(x: Num) -> Num { ... }
    }
    sup Fn[Str, Str] for __MOCK_a {
      fn call_ref(x: Str) -> Str { ... }
    }
    let a = __MOCK_a {}

Because `a` is immutable, the function can't be re-assigned to at runtime, so the compiler can safely assume that the
function will always be the same, and therefore the same class can be used for all instances of `a`. Also, `__MOCK_a` is
prefixed by a double underscore, meaning that as a type, it is inaccessible to the user, and therefore can't be used
directly. It can be overriden by an identifier, but again this doesn't matter, as `a` is already instantiated and
`__MOCK_a` will never have to be instantiated again.

This decision was made, because a class can be made callable with multiple overloads anyway. If the decision of treating
"fn" functions differently was made, then there would be 2 ways to do the same thing, so the Fn[...] super-imposition
decision was made to force only 1 way of functions being callable.

2. Self type substitution:
- Substitute "Self" in class members to the class type
- Substitute "Self" in sup function parameters to the class type
- Substitute "Self" in sup function return types to the class type

This helps simplify type checking later on -- rather than having to lookup "Self" every time to get the type for it
(especially in lots of different places), it makes more sense to convert them all out to the class type, which is
already known.
"""
from src.SemanticAnalysis2.CommonTypes import CommonTypes
from src.SemanticAnalysis2.TypeInference import TypeInfer
from src.SyntacticAnalysis import Ast
from functools import cmp_to_key

# todo : change type.parts[-1].identifier == "Self" to type == CommonTypes.self()


class AstReduction:
    REDUCED_FUNCTIONS = {}

    @staticmethod
    def sort_members(lhs, rhs):
        def cmp(l, r):
            return (l > r) - (l < r)

        cmp_dict = {
            Ast.ClassPrototypeAst: 0,
            Ast.SupPrototypeNormalAst: 1,
            Ast.SupPrototypeInheritanceAst: 2,
            Ast.LetStatementAst: 3,
        }
        return cmp(cmp_dict[type(lhs)], cmp_dict[type(rhs)])

    @staticmethod
    def reduce(ast: Ast.ProgramAst) -> None:
        AstReduction.reduce_program(ast)

    @staticmethod
    def reduce_program(ast: Ast.ProgramAst) -> None:
        for member in ast.module.body.members: AstReduction.reduce_module_member(ast.module, member)
        ast.module.body.members.sort(key=cmp_to_key(AstReduction.sort_members))

    @staticmethod
    def reduce_module_member(mod: Ast.ModulePrototypeAst, ast: Ast.ModuleMemberAst):
        match ast:
            case Ast.FunctionPrototypeAst(): AstReduction.reduce_function_prototype(mod, ast)
            case Ast.SupPrototypeNormalAst(): AstReduction.reduce_sup_prototype(mod, ast)
            case Ast.SupPrototypeInheritanceAst(): AstReduction.reduce_sup_prototype(mod, ast)
            case Ast.ClassPrototypeAst(): AstReduction.reduce_class_prototype(mod, ast)

    @staticmethod
    def reduce_class_prototype(mod: Ast.ModulePrototypeAst, ast: Ast.ClassPrototypeAst):
        # Convert "Self" in class members to the class type
        for member in ast.body.members:
            if member.type_annotation == CommonTypes.self():
                member.type_annotation = ast.to_type()
            TypeInfer.substitute_generic_type(member.type_annotation, CommonTypes.self(), ast.to_type())

        # Prepend module name to class type
        # ast._mod = mod.identifier.remove_last()
        # print(ast._mod, ast.identifier)

    @staticmethod
    def reduce_function_prototype(owner: Ast.ModulePrototypeAst | Ast.SupPrototypeAst, ast: Ast.FunctionPrototypeAst):
        i = owner.body.members.index(ast)

        if not isinstance(owner, Ast.ModulePrototypeAst):
            for param in ast.parameters:
                if param.type_annotation == CommonTypes.self():
                    param.type_annotation = owner.to_type()
                TypeInfer.substitute_generic_type(param.type_annotation, CommonTypes.self(), owner.to_type())

            if ast.return_type == CommonTypes.self():
                ast.return_type = owner.to_type()
            TypeInfer.substitute_generic_type(ast.return_type, CommonTypes.self(), owner.to_type())

            for statement in ast.body.statements:
                match statement:
                    case Ast.LetStatementAst() if statement.type_annotation is not None:
                        if statement.type_annotation == CommonTypes.self():
                            statement.type_annotation = owner.to_type()
                        TypeInfer.substitute_generic_type(statement.type_annotation, CommonTypes.self(), owner.to_type())

        # Recursion break case
        if ast.identifier.identifier in ["call_ref", "call_mut", "call_one"]:
            return

        # If no overload of a function has been seen before, then create the class for it. So for the first instance of
        # a function named "f", the class "__MOCK_f" will be created. For every function definition for "f" found,
        # including this first one, the "Fn[Ref|Mut|One]" class will be super-imposed on it, with "call_[ref|mut|one]"
        # having the parameter and generic types from the original "f" definition.
        f = False
        if AstReduction.merge_names(owner.identifier, ast.identifier.identifier) not in AstReduction.REDUCED_FUNCTIONS.keys():
            cls_ast = Ast.ClassPrototypeAst(ast.decorators, "__MOCK_" + ast.identifier, [], None, Ast.ClassImplementationAst([], -1), -1)
            AstReduction.REDUCED_FUNCTIONS[AstReduction.merge_names(owner.identifier, ast.identifier.identifier)] = cls_ast
            owner.body.members.insert(i, cls_ast)
            f = True

        ty = AstReduction.REDUCED_FUNCTIONS[AstReduction.merge_names(owner.identifier, ast.identifier.identifier)]
        ty = Ast.TypeSingleAst([ty.identifier.to_generic_identifier()], ty.identifier._tok)

        function_type = AstReduction.deduce_function_type(isinstance(owner, Ast.SupPrototypeAst), ast.parameters, ast.return_type)
        new_fun = Ast.SupMethodPrototypeAst(
            [], ast.is_coro, AstReduction.deduce_call_method_from_function_type(function_type),
            ast.generic_parameters, ast.parameters, ast.return_type, None, ast.body, ast._tok)

        is_method = isinstance(owner, Ast.SupPrototypeAst)
        setattr(new_fun, "is_method", is_method)

        owner.body.members.insert(i, Ast.SupPrototypeInheritanceAst(
            ast.generic_parameters,
            Ast.TypeSingleAst([Ast.GenericIdentifierAst("__MOCK_" + ast.identifier.identifier, [], ast.identifier._tok)], ast.identifier._tok),
            None, Ast.SupImplementationAst([new_fun], -1), -1, function_type))

        if f:
            # todo : LetStatement doesn't need type if it's been given a value (check the case below)
            owner.body.members.insert(i + 1, Ast.LetStatementAst([Ast.LocalVariableAst(False, ast.identifier, -1)], Ast.PostfixExpressionAst(Ast.TypeSingleAst([("__MOCK_" + ast.identifier).to_generic_identifier()], ast.identifier._tok), Ast.PostfixStructInitializerAst([], -1), -1), ty, None, -1))
        owner.body.members.remove(ast)

    @staticmethod
    def deduce_function_type(is_method: bool, parameters: list[Ast.FunctionParameterAst], return_type: Ast.TypeAst) -> Ast.TypeAst:
        ty = "FnRef"
        if is_method and parameters and parameters[0].is_self:
            match parameters[0].calling_convention:
                case None: ty = "FnOne"
                case _ if parameters[0].calling_convention.is_mutable: ty = "FnMut"
                case _: ty = "FnRef"
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", [], -1), Ast.GenericIdentifierAst(ty, [return_type] + [p.type_annotation for p in parameters], return_type._tok)], return_type._tok)
        return t

    @staticmethod
    def deduce_call_method_from_function_type(function_type: Ast.TypeSingleAst) -> Ast.IdentifierAst:
        return Ast.IdentifierAst("call_" + function_type.parts[-1].identifier[2:].lower(), -1)

    @staticmethod
    def merge_names(*args) -> str:
        return ".".join([str(a) for a in args])

    @staticmethod
    def reduce_sup_prototype(owner: Ast.ModulePrototypeAst, ast: Ast.SupPrototypeAst):
        for member in [m for m in ast.body.members if isinstance(m, Ast.FunctionPrototypeAst)]:
            AstReduction.reduce_function_prototype(ast, member)
        ast.body.members.sort(key=cmp_to_key(AstReduction.sort_members))
