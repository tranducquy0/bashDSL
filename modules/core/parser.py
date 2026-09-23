from modules.core.lexer import Token
from modules.core.nodes import (
    VarDecl,
    OutStmt,
    RunStmt,
    FuncDef,
    ClassDef,
    Comment,
    MethodDef,
    CondExpr,
    IfBranch,
    IfStmt,
    ForInStmt,
    ForCStyleStmt,
)


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        self.in_func = False

    def peek(self) -> Token | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek_next(self) -> Token | None:
        if self.pos + 1 < len(self.tokens):
            return self.tokens[self.pos + 1]
        return None

    def consume(self, expected_type: str = None) -> Token:
        token = self.peek()
        if not token:
            raise SyntaxError("Unexpected end of input")
        if expected_type and token.type != expected_type:
            raise SyntaxError(
                f"Line {token.line}, Col {token.col}: "
                f"Expected {expected_type}, but got {token.type} ('{token.value}')"
            )
        self.pos += 1
        return token

    def parse_statement(self):
        token = self.peek()
        if not token:
            return None

        line, col = token.line, token.col

        if token.type == "COMMENT_SINGLE":
            return Comment(line, col, self.consume().value[1:].strip(), False)
        elif token.type == "COMMENT_MULTI":
            return Comment(line, col, self.consume().value[2:-2].strip(), True)

        is_pub = False
        if token.type == "IDENT" and token.value == "pub":
            self.consume("IDENT")
            is_pub = True
            token = self.peek()
            if not token:
                raise SyntaxError(
                    f"Line {line}, Col {col}: 'pub' must be followed by a declaration"
                )

        if token.type == "IDENT":
            if token.value == "var":
                node = self.parse_var_decl()
                if isinstance(node, VarDecl):
                    node.is_pub = is_pub
                return node
            elif token.value == "out":
                return self.parse_out()
            elif token.value == "func":
                node = self.parse_func_def()
                if isinstance(node, FuncDef):
                    node.is_pub = is_pub
                return node
            elif token.value == "class":
                return self.parse_class_def()
            elif token.value == "if":
                return self.parse_if()
            elif token.value == "for":
                return self.parse_for()
            elif token.value == "run":
                self.consume("IDENT")
                return self.parse_run(force_run=True)
            else:
                return self.parse_run()

        if token.type == "STRING":
            return self.parse_run()

        raise SyntaxError(
            f"Line {token.line}, Col {token.col}: "
            f"Unexpected token '{token.value}'"
        )

    def parse_var_decl(self):
        token = self.peek()
        line, col = token.line, token.col
        self.consume("IDENT")
        name_token = self.consume("IDENT")
        name, name_col = name_token.value, name_token.col
        self.consume("ASSIGN")
        val_token = self.peek()
        val, val_col = val_token.value, val_token.col
        self.consume()
        is_ref = val_token.type == "IDENT"
        vtype = "INT" if val_token.type == "NUMBER" else "STRING"
        if self.peek() and self.peek().type == "SEMICOLON":
            self.consume("SEMICOLON")
        return VarDecl(
            line,
            col,
            name,
            name_col,
            val,
            val_col,
            vtype,
            is_local=self.in_func,
            is_ref=is_ref,
        )

    def parse_out(self):
        token = self.peek()
        line, col = token.line, token.col
        self.consume("IDENT")
        values, val_cols, types, refs = [], [], [], []
        while self.peek() and self.peek().type not in ["SEMICOLON", "CBRACE", "NEWLINE"]:
            val_token = self.peek()
            values.append(val_token.value)
            val_cols.append(val_token.col)
            types.append("INT" if val_token.type == "NUMBER" else "STRING")
            refs.append(val_token.type == "IDENT")
            self.consume()
        if self.peek() and self.peek().type == "SEMICOLON":
            self.consume("SEMICOLON")
        return OutStmt(line, col, values, val_cols, types, refs)

    def parse_func_def(self):
        token = self.peek()
        line, col = token.line, token.col
        self.consume("IDENT")
        name_token = self.consume("IDENT")
        name = name_token.value
        self.consume("OPAR")
        args = []
        while self.peek() and self.peek().type != "CPAR":
            args.append(self.consume("IDENT").value)
            if self.peek() and self.peek().type == "COMMA":
                self.consume("COMMA")
        self.consume("CPAR")
        self.consume("OBRACE")
        old_in_func = self.in_func
        self.in_func = True
        body = []
        while self.peek() and self.peek().type != "CBRACE":
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
        self.consume("CBRACE")
        self.in_func = old_in_func
        return FuncDef(line, col, name, body=body, args=args)

    def parse_class_def(self):
        token = self.peek()
        line, col = token.line, token.col
        self.consume("IDENT")
        name = self.consume("IDENT").value
        self.consume("OBRACE")
        methods, fields = [], []
        while self.peek() and self.peek().type != "CBRACE":
            t = self.peek()
            if not t:
                break
            if t.value == "func":
                methods.append(self.parse_method_def())
            elif t.value == "var":
                fields.append(self.parse_var_decl())
            else:
                self.pos += 1
        self.consume("CBRACE")
        return ClassDef(line, col, name, methods, fields)

    def parse_method_def(self):
        token = self.peek()
        line, col = token.line, token.col
        self.consume("IDENT")
        name = self.consume("IDENT").value
        self.consume("OPAR")
        args = []
        while self.peek() and self.peek().type != "CPAR":
            args.append(self.consume("IDENT").value)
            if self.peek() and self.peek().type == "COMMA":
                self.consume("COMMA")
        self.consume("CPAR")
        self.consume("OBRACE")
        body = []
        while self.peek() and self.peek().type != "CBRACE":
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
        self.consume("CBRACE")
        return MethodDef(line, col, name, args, body)

    def parse_run(self, force_run=False):
        token = self.peek()
        line, col = token.line, token.col

        if token.type not in ["IDENT", "STRING"]:
            raise SyntaxError(
                f"Line {line}, Col {col}: Expected command name, but got {token.type}"
            )

        exec_name = self.consume().value

        if not force_run and self.peek() and self.peek().type == "DOT":
            self.consume("DOT")
            method_name = self.consume("IDENT").value
            exec_name = f"{exec_name}:{method_name}"

        args, arg_cols, arg_is_ref = [], [], []
        if self.peek() and self.peek().type == "OPAR":
            self.consume("OPAR")
            while self.peek() and self.peek().type != "CPAR":
                t = self.peek()
                args.append(t.value)
                arg_cols.append(t.col)
                arg_is_ref.append(t.type == "IDENT")
                self.consume()
                if self.peek() and self.peek().type == "COMMA":
                    self.consume("COMMA")
            self.consume("CPAR")
        else:
            while self.peek() and self.peek().type not in [
                "SEMICOLON",
                "CBRACE",
                "NEWLINE",
            ]:
                t = self.peek()
                args.append(t.value)
                arg_cols.append(t.col)
                arg_is_ref.append(t.type == "IDENT")
                self.consume()

        if self.peek() and self.peek().type == "SEMICOLON":
            self.consume("SEMICOLON")

        return RunStmt(line, col, exec_name, args, arg_cols, arg_is_ref=arg_is_ref)

    def parse_condition(self) -> CondExpr:
        left_tok = self.consume()
        left = left_tok.value
        left_col = left_tok.col
        left_is_ref = (left_tok.type == "IDENT")

        op_tok = self.peek()
        if op_tok and op_tok.type in ["EQ", "NE", "LE", "GE", "LT", "GT", "ASSIGN"]:
            op = self.consume().value
            right_tok = self.consume()
            right = right_tok.value
            right_col = right_tok.col
            right_is_ref = (right_tok.type == "IDENT")
            return CondExpr(
                line=left_tok.line,
                col=left_tok.col,
                left=left,
                left_col=left_col,
                left_is_ref=left_is_ref,
                op=op,
                right=right,
                right_col=right_col,
                right_is_ref=right_is_ref,
            )
        else:
            return CondExpr(
                line=left_tok.line,
                col=left_tok.col,
                left=left,
                left_col=left_col,
                left_is_ref=left_is_ref,
            )

    def parse_if(self) -> IfStmt:
        if_tok = self.consume("IDENT")
        line, col = if_tok.line, if_tok.col
        self.consume("OPAR")
        then_cond = self.parse_condition()
        self.consume("CPAR")
        self.consume("OBRACE")
        then_body = []
        while self.peek() and self.peek().type != "CBRACE":
            stmt = self.parse_statement()
            if stmt:
                then_body.append(stmt)
        self.consume("CBRACE")
        then_branch = IfBranch(
            line=then_cond.line,
            col=then_cond.col,
            condition=then_cond,
            body=then_body,
        )

        elif_branches = []
        while True:
            t = self.peek()
            if t and t.type == "IDENT" and t.value == "else":
                next_t = self.peek_next()
                if next_t and next_t.type == "IDENT" and next_t.value == "if":
                    self.consume("IDENT")
                    self.consume("IDENT")
                    self.consume("OPAR")
                    elif_cond = self.parse_condition()
                    self.consume("CPAR")
                    self.consume("OBRACE")
                    elif_body = []
                    while self.peek() and self.peek().type != "CBRACE":
                        stmt = self.parse_statement()
                        if stmt:
                            elif_body.append(stmt)
                    self.consume("CBRACE")
                    elif_branches.append(
                        IfBranch(
                            line=elif_cond.line,
                            col=elif_cond.col,
                            condition=elif_cond,
                            body=elif_body,
                        )
                    )
                else:
                    break
            else:
                break

        else_body = []
        t = self.peek()
        if t and t.type == "IDENT" and t.value == "else":
            self.consume("IDENT")
            self.consume("OBRACE")
            while self.peek() and self.peek().type != "CBRACE":
                stmt = self.parse_statement()
                if stmt:
                    else_body.append(stmt)
            self.consume("CBRACE")

        return IfStmt(
            line=line,
            col=col,
            then_branch=then_branch,
            elif_branches=elif_branches,
            else_body=else_body,
        )

    def parse_for(self) -> ForInStmt | ForCStyleStmt:
        for_tok = self.consume("IDENT")
        line, col = for_tok.line, for_tok.col
        self.consume("OPAR")

        is_c_style = False
        scan_pos = self.pos
        paren_count = 1
        while scan_pos < len(self.tokens) and paren_count > 0:
            t = self.tokens[scan_pos]
            if t.type == "OPAR":
                paren_count += 1
            elif t.type == "CPAR":
                paren_count -= 1
            elif t.type == "SEMICOLON" and paren_count == 1:
                is_c_style = True
            scan_pos += 1

        if not is_c_style:
            is_decl = False
            if self.peek() and self.peek().type == "IDENT" and self.peek().value == "var":
                self.consume("IDENT")
                is_decl = True
            var_token = self.consume("IDENT")
            var_name, var_col = var_token.value, var_token.col

            in_tok = self.peek()
            if not in_tok or in_tok.type != "IDENT" or in_tok.value != "in":
                raise SyntaxError(
                    f"Line {var_token.line}, Col {var_token.col}: Expected 'in' in for loop"
                )
            self.consume("IDENT")

            items, item_cols, item_is_ref = [], [], []
            while self.peek() and self.peek().type != "CPAR":
                t = self.peek()
                items.append(t.value)
                item_cols.append(t.col)
                item_is_ref.append(t.type == "IDENT")
                self.consume()
            self.consume("CPAR")
            self.consume("OBRACE")
            body = []
            while self.peek() and self.peek().type != "CBRACE":
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
            self.consume("CBRACE")

            return ForInStmt(
                line=line,
                col=col,
                var_name=var_name,
                var_col=var_col,
                is_decl=is_decl,
                is_local=self.in_func,
                items=items,
                item_cols=item_cols,
                item_is_ref=item_is_ref,
                body=body,
            )
        else:
            is_decl = False
            if self.peek() and self.peek().type == "IDENT" and self.peek().value == "var":
                self.consume("IDENT")
                is_decl = True
            var_token = self.consume("IDENT")
            name, name_col = var_token.value, var_token.col
            self.consume("ASSIGN")
            val_token = self.peek()
            val, val_col = val_token.value, val_token.col
            self.consume()
            is_ref = (val_token.type == "IDENT")
            vtype = "INT" if val_token.type == "NUMBER" else "STRING"
            init_node = VarDecl(
                line=line,
                col=col,
                name=name,
                name_col=name_col,
                value=val,
                value_col=val_col,
                value_type=vtype,
                is_local=self.in_func,
                is_ref=is_ref,
            )
            self.consume("SEMICOLON")
            cond_node = self.parse_condition()
            self.consume("SEMICOLON")

            step_tokens = []
            while self.peek() and self.peek().type != "CPAR":
                step_tokens.append(self.consume().value)
            step_str = " ".join(step_tokens)
            self.consume("CPAR")

            self.consume("OBRACE")
            body = []
            while self.peek() and self.peek().type != "CBRACE":
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
            self.consume("CBRACE")

            return ForCStyleStmt(
                line=line,
                col=col,
                init=init_node,
                condition=cond_node,
                step_var=name,
                step_expr=step_str,
                body=body,
            )

    def parse_all(self):
        nodes = []
        while self.peek():
            stmt = self.parse_statement()
            if stmt:
                nodes.append(stmt)
        return nodes
