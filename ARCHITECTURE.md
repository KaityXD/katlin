# The Katlin Language Architecture & Philosophy
**Mission:** Blazing Native Speed + Total Coding Freedom + Clean Static Typing.

---

## 1. The Core Pillars

1. **Very Fucking Fast**:
   - Compiles directly to native machine code via **LLVM / Cranelift**.
   - Zero Garbage Collector (Zero GC pauses, zero runtime baggage).
   - Compiler register promotion: chained nested functions flatten into raw CPU register operations with 0 heap allocation.
   - Cache-friendly contiguous memory layout (data-oriented design).

2. **The Memory Dial (Choose Your Strictness)**:
   - **Three Dial Levels**:
     - **`#strict` / Rust-like safe**: Enforces borrow checking and ownership lifetimes at compile-time.
     - **Default (Pragmatic / Fast)**: Stack-first value semantics, automatic scope cleanup, RAII, and `defer`.
     - **`raw` / C-like Bare Metal**: Raw pointers (`*mut T`), pointer arithmetic, hardware registers, SIMD.

3. **Syntactic Freedom ("Code Your Way")**:
   - Write cleanly: `fn fuck { ... }` (parentheses optional when empty).
   - Named parameters with `=`: `idkbro(timeout = 10).start()`.
   - Freeform multiline chaining.
   - Semicolons strictly optional.
   - Printing with clean `%` positional slots (`println("Total: %", total)`).
   - Return keyword optional (last expression is returned).

4. **Clean Static Typing & Variables**:
   - Type-first declarations: `int x = 10;`, `str name = "Katlin"`
   - Mutability freedom: `int &sum = 0;` OR `mut int count = 0;`
   - Inferred / dynamic typing with `:=`: `x := 10;`
   - 100% Statically typed for maximum performance and compiler optimization.

---

## 2. Memory Strictness Dial: Choose How You Manage Memory

```katlin
// Dial 1: RAW / BARE-METAL (For game engines, drivers, extreme speed)
fn fast_memcpy(*mut byte dest, *const byte src, usize count) {
    raw {
        mut usize i = 0;
        while i < count {
            *(dest + i) = *(src + i);
            i += 1;
        }
    }
}

// Dial 2: DEFAULT (Pragmatic systems coding - fast & clean)
fn process_audio([]f32 samples) {
    buffer := allocate_stack[f32](1024);
    defer buffer.free();

    apply_reverb(samples, buffer);
}

// Dial 3: #strict (Rust-grade borrow checking)
#strict

fn safe_transfer(mut Account a, mut Account b) {
    a.balance -= 100;
    b.balance += 100;
}
```

---

## 3. "Code However You Want": Syntactic Freedom

### 3.1 Parameterless Functions (Parentheses Optional)
```katlin
fn fuck {
    idkbro(
        timeout = 10
    ).start();
}
```

### 3.2 Named Arguments with `=` or `:`
```katlin
idkbro(timeout = 10, retries = 3).start();
idkbro(timeout: 10, retries: 3).start();
idkbro(10, 3).start();
```

### 3.3 Printing with Slot `%`
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
