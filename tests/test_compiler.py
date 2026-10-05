# tests/test_compiler.py
# Comprehensive Unit Tests for the Katlin Toolchain

import unittest
import os
import subprocess

from src.lexer import Lexer, TokenType
from src.parser import Parser
from src.semantics import SemanticAnalyzer, SemanticError
from src.codegen import CodeGenerator
from src.compiler import compile_katlin, ROOT_DIR

class TestLexer(unittest.TestCase):
    def test_keywords_and_types(self):
        code = "fn mut strict raw struct enum match case test or"
        tokens = Lexer(code).tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        self.assertEqual(types, [
            TokenType.FN, TokenType.MUT, TokenType.STRICT, TokenType.RAW,
            TokenType.STRUCT, TokenType.ENUM, TokenType.MATCH, TokenType.CASE,
            TokenType.TEST, TokenType.OR_KW
        ])

    def test_literals(self):
        code = '100 0xFF 0b1010 3.14 "hello %" true false'
        tokens = Lexer(code).tokenize()
        vals = [t.value for t in tokens if t.type != TokenType.EOF]
        self.assertEqual(vals, ["100", "0xFF", "0b1010", "3.14", "hello %", "true", "false"])

        # Check that parser converts hex, binary, float, bool to native values
        ast = Parser(tokens).parse()
        parsed_vals = [s.expr.value for s in ast.statements]
        self.assertEqual(parsed_vals, [100, 255, 10, 3.14, "hello %", True, False])

    def test_pragma(self):
        code = "#strict\nfn test {}"
        tokens = Lexer(code).tokenize()
        self.assertEqual(tokens[0].type, TokenType.PRAGMA_STRICT)

class TestParser(unittest.TestCase):
    def test_parameterless_fn(self):
        code = "fn greet { println(\"Hi\"); }"
        ast = Parser(Lexer(code).tokenize()).parse()
        self.assertEqual(len(ast.statements), 1)
        self.assertEqual(ast.statements[0].name, "greet")
        self.assertEqual(len(ast.statements[0].params), 0)

    def test_for_step_loop(self):
        code = "fn main { for i in 0..100 step 10 { println(\"%\", i); } }"
        ast = Parser(Lexer(code).tokenize()).parse()
        func = ast.statements[0]
        for_stmt = func.body[0]
        self.assertEqual(for_stmt.var_name, "i")
        self.assertIsNotNone(for_stmt.step)

    def test_struct_def(self):
        code = "struct Vec2 { float x; float y; }"
        ast = Parser(Lexer(code).tokenize()).parse()
        struct_def = ast.statements[0]
        self.assertEqual(struct_def.name, "Vec2")
        self.assertEqual(len(struct_def.fields), 2)

    def test_test_block(self):
        code = 'test "sample" { assert(1 == 1, "ok"); }'
        ast = Parser(Lexer(code).tokenize()).parse()
        tb = ast.statements[0]
        self.assertEqual(tb.name, "sample")

class TestSemantics(unittest.TestCase):
    def test_strict_borrow_checker_catches_alias(self):
        code = """
#strict
fn swap(int &a, int &b) {}

fn main {
    mut int x = 10;
    swap(&x, &x);
}
"""
        ast = Parser(Lexer(code).tokenize()).parse()
        tokens = Lexer(code).tokenize()
        analyzer = SemanticAnalyzer(ast, file_strict=True)
        with self.assertRaises(SemanticError):
            analyzer.analyze()

    def test_strict_borrow_checker_allows_distinct_borrows(self):
        code = """
#strict
fn swap(int &a, int &b) {}

fn main {
    mut int x = 10;
    mut int y = 20;
    swap(&x, &y);
}
"""
        ast = Parser(Lexer(code).tokenize()).parse()
        analyzer = SemanticAnalyzer(ast, file_strict=True)
        # Should not raise exception
        analyzer.analyze()

class TestEndToEndExecution(unittest.TestCase):
    def test_run_idkbro(self):
        sample = os.path.join(ROOT_DIR, "examples", "idkbro.ktl")
        exit_code = compile_katlin(sample, run_after=False, optimize=True)
        self.assertEqual(exit_code, 0)

    def test_run_arena_benchmark(self):
        sample = os.path.join(ROOT_DIR, "examples", "arena_test.ktl")
        exit_code = compile_katlin(sample, run_after=False, optimize=True)
        self.assertEqual(exit_code, 0)

    def test_run_stdlib_showcase(self):
        sample = os.path.join(ROOT_DIR, "examples", "stdlib_showcase.ktl")
        exit_code = compile_katlin(sample, run_after=False, optimize=True)
        self.assertEqual(exit_code, 0)

if __name__ == "__main__":
    unittest.main()
