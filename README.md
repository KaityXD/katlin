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
| Arguments | Default arguments, named arguments, postfix guard clauses — working |
| Error handling | `or` fallbacks: value default, `or return`, `or panic(...)` — working |
| Memory | Arena, vector, string builder, raw pointers, `raw` blocks — working, no GC |
| Toolchain | `run`, `build`, `check`, `test`, `fmt`, `init`, cross-compilation — working |
| Builds | Incremental; unchanged sources skip clang entirely |
| `#strict` borrow checking | **Enforced** for aliased `&` borrows and borrows of immutable variables |
| Inner functions | Fluent `.start()` chaining — **not implemented** |

See [Feature support](#feature-support) for the full matrix, and
[`examples/unsupported/`](examples/unsupported/README.md) for programs that
need the missing features.

---

## Quick start

```bash
git clone <this-repo> && cd katlin

./bin/katlin run examples/tour.ktl      # compile and run immediately
./bin/katlin run examples/pointers.ktl  # raw pointers and raw { } blocks
./bin/katlin run examples/arguments.ktl # defaults, named args, guards
./bin/katlin run examples/fallbacks.ktl # `or` fallbacks
./bin/katlin build examples/tour.ktl -o /tmp/tour && /tmp/tour
./bin/katlin check examples/tour.ktl    # type-check only, no binary
./bin/katlin test examples/             # run all `test` blocks
./bin/katlin fmt examples/              # format sources
./bin/katlin init my_project            # scaffold a new project
```

`bin/katlin` is committed and ready to run. To rebuild it from source:

```bash
./build.sh              # bootstrap via the Python compiler in src/
./build.sh --verify     # additionally check the compiler can rebuild itself
PREFIX=~/.local ./install.sh   # install to <prefix>/bin + <prefix>/lib/katlin/std
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
- Explicit types: `int`, `i64`, `u64`, `str`, `bool`, `float`, `byte`, `usize`,
  `vec`, `sb`, `arena`
- `mut` declarations, typed (`mut int x = 1`) and inferred (`mut x := 1`)
- `if` / `else`, `while`, `for i in a..b step n`, `loop`
- Compound assignment (`+=`, `-=`, `*=`, `/=`)
- `struct` definitions, `Point{ x = 1, y = 2 }` literals, member access
- `enum` definitions, `Color.Green` variants, `match` with `case .Variant:`
- Reference parameters (`int &a`) — writes propagate to the caller
- Address-of `&x` and dereference `*p`, including `*p = value`
- Raw pointers: `*mut T`, `*const T`, pointer arithmetic, `raw { ... }` blocks
- Default arguments and named arguments in any order
- Postfix guard clauses: `return if cond;`
- `or` fallbacks: `x := f() or 8080`, `or return`, `or panic("...")`
- `#strict` borrow checking: rejects aliased mutable borrows and borrows of
  immutable variables, with line/column diagnostics (see below)
- `println` / `print` with `%` placeholders (type-generic, no format guessing)
- `test "name" { ... }` blocks and the `katlin test` runner
- `katlin.toml` `opt_level`, read at build time
- Runtime: arena allocator, dynamic vector, string builder, string helpers,
  file I/O, CLI args, `min`/`max`/`abs`/`hash`, timing and RSS measurement
- Toolchain flags: `--debug`, `--release`, `--target=<triple>`, `--sysroot=<dir>`

### Not implemented

| Feature | Behaviour today |
| :--- | :--- |
| Inner functions / fluent `.start()` chaining | C backend error |
| Reference struct fields (`int &balance`) | C backend error |
| Member access through a `&` parameter (`from.balance`) | C backend error |
| Local `int &x = 0` mutability syntax | C backend error |
| `strict fn` (per-function strict mode) | Not recognised |
| `or` nested inside a call argument | C backend error |
| Implicit return of a function's last expression | C backend error |
| `import` / multi-file projects | Silently ignored |

Inner functions are the significant gap: capturing a closure's environment
needs to know the shape of the enclosing scope, which the character-level
front end cannot determine. That is the main item in the roadmap below.

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

Three details worth knowing:

- **Source-to-source pre-passes.** Named arguments, parameter defaults and
  `or` fallbacks are rewritten into plain Katlin/C before transpilation, so
  the character scanner never has to reorder arguments or wrap expressions as
  it emits them. Anything a pass cannot parse confidently is left untouched
  rather than guessed at.
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
./tests/run_tests.sh                    # 66 end-to-end tests, shipped binary
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
   `compiler/main.ktl`. Inner functions with scope capture, reference struct
   fields, member access through `&` parameters, and implicit last-expression
   returns are all blocked on this — they need to know the shape of an
   expression, which a scanner cannot determine.
2. Deepen `#strict`: lifetime and move tracking, scope-aware mutability, and
   struct field borrows. Today it covers aliased `&` borrows only.
3. `import` and multi-file projects. Currently `import` is silently skipped.
4. An LSP so editors get the diagnostics the compiler already produces.
5. Cross-compilation is wired up (`--target`, `--sysroot`) but untested
   against a real cross toolchain; add a CI job with one.
6. Warning infrastructure — the compiler reports errors only.

---

## License

MIT — see [LICENSE](LICENSE).
