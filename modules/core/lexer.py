import re
from typing import NamedTuple


class Token(NamedTuple):
    type: str
    value: str
    line: int
    col: int


TOKEN_SPEC = [
    ("COMMENT_MULTI", r"/\*[\s\S]*?\*/"),
    ("COMMENT_SINGLE", r"#.*"),
    ("STRING", r'"[^"]*"'),
    ("NUMBER", r"\d+"),
    ("IDENT", r"[a-zA-Z_]\w*"),
    ("ASSIGN", r"="),
    ("DOT", r"\."),
    ("SEMICOLON", r";"),
    ("OPAR", r"\("),
    ("CPAR", r"\)"),
    ("OBRACE", r"\{"),
    ("CBRACE", r"\}"),
    ("COMMA", r","),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
    ("MISMATCH", r"."),
]


def tokenize(code: str) -> list[Token]:
    tokens = []
    line_num = 1
    line_start = 0
    regex = "|".join("(?P<%s>%s)" % pair for pair in TOKEN_SPEC)
    for mo in re.finditer(regex, code):
        kind = mo.lastgroup
        value = mo.group()
        column = mo.start() - line_start + 1

        if kind == "NEWLINE":
            line_num += 1
            line_start = mo.end()
            continue
        elif kind == "SKIP":
            continue
        elif kind == "COMMENT_SINGLE" or kind == "COMMENT_MULTI":
            tokens.append(Token(kind, value, line_num, column))
            if "\n" in value:
                line_num += value.count("\n")
                line_start = mo.start() + value.rfind("\n") + 1
            continue
        elif kind == "MISMATCH":
            raise RuntimeError(
                f'Error: Unexpected character "{value}" at Line {line_num}, Col {column}'
            )

        tokens.append(Token(kind, value, line_num, column))
    return tokens
