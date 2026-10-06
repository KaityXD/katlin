# Learning Katlin

Welcome to the official Katlin language documentation!

Katlin (`.ktl`) is a statically typed systems programming language that compiles to native machine code through an optimizing C99 backend. It features **zero garbage collection**, **fast compile times**, **expressive modern syntax**, and a pragmatic safety dial.

---

## Documentation Index

1. [**Getting Started**](getting_started.md)
   Installation, toolchain commands (`run`, `build`, `check`, `test`, `fmt`, `init`), project structure, and compiler flags.

2. [**Language Basics**](basics.md)
   Variables, type inference (`:=`), mutability (`mut`), primitive types, optional semicolons, comments, and printing with `%` slots.

3. [**Control Flow**](control_flow.md)
   `if` / `else`, `while`, ranges with `for ... in ... step ...`, infinite `loop`, postfix guards (`return if cond;`), `break`, and `continue`.

4. [**Functions & Arguments**](functions.md)
   Function declarations, return types, reference parameters (`int &a`), parameter default values, and named arguments (`box(width = 10)`).

5. [**Structs & Enums**](types_and_structs.md)
   Defining structs, struct literals, reference struct fields (`int &balance`), enum tagged unions, and pattern matching with `match` / `case`.

6. [**Error Handling & Fallbacks**](error_handling.md)
   The `or` operator: value fallbacks (`lookup() or 8080`), early returns (`lookup() or return`), and fatal panics (`lookup() or panic(...)`).

7. [**Memory Management & Pointers**](memory_and_pointers.md)
   Stack allocation, arena bump-allocators (`arena_create`), dynamic vectors (`vec`), string builders (`sb`), raw pointers (`*mut T`), and `raw { ... }` blocks.

8. [**#strict Borrow Checking**](strict_mode.md)
   Compile-time aliasing protection: rejecting duplicate mutable borrows (`swap(&x, &x)`), preventing borrows of immutable variables, and per-field tracking.

9. [**Standard Library Reference**](standard_library.md)
   Built-in functions for strings, vectors, file I/O, memory arenas, math, timing, CLI arguments, and system execution.

10. [**Modules & Imports**](modules_and_imports.md)
    Splitting code across multiple files, quoted and dot imports, automatic dependency bundling, diamond de-duplication, and cycle detection.

---

## 3-Minute Quick Tour

Here is a quick look at what Katlin code looks like in practice:

```katlin
// tour.ktl
struct Point {
    int x;
    int y;
}

enum Status {
    Idle,
    Running,
    Finished
}

// References mutate the caller directly with zero heap indirection
fn swap(int &a, int &b) {
    int temp = a;
    a = b;
    b = temp;
}

// Trailing default values and postfix return guards
fn calculate_area(int width = 1, int height = 1) -> int {
    return if width <= 0 || height <= 0;
    return width * height;
}

fn main {
    println("=== Katlin Quick Tour ===");

    // Inferred immutable constant
    greeting := "Hello, Katlin!";
    println("% (type: %)", greeting, greeting.type);

    // Inferred mutable variable
    mut a := 10;
    mut b := 20;
    swap(&a, &b);
    println("Swapped: a = %, b = %", a, b);

    // Struct literal
    p := Point{ x = 5, y = 12 };
    println("Point: x = %, y = %", p.x, p.y);

    // Named arguments in any order
    box_area := calculate_area(height = 4, width = 6);
    println("Area: %", box_area);

    // `or` fallback expression
    port := calculate_area(-1, 0) or 8080;
    println("Port: %", port);

    // Range loop with step
    for i in 0..10 step 3 {
        println("Step: %", i);
    }
}
```

Run it instantly with:

```bash
./bin/katlin run tour.ktl
```
