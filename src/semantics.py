# src/semantics.py
# Semantic Analyzer & Strict Borrow Checker for Katlin

from typing import Dict, List, Set, Optional, Any
from src.ast_nodes import (
    Program, FunctionDef, Parameter, VarDecl, AssignStmt, ReturnStmt,
    PrintStmt, CallExpr, ChainedCall, IfStmt, WhileStmt, LoopStmt, ForStmt,
    RawBlock, BinaryOp, UnaryOp, Literal, Identifier, ExprStmt, IndexAssign, IndexExpr,
    StructField, StructDef, StructInit, MemberAccess, EnumDef, OrExpr, MatchBranch, MatchStmt, TestBlock, ASTNode
)

from src.diagnostics import KatlinSemanticError

class SemanticError(KatlinSemanticError):
    pass

class Scope:
    def __init__(self, parent: Optional['Scope'] = None):
        self.parent = parent
        self.symbols: Dict[str, str] = {} # name -> type
        self.mutables: Set[str] = set()

    def define(self, name: str, type_name: str, is_mutable: bool = False):
        self.symbols[name] = type_name
        if is_mutable:
            self.mutables.add(name)

    def lookup(self, name: str) -> Optional[str]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def is_mutable(self, name: str) -> bool:
        if name in self.mutables:
            return True
        if self.parent:
            return self.parent.is_mutable(name)
        return False

class SemanticAnalyzer:
    def __init__(self, program: Program, file_strict: bool = False):
        self.program = program
        self.file_strict = file_strict
        self.structs: Dict[str, StructDef] = {}
        self.enums: Dict[str, EnumDef] = {}
        self.functions: Dict[str, FunctionDef] = {}
        self.current_scope = Scope()

    def analyze(self):
        # Pass 1: Collect declarations
        for stmt in self.program.statements:
            if isinstance(stmt, StructDef):
                self.structs[stmt.name] = stmt
            elif isinstance(stmt, EnumDef):
                self.enums[stmt.name] = stmt
            elif isinstance(stmt, FunctionDef):
                self.functions[stmt.name] = stmt

        # Pass 2: Analyze functions and statements
        for stmt in self.program.statements:
            if isinstance(stmt, FunctionDef):
                self.analyze_function(stmt)
            elif isinstance(stmt, TestBlock):
                self.analyze_test(stmt)

    def analyze_function(self, func: FunctionDef):
        func_strict = self.file_strict or func.is_strict
        local_scope = Scope(self.current_scope)
        old_scope = self.current_scope
        self.current_scope = local_scope

        # Register parameters
        for p in func.params:
            self.current_scope.define(p.name, p.type_name, is_mutable=p.is_ref)

        # Analyze body
        for stmt in func.body:
            self.analyze_statement(stmt, is_strict=func_strict)

        self.current_scope = old_scope

    def analyze_test(self, test: TestBlock):
        test_scope = Scope(self.current_scope)
        old_scope = self.current_scope
        self.current_scope = test_scope

        for stmt in test.body:
            self.analyze_statement(stmt, is_strict=False)

        self.current_scope = old_scope

    def analyze_statement(self, stmt: ASTNode, is_strict: bool = False):
        if isinstance(stmt, VarDecl):
            self.current_scope.define(stmt.name, stmt.type_name or "int", is_mutable=stmt.is_mutable)
            if stmt.value:
                self.analyze_expr(stmt.value, is_strict)

        elif isinstance(stmt, AssignStmt):
            self.analyze_expr(stmt.value, is_strict)

        elif isinstance(stmt, IndexAssign):
            self.analyze_expr(stmt.index, is_strict)
            self.analyze_expr(stmt.value, is_strict)

        elif isinstance(stmt, IfStmt):
            self.analyze_expr(stmt.condition, is_strict)
            for s in stmt.then_body: self.analyze_statement(s, is_strict)
            for cond, body in stmt.elif_branches:
                self.analyze_expr(cond, is_strict)
                for s in body: self.analyze_statement(s, is_strict)
            for s in stmt.else_body: self.analyze_statement(s, is_strict)

        elif isinstance(stmt, WhileStmt):
            self.analyze_expr(stmt.condition, is_strict)
            for s in stmt.body: self.analyze_statement(s, is_strict)

        elif isinstance(stmt, ForStmt):
            self.current_scope.define(stmt.var_name, "int", is_mutable=stmt.is_ref)
            self.analyze_expr(stmt.range_start, is_strict)
            self.analyze_expr(stmt.range_end, is_strict)
            if stmt.step: self.analyze_expr(stmt.step, is_strict)
            for s in stmt.body: self.analyze_statement(s, is_strict)

        elif isinstance(stmt, MatchStmt):
            self.analyze_expr(stmt.subject, is_strict)
            for b in stmt.branches:
                for s in b.body: self.analyze_statement(s, is_strict)

        elif isinstance(stmt, ExprStmt):
            self.analyze_expr(stmt.expr, is_strict)

        elif isinstance(stmt, PrintStmt):
            for a in stmt.args: self.analyze_expr(a, is_strict)

    def analyze_expr(self, expr: Optional[ASTNode], is_strict: bool = False):
        if not expr: return

        if isinstance(expr, CallExpr):
            # Check for borrow aliasing in #strict mode!
            if is_strict:
                self.check_borrow_aliasing(expr)

            for a in expr.args:
                self.analyze_expr(a, is_strict)

        elif isinstance(expr, BinaryOp):
            self.analyze_expr(expr.left, is_strict)
            self.analyze_expr(expr.right, is_strict)

        elif isinstance(expr, UnaryOp):
            self.analyze_expr(expr.operand, is_strict)

        elif isinstance(expr, OrExpr):
            self.analyze_expr(expr.left, is_strict)
            if expr.fallback_expr:
                self.analyze_expr(expr.fallback_expr, is_strict)

    def check_borrow_aliasing(self, call: CallExpr):
        # In strict mode: verify no two arguments borrow the same variable as mutable simultaneously
        borrowed_mutables: Dict[str, Tuple[int, int, int]] = {} # var_name -> (line, col, len)
        target_func = self.functions.get(call.callee)

        if target_func:
            for i, arg in enumerate(call.args):
                if i < len(target_func.params):
                    param = target_func.params[i]
                    if param.is_ref:
                        var_name = None
                        arg_line = arg.line
                        arg_col = arg.col
                        arg_len = 1
                        if isinstance(arg, Identifier):
                            var_name = arg.name
                            arg_len = len(var_name)
                        elif isinstance(arg, UnaryOp) and arg.op == "&" and isinstance(arg.operand, Identifier):
                            var_name = arg.operand.name
                            arg_len = len(var_name) + 1
                        
                        if var_name:
                            if var_name in borrowed_mutables:
                                first_line, first_col, first_len = borrowed_mutables[var_name]
                                raise SemanticError(
                                    f"cannot borrow `{var_name}` as mutable more than once simultaneously in call to `{call.callee}`",
                                    line=arg_line if arg_line else call.line,
                                    col=arg_col if arg_col else call.col,
                                    length=arg_len,
                                    note="in #strict mode, aliased mutable references (&) are forbidden to prevent data races",
                                    help_text="pass separate variables or remove one of the mutable borrows",
                                    secondary_spans=[(first_line, first_col, first_len, "first mutable borrow occurs here")]
                                )
                            borrowed_mutables[var_name] = (arg_line, arg_col, arg_len)
