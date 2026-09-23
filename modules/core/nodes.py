from dataclasses import dataclass, field


@dataclass
class Node:
    line: int = 0
    col: int = 0


@dataclass
class Comment(Node):
    value: str = ""
    multi_line: bool = False


@dataclass
class VarDecl(Node):
    name: str = ""
    name_col: int = 0
    value: str = ""
    value_col: int = 0
    value_type: str = ""
    is_pub: bool = False
    is_local: bool = False
    is_ref: bool = False


@dataclass
class OutStmt(Node):
    values: list[str] = field(default_factory=list)
    val_cols: list[int] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    refs: list[bool] = field(default_factory=list)


@dataclass
class RunStmt(Node):
    executable: str = ""
    args: list[str] = field(default_factory=list)
    arg_cols: list[int] = field(default_factory=list)
    arg_is_ref: list[bool] = field(default_factory=list)


@dataclass
class MethodDef(Node):
    name: str = ""
    args: list[str] = field(default_factory=list)
    body: list = field(default_factory=list)


@dataclass
class FuncDef(Node):
    name: str = ""
    args: list[str] = field(default_factory=list)
    body: list = field(default_factory=list)
    is_pub: bool = False


@dataclass
class ClassDef(Node):
    name: str = ""
    methods: list[MethodDef] = field(default_factory=list)
    fields: list[VarDecl] = field(default_factory=list)


@dataclass
class CondExpr(Node):
    left: str = ""
    left_col: int = 0
    left_is_ref: bool = False
    op: str | None = None
    right: str | None = None
    right_col: int = 0
    right_is_ref: bool = False


@dataclass
class IfBranch(Node):
    condition: CondExpr = field(default_factory=CondExpr)
    body: list = field(default_factory=list)


@dataclass
class IfStmt(Node):
    then_branch: IfBranch = field(default_factory=IfBranch)
    elif_branches: list[IfBranch] = field(default_factory=list)
    else_body: list = field(default_factory=list)


@dataclass
class ForInStmt(Node):
    var_name: str = ""
    var_col: int = 0
    is_decl: bool = False
    is_local: bool = False
    items: list[str] = field(default_factory=list)
    item_cols: list[int] = field(default_factory=list)
    item_is_ref: list[bool] = field(default_factory=list)
    body: list = field(default_factory=list)


@dataclass
class ForCStyleStmt(Node):
    init: VarDecl = field(default_factory=VarDecl)
    condition: CondExpr = field(default_factory=CondExpr)
    step_var: str = ""
    step_expr: str = ""
    body: list = field(default_factory=list)
