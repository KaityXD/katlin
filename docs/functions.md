# Functions and Arguments

Functions are first-class constructs in Katlin. They compile to zero-cost, inlined static machine code.

---

## 1. Declaring Functions

Use the `fn` keyword to declare a function:

```katlin
fn add(int a, int b) -> int {
    return a + b;
}

fn greet(str name) {
    println("Hello, %!", name);
}
```

### Parentheses-Optional Syntax
Functions that take no parameters can omit empty parentheses `()`:

```katlin
fn print_header {
    println("====================");
    println("  SYSTEM DASHBOARD  ");
    println("====================");
}

fn main {
    print_header();
}
```

---

## 2. Reference Parameters (`&`)

When you pass large structs or want a function to modify its caller's variable directly, use the `&` modifier in the parameter list:

```katlin
fn increment(int &val, int step) {
    val += step;
}

fn swap(int &a, int &b) {
    int temp = a;
    a = b;
    b = temp;
}
```

At the call site, you can pass either an explicit address `&x` or the variable name `x`:

```katlin
fn main {
    mut x := 10;
    increment(&x, 5);
    println("x = %", x); // x = 15

    mut a := 1;
    mut b := 2;
    swap(&a, &b);
    println("a = %, b = %", a, b); // a = 2, b = 1
}
```

### How References Work Under the Hood
In the generated C99 code, an `&` parameter compiles to a raw pointer (`int* val`). Dereferences and writes propagate straight through to the caller's stack frame with **zero heap allocation** and **zero runtime overhead**.

---

## 3. Parameter Defaults

Trailing parameters can have default expressions:

```katlin
fn box(int width = 1, int height = 1, int depth = 1) -> int {
    return width * height * depth;
}
```

You can call the function with any number of positional arguments, and unspecified parameters assume their defaults:

```katlin
v1 := box();          // 1 * 1 * 1 = 1
v2 := box(5);         // 5 * 1 * 1 = 5
v3 := box(5, 10);     // 5 * 10 * 1 = 50
v4 := box(5, 10, 2);  // 5 * 10 * 2 = 100
```

---

## 4. Named Arguments

Katlin lets you call functions using named arguments (`param_name = value`), allowing you to supply arguments in **any order**:

```katlin
fn configure_server(str host = "127.0.0.1", int port = 8080, bool ssl = false) {
    println("Server running on %:% (SSL: %)", host, port, ssl);
}

fn main {
    // Specify only the parameter you want to change:
    configure_server(port = 9000);

    // Provide arguments in arbitrary order:
    configure_server(ssl = true, port = 443, host = "0.0.0.0");

    // Mix positional and named arguments:
    configure_server("192.168.1.1", ssl = true);
}
```

### Pre-Pass Transpilation
During compilation, Katlin collects function signatures and resolves named/default arguments into clean positional arguments before emitting code. There is **zero runtime overhead** for using named arguments.

---

## 5. Dot-Method Calls

Every standard-library function also works as a dot-method on its first argument. The old underscore names keep working — both compile to the same C:

```katlin
s := "  hello katlin  ";
println("% %", s.len(), str_len(s));       // 16 16
println("%", s.trim().upper());            // HELLO KATLIN
println("%", s.contains("katlin"));        // true

v := vec_create(4);
v.push(10);
vec_push(v, 20);
println("% %", v.len(), v.get(1));         // 2 20

m := map_create(8);
m.set("k", "v");
println("%", m.get("k"));                  // v

mut sb := sb_create(64);
sb.append("hi ");
println("% %", sb.build(), sb.len());      // hi  8
```

Method calls chain (`s.trim().upper()`), work on string literals (`"hi".len()`), and nest (`v.get(s.len())`). `x.type()` mirrors the compile-time `x.type` property. See [`examples/methods.ktl`](../examples/methods.ktl) for a runnable demo.
