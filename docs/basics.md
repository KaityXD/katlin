# Katlin Language Basics

This chapter covers the fundamental building blocks of writing programs in Katlin.

---

## 1. Hello, World!

Here is the quintessential starting program:

```katlin
fn main {
    println("Hello, World!");
}
```

Key observations:
1. `fn main` defines the program entrypoint. Empty parentheses `()` are optional.
2. `println` writes text to standard output followed by a newline.
3. Semicolons `;` can be used or omitted at the end of lines.

---

## 2. Variables and Mutability

Katlin values are **immutable by default**. To allow mutation, use the `mut` keyword.

### 2.1 Inferred Typing (`:=`)
Use `:=` when you want Katlin to automatically infer the variable's type from its assigned expression:

```katlin
// Immutable constants (cannot be reassigned)
message := "Katlin";
count := 100;
ratio := 3.14159;
is_active := true;

// Mutable variables (can be reassigned and modified)
mut score := 0;
score += 10;
score = score * 2;
```

### 2.2 Explicit Typing
You can also provide the explicit type name before the variable:

```katlin
// Explicit immutable constants
int port = 8080;
str host = "127.0.0.1";
bool secure = false;

// Explicit mutable variables
mut int attempts = 0;
attempts += 1;

mut str buffer = "start";
```

---

## 3. Primitive Types

Katlin provides low-level primitive types matching hardware registers:

| Type | Description | Example Literal |
| :--- | :--- | :--- |
| `int` | 32-bit signed integer | `42`, `-10`, `0xFF` |
| `i64` | 64-bit signed integer | `1000000000` |
| `u64` | 64-bit unsigned integer | `18446744073709551615` |
| `byte` | 8-bit unsigned byte | `255`, `0x7F` |
| `usize` | Target pointer-width unsigned integer | `4096` |
| `float` | 64-bit IEEE double-precision float | `3.14`, `-0.005` |
| `bool` | Boolean truth value | `true`, `false` |
| `str` | UTF-8 zero-terminated string pointer | `"Hello\n"` |

### Compile-Time Type Reflection (`.type`)
For any variable declared with `:=`, accessing `.type` evaluates at compile-time to a string constant representing its resolved type:

```katlin
answer := 42;
println("Value: %, Type: %", answer, answer.type);
// Output: Value: 42, Type: int
```

`answer.type()` (with parentheses) works identically — use whichever reads better. This also resolves through dot-method chains: `s.trim().type()` is `"str"`.

---

## 4. String Formatting with `%` Slots

Katlin does not use format specifier guessing (`%d`, `%s`, `%f`) or complex string interpolation syntax. Instead, format strings use clean **`%` slots**:

```katlin
name := "Alice";
score := 95;
rate := 98.6;
passed := true;

println("Student % scored % (rate: %, passed: %)", name, score, rate, passed);
```

### Why `%` Slots are Safe
In traditional C, passing a float to `%d` causes silent stack corruption or undefined behavior. In Katlin:
- Every `%` slot expands to a C11 `_Generic` type dispatch at compile-time.
- Integers, floats, doubles, booleans, and strings format accurately without type guesswork.
- `print` writes without an automatic newline, while `println` appends a newline.

---

## 5. Operators

Katlin supports standard arithmetic, logical, and bitwise operators:

### Arithmetic
- Binary: `+`, `-`, `*`, `/`, `%`
- Compound assignment: `+=`, `-=`, `*=`, `/=`
- Increment/Decrement: `++`, `--`

### Comparison & Logic
- Equality: `==`, `!=`
- Relational: `<`, `<=`, `>`, `>=`
- Boolean: `&&` (and), `||` (or), `!` (not)

### Bitwise
- Bitwise operations: `&`, `|`, `^`, `<<`, `>>`

---

## 6. Comments

```katlin
// This is a single-line comment

/*
   This is a multi-line
   block comment.
*/
```
