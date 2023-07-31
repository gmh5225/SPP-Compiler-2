from __future__ import annotations
from typing import Callable, Optional

from src.SyntacticAnalysis import Ast
from src.SyntacticAnalysis.Parser import Parser, ErrFmt
from src.LexicalAnalysis.Lexer import Lexer

import re

CURRENT_MODULE_MEMBER: Optional[Ast.TypeAst] = None

class Symbol:
    name: str
    type: Optional[Ast.TypeAst]
    value: Optional[Ast.ExpressionAst]

    # optional metadata
    index: int
    bases: list[Ast.TypeAst]

    # memory
    initialized: bool
    defined: bool # ie exists but not initialized
    mutable: bool
    # borrowed_ref: bool
    # borrowed_mut: bool

    def __init__(self, name: str, type_: Optional[Ast.TypeAst], value: Optional[Ast.ExpressionAst], **kwargs):
        self.name = name
        self.type = type_
        self.value = value

        self.index = kwargs.get("index", 0)
        self.bases = []

        self.initialized = self.value is not None
        self.defined = False
        self.mutable = kwargs.get("mutable", False)
        self.borrowed_ref = kwargs.get("borrowed_ref", False)
        self.borrowed_mut = kwargs.get("borrowed_mut", False)

    def json(self) -> dict[str, any]:
        d = {
            "Name": self.name,
            "Type": convert_type_to_string(self.type),  # base64.b64encode(pickle.dumps(self.type)).decode(),
            # "Value": 1,  # base64.b64encode(pickle.dumps(self.value)).decode(),
            "Index": self.index,
        }

        if self.bases:
            d["Bases"] = [repr(b) for b in self.bases]

        return d


class SymbolTable:
    symbols: dict[str, Symbol]

    def __init__(self):
        self.symbols = {}

    def add(self, symbol: Symbol):
        # todo : check for duplicates if a "#" is in the name

        self.symbols[symbol.name] = symbol

    def get(self, name: str) -> Symbol:
        return self.symbols[name]

    def has(self, name: str) -> bool:
        return name in self.symbols

    def json(self) -> dict[str, any]:
        return {name: symbol.json() for name, symbol in self.symbols.items()}

class Scope:
    name: str
    symbols: SymbolTable
    types: SymbolTable
    parent: Optional[Scope]
    children: list[Scope]
    visited: bool

    sup_scopes: list[Scope]

    def __init__(self, name: str, parent: Optional[Scope] = None):
        self.name = name
        self.symbols = SymbolTable()
        self.types = SymbolTable()

        self.parent = parent
        self.children = []
        if self.parent is not None:
            self.parent.children.append(self)

        self.visited = False
        self.sup_scopes = []

    def add_symbol(self, symbol: Symbol):
        if "#" in (name := symbol.name):
            params_a = name.split("#")[1].split(",")
            params_a = [p.split("|")[1] for p in params_a]

            for symbol_name in self.all_symbols():
                if "#" not in symbol_name: continue
                if symbol_name.split("#")[0] != name.split("#")[0]: continue

                symbol_b = self.get_symbol(symbol_name)
                params_b = symbol_b.name.split("#")[1].split(",")
                params_b = [p.split("|")[1] for p in params_b]

                if len(params_a) != len(params_b): continue
                if all([p_a == p_b for p_a, p_b in zip(params_a, params_b)]):
                    raise SystemExit(ErrFmt.err(symbol.type._tok) + f"Invalid function overload '{function_identifier_strip_signature(name, string_ref=True)}'")

        self.symbols.add(symbol)

    def add_type(self, symbol: Symbol):
        self.types.add(symbol)

    def get_symbol(self, name: str) -> Symbol:
        current = self
        while current is not None:
            if current.symbols.has(name):
                return current.symbols.get(name)
            current = current.parent

        # next check linked sup-scopes
        for sup_scope in self.sup_scopes:
            if sup_scope.symbols.has(name):
                return sup_scope.symbols.get(name)

        # base class checks for fn
        if "#" in name:
            # allow for params to match base types
            params_a = name.split("#")[1].split(",")
            conv_a = [p.split("|")[0] for p in params_a]
            params_a = [p.split("|")[1] for p in params_a]
            for symbol_name in self.all_symbols():
                match = True

                if "#" not in symbol_name: continue
                if symbol_name.split("#")[0] != name.split("#")[0]: continue

                symbol = self.get_symbol(symbol_name)
                params_b = symbol.name.split("#")[1].split(",")
                conv_b = [p.split("|")[0] for p in params_b]
                params_b = [p.split("|")[1] for p in params_b]

                if len(params_a) != len(params_b): continue
                for p_a, p_b, c_a, c_b in zip(params_a, params_b, conv_a, conv_b):
                    if c_a == c_b or c_a == "???":

                        if p_a == p_b: continue

                        # get the base classes of p_a
                        p_a_type = self.get_type(p_a)
                        p_a_bases = p_a_type.bases
                        if p_b in [convert_type_to_string(b) for b in p_a_bases]: continue

                    # not a match
                    match = False
                    break

                if match: return symbol


        raise Exception(f"Symbol '{name}' not found")

    def get_type(self, name: str) -> Symbol:
        current = self
        while current is not None:
            if current.types.has(name):
                return current.types.get(name)
            current = current.parent

        raise Exception(f"Type '{name}' not found")

    def has_symbol(self, name: str) -> bool:
        try:
            self.get_symbol(name)
            return True
        except:
            return False

    def has_type(self, name: str) -> bool:
        current = self
        while current is not None:
            if current.types.has(name):
                return True
            current = current.parent

        return False

    def all_symbols(self) -> list[str]:
        current = self
        symbols = []
        while current is not None:
            symbols += current.symbols.symbols.keys()
            current = current.parent

        # next check linked sup-scopes
        for sup_scope in self.sup_scopes:
            symbols += sup_scope.symbols.symbols.keys()

        return symbols

    def all_exclusive_symbols(self) -> list[str]:
        return list(self.symbols.symbols.keys())

    def get_child_scope_for_fn(self, fn_name: str) -> Optional[Scope]:
        for child in self.children:
            if child.name == f"FnPrototype__{fn_name}":
                return child
        return None

    def get_child_scope_for_cls(self, cls_name: str) -> Optional[Scope]:
        for child in self.children:
            if child.name == f"ClsPrototype__{cls_name}":
                return child
        return None

    def json(self) -> dict[str, any]:
        return {
            "Name": self.name,
            "Symbols": self.symbols.json(),
            "Types": self.types.json(),
            "ChildScopes": [s.json() for s in self.children]
        }


class ScopeHandler:
    global_scope: Scope
    current_scope: Scope

    def __init__(self):
        self.global_scope = Scope("Global")
        self.current_scope = self.global_scope

    def enter_scope(self, name: str) -> None:
        self.current_scope = Scope(name, self.current_scope)

    def exit_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def next_scope(self) -> None:
        # Use the Scope.visited flag to keep track of which scopes have been visited.

        # First check if any children are unvisited, and visit the first one
        if any([not scope.visited for scope in self.current_scope.children]):
            unvisited_scopes = [scope for scope in self.current_scope.children if not scope.visited]
            next_scope = unvisited_scopes[0]
            next_scope.visited = True
            self.current_scope = next_scope

        else:
            raise Exception("No unvisited scopes")

    def prev_scope(self) -> None:
        self.current_scope = self.current_scope.parent

    def skip_scope(self) -> None:
        self.next_scope()
        self.prev_scope()

    def switch_to_global_scope(self) -> None:
        # switch to global and "un-visit" every scope
        self.current_scope = self.global_scope
        self.visit_every_scope(lambda scope: setattr(scope, "visited", False))

    def visit_every_scope(self, func: Callable) -> None:
        # Apply some function to every scope, starting from the current scope and recursively visiting children
        def visit_every_scope_helper(scope: Scope, func: Callable) -> None:
            func(scope)
            for child in scope.children:
                visit_every_scope_helper(child, func)

        current_scope = self.current_scope
        visit_every_scope_helper(current_scope, func)

    def json(self) -> dict[str, any]:
        return self.global_scope.json()


class SymbolTableBuilder:
    @staticmethod
    def build(ast: Ast.ProgramAst) -> ScopeHandler:
        s = ScopeHandler()
        SymbolTableBuilder.build_program_symbols(ast, s)
        s.switch_to_global_scope()
        return s

    @staticmethod
    def build_program_symbols(ast: Ast.ProgramAst, s: ScopeHandler) -> None:
        global CURRENT_MODULE_MEMBER
        # Match each module member by AST type, and call the appropriate function to build the symbols for that member.
        # This will recursively call into other functions to build symbols for nested members.
        for module_member in ast.module.body.members:
            CURRENT_MODULE_MEMBER = None
            match module_member:
                case Ast.FunctionPrototypeAst(): SymbolTableBuilder.build_function_prototype_symbols(module_member, s)
                case Ast.ClassPrototypeAst(): SymbolTableBuilder.build_class_prototype_symbols(module_member, s)
                case Ast.EnumPrototypeAst(): SymbolTableBuilder.build_enum_prototype_symbols(module_member, s)
                case Ast.SupPrototypeNormalAst(): SymbolTableBuilder.build_sup_prototype_symbols(module_member, s)
                case Ast.SupPrototypeInheritanceAst(): SymbolTableBuilder.build_sup_prototype_symbols(module_member, s)

        if ast.module.body.import_block is not None:
            for import_ in ast.module.body.import_block.imports:
                SymbolTableBuilder.build_import_symbols(import_, s)

    @staticmethod
    def build_import_symbols(ast: Ast.ImportStatementAst, s: ScopeHandler) -> None:
        # Create a new scope for the imported module, and enter it.
        # todo : only import what's needed per module (somehow)
        ts = ErrFmt.TOKENS
        module_name = f"./TestCode/{convert_module_name_to_file_name(ast.module)}.spp"
        try:
            module_code = open(f"{module_name}", "r").read()
        except FileNotFoundError:
            error = Exception(
                ErrFmt.err(ast._tok) +
                f"Could not find module '{module_name}'")
            raise SystemExit(error) from None
        SymbolTableBuilder.build_program_symbols(Parser(Lexer(module_code).lex()).parse(), s)  # bring into global scope
        ErrFmt.TOKENS = ts

    @staticmethod
    def build_function_prototype_symbols(ast: Ast.FunctionPrototypeAst, s: ScopeHandler) -> None:
        s.enter_scope(f"FnPrototype__{convert_identifier_to_string(ast.identifier)}")

        # Register the function parameters as symbols with their type annotations used to determine the type of the
        # symbol. Add the generic type parameters as types. Finally, recursively visit each statement in the function
        # body to build symbols for nested members.
        for param in ast.parameters:
            s.current_scope.add_symbol(Symbol(
                convert_identifier_to_string(param.identifier), normalize_type(param.type_annotation), None,
                mutable=param.is_mutable,
                borrowed_ref=param.calling_convention and not param.calling_convention.is_mutable,
                borrowed_mut=param.calling_convention and param.calling_convention.is_mutable))
        for generic in ast.generic_parameters:
            s.current_scope.add_type(Symbol(convert_identifier_to_string(generic.identifier), None, None))
        for statement in ast.body.statements:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        ast.return_type = normalize_type(ast.return_type)

        # Exit the function body scope and return to the parent scope.
        s.exit_scope()

        # Add the function prototype to the current scope, and enter a new scope for the function body.
        ast.identifier.identifier += f"#{','.join([convert_convention_to_string(p.calling_convention) + '|' + convert_type_to_string(p.type_annotation) for p in ast.parameters])}"
        s.current_scope.add_symbol(Symbol(convert_identifier_to_string(ast.identifier), get_function_type(ast), None))

    @staticmethod
    def build_statement_symbols(ast: Ast.StatementAst, s: ScopeHandler) -> None:
        # The actual statements are the non-expression statement -- TypedefStatementAst, ReturnStatementAst,
        # LetStatementAst and FunctionPrototypeAst. The expression statements are handled in the expression match.
        # Because an expression is a valid statement, the "default" case for non-expression statements is to build
        # symbols for the expression.
        match ast:
            case Ast.TypedefStatementAst(): SymbolTableBuilder.build_typedef_statement_symbols(ast, s)
            case Ast.ReturnStatementAst(): SymbolTableBuilder.build_return_statement_symbols(ast, s)
            case Ast.LetStatementAst(): SymbolTableBuilder.build_let_statement_symbols(ast, s)
            case Ast.FunctionPrototypeAst(): SymbolTableBuilder.build_function_prototype_symbols(ast, s)
            case _: SymbolTableBuilder.build_expression_symbols(ast, s)

    @staticmethod
    def build_typedef_statement_symbols(ast: Ast.TypedefStatementAst, s: ScopeHandler) -> None:
        s.current_scope.add_type(Symbol(convert_type_to_string(ast.new_type), normalize_type(ast.old_type), None))

    @staticmethod
    def build_return_statement_symbols(ast: Ast.ReturnStatementAst, s: ScopeHandler) -> None:
        SymbolTableBuilder.build_expression_symbols(ast.value, s)

    @staticmethod
    def build_let_statement_symbols(ast: Ast.LetStatementAst, s: ScopeHandler) -> None:
        for i, variable in enumerate(ast.variables):
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(variable.identifier), normalize_type(ast.type_annotation) if ast.type_annotation else None, ast.value, index=i, mutable=variable.is_mutable))
            if ast.value: SymbolTableBuilder.build_expression_symbols(ast.value, s)
        if ast.if_null:
            SymbolTableBuilder.build_inner_scope_symbols(ast.if_null, s)

    @staticmethod
    def build_expression_symbols(ast: Ast.ExpressionAst, s: ScopeHandler) -> None:
        match ast:
            case Ast.BinaryExpressionAst(): pass
            case Ast.PostfixExpressionAst(): pass
            case Ast.AssignmentExpressionAst(): pass
            case Ast.IdentifierAst(): pass
            case Ast.LambdaAst(): SymbolTableBuilder.build_lambda_symbols(ast, s)
            case Ast.PlaceholderAst(): pass
            case Ast.TypeSingleAst(): pass
            case Ast.IfStatementAst(): SymbolTableBuilder.build_if_statement_symbols(ast, s)
            case Ast.WhileStatementAst(): SymbolTableBuilder.build_while_statement_symbols(ast, s)
            case Ast.YieldStatementAst(): pass
            case Ast.InnerScopeAst(): SymbolTableBuilder.build_inner_scope_symbols(ast, s)
            case Ast.WithStatementAst(): SymbolTableBuilder.build_with_statement_symbols(ast, s)
            case Ast.TokenAst(): pass
            case _ :
                if type(ast) in Ast.LiteralAst.__args__: return
                if type(ast) in Ast.NumberLiteralAst.__args__: return
                raise NotImplementedError(f"ExpressionAst {ast} not implemented")

    @staticmethod
    def build_lambda_symbols(ast: Ast.LambdaAst, s: ScopeHandler) -> None:
        s.enter_scope("Lambda")
        for param in ast.parameters:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(param.identifier), None, None))
        SymbolTableBuilder.build_expression_symbols(ast.body, s)
        s.exit_scope()

    @staticmethod
    def build_if_statement_symbols(ast: Ast.IfStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("IfStatement")
        for branch in ast.branches:
            SymbolTableBuilder.build_if_branch_symbols(branch, s)
        s.exit_scope()

    @staticmethod
    def build_if_branch_symbols(ast: Ast.PatternStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("PatternBranch")
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_while_statement_symbols(ast: Ast.WhileStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("WhileStatement")
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_inner_scope_symbols(ast: Ast.InnerScopeAst, s: ScopeHandler) -> None:
        s.enter_scope("InnerScope")
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_with_statement_symbols(ast: Ast.WithStatementAst, s: ScopeHandler) -> None:
        s.enter_scope("WithStatement")
        s.current_scope.add_symbol(Symbol(convert_identifier_to_string(ast.alias.identifier), None, None, mutable=ast.alias.is_mutable))
        for statement in ast.body:
            SymbolTableBuilder.build_statement_symbols(statement, s)
        s.exit_scope()

    @staticmethod
    def build_class_prototype_symbols(ast: Ast.ClassPrototypeAst, s: ScopeHandler) -> None:
        global CURRENT_MODULE_MEMBER
        CURRENT_MODULE_MEMBER = Ast.TypeSingleAst([Ast.GenericIdentifierAst(ast.identifier.identifier, [], ast.identifier._tok)], ast.identifier._tok)

        s.current_scope.add_type(Symbol(convert_identifier_to_string(ast.identifier), None, None))
        s.enter_scope(f"ClsPrototype__{convert_identifier_to_string(ast.identifier)}")
        for member in ast.body.members:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(member.identifier), normalize_type(member.type_annotation), None, mutable=member.is_mutable))
        s.exit_scope()

    @staticmethod
    def build_enum_prototype_symbols(ast: Ast.EnumPrototypeAst, s: ScopeHandler) -> None:
        s.current_scope.add_type(Symbol(convert_identifier_to_string(ast.identifier), None, None))
        s.enter_scope("EnumPrototype")
        for member in ast.body.members:
            s.current_scope.add_symbol(Symbol(convert_identifier_to_string(member.identifier), None, None))
        s.exit_scope()

    @staticmethod
    def build_sup_prototype_symbols(ast: Ast.SupPrototypeNormalAst | Ast.SupPrototypeInheritanceAst, s: ScopeHandler) -> None:
        global CURRENT_MODULE_MEMBER
        CURRENT_MODULE_MEMBER = ast.identifier

        if isinstance(ast, Ast.SupPrototypeInheritanceAst):
            s.global_scope.get_type(convert_type_to_string(ast.identifier)).bases.append(convert_type_to_string(ast.super_class))

        s.enter_scope("SupPrototype")
        for typedef in filter(lambda member: isinstance(member, Ast.SupTypedefAst), ast.body.members):
            s.current_scope.add_type(Symbol(convert_type_to_string(typedef.new_type), typedef.old_type, None))
        for method in filter(lambda member: isinstance(member, Ast.SupMethodPrototypeAst), ast.body.members):
            SymbolTableBuilder.build_function_prototype_symbols(method, s)

        # bind the sup-Scope to the cls-Scope
        cls = ast.identifier
        cls_scope = s.global_scope.get_child_scope_for_cls(cls.parts[0].identifier)
        cls_scope.sup_scopes.append(s.current_scope)

        s.exit_scope()


def convert_identifier_to_string(ast: Ast.IdentifierAst | Ast.GenericIdentifierAst) -> str:
    if isinstance(ast, int): return str(ast)
    x = ast.identifier
    if type(ast) == Ast.GenericIdentifierAst:
        return x + f"[{', '.join(map(lambda y: convert_identifier_to_string(y.identifier), ast.generic_arguments))}]"
    return x

def convert_multi_identifier_to_string(ast: Ast.ModuleIdentifierAst) -> str:
    return ".".join(map(lambda x: x.identifier, ast.parts))

def convert_type_to_string(ast: Ast.TypeAst) -> str:
    if isinstance(ast, Ast.TypeSingleAst):
        s = ""
        for p in ast.parts:
            if isinstance(p, Ast.SelfTypeAst):
                s += "Self."
                continue
            if isinstance(p, int):
                s += str(p) + "."
                continue
            s += p.identifier
            if isinstance(p, Ast.GenericIdentifierAst) and p.generic_arguments:
                generics = list(map(lambda y: convert_type_to_string(y.value), p.generic_arguments))
                joined_generics = ", ".join(generics)
                s += f"[{joined_generics}]"
            s += "."
        return s[:-1]
    elif isinstance(ast, Ast.TypeTupleAst):
        s = "("
        for p in ast.types:
            s += convert_type_to_string(p) + ", "
        return (s[:-2] if len(s) > 2 else s) + ")"
    elif isinstance(ast, str):
        return ast # temp (for type: "TODO") etc
    elif ast is None:
        return ""
    else:
        raise NotImplementedError(f"TypeAst {ast} not implemented")

def convert_identifier_to_string_no_generics(ast: Ast.IdentifierAst | Ast.GenericIdentifierAst) -> str:
    return ast.identifier

def get_function_type(ast: Ast.FunctionPrototypeAst) -> Ast.TypeAst:
    # todo : FnRef vs FnMut vs Fn

    return_type = Ast.TypeGenericArgumentAst(None, ast.return_type, ast.return_type._tok)
    param_types = Ast.TypeGenericArgumentAst(None, Ast.TypeTupleAst([a.type_annotation for a in ast.parameters], ast.identifier._tok), ast.identifier._tok)

    return Ast.TypeSingleAst([
        Ast.GenericIdentifierAst("std", [], ast.identifier._tok),
        Ast.GenericIdentifierAst("FnRef", [return_type, param_types], ast.identifier._tok)], ast.identifier._tok)

def convert_module_name_to_file_name(ast: Ast.ModuleIdentifierAst | Ast.ImportIdentifierAst) -> str:
    return "/".join(map(lambda x: x.identifier, ast.parts))

def convert_convention_to_string(ast: Ast.ParameterPassingConventionReferenceAst) -> str:
    if not ast: return "one"
    if ast.is_mutable: return "mut"
    return "ref"

def normalize_type(ast: Ast.TypeAst) -> Ast.TypeAst:
    # For a tuple type, check that each type in the tuple is a valid type, by recursively calling this function.
    # Return the same ast back out, as the inference of a type node is the same as the type node itself.
    if isinstance(ast, Ast.TypeTupleAst):
        for i, type in enumerate(ast.types):
            ast.types[i] = normalize_type(type)
        return ast

    # Infer the "Self" keyword to the current class type. This is done by moving up the scopes until the current
    # scope is the class scope, and then getting the type of the class.
    if isinstance(ast.parts[0], Ast.SelfTypeAst):
        enclosing_type = CURRENT_MODULE_MEMBER
        if not enclosing_type:
            raise SystemExit(ErrFmt.err(ast._tok) + f"Cannot use 'Self' outside of a class.")

        # Change the "Self" to the actual class name. The "Self" is only able to be the first part of a type, so
        # only "ast.part[0]" has to be inspected and changed.
        ast.parts = ast.parts[1:]
        for p in reversed(enclosing_type.parts):
            ast.parts.insert(0, p)

    return ast

def function_identifier_strip_signature(identifier: str, string_ref: bool = False) -> str:
    stripped = identifier.replace("#", "(").replace(",", ", ") + ")"
    if not string_ref:
        stripped = re.sub(r"(one|ref|mut)\|", "", stripped)
    else:
        while True:
            if "one|" in stripped:
                stripped = stripped.replace("one|", "")
            elif "ref|" in stripped:
                stripped = stripped.replace("ref|", "&")
            elif "mut|" in stripped:
                stripped = stripped.replace("mut|", "&mut ")
            elif "???" in stripped:
                stripped = stripped.replace("???|", "[infer]")
            else:
                break
    return stripped
