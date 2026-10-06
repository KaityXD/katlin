# The Katlin Language Architecture & Philosophy
**Mission:** Native-speed output, flexible syntax, clean static typing.

> **Accuracy notice.** Parts of this document describe the *intended* design,
> not the current implementation. For a verified list of what actually works
> today, see the support matrix in [README.md](README.md). Known divergences
> are flagged inline below.

---

## 1. The Core Pillars

1. **Fast output, honest about how**:
   - The compiler emits **C99**, which clang compiles with `-O3 -flto`. It is
     not a direct machine-code emitter, and there is no LLVM IR or Cranelift
     backend in the tree.
   - Zero Garbage Collector: allocation is explicit (`arena`, `vec`,
     `alloc_ints`, `malloc` via the runtime). Nothing is collected for you.
   - Cache-friendly contiguous memory layout (data-oriented design).

2. **The Memory Dial (Choose Your Strictness)**:
   - **Default (Pragmatic / Fast)** — stack-first value semantics. Working.
   - **`#strict`** — enforced by a source-level pass in the native compiler for
     two rules: no aliased mutable borrows within a call, and no borrowing of
     variables that were not declared `mut`. It is not a full borrow checker —
     no lifetimes, moves, scopes or struct-field borrows. See the README
     section of the same name for the exact scope.
   - **`raw` blocks and `*mut T` pointers** — *not implemented.* They fail with
     a C backend error rather than giving you bare-metal access.

3. **Syntactic Freedom ("Code Your Way")**:
   - Parentheses optional on parameterless functions: `fn main { ... }`.
   - Semicolons optional.
   - Printing with `%` positional slots (`println("Total: %", total)`), expanded
     to a type-generic C `_Generic` dispatch rather than a guessed specifier.
   - Named parameters and fluent chaining (`idkbro(timeout = 10).start()`) are
     *not implemented* in the native compiler.

4. **Clean Static Typing & Variables**:
   - Type-first declarations: `int x = 10;`, `str name = "Katlin"`.
   - Inferred typing with `:=`: `x := 10;` — this is the primary inference form.
   - `mut int count = 0;` and `mut count := 0;` both work.
   - `int &sum = 0;` as *local mutability syntax* is **not** supported; `&` is
     meaningful only in parameter lists (reference parameters).
   - Types are checked by the C compiler downstream. The Katlin front end
     infers enough to emit correct C but is not a full type checker, so some
     mistakes surface as clang diagnostics.

---

## 2. Memory Strictness Dial

```katlin
// DEFAULT: value semantics, explicit allocation. This works today.
fn process_audio([]f32 samples) { ... }   // slice syntax: not implemented

fn main {
    arena := arena_create(1 << 20);
    buf := arena_alloc(arena, 4096);
    // ... use buf ...
    arena_reset(arena);        // one bulk wipe, no per-object frees
    arena_destroy(arena);
}
```

The bare-metal dial is implemented for the cases that matter:

```katlin
fn fast_memcpy(*mut byte dest, *const byte src, usize count) {
    raw {
        mut usize i = 0;
        while i < count {
            *(dest + i) = *(src + i);
            i += 1;
        }
    }
}
```

`*mut T` becomes `T*`, `*const T` becomes `const T*`, pointer arithmetic and
deref-assignment work, and `raw { ... }` is accepted (currently as an ordinary
block with a marker comment — there are no distinct "raw" semantics to switch
to yet). See [`examples/pointers.ktl`](examples/pointers.ktl).

Allocation-free pointer work is also available without a `&`-parameter, via
`alloc_ints` and indexed access:

```katlin
fn main {
    ptr := alloc_ints(1024);      // int32_t*
    mut int i = 0;
    while i < 1024 {
        ptr[i] = 0;               // index assignment works
        i += 1;
    }
    free_ints(ptr);
}
```

---

## 3. "Code However You Want": Syntactic Freedom

> The examples in this section are **aspirational syntax**. Named arguments,
> fluent chaining and inner functions are not implemented by the native
> compiler; see [README.md](README.md) for the working subset.

### 3.1 Parameterless Functions (Parentheses Optional) — works
```katlin
fn main {
    println("no parentheses needed");
}
```

### 3.2 Named Arguments with `=` or `:` — implemented for `=`
```katlin
idkbro(timeout = 10, retries = 3);   // named, in any order
idkbro(10, 3);                       // positional
idkbro(10);                          // trailing defaults filled in
```
Defaults and named arguments are rewritten into positional form before
transpilation. The `name: value` colon form is not recognised.

### 3.3 Printing with Slot `%` — works
```katlin
println("Player % reached level % in % seconds", name, level, time);
```

---

## 4. Compiler Architecture: How It Runs Fast as Hell

```
[ Katlin Source (.ktl) ]
         │
         ▼
[ Lexer & Parser ]  (Flexible grammar, optional (), optional ';', named args, '%' slots)
         │
         ▼
[ Type Checker ]    (Hindley-Milner bidirectional inference + Safety Dial)
         │
         ▼
[ Katlin IR (KIR) ] (Flattens nested fn chains into scalar SSA registers)
         │
         ▼
[ LLVM Optimization Pipeline ] (-O3, SIMD auto-vectorization, inlining)
         │
         ▼
[ Native Binary (Machine Code) ] (x86_64, AArch64 / Apple Silicon, WASM)
```

### Why Nested `.fn()` Inlining is Zero-Cost:
When you write:
```katlin
idkbro(timeout = 10).start();
```
The **Katlin IR (KIR)** converts this directly into:
```llvm
%timeout = alloca i32
store i32 10, i32* %timeout
call void @idkbro_start(i32 10)
```
**No heap allocation. No pointer chasing. No runtime penalty.**
