# src/lexer.py
# High-performance Lexer for Katlin programming language

import sys
from typing import List, Optional
from src.diagnostics import KatlinLexerError

class TokenType:
    # Special
    EOF = "EOF"
    NEWLINE = "NEWLINE"
    
    # Identifiers & Literals
    IDENT = "IDENT"
    INT_LIT = "INT_LIT"
    FLOAT_LIT = "FLOAT_LIT"
    STR_LIT = "STR_LIT"
    BOOL_LIT = "BOOL_LIT"
    
    # Keywords
    FN = "fn"
    STRUCT = "struct"
    ENUM = "enum"
    OR_KW = "or"
    MATCH = "match"
    CASE = "case"
    PANIC = "panic"
    TEST = "test"
    INT = "int"
    I64 = "i64"
    U64 = "u64"
    STR = "str"
    BOOL = "bool"
    FLOAT = "float"
    MUT = "mut"
    IF = "if"
    ELIF = "elif"
    ELSE = "else"
    WHILE = "while"
    FOR = "for"
    IN = "in"
    STEP = "step"
    LOOP = "loop"
    RETURN = "return"
    BREAK = "break"
    CONTINUE = "continue"
    RAW = "raw"
    STRICT = "strict"
    PRINTLN = "println"
    PRINT = "print"
    IMPORT = "import"
    PRAGMA_STRICT = "#strict"
    
    # Operators & Delimiters
    ASSIGN = "="
    DEFINE = ":="       # Dynamic inferred typing
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    PERCENT = "%"
    AMP = "&"           # Mutability or address
    BANG = "!"
    
    PLUS_ASSIGN = "+="
    MINUS_ASSIGN = "-="
    STAR_ASSIGN = "*="
    SLASH_ASSIGN = "/="
    
    EQ = "=="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="
    AND = "&&"
    OR = "||"
    PIPE = "|"
    CARET = "^"
    TILDE = "~"
    SHL = "<<"
    SHR = ">>"
    
    DOT = "."
    DOTDOT = ".."       # Range
    COMMA = ","
    COLON = ":"
    SEMICOLON = ";"
    
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"

KEYWORDS = {
    "fn": TokenType.FN,
    "int": TokenType.INT,
    "i64": TokenType.I64,
    "u64": TokenType.U64,
    "str": TokenType.STR,
    "bool": TokenType.BOOL,
    "float": TokenType.FLOAT,
    "mut": TokenType.MUT,
    "if": TokenType.IF,
    "elif": TokenType.ELIF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "step": TokenType.STEP,
    "loop": TokenType.LOOP,
    "return": TokenType.RETURN,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "raw": TokenType.RAW,
    "strict": TokenType.STRICT,
    "struct": TokenType.STRUCT,
    "enum": TokenType.ENUM,
    "or": TokenType.OR_KW,
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "panic": TokenType.PANIC,
    "test": TokenType.TEST,
    "println": TokenType.PRINTLN,
    "print": TokenType.PRINT,
    "import": TokenType.IMPORT,
    "true": TokenType.BOOL_LIT,
    "false": TokenType.BOOL_LIT,
}

class Token:
    def __init__(self, typ: str, val: str, line: int, col: int):
        self.type = typ
        self.value = val
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, L{self.line}:C{self.col})"

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.length = len(source)
        self.line = 1
        self.col = 1

    def peek(self, offset: int = 0) -> str:
        idx = self.pos + offset
        if idx >= self.length:
            return ""
        return self.source[idx]

    def advance(self) -> str:
        if self.pos >= self.length:
            return ""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.peek() == expected:
            self.advance()
            return True
        return False

    def skip_whitespace_and_comments(self):
        while self.pos < self.length:
            ch = self.peek()
            if ch in " \t\r\n":
                self.advance()
            elif ch == "/" and self.peek(1) == "/":
                # Single-line comment
                while self.pos < self.length and self.peek() != "\n":
                    self.advance()
            elif ch == "/" and self.peek(1) == "*":
                # Multi-line comment
                self.advance() # /
                self.advance() # *
                while self.pos < self.length:
                    if self.peek() == "*" and self.peek(1) == "/":
                        self.advance()
                        self.advance()
                        break
                    self.advance()
            else:
                break

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            self.skip_whitespace_and_comments()
            if self.pos >= self.length:
                break

            start_line = self.line
            start_col = self.col
            ch = self.peek()

            # Pragmas (e.g. #strict)
            if ch == "#":
                self.advance()
                ident = ""
                while self.peek().isalnum() or self.peek() == "_":
                    ident += self.advance()
                if ident == "strict":
                    tokens.append(Token(TokenType.PRAGMA_STRICT, "#strict", start_line, start_col))
                    continue
                else:
                    raise KatlinLexerError(f"unknown pragma '#{ident}'", start_line, start_col, len(ident) + 1, help_text="supported pragmas include '#strict'")

            # String literal
            if ch == '"':
                self.advance()
                s_val = ""
                while self.pos < self.length and self.peek() != '"':
                    if self.peek() == "\\":
                        self.advance()
                        esc = self.advance()
                        if esc == "n": s_val += "\n"
                        elif esc == "t": s_val += "\t"
                        elif esc == "r": s_val += "\r"
                        elif esc == "0": s_val += "\0"
                        elif esc == "e": s_val += "\x1b"
                        elif esc == "x":
                            hex_str = ""
                            if self.peek() in "0123456789abcdefABCDEF":
                                hex_str += self.advance()
                            if self.peek() in "0123456789abcdefABCDEF":
                                hex_str += self.advance()
                            if hex_str:
                                s_val += chr(int(hex_str, 16))
                            else:
                                s_val += "\\x"
                        elif esc == '"': s_val += '"'
                        elif esc == "\\": s_val += "\\"
                        else: s_val += "\\" + esc
                    else:
                        s_val += self.advance()
                if self.peek() == '"':
                    self.advance()
                else:
                    raise KatlinLexerError("unterminated string literal", start_line, start_col, max(1, len(s_val) + 1), help_text="string literals must be closed with a matching double-quote '\"'")
                tokens.append(Token(TokenType.STR_LIT, s_val, start_line, start_col))
                continue

            # Number literal
            if ch.isdigit():
                num_str = ""
                is_float = False
                
                # Hex literal: 0x...
                if ch == "0" and self.peek(1) in ("x", "X"):
                    num_str += self.advance()
                    num_str += self.advance()
                    while self.peek().isalnum() or self.peek() == "_":
                        num_str += self.advance()
                    tokens.append(Token(TokenType.INT_LIT, num_str, start_line, start_col))
                    continue

                # Binary literal: 0b...
                if ch == "0" and self.peek(1) in ("b", "B"):
                    num_str += self.advance()
                    num_str += self.advance()
                    while self.peek() in ("0", "1", "_"):
                        num_str += self.advance()
                    tokens.append(Token(TokenType.INT_LIT, num_str, start_line, start_col))
                    continue

                while self.peek().isdigit() or self.peek() == "_" or (self.peek() == "." and self.peek(1).isdigit()):
                    if self.peek() == ".":
                        is_float = True
                    num_str += self.advance()
                tok_type = TokenType.FLOAT_LIT if is_float else TokenType.INT_LIT
                tokens.append(Token(tok_type, num_str, start_line, start_col))
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                ident = ""
                while self.peek().isalnum() or self.peek() == "_":
                    ident += self.advance()
                tok_type = KEYWORDS.get(ident, TokenType.IDENT)
                tokens.append(Token(tok_type, ident, start_line, start_col))
                continue

            # Multi-character & Single-character operators
            self.advance()
            if ch == ":":
                if self.match("="):
                    tokens.append(Token(TokenType.DEFINE, ":=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.COLON, ":", start_line, start_col))
            elif ch == "+":
                if self.match("="):
                    tokens.append(Token(TokenType.PLUS_ASSIGN, "+=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.PLUS, "+", start_line, start_col))
            elif ch == "-":
                if self.match("="):
                    tokens.append(Token(TokenType.MINUS_ASSIGN, "-=", start_line, start_col))
                elif self.match(">"):
                    # Arrow if needed
                    tokens.append(Token(TokenType.IDENT, "->", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.MINUS, "-", start_line, start_col))
            elif ch == "*":
                if self.match("="):
                    tokens.append(Token(TokenType.STAR_ASSIGN, "*=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.STAR, "*", start_line, start_col))
            elif ch == "/":
                if self.match("="):
                    tokens.append(Token(TokenType.SLASH_ASSIGN, "/=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.SLASH, "/", start_line, start_col))
            elif ch == "=":
                if self.match("="):
                    tokens.append(Token(TokenType.EQ, "==", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.ASSIGN, "=", start_line, start_col))
            elif ch == "!":
                if self.match("="):
                    tokens.append(Token(TokenType.NEQ, "!=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.BANG, "!", start_line, start_col))
            elif ch == "<":
                if self.match("<"):
                    tokens.append(Token(TokenType.SHL, "<<", start_line, start_col))
                elif self.match("="):
                    tokens.append(Token(TokenType.LTE, "<=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.LT, "<", start_line, start_col))
            elif ch == ">":
                if self.match(">"):
                    tokens.append(Token(TokenType.SHR, ">>", start_line, start_col))
                elif self.match("="):
                    tokens.append(Token(TokenType.GTE, ">=", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.GT, ">", start_line, start_col))
            elif ch == "^":
                tokens.append(Token(TokenType.CARET, "^", start_line, start_col))
            elif ch == "~":
                tokens.append(Token(TokenType.TILDE, "~", start_line, start_col))
            elif ch == "&":
                if self.match("&"):
                    tokens.append(Token(TokenType.AND, "&&", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.AMP, "&", start_line, start_col))
            elif ch == "|":
                if self.match("|"):
                    tokens.append(Token(TokenType.OR, "||", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.PIPE, "|", start_line, start_col))
            elif ch == ".":
                if self.match("."):
                    tokens.append(Token(TokenType.DOTDOT, "..", start_line, start_col))
                else:
                    tokens.append(Token(TokenType.DOT, ".", start_line, start_col))
            elif ch == ";":
                tokens.append(Token(TokenType.SEMICOLON, ";", start_line, start_col))
            elif ch == ",":
                tokens.append(Token(TokenType.COMMA, ",", start_line, start_col))
            elif ch == "%":
                tokens.append(Token(TokenType.PERCENT, "%", start_line, start_col))
            elif ch == "(":
                tokens.append(Token(TokenType.LPAREN, "(", start_line, start_col))
            elif ch == ")":
                tokens.append(Token(TokenType.RPAREN, ")", start_line, start_col))
            elif ch == "{":
                tokens.append(Token(TokenType.LBRACE, "{", start_line, start_col))
            elif ch == "}":
                tokens.append(Token(TokenType.RBRACE, "}", start_line, start_col))
            elif ch == "[":
                tokens.append(Token(TokenType.LBRACKET, "[", start_line, start_col))
            elif ch == "]":
                tokens.append(Token(TokenType.RBRACKET, "]", start_line, start_col))
            else:
                raise KatlinLexerError(f"unexpected character '{ch}'", start_line, start_col, 1, help_text="valid Katlin tokens include keywords, identifiers, numbers, strings, and operators")

        tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return tokens
