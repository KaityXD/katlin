# `#strict` Borrow Checking

Katlin includes an opt-in compile-time borrow checker pass enabled by placing the `#strict` pragma at the very top of your file.

```katlin
#strict
```

When `#strict` is active, the compiler performs a source-level aliasing check to catch the common double-borrow and immutable-borrow mistakes **before any C code is generated**. It is a guard against aliasing bugs, not a full borrow checker: no lifetimes, moves, or thread-safety analysis.

---

## 1. The Two Strict Rules

### Rule 1: No Aliased Mutable Borrows
Within any function call, the same variable or place cannot be passed as a mutable reference (`&`) more than once:

```katlin
#strict

fn swap(int &a, int &b) {
    int t = a;
    a = b;
    b = t;
}

fn main {
    mut int x = 1;
    mut int y = 2;

    swap(&x, &y); // OK: x and y are distinct variables

    swap(&x, &x); // ERROR: x is borrowed mutably twice!
}
```

When compiled, Katlin halts with a clear diagnostic:

```
error: cannot borrow `x` as mutable more than once at a time
  --> src/main.ktl:14
   = note: #strict forbids aliased mutable references (&)
```

---

### Rule 2: No Borrowing Immutables
A variable declared without the `mut` keyword is immutable and cannot be borrowed as a mutable reference (`&`):

```katlin
#strict

fn increment(int &val) {
    val += 1;
}

fn main {
    int constant_value = 10; // Immutable!

    increment(&constant_value); // ERROR: constant_value is not declared mut!
}
```

The compiler rejects this:

```
error: cannot borrow immutable variable `constant_value` as mutable
  --> src/main.ktl:10
   = note: declare it with `mut` if it needs to be modified
```

---

## 2. Per-Field Borrow Tracking

The `#strict` pass understands struct member access. Borrowing two distinct fields of the same struct is fully permitted:

```katlin
#strict

struct Point {
    int x;
    int y;
}

fn swap_coords(int &a, int &b) {
    int t = a;
    a = b;
    b = t;
}

fn main {
    mut pt := Point{ x = 1, y = 2 };

    // PERMITTED: pt.x and pt.y are distinct memory locations
    swap_coords(&pt.x, &pt.y);

    // REJECTED: borrowing the same field twice
    swap_coords(&pt.x, &pt.x);
}
```

---

## 3. Scope-Aware Mutability

Mutability is strictly scoped to the declaring function:
- A local `mut` variable declared inside function `A` does not leak mutability to an identically named variable in function `B`.
- File-level `mut` variables remain mutable and accessible across all functions in the file.

---

## 4. Stated Scope of `#strict`

> [!NOTE]
> Katlin's `#strict` mode is a **source-level aliasing guard**, designed to catch common reference aliasing bugs without the complexity of lifetime annotations or complex borrow graphs. It does not track lifetimes or moves across threads.
