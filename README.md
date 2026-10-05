# The Katlin Programming Language

**Statically typed. Compiles to native binaries. Zero garbage collection.**

Katlin (`.ktl`) is a systems programming language that compiles to native
machine code through a C99 backend. The compiler itself is written in Katlin
and bootstraps to a single native binary with no interpreter runtime.

---

## Status

This is an early-stage language implementation, published so the design is
readable and hackable. It is honest about what works:

| Area | State |
| :--- | :--- |
| Compiler | Self-hosted. `bin/katlin` is a native binary built from `compiler/main.ktl` |
| Backend | Emits C99, compiled with clang `-O3 -flto`. Not a direct machine-code emitter |
| Core language | Functions, structs, enums, `match`, loops, references, inference — working |
| Toolchain | `run`, `build`, `test`, `fmt`, `init`, cross-compilation — working |
| Memory | Arena, vector, string builder, raw heap buffers — working, no GC |
| `#strict` borrow checking | **Enforced** for aliased `&` borrows and borrows of immutable variables |
| Advanced syntax | Default/named arguments, inner functions, `or` fallbacks — **not implemented** |

See [Feature support](#feature-support) for the full matrix, and
[`examples/unsupported/`](examples/unsupported/README.md) for programs that
need the missing features.

---

## Quick start

```bash
git clone <this-repo> && cd katlin

./bin/katlin run examples/tour.ktl      # compile and run immediately
./bin/katlin build examples/tour.ktl -o /tmp/tour && /tmp/tour
./bin/katlin test examples/             # run all `test` blocks
./bin/katlin fmt examples/              # format sources
./bin/katlin init my_project            # scaffold a new project
```

`bin/katlin` is committed and ready to run. To rebuild it from source:

```bash
./build.sh              # bootstrap via the Python compiler in src/
./build.sh --verify     # additionally check the compiler can rebuild itself
```

---

## The language

```katlin
struct Point {
    int x;
    int y;
}

enum Color {
    Red,
    Green,
    Blue
}

fn color_code(Color c) -> int {
    mut int code = 0;
    match c {
        case .Red:   { code = 1; }
        case .Green: { code = 2; }
        case .Blue:  { code = 3; }
    }
    return code;
}

fn swap(int &a, int &b) {     // `&` parameters really write through
    int temp = a;
    a = b;
    b = temp;
}

fn main {
    mut answer := 42;                 // inferred typing
    println("answer: % (%)", answer, answer.type);   // .type resolved at compile time

    p := Point{ x = 3, y = 4 };
    println("dist2 = %", p.x * p.x + p.y * p.y);

    println("green => %", color_code(Color.Green));

    mut a := 1;
    mut b := 2;
    swap(&a, &b);
    println("swapped: % %", a, b);

    for i in 0..10 step 3 {
        println("step: %", i);
    }
}
```

More in [`examples/tour.ktl`](examples/tour.ktl) and
[`SYNTAX.md`](SYNTAX.md).

---

## Feature support

Verified by `tests/run_tests.sh` against the shipped binary.

### Working

- `fn`, `fn main`, return-type annotations, parentheses-optional declarations
- Inferred typing with `:=`, including compile-time `value.type`
- Explicit types: `int`, `i64`, `str`, `bool`, `float`, `vec`, `sb`
- `mut` declarations, both typed (`mut int x = 1`) and inferred (`mut x := 1`)
- `if` / `else`, `while`, `for i in a..b step n`, `loop`
- Compound assignment (`+=`, `-=`, `*=`, `/=`)
- `struct` definitions, `Point{ x = 1, y = 2 }` literals, member access
- `enum` definitions, `Color.Green` variants, `match` with `case .Variant:`
- Reference parameters (`int &a`) — writes propagate to the caller
- Address-of `&x` and dereference `*p`, including `*p = value`
- `#strict` borrow checking: rejects aliased mutable borrows and borrows of
  immutable variables, with line/column diagnostics (see below)
- `println` / `print` with `%` placeholders (type-generic, no format guessing)
- `test "name" { ... }` blocks and the `katlin test` runner
- Runtime: arena allocator, dynamic vector, string builder, string helpers,
  file I/O, CLI args, `min`/`max`/`abs`, timing and RSS measurement
- Toolchain flags: `--debug`, `--release`, `--target=<triple>`, `--sysroot=<dir>`

### Not implemented

| Feature | Behaviour today |
| :--- | :--- |
| Default arguments | C backend error |
| Named arguments | C backend error |
| Inner functions / fluent `.start()` chaining | C backend error |
| `or` fallback expressions | C backend error |
| Reference struct fields (`int &balance`) | C backend error |
| Local `int &x = 0` mutability syntax | C backend error |
| `*mut T` / `*const T` pointer types | C backend error |
| `raw { ... }` blocks | C backend error |

---

## `#strict` borrow checking

A file-level `#strict` pragma turns on compile-time aliasing checks. Two rules
are enforced, before any code is generated:

1. **No aliased mutable borrows.** Within one call, the same variable may not
   be borrowed with `&` twice.
2. **No borrowing immutables.** A variable declared without `mut` cannot be
   passed as `&x`.

```katlin
#strict

fn swap(int &a, int &b) { int t = a; a = b; b = t; }

fn main {
    mut int x = 1;
    mut int y = 2;
    swap(&x, &y);      // OK: two distinct variables
    swap(&x, &x);      // error: cannot borrow `x` as mutable more than once
}
```

```
$ katlin build examples/borrow_fail.ktl
error: cannot borrow `x` as mutable more than once at a time
  --> examples/borrow_fail.ktl:15
   = note: #strict forbids aliased mutable references (&)
```

Runnable examples: [`examples/strict_borrows.ktl`](examples/strict_borrows.ktl)
(passes), [`examples/borrow_fail.ktl`](examples/borrow_fail.ktl) and
[`examples/borrow_immutable.ktl`](examples/borrow_immutable.ktl) (rejected).

**Scope, stated plainly.** This is a source-level pass, not a full borrow
checker. It does not track lifetimes, moves, scopes, or struct fields, and it
uses one flat namespace for mutability. `&` is only treated as a borrow in an
argument or parameter position, so bitwise-and (`count & 1`) is never
misread. Treat it as a guard against the common aliasing mistake, not as
Rust-grade safety.

The Python bootstrap compiler in `src/` implements several of these
(default/named arguments, inner functions, a narrow aliased-`&` check, `or`
fallbacks). The two implementations are not yet at parity.

---

## Architecture

```
compiler/main.ktl   Katlin source of the compiler (self-hosted)
        |
        |  bin/katlin_py build  (Python bootstrap, src/)
        v
   bin/katlin       native binary, no runtime dependency
        |
        |  transpiles .ktl -> C99, then invokes clang
        v
   native executable
```

The native compiler scans Katlin source and emits C99, which clang optimises
with `-O3 -flto -march=native`. `std/katlin_runtime.h` provides the runtime as
`static inline` C, so the generated program is self-contained.

Two details worth knowing:

- **Compile-time, not runtime, type info.** `value.type` on a `:=` variable is
  resolved during transpilation and emitted as a string literal.
- **`%` placeholders are type-generic.** `println("x = %", v)` expands to a
  `_Generic` dispatch in C rather than a guessed `printf` format specifier, so
  a mismatch cannot silently print garbage.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the longer design notes.

---

## Benchmarks

Measured on one x86-64 machine, `-O3 -flto -march=native`:

| Benchmark | Operations | `--release` | `--debug` |
| :--- | :--- | :--- | :--- |
| Integer counter with checksum | 1,000,000,000 | 0.0021 s | 1.78 s |
| Heap buffer fill | 25,000,000 ints (100 MB) | ~0.009 s | — |
| Arena alloc + bulk reset | 100,000 objects | < 1 µs | — |

The counter result is real but worth reading carefully: the loop genuinely
executes a billion iterations (the checksum is verified), and clang vectorises
it four-wide and unrolls it 64×, so ~4 million loop passes do the work of a
billion scalar ones. The `--debug` column shows the same loop without
vectorisation. These are compiler-throughput numbers, not a claim about the
language being magically faster than C.

Reproduce with:

```bash
./bin/katlin run examples/count_billion.ktl
./bin/katlin build examples/count_billion.ktl --debug -o /tmp/cb_dbg && /tmp/cb_dbg
```

---

## Testing

```bash
./tests/run_tests.sh                    # 28 end-to-end tests, shipped binary
python3 -m unittest discover tests/     # 14 unit tests, Python bootstrap
```

`tests/run_tests.sh` is the one that matters for releases: it covers CLI exit
codes, language features, the test runner, the formatter, scaffolding, and
every file in `examples/`. CI runs both suites plus a formatter idempotency
check.

---

## Repository layout

```
bin/katlin              Bootstrapped native compiler (committed)
bin/katlin_py           Python bootstrap driver
compiler/main.ktl       Compiler source, written in Katlin
src/                    Python bootstrap compiler (lexer, parser, codegen)
std/katlin_runtime.h    Runtime + standard library, as static inline C
examples/               Working programs; unsupported/ holds the rest
tests/run_tests.sh      End-to-end tests for the shipped binary
tests/test_compiler.py  Unit tests for the Python bootstrap
build.sh                Bootstrap script (./build.sh --verify)
editors/vscode/         Syntax highlighting and snippets
SYNTAX.md               Language reference
ARCHITECTURE.md         Design notes
```

---

## Roadmap

1. Replace the character-level scanner with a real lexer/parser/AST in
   `compiler/main.ktl`. Most missing features are blocked on this.
2. Deepen `#strict`: lifetime and move tracking, scope-aware mutability, and
   struct field borrows. Today it covers aliased `&` borrows only.
3. Argument defaults and named arguments.
4. Inner functions with scope capture.
5. Incremental compilation — avoid re-running clang when the generated C is
   unchanged.

---

## License

MIT — see [LICENSE](LICENSE).
