# src/parser.py
# Recursive Descent Parser for Katlin

from typing import List, Optional, Tuple, Any
from src.lexer import Token, TokenType
from src.ast_nodes import (
    Program, FunctionDef, Parameter, VarDecl, AssignStmt, ReturnStmt,
    PrintStmt, CallExpr, ChainedCall, IfStmt, WhileStmt, LoopStmt, ForStmt,
    RawBlock, BinaryOp, UnaryOp, Literal, Identifier, ExprStmt, IndexAssign, IndexExpr,
    StructField, StructDef, StructInit, MemberAccess, EnumDef, OrExpr, MatchBranch, MatchStmt, TestBlock, ASTNode
)

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1] # EOF
        return self.tokens[idx]

    def advance(self) -> Token:
        tok = self.peek()
        if self.pos < len(self.tokens):
            self.pos += 1
        return tok

    def match(self, *expected_types: str) -> bool:
        if self.peek().type in expected_types:
            self.advance()
            return True
        return False

    def consume(self, expected_type: str, msg: str = "") -> Token:
        tok = self.peek()
        if tok.type == expected_type:
            return self.advance()
        err_msg = msg or f"Expected {expected_type}, got {tok.type} ('{tok.value}')"
        raise SyntaxError(f"Parse error at L{tok.line}:C{tok.col}: {err_msg}")

    def skip_semicolons(self):
        while self.peek().type == TokenType.SEMICOLON:
            self.advance()

    def parse(self) -> Program:
        prog = Program()
        while self.peek().type != TokenType.EOF:
            if self.peek().type == TokenType.PRAGMA_STRICT:
                self.advance() # #strict at top of file
                self.skip_semicolons()
                continue
            if self.peek().type == TokenType.IMPORT:
                self.parse_import()
                continue
            if self.peek().type in (TokenType.FN, TokenType.STRICT):
                func = self.parse_function()
                prog.statements.append(func)
                continue
            if self.peek().type == TokenType.STRUCT:
                s_def = self.parse_struct()
                prog.statements.append(s_def)
                continue
            if self.peek().type == TokenType.ENUM:
                e_def = self.parse_enum()
                prog.statements.append(e_def)
                continue
            if self.peek().type == TokenType.TEST:
                t_def = self.parse_test()
                prog.statements.append(t_def)
                continue
            # Skip stray semicolons
            if self.peek().type == TokenType.SEMICOLON:
                self.advance()
                continue
            # Top level statement
            stmt = self.parse_statement()
            if stmt:
                prog.statements.append(stmt)
        return prog

    def parse_import(self):
        self.consume(TokenType.IMPORT)
        # Parse until semicolon or newline (e.g. std.io.{println}; or std.net;)
        while self.peek().type not in (TokenType.SEMICOLON, TokenType.EOF, TokenType.FN, TokenType.STRICT, TokenType.STRUCT, TokenType.ENUM, TokenType.TEST):
            self.advance()
        self.skip_semicolons()

    def parse_struct(self) -> StructDef:
        tok = self.consume(TokenType.STRUCT)
        name = self.consume(TokenType.IDENT, "Expected struct name").value
        self.consume(TokenType.LBRACE, "Expected '{' after struct name")
        fields = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            self.skip_semicolons()
            if self.peek().type == TokenType.RBRACE:
                break
            type_name = "int"
            if self.peek().type in (TokenType.INT, TokenType.I64, TokenType.U64, TokenType.STR, TokenType.BOOL, TokenType.FLOAT, TokenType.IDENT):
                type_name = self.advance().value
            is_ref = False
            if self.match(TokenType.AMP):
                is_ref = True
            f_name = self.consume(TokenType.IDENT, "Expected field name").value
            def_val = None
            if self.match(TokenType.ASSIGN):
                def_val = self.parse_expression()
            fields.append(StructField(name=f_name, type_name=type_name, default_value=def_val, is_ref=is_ref, line=tok.line, col=tok.col))
            self.skip_semicolons()
        self.consume(TokenType.RBRACE)
        self.skip_semicolons()
        return StructDef(name=name, fields=fields, line=tok.line, col=tok.col)

    def parse_enum(self) -> EnumDef:
        tok = self.consume(TokenType.ENUM)
        name = self.consume(TokenType.IDENT, "Expected enum name").value
        self.consume(TokenType.LBRACE, "Expected '{' after enum name")
        variants = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            self.skip_semicolons()
            if self.peek().type == TokenType.RBRACE:
                break
            v_name = self.consume(TokenType.IDENT, "Expected variant name").value
            variants.append(v_name)
            self.match(TokenType.COMMA)
            self.skip_semicolons()
        self.consume(TokenType.RBRACE)
        self.skip_semicolons()
        return EnumDef(name=name, variants=variants, line=tok.line, col=tok.col)

    def parse_test(self) -> TestBlock:
        tok = self.consume(TokenType.TEST)
        name = self.consume(TokenType.STR_LIT, "Expected test description string").value
        self.consume(TokenType.LBRACE, "Expected '{' after test name")
        body = []
        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            s = self.parse_statement()
            if s: body.append(s)
            self.skip_semicolons()
        self.consume(TokenType.RBRACE)
        self.skip_semicolons()
        return TestBlock(name=name, body=body, line=tok.line, col=tok.col)

    def parse_function(self, is_inner: bool = False) -> FunctionDef:
        is_strict = False
        tok = self.peek()
        if self.match(TokenType.STRICT):
            is_strict = True
        self.consume(TokenType.FN)
        
        name = self.consume(TokenType.IDENT, "Expected function name").value
        params: List[Parameter] = []

        # Optional parentheses: fn fuck { ... } or fn idkbro(timeout = 5) { ... }
        if self.peek().type == TokenType.LPAREN:
            self.advance()
            while self.peek().type != TokenType.RPAREN and self.peek().type != TokenType.EOF:
                param = self.parse_parameter()
                params.append(param)
                if not self.match(TokenType.COMMA):
                    break
            self.consume(TokenType.RPAREN)

        # Optional return type: -> int or : int
        return_type = None
        if self.peek().value == "->" or self.peek().type == TokenType.COLON:
            self.advance()
            return_type = self.advance().value

        # Function body: { ... }
        self.consume(TokenType.LBRACE, "Expected '{' to start function body")
        body: List[ASTNode] = []
        inner_functions: List[FunctionDef] = []

        while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
            self.skip_semicolons()
            if self.peek().type == TokenType.RBRACE:
                break
            # Check for inner function
            if self.peek().type in (TokenType.FN, TokenType.STRICT):
                inner_fn = self.parse_function(is_inner=True)
                inner_functions.append(inner_fn)
            else:
                stmt = self.parse_statement()
                if stmt:
                    body.append(stmt)
            self.skip_semicolons()

        self.consume(TokenType.RBRACE, "Expected '}' to close function body")
        self.skip_semicolons()

        return FunctionDef(
            name=name,
            params=params,
            return_type=return_type,
            body=body,
            inner_functions=inner_functions,
            is_strict=is_strict,
            line=tok.line,
            col=tok.col
        )

    def parse_parameter(self) -> Parameter:
        tok = self.peek()
        is_ref = False
        type_name = "int"

        # e.g. int timeout = 5, or Point p, or Point &p, or timeout = 5
        if self.peek().type in (TokenType.INT, TokenType.I64, TokenType.U64, TokenType.STR, TokenType.BOOL, TokenType.FLOAT):
            type_name = self.advance().value
        elif self.peek().type == TokenType.IDENT and (self.peek(1).type == TokenType.IDENT or self.peek(1).type == TokenType.AMP):
            type_name = self.advance().value
        
        if self.match(TokenType.AMP):
            is_ref = True

        name = self.consume(TokenType.IDENT, "Expected parameter name").value
        default_val = None
        if self.match(TokenType.ASSIGN):
            default_val = self.parse_expression()

        return Parameter(name=name, type_name=type_name, default_value=default_val, is_ref=is_ref, line=tok.line, col=tok.col)

    def parse_statement(self) -> Optional[ASTNode]:
        tok = self.peek()

        # Return statement (with optional postfix guard: return if condition;)
        if self.match(TokenType.RETURN):
            val = None
            if self.peek().type not in (TokenType.SEMICOLON, TokenType.IF, TokenType.RBRACE):
                val = self.parse_expression()
            guard = None
            if self.match(TokenType.IF):
                guard = self.parse_expression()
            self.skip_semicolons()
            return ReturnStmt(value=val, guard_condition=guard, line=tok.line, col=tok.col)

        # Print / Println statement
        if tok.type in (TokenType.PRINTLN, TokenType.PRINT):
            is_nl = (tok.type == TokenType.PRINTLN)
            self.advance()
            self.consume(TokenType.LPAREN)
            fmt_str = ""
            args = []
            if self.peek().type == TokenType.STR_LIT:
                fmt_str = self.advance().value
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            elif self.peek().type != TokenType.RPAREN:
                # Expression directly
                args.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    args.append(self.parse_expression())
            self.consume(TokenType.RPAREN)
            self.skip_semicolons()
            return PrintStmt(format_str=fmt_str, args=args, is_newline=is_nl, line=tok.line, col=tok.col)

        # Raw block: raw { ... }
        if self.match(TokenType.RAW):
            self.consume(TokenType.LBRACE)
            raw_body = []
            while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                s = self.parse_statement()
                if s: raw_body.append(s)
                self.skip_semicolons()
            self.consume(TokenType.RBRACE)
            self.skip_semicolons()
            return RawBlock(body=raw_body, line=tok.line, col=tok.col)

        # While loop: while condition { ... }
        if self.match(TokenType.WHILE):
            cond = self.parse_expression()
            self.match(TokenType.COLON) # optional colon
            self.consume(TokenType.LBRACE)
            while_body = []
            while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                s = self.parse_statement()
                if s: while_body.append(s)
                self.skip_semicolons()
            self.consume(TokenType.RBRACE)
            self.skip_semicolons()
            return WhileStmt(condition=cond, body=while_body, line=tok.line, col=tok.col)

        # Infinite loop: loop { ... }
        if self.match(TokenType.LOOP):
            self.consume(TokenType.LBRACE)
            loop_body = []
            while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                s = self.parse_statement()
                if s: loop_body.append(s)
                self.skip_semicolons()
            self.consume(TokenType.RBRACE)
            self.skip_semicolons()
            return LoopStmt(body=loop_body, line=tok.line, col=tok.col)

        # For loop: for i in 0..10 step 2 { ... }
        if self.match(TokenType.FOR):
            is_ref = False
            if self.match(TokenType.AMP):
                is_ref = True
            var_name = self.consume(TokenType.IDENT).value
            self.consume(TokenType.IN)
            range_start = self.parse_expression()
            self.consume(TokenType.DOTDOT)
            range_end = self.parse_expression()
            step = None
            if self.match(TokenType.STEP):
                step = self.parse_expression()
            self.match(TokenType.COLON) # optional colon
            self.consume(TokenType.LBRACE)
            for_body = []
            while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                s = self.parse_statement()
                if s: for_body.append(s)
                self.skip_semicolons()
            self.consume(TokenType.RBRACE)
            self.skip_semicolons()
            return ForStmt(var_name=var_name, is_ref=is_ref, range_start=range_start, range_end=range_end, step=step, body=for_body, line=tok.line, col=tok.col)

        # If statement: if cond { ... } elif cond { ... } else { ... }
        if self.match(TokenType.IF):
            cond = self.parse_expression()
            self.match(TokenType.COLON) # optional colon
            self.consume(TokenType.LBRACE)
            then_body = []
            while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                s = self.parse_statement()
                if s: then_body.append(s)
                self.skip_semicolons()
            self.consume(TokenType.RBRACE)

            elifs = []
            while self.match(TokenType.ELIF):
                elif_cond = self.parse_expression()
                self.match(TokenType.COLON)
                self.consume(TokenType.LBRACE)
                elif_body = []
                while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                    s = self.parse_statement()
                    if s: elif_body.append(s)
                    self.skip_semicolons()
                self.consume(TokenType.RBRACE)
                elifs.append((elif_cond, elif_body))

            else_body = []
            if self.match(TokenType.ELSE):
                self.match(TokenType.COLON)
                self.consume(TokenType.LBRACE)
                while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                    s = self.parse_statement()
                    if s: else_body.append(s)
                    self.skip_semicolons()
                self.consume(TokenType.RBRACE)

            self.skip_semicolons()
            return IfStmt(condition=cond, then_body=then_body, elif_branches=elifs, else_body=else_body, line=tok.line, col=tok.col)

        # Match statement: match subject { case .idle: ... }
        if self.match(TokenType.MATCH):
            subj = self.parse_expression()
            self.consume(TokenType.LBRACE)
            branches = []
            while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                self.skip_semicolons()
                if self.peek().type == TokenType.RBRACE:
                    break
                self.consume(TokenType.CASE)
                pattern_parts = []
                if self.match(TokenType.DOT):
                    pattern_parts.append("." + self.consume(TokenType.IDENT).value)
                else:
                    pattern_parts.append(self.advance().value)
                pattern = "".join(pattern_parts)
                self.consume(TokenType.COLON)
                b_body = []
                if self.peek().type == TokenType.LBRACE:
                    self.advance()
                    while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                        s = self.parse_statement()
                        if s: b_body.append(s)
                        self.skip_semicolons()
                    self.consume(TokenType.RBRACE)
                else:
                    s = self.parse_statement()
                    if s: b_body.append(s)
                branches.append(MatchBranch(pattern=pattern, body=b_body, line=tok.line, col=tok.col))
                self.skip_semicolons()
            self.consume(TokenType.RBRACE)
            self.skip_semicolons()
            return MatchStmt(subject=subj, branches=branches, line=tok.line, col=tok.col)

        # Variable declarations:
        # Style A: Explicit type: int score = 100; int &sum = 0; Point p = ...;
        is_explicit_type = (tok.type in (TokenType.INT, TokenType.I64, TokenType.U64, TokenType.STR, TokenType.BOOL, TokenType.FLOAT)) or \
                           (tok.type == TokenType.IDENT and (self.peek(1).type == TokenType.IDENT or (self.peek(1).type == TokenType.AMP and self.peek(2).type == TokenType.IDENT)))
        if is_explicit_type:
            type_name = self.advance().value
            is_mutable = False
            if self.match(TokenType.AMP):
                is_mutable = True
            var_name = self.consume(TokenType.IDENT, "Expected variable name").value
            val = None
            if self.match(TokenType.ASSIGN):
                val = self.parse_expression()
            self.skip_semicolons()
            return VarDecl(name=var_name, type_name=type_name, value=val, is_mutable=is_mutable, is_inferred=False, line=tok.line, col=tok.col)

        # Style B: 'mut' keyword: mut int gayppl = 3; or mut Point pt = ...; or mut count := 0;
        if tok.type == TokenType.MUT:
            self.advance()
            type_name = None
            if self.peek().type in (TokenType.INT, TokenType.I64, TokenType.U64, TokenType.STR, TokenType.BOOL, TokenType.FLOAT):
                type_name = self.advance().value
            elif self.peek().type == TokenType.IDENT and self.peek(1).type == TokenType.IDENT:
                type_name = self.advance().value
            var_name = self.consume(TokenType.IDENT, "Expected variable name").value
            is_inferred = False
            if self.match(TokenType.DEFINE): # ':='
                is_inferred = True
                val = self.parse_expression()
            elif self.match(TokenType.ASSIGN): # '='
                val = self.parse_expression()
            else:
                val = None
            self.skip_semicolons()
            return VarDecl(name=var_name, type_name=type_name, value=val, is_mutable=True, is_inferred=is_inferred, line=tok.line, col=tok.col)

        # Style C: Dynamic inferred with ':=': total := counter + gayppl;
        if tok.type == TokenType.IDENT and self.peek(1).type == TokenType.DEFINE:
            var_name = self.advance().value # ident
            self.advance() # :=
            val = self.parse_expression()
            self.skip_semicolons()
            return VarDecl(name=var_name, type_name=None, value=val, is_mutable=False, is_inferred=True, line=tok.line, col=tok.col)

        # Index assignment: buffer[i] = val;
        if tok.type == TokenType.IDENT and self.peek(1).type == TokenType.LBRACKET:
            target_name = self.advance().value
            self.advance() # [
            idx_node = self.parse_expression()
            self.consume(TokenType.RBRACKET)
            if self.peek().type in (TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN, TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN):
                op = self.advance().value
                val = self.parse_expression()
                self.skip_semicolons()
                return IndexAssign(target=target_name, index=idx_node, op=op, value=val, line=tok.line, col=tok.col)

        # Reassignments: counter += 5; x = 10;
        if tok.type == TokenType.IDENT and self.peek(1).type in (TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MINUS_ASSIGN, TokenType.STAR_ASSIGN, TokenType.SLASH_ASSIGN):
            var_name = self.advance().value
            op = self.advance().value
            val = self.parse_expression()
            self.skip_semicolons()
            return AssignStmt(target=var_name, op=op, value=val, line=tok.line, col=tok.col)

        # General Expression or Chained Call
        expr = self.parse_expression()
        self.skip_semicolons()
        return ExprStmt(expr=expr, line=tok.line, col=tok.col)

    def parse_expression(self) -> ASTNode:
        expr = self.parse_logic_or()
        if self.match(TokenType.OR_KW):
            tok = self.peek()
            if self.match(TokenType.RETURN):
                return OrExpr(left=expr, is_return=True, line=expr.line, col=expr.col)
            elif self.match(TokenType.PANIC):
                self.consume(TokenType.LPAREN)
                msg = self.consume(TokenType.STR_LIT, "Expected panic message").value
                self.consume(TokenType.RPAREN)
                return OrExpr(left=expr, is_panic=True, panic_msg=msg, line=expr.line, col=expr.col)
            else:
                fallback = self.parse_expression()
                return OrExpr(left=expr, fallback_expr=fallback, line=expr.line, col=expr.col)
        return expr

    def parse_logic_or(self) -> ASTNode:
        left = self.parse_logic_and()
        while self.match(TokenType.OR):
            op = "||"
            right = self.parse_logic_and()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_logic_and(self) -> ASTNode:
        left = self.parse_bitwise_or()
        while self.match(TokenType.AND):
            op = "&&"
            right = self.parse_bitwise_or()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_bitwise_or(self) -> ASTNode:
        left = self.parse_bitwise_and()
        while self.peek().value == "|":
            self.advance()
            op = "|"
            right = self.parse_bitwise_and()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_bitwise_and(self) -> ASTNode:
        left = self.parse_comparison()
        while self.match(TokenType.AMP):
            op = "&"
            right = self.parse_comparison()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_comparison(self) -> ASTNode:
        left = self.parse_additive()
        while self.peek().type in (TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            op = self.advance().value
            right = self.parse_additive()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()
        while self.peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self.advance().value
            right = self.parse_multiplicative()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_unary()
        while self.peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self.advance().value
            right = self.parse_unary()
            left = BinaryOp(left=left, op=op, right=right, line=left.line, col=left.col)
        return left

    def parse_unary(self) -> ASTNode:
        if self.peek().type in (TokenType.MINUS, TokenType.BANG, TokenType.STAR, TokenType.AMP):
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryOp(op=op, operand=operand, line=operand.line, col=operand.col)
        return self.parse_call_or_primary()

    def parse_call_or_primary(self) -> ASTNode:
        tok = self.peek()

        # Grouping (expr)
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr

        # Literals
        if self.match(TokenType.INT_LIT):
            return Literal(value=int(tok.value.replace("_", ""), 0), lit_type="int", line=tok.line, col=tok.col)
        if self.match(TokenType.FLOAT_LIT):
            return Literal(value=float(tok.value.replace("_", "")), lit_type="float", line=tok.line, col=tok.col)
        if self.match(TokenType.STR_LIT):
            return Literal(value=tok.value, lit_type="str", line=tok.line, col=tok.col)
        if self.match(TokenType.BOOL_LIT):
            return Literal(value=(tok.value == "true"), lit_type="bool", line=tok.line, col=tok.col)

        # Identifier or Call (including chained call)
        if tok.type == TokenType.IDENT:
            name = self.advance().value
            
            # Function call? e.g. idkbro(...) or fuck()
            if self.peek().type == TokenType.LPAREN:
                args, named_args = self.parse_call_args()
                base_call = CallExpr(callee=name, args=args, named_args=named_args, line=tok.line, col=tok.col)
                
                # Check for chaining: .start() .retry(...)
                chain: List[CallExpr] = []
                while self.match(TokenType.DOT):
                    method_name = self.consume(TokenType.IDENT, "Expected method name after '.'").value
                    m_args, m_named = [], []
                    if self.peek().type == TokenType.LPAREN:
                        m_args, m_named = self.parse_call_args()
                    chain.append(CallExpr(callee=method_name, args=m_args, named_args=m_named, line=tok.line, col=tok.col))
                
                if chain:
                    return ChainedCall(base_call=base_call, chain=chain, line=tok.line, col=tok.col)
                return base_call

            # Struct initialization? e.g. Player{ id = 1, name = "Kaitlyn" }
            if self.peek().type == TokenType.LBRACE and self.peek(1).type == TokenType.IDENT and self.peek(2).type in (TokenType.ASSIGN, TokenType.COLON):
                self.advance() # {
                fields = []
                while self.peek().type != TokenType.RBRACE and self.peek().type != TokenType.EOF:
                    f_name = self.consume(TokenType.IDENT, "Expected field name in struct init").value
                    self.consume(TokenType.ASSIGN)
                    f_val = self.parse_expression()
                    fields.append((f_name, f_val))
                    self.match(TokenType.COMMA)
                    self.skip_semicolons()
                self.consume(TokenType.RBRACE)
                return StructInit(struct_name=name, fields=fields, line=tok.line, col=tok.col)

            # Index access? e.g. buffer[i]
            if self.peek().type == TokenType.LBRACKET:
                self.advance() # [
                idx_node = self.parse_expression()
                self.consume(TokenType.RBRACKET)
                return IndexExpr(target=Identifier(name=name, line=tok.line, col=tok.col), index=idx_node, line=tok.line, col=tok.col)

            node: ASTNode = Identifier(name=name, line=tok.line, col=tok.col)
            while self.match(TokenType.DOT):
                m_name = self.consume(TokenType.IDENT).value
                node = MemberAccess(target=node, member=m_name, line=tok.line, col=tok.col)

            return node

        raise SyntaxError(f"Unexpected token {tok.type} ('{tok.value}') at L{tok.line}:C{tok.col}")

    def parse_call_args(self) -> Tuple[List[ASTNode], List[Tuple[str, ASTNode]]]:
        self.consume(TokenType.LPAREN)
        args: List[ASTNode] = []
        named_args: List[Tuple[str, ASTNode]] = []

        while self.peek().type != TokenType.RPAREN and self.peek().type != TokenType.EOF:
            # Check for named arg: name = value or name: value
            if self.peek().type == TokenType.IDENT and self.peek(1).type in (TokenType.ASSIGN, TokenType.COLON):
                arg_name = self.advance().value
                self.advance() # = or :
                arg_val = self.parse_expression()
                named_args.append((arg_name, arg_val))
            else:
                args.append(self.parse_expression())

            if not self.match(TokenType.COMMA):
                break

        self.consume(TokenType.RPAREN)
        return args, named_args
