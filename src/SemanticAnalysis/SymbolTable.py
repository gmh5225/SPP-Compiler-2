"""
Construct symbol tables for each scope in the program, including the global scope.
"""

from __future__ import annotations
from typing import Generic, Optional, TypeVar
import inflection
import inspect

from src.SyntacticAnalysis import Ast
from src.SemanticAnalysis.TypeInference import TypeInference


T = TypeVar('T')


class SymbolName(Generic[T]):
    _module_name: Ast.ModuleIdentifierAst
    _symbol_name: T

    def __init__(self, symbol_name: T, module_name: Ast.ModuleIdentifierAst = None):
        self._module_name = module_name or Ast.ModuleIdentifierAst([])
        self._symbol_name = symbol_name

    def __eq__(self, that):
        return self._module_name == that.module_name and self._symbol_name == that.symbol_name

    @property
    def module_name(self) -> Ast.ModuleIdentifierAst:
        return self._module_name

    @property
    def symbol_name(self) -> T:
        return self._symbol_name

    def __repr__(self):
        mod = f"{'::'.join([p.identifier for p in self._module_name.parts])}::"
        var = f"{self._symbol_name.identifier if self._symbol_name else ''}"
        return f"{mod}{var}" if mod != "::" else f"{var}"

    def __hash__(self):
        return hash(self.__repr__())


class SymbolType:
    _type: Ast.TypeAst
    _deferred: bool = False

    def __init__(self, type_: Ast.TypeAst):
        self._type = type_

    @staticmethod
    def deferred(func: callable) -> SymbolType:
        return SymbolType(func)

    def load_deferred(self):
        self._type = self._type()

    @property
    def type(self) -> Ast.TypeAst:
        return self._type

    def __repr__(self):
        match self._type:
            case Ast.TypeSingleAst(): return f"{'::'.join([p.identifier for p in self._type.parts])}"
            case Ast.TypeTupleAst(): return f"({','.join([repr(p) for p in self._type.parts])})"
            case Ast.TypeGenericParameterAst(): return f"{self._type.identifier}"
            case None: return f"None [ERR]"
            case _: raise NotImplementedError(f"Type {self._type} not implemented")


class Symbol(Generic[T]):
    _name: SymbolName[T]
    _type: SymbolType

    def __init__(self, name: SymbolName[T], type: Optional[SymbolType]):
        self._name = name
        self._type = type

    @property
    def name(self) -> SymbolName[T]:
        return self._name

    @property
    def type(self) -> SymbolType:
        return self._type

    def json(self):
        return {repr(self._name): repr(self._type)}


class SymbolTable(Generic[T]):
    _symbols: dict[SymbolName[T], Symbol]

    def __init__(self):
        self._symbols = {}

    def define(self, symbol: Symbol):
        self._symbols[symbol.name] = symbol

    def lookup(self, name: SymbolName[T]) -> Optional[Symbol]:
        return self._symbols.get(name)

    def json(self):
        d = {}
        for k, v in self._symbols.items():
            d[repr(k)] = repr(v.type)
        return d


class Scope:
    _name: str

    _symbol_table: SymbolTable[Ast.IdentifierAst]
    _type_table: SymbolTable[Ast.TypeAst]
    _tag_table: SymbolTable[Ast.TagIdentifierAst]

    _parent_scope: Optional[Scope]
    _child_scopes: list[Scope]

    def __init__(self, parent_scope: Optional[Scope] = None):
        self._name = inflection.camelize(inspect.stack()[2].function[1:])

        self._symbol_table = SymbolTable()
        self._type_table = SymbolTable()
        self._tag_table = SymbolTable()

        self._parent_scope = parent_scope
        self._child_scopes = []
        self._parent_scope._child_scopes.append(self) if self._parent_scope is not None else None

    def define_symbol(self, symbol: Symbol):
        self._symbol_table.define(symbol)

    def define_type(self, symbol: Symbol):
        self._type_table.define(symbol)

    def define_tag(self, symbol: Symbol):
        self._tag_table.define(symbol)

    def lookup_symbol(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._symbol_table.lookup(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup_symbol(name)
        return None

    def lookup_type(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._type_table.lookup(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup_type(name)
        return None

    def lookup_tag(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        symbol = self._tag_table.lookup(name)
        if symbol is not None: return symbol
        if current_scope_only: return None
        if self._parent_scope is not None: return self._parent_scope.lookup_tag(name)
        return None

    @property
    def parent_scope(self) -> Optional[Scope]:
        return self._parent_scope

    def json(self):
        return {
            "Name": self._name,
            "Symbols": self._symbol_table.json(),
            "Types": self._type_table.json(),
            "Tags": self._tag_table.json(),
            "ChildScopes": [s.json() for s in self._child_scopes]
        }


class GlobalScope(Scope):
    _module_name: Ast.ModuleIdentifierAst

    def __init__(self, module_name: Ast.ModuleIdentifierAst):
        Scope.__init__(self)
        self._module_name = module_name

    @property
    def module_name(self) -> Ast.ModuleIdentifierAst:
        return self._module_name


class ScopeManager:
    _global_scope: GlobalScope
    _current_scope: Scope

    def __init__(self, module_name: Ast.ModuleIdentifierAst):
        self._global_scope = GlobalScope(module_name)
        self._current_scope = self._global_scope

    def define_symbol(self, symbol: Symbol):
        self._current_scope.define_symbol(symbol)

    def define_type(self, symbol: Symbol):
        self._current_scope.define_type(symbol)

    def define_tag(self, symbol: Symbol):
        self._current_scope.define_tag(symbol)

    def lookup_symbol(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        return self._current_scope.lookup_symbol(name, current_scope_only)

    def lookup_type(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        return self._current_scope.lookup_type(name, current_scope_only)

    def lookup_tag(self, name: SymbolName, current_scope_only=False) -> Optional[Symbol]:
        return self._current_scope.lookup_tag(name, current_scope_only)

    def enter_scope(self):
        self._current_scope = Scope(self._current_scope)

    def exit_scope(self):
        self._current_scope = self._current_scope.parent_scope

    @property
    def current_scope(self) -> Scope:
        return self._current_scope

    @property
    def global_scope(self) -> GlobalScope:
        return self._global_scope

    def json(self):
        return self._global_scope.json()


class SymbolTableBuilder:
    @staticmethod
    def build_program(ast: Ast.ProgramAst, s: ScopeManager) -> None:
        # Build symbols for each member of the module. These will be in the global namespace of this module, and
        # contains the symbols for the functions (objects of type std::Fn), the type definitions for the class
        # definitions, and the type definitions for the enum definitions. The methods and typedefs defined in the
        # super-impositions are shifted to the global namespace, because the "self" parameter has to be used by the
        # correct class anyway. Access modifiers are handled separately - this is just about verifying all the symbols
        # have been defined.
        for member in ast.module.body.members: SymbolTableBuilder._build_module_member(member, s)
        SymbolTableBuilder._load_all_deferred_types(s)

    @staticmethod
    def _load_all_deferred_types(s: ScopeManager) -> None:
        # Load all the deferred types. This is done after all the symbols have been defined, so that the types can be
        # resolved correctly.
        ...

    @staticmethod
    def _build_module_member(ast: Ast.ModuleMemberAst, s: ScopeManager) -> None:
        # Check what module member this is, and call the appropriate function to build the symbol for it. Simple match-
        # case statement to determine the function to call.
        match ast:
            case Ast.FunctionPrototypeAst(): SymbolTableBuilder._build_function_prototype(ast, s)
            case Ast.ClassPrototypeAst(): SymbolTableBuilder._build_class_prototype(ast, s)
            case Ast.EnumPrototypeAst(): SymbolTableBuilder._build_enum_prototype(ast, s)
            case Ast.SupPrototypeNormalAst(): SymbolTableBuilder._build_sup_prototype_normal(ast, s)
            case Ast.SupPrototypeInheritanceAst(): raise NotImplementedError("Super-imposition inheritance not implemented")
            case _: raise NotImplementedError(f"Unknown module member type: {ast}")

    @staticmethod
    def _build_function_prototype(ast: Ast.FunctionPrototypeAst, s: ScopeManager) -> None:
        # Define the function as an object in the current scope, as it needs to be accessible from whatever scope it
        # was defined in.
        s.define_symbol(Symbol(SymbolName(ast.identifier, s.global_scope.module_name), SymbolType(Utils.extract_function_type(ast))))

        # Enter a new scope for the function, and build the symbols for the parameters. Register the type parameters,
        # which can be different per function call. However, their tue type is irrelevant at this point, as this stage
        # only verifies that the type exists, ie register the generics as valid type names. Folllow with building'
        # symbols for each statement in the function body.
        s.enter_scope()
        for parameter in ast.parameters: SymbolTableBuilder._build_function_parameter(parameter, s)
        for generic_p in ast.generic_parameters: SymbolTableBuilder._build_generic_parameter(generic_p, s)
        for statement in ast.body.statements: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_function_parameter(ast: Ast.FunctionParameterAst, s: ScopeManager) -> None:
        # Define the parameter as a symbol in the current scope, as the function prototype will have opened the scope
        # for everything to e defined in it.
        s.define_symbol(Symbol(SymbolName(ast.identifier), SymbolType(ast.type_annotation)))

    @staticmethod
    def _build_generic_parameter(ast: Ast.TypeGenericParameterAst, s: ScopeManager) -> None:
        # Define the generic parameter as a type in the current scope, as the function prototype will have opened the
        # scope for everything to be defined in it.
        s.define_type(Symbol(SymbolName(ast.identifier), SymbolType(ast)))

    @staticmethod
    def _build_statement(ast: Ast.StatementAst, s: ScopeManager) -> None:
        # Check what statement this is, and call the appropriate function to build the symbol for it. Simple match-
        # case statement to determine the function to call. Return, Yield and Expression statements cannot define any
        # new symbols, so they are ignored (this stage just builds the symbols, the checking every symbol used is in the
        # next stage).
        match ast:
            case Ast.IfStatementAst(): SymbolTableBuilder._build_if_statement(ast, s)
            case Ast.WhileStatementAst(): SymbolTableBuilder._build_while_statement(ast, s)
            case Ast.ForStatementAst(): SymbolTableBuilder._build_for_statement(ast, s)
            case Ast.DoWhileStatementAst(): SymbolTableBuilder._build_do_while_statement(ast, s)
            case Ast.MatchStatementAst(): SymbolTableBuilder._build_match_statement(ast, s)
            case Ast.WithStatementAst(): SymbolTableBuilder._build_with_statement(ast, s)
            case Ast.ReturnStatementAst(): pass
            case Ast.YieldStatementAst(): pass
            case Ast.TypedefStatementAst(): SymbolTableBuilder._build_typedef_statement(ast, s)
            case Ast.LetStatementAst(): SymbolTableBuilder._build_let_statement(ast, s)
            case True if type(ast) in Ast.ExpressionAst.__args__: pass
            case _: raise NotImplementedError(f"Unknown statement type: {ast}")

    @staticmethod
    def _build_if_statement(ast: Ast.IfStatementAst, s: ScopeManager) -> None:
        # new scope isn't needed from a symbol table perspective, but is easier to contain the cases in one scope for
        # future ideas like an all-branch scope sort of thing.
        s.enter_scope()
        SymbolTableBuilder._build_if_branch(ast.if_branch, s)
        for elif_branch in ast.elif_branches: SymbolTableBuilder._build_if_branch(elif_branch, s)
        if ast.else_branch is not None: SymbolTableBuilder._build_if_branch(ast.else_branch, s)
        s.exit_scope()

    @staticmethod
    def _build_if_branch(ast: Ast.IfStatementBranchAst, s: ScopeManager) -> None:
        for inline_definition in ast.definitions: SymbolTableBuilder._build_let_statement(inline_definition, s)
        s.enter_scope()
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_while_statement(ast: Ast.WhileStatementAst, s: ScopeManager) -> None:
        s.enter_scope()
        s.define_tag(Symbol(SymbolName(ast.tag), None))
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_for_statement(ast: Ast.ForStatementAst, s: ScopeManager) -> None:
        s.enter_scope()
        s.define_tag(Symbol(SymbolName(ast.tag), None))
        iterable_type = iter([None] * 20) # TODO : iter(lambda: TypeInference.infer_type(ast.iterable, s)[0].types)
        for identifier in ast.identifiers: s.define_symbol(Symbol(SymbolName(identifier.identifier), next(iterable_type)))
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_do_while_statement(ast: Ast.DoWhileStatementAst, s: ScopeManager) -> None:
        s.enter_scope()
        s.define_tag(Symbol(SymbolName(ast.tag), None))
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_match_statement(ast: Ast.MatchStatementAst, s: ScopeManager) -> None:
        # new scope isn't needed from a symbol table perspective, but is easier to contain the cases in one scope for
        # future ideas like an all-case scope sort of thing.
        s.enter_scope()
        for case in ast.cases: SymbolTableBuilder._build_case_statement(case, s)
        s.exit_scope()

    @staticmethod
    def _build_case_statement(ast: Ast.CaseStatementAst, s: ScopeManager) -> None:
        s.enter_scope()
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_with_statement(ast: Ast.WithStatementAst, s: ScopeManager) -> None:
        s.enter_scope()
        if ast.alias: s.define_symbol(Symbol(SymbolName(ast.alias), SymbolType.deferred(lambda: TypeInference.infer_type(ast.value, s))))
        for statement in ast.body: SymbolTableBuilder._build_statement(statement, s)
        s.exit_scope()

    @staticmethod
    def _build_typedef_statement(ast: Ast.TypedefStatementAst, s: ScopeManager) -> None:
        s.define_type(Symbol(SymbolName(ast.new_type), SymbolType(ast.old_type)))

    @staticmethod
    def _build_let_statement(ast: Ast.LetStatementAst, s: ScopeManager) -> None:
        if len(ast.variables) > 1: assert ast.type_annotation or type(lambda: TypeInference.infer_type(ast.value, s)) == Ast.TypeTupleAst
        if ast.type_annotation:
            for variable in ast.variables: s.define_symbol(Symbol(SymbolName(variable.identifier), SymbolType(ast.type_annotation)))
        else:
            type_annotation = TypeInference.infer_type(ast.value, s)
            if type(type_annotation) == Ast.TypeTupleAst: type_annotation = iter(type_annotation.types)
            else: type_annotation = iter([type_annotation])

            for variable in ast.variables:
                s.define_symbol(Symbol(SymbolName(variable.identifier), SymbolType(next(type_annotation))))

    @staticmethod
    def _build_class_prototype(ast: Ast.ClassPrototypeAst, s: ScopeManager) -> None:
        s.define_type(Symbol(SymbolName(ast.identifier), SymbolType(Utils.extract_class_type(ast))))
        s.enter_scope()
        for attr in ast.body.members:
            s.define_symbol(Symbol(SymbolName(attr.identifier), SymbolType(attr.type_annotation)))

    @staticmethod
    def _build_enum_prototype(ast: Ast.EnumPrototypeAst, s: ScopeManager) -> None:
        s.define_type(Symbol(SymbolName(ast.identifier), SymbolType(ast)))
        s.enter_scope()
        for attr in ast.body.members:
            s.define_symbol(Symbol(SymbolName(attr.identifier), SymbolType.deferred(lambda: TypeInference.infer_type(attr.value, s))))
        s.exit_scope()

    @staticmethod
    def _build_sup_prototype_normal(ast: Ast.SupPrototypeNormalAst, s: ScopeManager) -> None:
        # The methods can be registered to the global symbol table, because calling a.b(c, d) is the same as calling
        # b(a, c, d) -- it's just the first argumentt hat is automatically passed in, whose type is enclosing class. The
        # typedefs are registered against the class's type table, because they are only accessible from within the class
        # itself.
        for member in ast.body.members: SymbolTableBuilder._build_sup_member(member, s)

    @staticmethod
    def _build_sup_member(ast: Ast.SupMemberAst, s: ScopeManager) -> None:
        match ast:
            case Ast.SupMethodPrototypeAst(): raise NotImplementedError(f"Sup method {ast} not implemented")
            case Ast.SupTypedefAst(): raise NotImplementedError(f"Sup typedef {ast} not implemented")
            case _: raise NotImplementedError(f"Sup member {ast} not implemented")


class Utils:
    @staticmethod
    def extract_function_type(ast: Ast.FunctionPrototypeAst) -> Ast.TypeAst:
        param_types = Ast.TypeTupleAst([param.type_annotation for param in ast.parameters])
        return_type = ast.return_type # if ast.return_type else Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("None", [])])
        return Ast.TypeSingleAst([Ast.GenericIdentifierAst("std", []), Ast.GenericIdentifierAst("Fn", [return_type, param_types])])

    @staticmethod
    def extract_class_type(ast: Ast.ClassPrototypeAst) -> Ast.TypeAst:
        t = Ast.TypeSingleAst([Ast.GenericIdentifierAst(ast.identifier.identifier, [Utils.generic_parameter_to_argument(p) for p in ast.generic_parameters])])

    @staticmethod
    def generic_parameter_to_argument(ast: Ast.TypeGenericParameterAst) -> Ast.TypeGenericArgumentAst:
        return Ast.TypeGenericArgumentAst(ast.identifier, None)  # todo
