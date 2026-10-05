# The Katlin Programming Language
**Fast as C/C++. Flexible as your thoughts. Statically typed. Zero Garbage Collection.**

---

## ⚡ What is Katlin?

Katlin (`.ktl`) is a modern, bare-metal systems programming language combining the raw speed of C and C++ with the cleanest, most flexible syntax possible. It compiles directly to native static binaries with Clang `-O3 -flto` optimizations and provides a 3-tier memory model (Stack, Arena, Heap) with **Zero mandatory garbage collection**.

### Key Language Features:
- **`fn` inside `fn` with Fluent Dot-Chaining**: Write `idkbro(timeout = 10).start()` without class or builder boilerplate. Flattens into registers via SROA.
- **Parentheses-Optional Functions**: Clean parameterless functions `fn fuck { ... }` or `fn main { ... }`.
- **Flexible Declarations**: Type-first (`int score = 100;`), inferred dynamic typing (`total := a + b;`), and explicit struct types (`Point pt = Point{ x = 1, y = 2 }`).
- **Choose Your Mutability**: Both C/Rust-style `int &sum = 0;` AND `mut int sum = 0;`.
- **The Memory Dial**:
  - Regular safe mode.
  - `#strict` borrow-checked mode (detects aliased mutable references at compile-time).
  - `raw { ... }` blocks with raw pointer manipulation.
- **First-Class Arena Bump Allocators**: Allocate millions of micro-objects and wipe them in a single CPU cycle.
- **Zero-Brace `%` Format Strings**: `println("Score: %, Name: %", score, name)`.
- **Postfix Guard Clauses**: `return if timeout <= 0;`.
- **Ranges with Custom Step**: `for i in 0..100 step 10 { ... }`.
- **Match & Tagged Enums**: Pattern matching on enum variants (`match state { case .Idle: ... }`).
- **First-Class Unit Tests**: Write `test "description" { assert(...); }` blocks right in your source files and execute with `katlin test`.

---

## 🏎️ Verified Benchmarks

| Benchmark | Language / Backend | Operations | Time | Speedup vs Python |
| :--- | :--- | :--- | :--- | :--- |
| **0 to 1,000,000,000 Counter** | Katlin (`-O3`) | 1 Billion ops + checksum | **0.002287 s** | **~22,000x** |
| **100 MB RAM Allocation & Write** | Katlin Raw Memory | 25,000,000 integers | **0.013098 s** | **7.6 GB/sec** (0 GC overhead) |
| **Arena Bump-Allocator** | Katlin Arena | 100,000 allocations | **< 1 µs** | Instant 1-cycle bulk wipe |

---

## 🛠️ Katlin Toolchain CLI

Katlin ships with a single unified CLI (`bin/katlin`):

### 1. Run Katlin Code Immediately
```bash
katlin run examples/idkbro.ktl
```

### 2. Build Native Static Executable
```bash
katlin build examples/idkbro.ktl -o myapp
./myapp
```

### 3. Cross-Compile to Other Architectures
```bash
# Windows
katlin build src/main.ktl --target=x86_64-w64-mingw32 -o app.exe

# ARM64 / Linux
katlin build src/main.ktl --target=aarch64-linux-gnu -o app_arm64
```

### 4. Run Built-in Test Suites
Finds and runs all `test "name" { ... }` blocks across your project:
```bash
katlin test
```

### 5. Auto-Format Code
```bash
katlin fmt .
```

### 6. Scaffold a New Project
```bash
katlin init my_project
cd my_project
katlin run src/main.ktl
```

---

## 📦 Standard Library (`std`)

Katlin includes an embedded bare-metal standard library with zero runtime bloat:

- **Memory (`std/katlin_runtime.h`)**:
  - `arena_create(capacity)`
  - `arena_alloc(arena, size)`
  - `arena_reset(arena)` (1 CPU cycle bulk wipe)
  - `arena_destroy(arena)`
  - `alloc_ints(count)` / `free_ints(ptr)`
- **Dynamic Vector**:
  - `vec_create(cap)`
  - `vec_push(vec, val)`
  - `vec_get(vec, idx)`
  - `vec_set(vec, idx, val)`
  - `vec_len(vec)`
  - `vec_free(vec)`
- **File I/O**:
  - `file_read(path)` -> `str`
  - `file_write(path, text)` -> `bool`
  - `file_append(path, text)` -> `bool`
  - `file_exists(path)` -> `bool`
- **Strings**:
  - `str_len(s)` -> `int`
  - `str_eq(a, b)` -> `bool`
  - `str_concat(a, b)` -> `str`
- **Math & Profiling**:
  - `abs(x)`, `min(a, b)`, `max(a, b)`
  - `time_now()` -> high-resolution timestamp in seconds
  - `get_ram_mb()` -> live Resident Set Size physical RAM consumption

---

## 🎨 Visual Studio Code Extension

Katlin includes full syntax highlighting, bracket matching, and snippets for VS Code.

To install into your local VS Code editor:
```bash
cp -r editors/vscode ~/.vscode/extensions/katlin-lang-0.1.0
```
Restart VS Code and all `.ktl` files will have syntax coloring and snippets.

---

## 🧪 Running Automated Tests

Run the full Python-based compiler test suite:
```bash
python3 -m unittest discover tests/
```

Run Katlin's native test suites:
```bash
./bin/katlin test examples/
```

---

## 📁 Repository Structure

```
├── bin/
│   └── katlin                  # Katlin CLI Tool
├── src/
│   ├── ast_nodes.py            # AST Node Definitions
│   ├── lexer.py                # Tokenizer (Hex, Binary, Pragmas, Keywords)
│   ├── parser.py               # Recursive Descent Parser
│   ├── semantics.py            # Semantic Analyzer & #strict Borrow Checker
│   ├── codegen.py              # C99/LLVM Native Code Generator & Test Runner
│   ├── formatter.py            # Source Code Formatter (katlin fmt)
│   └── compiler.py             # Compiler Driver (run, build, test, fmt, init)
├── std/
│   └── katlin_runtime.h        # Bare-Metal Runtime & Standard Library
├── editors/
│   └── vscode/                 # VS Code Language Extension (.tmLanguage.json)
├── tests/
│   └── test_compiler.py        # Automated Compiler Unit Tests
├── examples/
│   ├── idkbro.ktl              # Fluent chained calls & mutability showcase
│   ├── count_billion.ktl       # 1 Billion operation speed benchmark
│   ├── memory_test.ktl         # 100 MB RAM allocation & throughput test
│   ├── arena_test.ktl          # 1-cycle bulk arena wipe benchmark
│   ├── stdlib_showcase.ktl     # File I/O, Strings, Vectors showcase
│   └── core_tests.ktl          # Structs, Enums, and Core Language Tests
├── SYNTAX.md                   # Full Katlin Syntax Guide
└── ARCHITECTURE.md             # Compiler Internals & Memory Architecture
```
