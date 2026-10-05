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

### Dial 1: `#strict` at Line 1 (Rust-Grade File Safety)
Put `#strict` at the top of a file to enforce compile-time borrow checking across the entire file:
```katlin
#strict

import std.net;

fn transfer(Account &from, Account &to, int amount) {
    // Compiler strictly verifies:
    // - No two mutable references point to the same memory (zero aliasing bugs)
    // - Zero data races across threads
    from.balance -= amount;
    to.balance += amount;
}
```

### Dial 2: `strict fn` (Function-Level Safety)
Enforce strict borrow checking on a single sensitive function in a normal file:
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

### Dial 4: `raw` / Bare-Metal Pointers (C / Zig Speed)
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

---

## 5. Clean Error Handling with `or`

```katlin
port := parse_int(env("PORT")) or 8080;
file := open(path) or return;
socket := bind(port) or panic("Port unavailable");
```
