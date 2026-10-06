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
        # idkbro exercises fluent chaining and default arguments, which the
        # Python bootstrap compiler supports but the native compiler does not
        # yet. It therefore lives under examples/unsupported/ .
        sample = os.path.join(ROOT_DIR, "examples", "unsupported", "idkbro.ktl")
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

    def test_run_multi_module(self):
        sample = os.path.join(ROOT_DIR, "examples", "multi_module", "main.ktl")
        bin_path = os.path.join(ROOT_DIR, ".build", "bin", "multi_module_test")
        exit_code = compile_katlin(sample, output_binary=bin_path, run_after=False, optimize=True)
        self.assertEqual(exit_code, 0)
        res = subprocess.run([bin_path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Vector 1: (3, 4)", res.stdout)
        self.assertIn("Sum: (8, 16)", res.stdout)
        self.assertIn("Dot product: 63", res.stdout)

    def test_missing_import_raises_error(self):
        from src.compiler import bundle_imports
        from src.diagnostics import KatlinError
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ktl", mode="w", delete=False) as f:
            f.write('import "nonexistent_file_xyz.ktl";\nfn main() {}\n')
            temp_path = f.name
        try:
            with self.assertRaises(KatlinError) as ctx:
                bundle_imports(temp_path)
            self.assertIn("cannot find imported module", str(ctx.exception))
        finally:
            os.remove(temp_path)

    def test_imported_main_raises_error(self):
        from src.compiler import bundle_imports
        from src.diagnostics import KatlinError
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ktl", mode="w", delete=False) as f_sub:
            f_sub.write('fn main() { println("sub"); }\n')
            sub_path = f_sub.name
        with tempfile.NamedTemporaryFile(suffix=".ktl", mode="w", delete=False) as f_top:
            f_top.write(f'import "{sub_path}";\nfn main() {{ println("top"); }}\n')
            top_path = f_top.name
        try:
            with self.assertRaises(KatlinError) as ctx:
                bundle_imports(top_path)
            self.assertIn("cannot define 'fn main'", str(ctx.exception))
        finally:
            os.remove(sub_path)
            os.remove(top_path)

class TestDiagnostics(unittest.TestCase):
    def test_lexer_error_diagnostic(self):
        from src.diagnostics import KatlinLexerError, render_diagnostic
        code = 'fn main {\n    msg := "unclosed string\n}'
        err = KatlinLexerError("unterminated string literal", line=2, col=12, length=15, help_text='close string with "')
        diag = render_diagnostic("main.ktl", code, err)
        self.assertIn("unterminated string literal", diag)
        self.assertIn("main.ktl:2:12", diag)
        self.assertIn("^", diag)
        self.assertIn("help", diag)

    def test_borrow_error_diagnostic(self):
        from src.diagnostics import KatlinSemanticError, render_diagnostic
        code = '#strict\nfn main {\n    mut int x = 10;\n    swap(&x, &x);\n}'
        err = KatlinSemanticError(
            "cannot borrow `x` as mutable more than once simultaneously",
            line=4,
            col=14,
            length=2,
            note="in #strict mode, aliasing mutable references is forbidden",
            help_text="pass separate variables",
            secondary_spans=[(4, 10, 2, "first mutable borrow occurs here")]
        )
        diag = render_diagnostic("main.ktl", code, err)
        self.assertIn("cannot borrow `x`", diag)
        self.assertIn("main.ktl:4:14", diag)
        self.assertIn("first mutable borrow occurs here", diag)
        self.assertIn("second mutable borrow occurs here", diag)
        self.assertIn("note", diag)
        self.assertIn("help", diag)

if __name__ == "__main__":
    unittest.main()
