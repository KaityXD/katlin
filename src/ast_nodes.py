# src/ast_nodes.py
# Abstract Syntax Tree nodes for Katlin

from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple

@dataclass
class ASTNode:
    line: int = 0
    col: int = 0

@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

@dataclass
class Parameter(ASTNode):
    name: str = ""
    type_name: str = "int"
    default_value: Optional[Any] = None
    is_ref: bool = False

@dataclass
class FunctionDef(ASTNode):
    name: str = ""
    params: List[Parameter] = field(default_factory=list)
    return_type: Optional[str] = None
    body: List[ASTNode] = field(default_factory=list)
    inner_functions: List['FunctionDef'] = field(default_factory=list)
    is_strict: bool = False

@dataclass
class VarDecl(ASTNode):
    name: str = ""
    type_name: Optional[str] = None
    value: Optional[ASTNode] = None
    is_mutable: bool = False
    is_inferred: bool = False  # True for ':='

@dataclass
class AssignStmt(ASTNode):
    target: str = ""
    op: str = "="  # '=', '+=', '-=', etc.
    value: Optional[ASTNode] = None

@dataclass
class IndexAssign(ASTNode):
    target: str = ""
    index: Optional[ASTNode] = None
    op: str = "="
    value: Optional[ASTNode] = None

@dataclass
class IndexExpr(ASTNode):
    target: Optional[ASTNode] = None
    index: Optional[ASTNode] = None

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode] = None
    guard_condition: Optional[ASTNode] = None  # for 'return if condition'

@dataclass
class PrintStmt(ASTNode):
    format_str: str = ""
    args: List[ASTNode] = field(default_factory=list)
    is_newline: bool = True

@dataclass
class CallExpr(ASTNode):
    callee: str = ""
    args: List[ASTNode] = field(default_factory=list)
    named_args: List[Tuple[str, ASTNode]] = field(default_factory=list)

@dataclass
class ChainedCall(ASTNode):
    base_call: CallExpr = field(default_factory=CallExpr)
    chain: List[CallExpr] = field(default_factory=list)

@dataclass
class IfStmt(ASTNode):
    condition: Optional[ASTNode] = None
    then_body: List[ASTNode] = field(default_factory=list)
    elif_branches: List[Tuple[ASTNode, List[ASTNode]]] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)

@dataclass
class WhileStmt(ASTNode):
    condition: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class LoopStmt(ASTNode):
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ForStmt(ASTNode):
    var_name: str = ""
    is_ref: bool = False
    range_start: Optional[ASTNode] = None
    range_end: Optional[ASTNode] = None
    step: Optional[ASTNode] = None
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class RawBlock(ASTNode):
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class BinaryOp(ASTNode):
    left: Optional[ASTNode] = None
    op: str = ""
    right: Optional[ASTNode] = None

@dataclass
class UnaryOp(ASTNode):
    op: str = ""
    operand: Optional[ASTNode] = None

@dataclass
class Literal(ASTNode):
    value: Any = None
    lit_type: str = "int"  # 'int', 'float', 'str', 'bool'

@dataclass
class Identifier(ASTNode):
    name: str = ""

@dataclass
class ExprStmt(ASTNode):
    expr: Optional[ASTNode] = None

@dataclass
class StructField(ASTNode):
    name: str = ""
    type_name: str = "int"
    default_value: Optional[ASTNode] = None
    is_ref: bool = False

@dataclass
class StructDef(ASTNode):
    name: str = ""
    fields: List[StructField] = field(default_factory=list)

@dataclass
class StructInit(ASTNode):
    struct_name: str = ""
    fields: List[Tuple[str, ASTNode]] = field(default_factory=list)

@dataclass
class MemberAccess(ASTNode):
    target: Optional[ASTNode] = None
    member: str = ""

@dataclass
class EnumDef(ASTNode):
    name: str = ""
    variants: List[str] = field(default_factory=list)

@dataclass
class OrExpr(ASTNode):
    left: Optional[ASTNode] = None
    fallback_expr: Optional[ASTNode] = None
    is_return: bool = False
    is_panic: bool = False
    panic_msg: str = ""

@dataclass
class MatchBranch(ASTNode):
    pattern: str = "" # e.g. '.idle' or '1' or '_'
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class MatchStmt(ASTNode):
    subject: Optional[ASTNode] = None
    branches: List[MatchBranch] = field(default_factory=list)

@dataclass
class TestBlock(ASTNode):
    name: str = ""
    body: List[ASTNode] = field(default_factory=list)
