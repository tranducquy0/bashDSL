from modules.core.lexer import Token
from modules.core.nodes import (
    VarDecl,
    OutStmt,
    RunStmt,
    FuncDef,
    ClassDef,
    Comment,
    MethodDef,
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
            elif token.value == "run":
                self.consume("IDENT")
                return self.parse_run(force_run=True)
            else:
                return self.parse_run()

        if token.type == "STRING":
            return self.parse_run()

        raise SyntaxError(
            f"Line {token.line}, Col {token.col}: Unexpected token '{token.value}'"
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
        while self.peek() and self.peek().type not in [
            "SEMICOLON",
            "CBRACE",
            "NEWLINE",
        ]:
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

    def parse_all(self):
        nodes = []
        while self.peek():
            stmt = self.parse_statement()
            if stmt:
                nodes.append(stmt)
        return nodes
