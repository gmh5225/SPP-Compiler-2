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
"""
from src.SemanticAnalysis2.TypeInference import TypeInfer
from src.SyntacticAnalysis import Ast
from functools import cmp_to_key

from src.SyntacticAnalysis.Parser import ErrFmt


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
            case Ast.ClassPrototypeAst(): AstReduction.reduce_class_prototype(ast)

    @staticmethod
    def reduce_class_prototype(ast: Ast.ClassPrototypeAst):
        # Convert "Self" in class members to the class type
        for member in ast.body.members:
            if member.type_annotation.parts[-1].identifier == "Self":
                member.type_annotation = ast.to_type()
            TypeInfer.substitute_generic_type(member.type_annotation, "Self", ast.to_type())

    @staticmethod
    def reduce_function_prototype(owner: Ast.ModulePrototypeAst | Ast.SupPrototypeAst, ast: Ast.FunctionPrototypeAst):
        i = owner.body.members.index(ast)

        if not isinstance(owner, Ast.ModulePrototypeAst):
            for param in ast.parameters:
                if param.type_annotation.parts[-1].identifier == "Self":
                    param.type_annotation = owner.to_type()
                TypeInfer.substitute_generic_type(param.type_annotation, "Self", owner.to_type())
            for statement in ast.body.statements:
                match statement:
                    case Ast.LetStatementAst() if statement.type_annotation is not None:
                        if statement.type_annotation.parts[-1].identifier == "Self":
                            statement.type_annotation = owner.to_type()
                        TypeInfer.substitute_generic_type(statement.type_annotation, "Self", owner.to_type())

        # Recursion break case
        if ast.identifier.identifier in ["call_ref", "call_mut", "call_one"]:
            return

        # If no overload of a function has been seen before, then create the class for it. So for the first instance of
        # a function named "f", the class "__MOCK_f" will be created. For every function definition for "f" found,
        # including this first one, the "FnRef" class will be super-imposed on it, with "call_ref" having the parameter
        # and generic types from the original "f" definition.
        f = False
        if AstReduction.merge_names(owner.identifier, ast.identifier.identifier) not in AstReduction.REDUCED_FUNCTIONS.keys():
            cls_ast = Ast.ClassPrototypeAst(ast.decorators, "__MOCK_" + ast.identifier, [], None, Ast.ClassImplementationAst([], -1), -1)
            AstReduction.REDUCED_FUNCTIONS[AstReduction.merge_names(owner.identifier, ast.identifier.identifier)] = cls_ast
            owner.body.members.insert(i, cls_ast)
            f = True

        ty = AstReduction.REDUCED_FUNCTIONS[AstReduction.merge_names(owner.identifier, ast.identifier.identifier)]
        ty = Ast.TypeSingleAst([ty.identifier.to_generic_identifier()], ty.identifier._tok)

        new_fun = Ast.SupMethodPrototypeAst([], ast.is_coro, Ast.IdentifierAst("call_ref", -1), ast.generic_parameters, ast.parameters, ast.return_type, None, ast.body, ast._tok)
        setattr(new_fun, "is_method", isinstance(owner, Ast.SupPrototypeAst))
        owner.body.members.insert(i, Ast.SupPrototypeInheritanceAst(
            ast.generic_parameters,
            Ast.TypeSingleAst([ast.identifier.to_generic_identifier()], ast.identifier._tok),
            None,
            Ast.SupImplementationAst([new_fun], -1),
            -1,
            Ast.TypeSingleAst([Ast.GenericIdentifierAst("FnRef", [ast.return_type] + [p.type_annotation for p in ast.parameters], ast.identifier._tok)], ast._tok)))

        if f:
            owner.body.members.insert(i + 1, Ast.LetStatementAst([Ast.LocalVariableAst(False, ast.identifier, -1)], Ast.PostfixExpressionAst(Ast.TypeSingleAst([("__MOCK_" + ast.identifier).to_generic_identifier()], ast.identifier._tok), Ast.PostfixStructInitializerAst([], -1), -1), ty, None, -1))
        owner.body.members.remove(ast)

    @staticmethod
    def merge_names(*args) -> str:
        return ".".join([str(a) for a in args])

    @staticmethod
    def reduce_sup_prototype(owner: Ast.ModulePrototypeAst, ast: Ast.SupPrototypeAst):
        for member in [m for m in ast.body.members if isinstance(m, Ast.FunctionPrototypeAst)]:
            AstReduction.reduce_function_prototype(ast, member)
        ast.body.members.sort(key=cmp_to_key(AstReduction.sort_members))
