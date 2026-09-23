import re
from modules.core.nodes import (
    VarDecl,
    OutStmt,
    RunStmt,
    FuncDef,
    ClassDef,
    Comment,
    CondExpr,
    IfStmt,
    ForInStmt,
    ForCStyleStmt,
)


class DSLVibeError(Exception):
    def __init__(self, message, line, col, file_path, code):
        self.message = message
        self.line = line
        self.col = col
        self.file_path = file_path
        self.code = code

    def __str__(self):
        lines = self.code.split("\n")
        line_idx = self.line - 1
        col_idx = self.col - 1

        error_msg = [
            f"Error: {self.message} on line {self.line}",
            f"Location: {self.file_path}:{self.line}:{self.col}",
            "\nContext:",
        ]

        if line_idx > 0:
            error_msg.append(f"| {self.line - 1} {lines[line_idx - 1]}")

        actual_line = lines[line_idx]
        error_msg.append(f"| {self.line} {actual_line}")

        prefix = f"| {self.line} "
        pointer = " " * (len(prefix) + col_idx - 1) + "^~~~~~"
        error_msg.append(pointer)

        if line_idx < len(lines) - 1:
            error_msg.append(f"| {self.line + 1} {lines[line_idx + 1]}")

        return "\n".join(error_msg)


class TypeChecker:
    def __init__(self, file_path, code):
        self.scopes = [{}]
        self.file_path = file_path
        self.code = code

    def current_scope(self):
        return self.scopes[-1]

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def check_condition(self, cond: CondExpr):
        if cond.left_is_ref:
            if not self.lookup(cond.left):
                raise DSLVibeError(
                    f"undefined token '{cond.left}'",
                    cond.line,
                    cond.left_col,
                    self.file_path,
                    self.code,
                )
        if cond.right_is_ref:
            if not self.lookup(cond.right):
                raise DSLVibeError(
                    f"undefined token '{cond.right}'",
                    cond.line,
                    cond.right_col,
                    self.file_path,
                    self.code,
                )

    def check(self, nodes):
        for node in nodes:
            if isinstance(node, Comment):
                continue

            if isinstance(node, VarDecl):
                if self.lookup(node.name):
                    raise DSLVibeError(
                        f"duplicate definition of '{node.name}'",
                        node.line,
                        node.name_col,
                        self.file_path,
                        self.code,
                    )
                if node.is_ref:
                    if not self.lookup(node.value):
                        raise DSLVibeError(
                            f"undefined token '{node.value}'",
                            node.line,
                            node.value_col,
                            self.file_path,
                            self.code,
                        )
                self.current_scope()[node.name] = "VAR"

            elif isinstance(node, OutStmt):
                for val, col, is_ref in zip(node.values, node.val_cols, node.refs):
                    if is_ref and not self.lookup(val):
                        raise DSLVibeError(
                            f"undefined token '{val}'",
                            node.line,
                            col,
                            self.file_path,
                            self.code,
                        )

            elif isinstance(node, RunStmt):
                if ":" not in node.executable:
                    if not self.lookup(node.executable):
                        raise DSLVibeError(
                            f"undefined token '{node.executable}' "
                            "(use 'run' for system commands)",
                            node.line,
                            node.col,
                            self.file_path,
                            self.code,
                        )

                if node.arg_is_ref:
                    for arg, col, is_ref in zip(
                        node.args, node.arg_cols, node.arg_is_ref
                    ):
                        if is_ref and not self.lookup(arg):
                            raise DSLVibeError(
                                f"undefined token '{arg}'",
                                node.line,
                                col,
                                self.file_path,
                                self.code,
                            )

            elif isinstance(node, FuncDef):
                if self.lookup(node.name):
                    raise DSLVibeError(
                        f"duplicate definition of function '{node.name}'",
                        node.line,
                        node.col,
                        self.file_path,
                        self.code,
                    )
                self.current_scope()[node.name] = "FUNC"

                new_scope = {arg: "VAR" for arg in node.args}
                self.scopes.append(new_scope)
                self.check(node.body)
                self.scopes.pop()

            elif isinstance(node, ClassDef):
                if self.lookup(node.name):
                    raise DSLVibeError(
                        f"duplicate definition of class '{node.name}'",
                        node.line,
                        node.col,
                        self.file_path,
                        self.code,
                    )
                self.current_scope()[node.name] = "CLASS"

                class_scope = {f.name: "VAR" for f in node.fields}
                self.scopes.append(class_scope)
                for method in node.methods:
                    method_scope = {arg: "VAR" for arg in method.args}
                    self.scopes.append({**self.current_scope(), **method_scope})
                    self.check(method.body)
                    self.scopes.pop()
                self.scopes.pop()

            elif isinstance(node, IfStmt):
                self.check_condition(node.then_branch.condition)
                self.scopes.append({})
                self.check(node.then_branch.body)
                self.scopes.pop()

                for elif_branch in node.elif_branches:
                    self.check_condition(elif_branch.condition)
                    self.scopes.append({})
                    self.check(elif_branch.body)
                    self.scopes.pop()

                if node.else_body:
                    self.scopes.append({})
                    self.check(node.else_body)
                    self.scopes.pop()

            elif isinstance(node, ForInStmt):
                if node.is_decl:
                    if self.lookup(node.var_name):
                        raise DSLVibeError(
                            f"duplicate definition of '{node.var_name}'",
                            node.line,
                            node.var_col,
                            self.file_path,
                            self.code,
                        )
                else:
                    if not self.lookup(node.var_name):
                        raise DSLVibeError(
                            f"undefined token '{node.var_name}'",
                            node.line,
                            node.var_col,
                            self.file_path,
                            self.code,
                        )

                for val, col, is_ref in zip(node.items, node.item_cols, node.item_is_ref):
                    if is_ref and not self.lookup(val):
                        raise DSLVibeError(
                            f"undefined token '{val}'",
                            node.line,
                            col,
                            self.file_path,
                            self.code,
                        )

                loop_scope = {node.var_name: "VAR"}
                self.scopes.append(loop_scope)
                self.check(node.body)
                self.scopes.pop()

            elif isinstance(node, ForCStyleStmt):
                self.scopes.append({})
                self.check([node.init])
                self.check_condition(node.condition)

                tokens = re.findall(r"[a-zA-Z_]\w*", node.step_expr)
                for tok in tokens:
                    if not self.lookup(tok):
                        raise DSLVibeError(
                            f"undefined token '{tok}'",
                            node.line,
                            node.col,
                            self.file_path,
                            self.code,
                        )

                self.check(node.body)
                self.scopes.pop()
