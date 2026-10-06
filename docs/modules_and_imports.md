# Modules & Multi-File Imports

Katlin programs can be split across multiple `.ktl` files and compiled into a single high-performance native binary without requiring external linker configurations or Makefiles.

The Katlin compiler automatically resolves dependencies, de-duplicates imports, detects cycles, and bundles modules in topological dependency order.

---

## Import Syntax

Katlin supports two forms of the `import` statement:

### 1. Quoted Path Import
Imports a `.ktl` file using a relative or absolute file path:

```katlin
import "math.ktl";
import "utils/logger.ktl";
import "../common/types.ktl";
```

### 2. Identifier / Dot-Notation Import
Imports a module using dot or identifier notation, mapping `.` to `/` and appending `.ktl`:

```katlin
import math;          // resolves to "math.ktl"
import utils.logger;  // resolves to "utils/logger.ktl"
```

### 3. Standard Library Modules
Standard library modules can be imported using `std` or `std.<subsystem>`:

```katlin
import std.io;
import std.mem;
```

---

## File Resolution Rules

When resolving an imported path, Katlin looks in:
1. **Relative to the importing file's directory** (recommended for modular project organization).
2. **Relative to the current working directory** (project root).

For example, given this project structure:
```
my_project/
├── src/
│   ├── main.ktl
│   ├── vector.ktl
│   └── physics/
│       └── collision.ktl
```

Inside `main.ktl`:
```katlin
import "vector.ktl";
import "physics/collision.ktl";
```

Inside `physics/collision.ktl`:
```katlin
import "../vector.ktl";
```

---

## De-Duplication & Diamond Imports

When multiple modules depend on a shared module, Katlin ensures that the shared module is bundled and compiled **exactly once**.

```
       main.ktl
       /      \
      v        v
  engine.ktl  render.ktl
      \        /
       v      v
       math.ktl
```

In this diamond dependency graph:
- `engine.ktl` imports `"math.ktl"`
- `render.ktl` imports `"math.ktl"`
- `main.ktl` imports `"engine.ktl"` and `"render.ktl"`

Katlin recognizes that `math.ktl` has already been visited and guarantees that types, functions, and structs in `math.ktl` are defined only once, prior to their usage in downstream modules.

---

## Cycle Protection

If two modules import each other:
```
module_a.ktl <---> module_b.ktl
```

The Katlin import resolver tracks active import visits to break recursion loops, avoiding infinite bundling or compiler deadlocks.

---

## Rules & Constraints

1. **Only the entry point defines `fn main`**:
   Imported modules are libraries/helpers and **cannot** declare an entry point `fn main`. Attempting to import a file containing `fn main` produces a compile-time error:
   ```
   error: imported module 'helper.ktl' cannot define 'fn main'
   ```

2. **Topological Ordering**:
   Dependencies are emitted before dependents so that C compilers have all type declarations before functions using those types.

3. **#strict Borrows across Modules**:
   Modules written with `#strict` have their borrow semantics verified before bundling.

---

## Complete Example

### `math.ktl`
```katlin
struct Vec2 {
    int x;
    int y;
}

fn vec_add(Vec2 a, Vec2 b) -> Vec2 {
    mut res := Vec2{ x = a.x + b.x, y = a.y + b.y };
    return res;
}

fn vec_dot(Vec2 a, Vec2 b) -> int {
    return a.x * b.x + a.y * b.y;
}
```

### `printer.ktl`
```katlin
import "math.ktl";

fn print_vec(str label, Vec2 v) {
    println("%: (%, %)", label, v.x, v.y);
}
```

### `main.ktl`
```katlin
import "math.ktl";
import "printer.ktl";

fn main {
    v1 := Vec2{ x = 3, y = 4 };
    v2 := Vec2{ x = 5, y = 12 };

    print_vec("Vector 1", v1);
    print_vec("Vector 2", v2);

    sum := vec_add(v1, v2);
    print_vec("Sum", sum);

    dot := vec_dot(v1, v2);
    println("Dot product: %", dot);
}
```

Compile and run:
```bash
./bin/katlin run main.ktl
```

Output:
```
Vector 1: (3, 4)
Vector 2: (5, 12)
Sum: (8, 16)
Dot product: 63
```
