# src/compiler.py
# The Katlin Compiler Driver & CLI Toolchain

import os
import sys
import re
import subprocess
import glob
from typing import Optional, List
from src.lexer import Lexer
from src.parser import Parser
from src.semantics import SemanticAnalyzer, SemanticError
from src.codegen import CodeGenerator
from src.formatter import format_katlin_code
from src.diagnostics import KatlinError, render_diagnostic, render_backend_error

VERSION = "0.1.0"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STD_DIR = os.path.join(ROOT_DIR, "std")

def compile_katlin(
    source_path: str,
    output_binary: Optional[str] = None,
    optimize: bool = True,
    run_after: bool = False,
    test_mode: bool = False,
    target: Optional[str] = None,
    extra_args: Optional[List[str]] = None
) -> int:
    if not os.path.exists(source_path):
        print(f"[Error]: Source file not found: {source_path}", file=sys.stderr)
        return 1

    with open(source_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    try:
        # Step 1: Lexing
        tokens = Lexer(source_code).tokenize()

        # Step 2: Parsing
        ast = Parser(tokens).parse()

        # Step 3: Semantic Analysis & Strict Borrow Checking
        file_is_strict = any(t.type == "#strict" for t in tokens)
        analyzer = SemanticAnalyzer(ast, file_strict=file_is_strict)
        analyzer.analyze()

        # Step 4: Code Generation
        c_code = CodeGenerator(ast, test_mode=test_mode).generate()

    except KatlinError as ke:
        print(render_diagnostic(source_path, source_code, ke), file=sys.stderr)
        return 1
    except Exception as e:
        err = KatlinError(str(e))
        print(render_diagnostic(source_path, source_code, err), file=sys.stderr)
        return 1

    # Step 5: Write intermediate C code
    build_dir = os.path.join(ROOT_DIR, ".build")
    os.makedirs(build_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    if test_mode:
        base_name += "_test"
    c_file = os.path.join(build_dir, f"{base_name}.c")
    
    with open(c_file, "w", encoding="utf-8") as f:
        f.write(c_code)

    # Step 6: Determine binary output path
    if output_binary is None:
        bin_dir = os.path.join(build_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        ext = ".exe" if (target and "windows" in target) else ""
        output_binary = os.path.join(bin_dir, f"{base_name}{ext}")

    # Step 7: Native Compilation via Clang or GCC
    compiler_cmd = "clang" if os.system("which clang > /dev/null 2>&1") == 0 else "gcc"
    opt_flags = ["-O3", "-flto"] if optimize else ["-O0", "-g"]
    if not target:
        opt_flags.append("-march=native")
    
    compile_args = [
        compiler_cmd,
        c_file,
        f"-I{STD_DIR}",
        "-o", output_binary,
    ] + opt_flags

    if target:
        compile_args.append(f"--target={target}")

    res = subprocess.run(compile_args, capture_output=True, text=True)
    if res.returncode != 0:
        print(render_backend_error(res.stderr, source_path, source_code), file=sys.stderr)
        return res.returncode

    # Step 8: Run if requested
    if run_after:
        run_cmd = [output_binary] + (extra_args if extra_args else [])
        run_res = subprocess.run(run_cmd)
        return run_res.returncode

    if not test_mode:
        print(f"✓ Successfully built: {output_binary}")
    return 0

def run_tests(target_path: Optional[str] = None) -> int:
    files_to_test = []
    if target_path and os.path.isfile(target_path):
        files_to_test.append(target_path)
    else:
        search_dir = target_path if (target_path and os.path.isdir(target_path)) else "."
        # Find all .ktl files
        for root, _, files in os.walk(search_dir):
            if ".build" in root or ".git" in root:
                continue
            for f in files:
                if f.endswith(".ktl"):
                    full_p = os.path.join(root, f)
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as kf:
                        content = kf.read()
                        if re.search(r'test\s+"[^"]+"\s*\{', content):
                            files_to_test.append(full_p)

    if not files_to_test:
        print("No test files found with 'test' blocks.")
        return 0

    print(f"Found {len(files_to_test)} test file(s).")
    total_exit = 0
    for f in files_to_test:
        print(f"\n--- Testing: {f} ---")
        ret = compile_katlin(f, run_after=True, test_mode=True, optimize=False)
        if ret != 0:
            total_exit = ret

    return total_exit

def format_path(target_path: str):
    if os.path.isfile(target_path):
        files = [target_path]
    elif os.path.isdir(target_path):
        files = glob.glob(os.path.join(target_path, "**/*.ktl"), recursive=True)
    else:
        print(f"Path not found: {target_path}")
        return

    formatted_count = 0
    for fp in files:
        if ".build" in fp:
            continue
        with open(fp, "r", encoding="utf-8") as f:
            code = f.read()
        new_code = format_katlin_code(code)
        if new_code != code:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(new_code)
            print(f"Formatted: {fp}")
            formatted_count += 1

    print(f"✓ Formatted {formatted_count} file(s).")

def init_project(name: str):
    if os.path.exists(name):
        print(f"Error: Directory '{name}' already exists.")
        return 1

    os.makedirs(os.path.join(name, "src"), exist_ok=True)
    os.makedirs(os.path.join(name, "tests"), exist_ok=True)

    toml_content = f'''[project]
name = "{name}"
version = "0.1.0"
author = "Developer"

[build]
opt_level = 3
'''
    with open(os.path.join(name, "katlin.toml"), "w") as f:
        f.write(toml_content)

    main_ktl = '''// src/main.ktl
// Welcome to Katlin! Blazing fast, zero-GC systems programming.

fn main {
    println("Hello, Katlin %!", "0.1.0");
    
    // Quick demonstration: Range loop with step
    mut int total = 0;
    for i in 0..10 step 2 {
        total += i;
    }
    println("Sum of even numbers below 10: %", total);
}
'''
    with open(os.path.join(name, "src", "main.ktl"), "w") as f:
        f.write(main_ktl)

    test_ktl = '''// tests/main_test.ktl

fn add(int a, int b) -> int {
    return a + b;
}

test "verify addition" {
    assert(add(2, 3) == 5, "2 + 3 must be 5");
}

test "verify string operations" {
    name := "Katlin";
    assert(str_len(name) == 6, "Length of 'Katlin' is 6");
}
'''
    with open(os.path.join(name, "tests", "main_test.ktl"), "w") as f:
        f.write(test_ktl)

    gitignore = '''.build/
bin/
*.o
*.a
*.so
'''
    with open(os.path.join(name, ".gitignore"), "w") as f:
        f.write(gitignore)

    readme = f'''# {name}

A blazing fast systems project built with [Katlin](https://katlin-lang.org).

## Commands

- **Run application**:
  ```bash
  katlin run src/main.ktl
  ```

- **Run tests**:
  ```bash
  katlin test
  ```

- **Build optimized native binary**:
  ```bash
  katlin build src/main.ktl -o {name}
  ```

- **Auto-format source code**:
  ```bash
  katlin fmt .
  ```
'''
    with open(os.path.join(name, "README.md"), "w") as f:
        f.write(readme)

    print(f"✓ Initialized new Katlin project in '{name}'")
    print("  Run 'katlin run src/main.ktl' to get started!")
    return 0

def print_help():
    print(f"Katlin Programming Language v{VERSION}")
    print("Usage: katlin <command> [options]\n")
    print("Commands:")
    print("  run <file.ktl> [args...]      Compile and execute Katlin source immediately")
    print("  build <file.ktl> [options]    Compile Katlin source to a native static binary")
    print("  test [path]                   Find and run all test blocks across the project")
    print("  fmt [path]                    Auto-format .ktl source files")
    print("  init <project_name>           Scaffold a new Katlin application project")
    print("  version, --version            Display Katlin compiler version info")
    print("\nBuild Options:")
    print("  -o <file>                     Specify output binary path")
    print("  --target <triple>             Cross-compile for target (e.g. x86_64-w64-mingw32, aarch64-linux-gnu)")
    print("  --debug                       Compile with -O0 -g without optimizations")
    print("  --release                     Compile with full -O3 -flto optimizations (default)")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_help()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd in ("-v", "--version", "version"):
        print(f"Katlin Compiler v{VERSION} (Native C99 / LLVM Backend)")
        sys.exit(0)

    elif cmd == "run":
        if len(sys.argv) < 3:
            print("Error: No input file specified.")
            sys.exit(1)
        source_file = sys.argv[2]
        extra_args = sys.argv[3:]
        sys.exit(compile_katlin(source_file, run_after=True, extra_args=extra_args))

    elif cmd == "build":
        if len(sys.argv) < 3:
            print("Error: No input file specified.")
            sys.exit(1)
        source_file = sys.argv[2]
        out_bin = None
        target = None
        optimize = True
        
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-o" and i + 1 < len(args):
                out_bin = args[i + 1]
                i += 2
            elif arg.startswith("--target="):
                target = arg.split("=", 1)[1]
                i += 1
            elif arg == "--target" and i + 1 < len(args):
                target = args[i + 1]
                i += 2
            elif arg == "--debug":
                optimize = False
                i += 1
            elif arg == "--release":
                optimize = True
                i += 1
            else:
                i += 1

        sys.exit(compile_katlin(source_file, output_binary=out_bin, optimize=optimize, run_after=False, target=target))

    elif cmd == "test":
        target_path = sys.argv[2] if len(sys.argv) > 2 else "."
        sys.exit(run_tests(target_path))

    elif cmd == "fmt":
        target_path = sys.argv[2] if len(sys.argv) > 2 else "."
        format_path(target_path)
        sys.exit(0)

    elif cmd == "init":
        if len(sys.argv) < 3:
            print("Error: Project name required. E.g.: katlin init my_project")
            sys.exit(1)
        project_name = sys.argv[2]
        sys.exit(init_project(project_name))

    else:
        # If user typed 'katlin file.ktl', default to run
        if os.path.exists(cmd):
            sys.exit(compile_katlin(cmd, run_after=True, extra_args=sys.argv[2:]))
        else:
            print(f"Unknown command: {cmd}")
            print_help()
            sys.exit(1)

if __name__ == "__main__":
    main()
