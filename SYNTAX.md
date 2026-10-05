# The Katlin Language Syntax Reference
**Tagline:** Blazing Native Speed. Statically Typed. Total Coding Freedom.

---

## 1. Variables & Mutability: Total Freedom

Katlin lets you choose the syntax that fits your coding style.

### 1.1 Explicit Types (Clean & Direct)
```katlin
int score = 100;
str name = "Katlin"
bool is_ready = true;
```

### 1.2 Mutability: Choose Between `&` or `mut`
Declare mutable variables using either the `&` ampersand modifier or the `mut` keyword:

```katlin
// Style A: Ampersand '&'
int &sum = 0;
str &buffer = ""

// Style B: 'mut' keyword
mut int gayppl = 3;
mut bool running = true;

// Both work identically!
sum += 10;
gayppl += 1;
```

### 1.3 Dynamic / Inferred Typing (`:=`)
When you don't feel like typing the type name, use `:=`:

```katlin
// Type inferred automatically at compile time:
x := 10;                     // Inferred as int
player := "Kaitlyn"          // Inferred as str
config := load_config()      // Inferred from return type

// Mutable inferred:
mut count := 0;
&speed := 1.5;
```

### 1.4 Optional Semicolons `;`
Put semicolons at the end of every line, or omit them completely. The compiler accepts both:

```katlin
int a = 1;
mut int b = 2;

int c = 3
mut int d = 4
```

---

## 2. Printing & String Formatting: Clean Slot `%`

Katlin rejects ugly braces `{}` inside strings. Format strings use clean, type-safe **`%` slots**:

```katlin
// Single slot
println("Total: %", total);

// Multiple slots (statically checked at compile-time)
println("Player % scored % in % seconds", name, score, time);

// Print simple string
println("Server started successfully");
```

---

## 3. Functions & Fluent Dot-Chaining

### 3.1 Parentheses-Optional Functions
Empty parentheses are optional on function declarations:

```katlin
fn fuck {
    idkbro(
        timeout = 10
    ).start();
}

fn main {
    println("Running fast!");
}
```

### 3.2 Named Arguments with `=` or `:`
```katlin
idkbro(timeout = 10, retries = 3).start();   // Python/Zig style
idkbro(timeout: 10, retries: 3).start();   // Swift/Odin style
idkbro(10, 3).start();                     // Positional
```

### 3.3 Nested Functions with Auto-Chaining
Declare inner functions inside any function. Chaining without explicit return automatically propagates the context:

```katlin
fn idkbro(int timeout = 5) {
    mut int current_timeout = timeout;
    mut int retries = 1;

    fn retry(int count) {
        retries = count;
    }

    fn start {
        println("idkbro started: timeout=%, retries=%", current_timeout, retries);
    }
}
```

---

## 4. The Memory Strictness Dial

Katlin lets you choose how strict or bare-metal your memory management is:

### Dial 1: `#strict` at Line 1 (File-Level Safety)
Put `#strict` at the top of a file to enable compile-time borrow checking for
the whole file. The native compiler enforces two rules:

- No aliased mutable borrows: the same variable may not be passed as `&x`
  twice in one call.
- No borrowing immutables: `&x` requires `x` to be declared `mut`.

```katlin
#strict

fn swap(int &a, int &b) {
    int temp = a;
    a = b;
    b = temp;
}

fn main {
    mut int x = 1;
    mut int y = 2;
    swap(&x, &y);   // accepted: distinct variables
    swap(&x, &x);   // error: cannot borrow `x` as mutable more than once
}
```

It does **not** verify thread safety, lifetimes, moves, or struct-field
borrows — see the `#strict` section in [README.md](README.md) for the exact
scope. Runnable examples: `examples/strict_borrows.ktl` (passes),
`examples/borrow_fail.ktl` and `examples/borrow_immutable.ktl` (rejected).

### Dial 2: `strict fn` (Function-Level Safety) — **not implemented**
> Per-function `strict fn` is not supported by the native compiler.

```katlin
strict fn safe_swap(int &a, int &b) {
    int temp = a;
    a = b;
    b = temp;
}
```

### Dial 3: Default (Fast & Pragmatic)
Stack by default, value semantics, `defer` for deterministic cleanup. Zero GC.
```katlin
fn load_asset(str path) {
    file := open_file(path) or return;
    defer file.close();

    buffer := allocate_stack[byte](1024);
    file.read_into(buffer);
}
```

### Dial 4: `raw` / Bare-Metal Pointers — **not implemented**

> This section describes intended syntax. `*mut byte` parameter types and
> `raw { ... }` blocks are **not supported** by the native compiler today; both
> produce a C backend error. See [README.md](README.md) for what works.

When you need direct VRAM, DMA, inline hardware registers, or SIMD:
```katlin
fn zero_memory(*mut byte ptr, usize size) {
    raw {
        mut usize i = 0;
        while i < size {
            *(ptr + i) = 0;
            i += 1;
        }
    }
}
```

**Working alternative today** — heap buffers with indexed access:
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

## 5. Clean Error Handling with `or` — **not implemented**

> `or` fallback expressions are **not supported** by the native compiler; they
> produce a C backend error. This is intended syntax.

```katlin
port := parse_int(env("PORT")) or 8080;
file := open(path) or return;
socket := bind(port) or panic("Port unavailable");
```
