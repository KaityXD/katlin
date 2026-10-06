# Error Handling with Fallback Expressions (`or`)

Katlin avoids heavyweight exception runtimes, hidden panics, and bloated stack-unwinding mechanisms. Instead, error handling is explicit, ergonomic, and centered around the **`or` fallback operator**.

---

## 1. The `or` Operator

The `or` keyword unwraps an expression. If the left-hand expression evaluates to a truthy (non-zero / valid) value, that value is used. If it evaluates to a falsy (zero / null / false) value, the right-hand branch executes.

There are three primary error-handling patterns using `or`:

---

## 2. Pattern 1: Value Defaults

When a lookup or calculation fails (returns zero or falsy), fallback to a safe default value:

```katlin
fn get_server_port() -> int {
    // Returns 0 if not configured
    return 0;
}

fn main {
    // If get_server_port() returns 0, default to 8080:
    port := get_server_port() or 8080;
    println("Binding to port %", port); // port = 8080
}
```

If the left side succeeds, the default is skipped:

```katlin
fn get_user_id() -> int {
    return 42;
}

id := get_user_id() or -1;
println("User ID: %", id); // Prints 42
```

---

## 3. Pattern 2: Early Return (`or return`)

When a step fails and the function cannot proceed, bail out immediately with `or return`:

```katlin
fn lookup_user(int id) -> int {
    // Returns 0 when the user does not exist
    return if id < 0;
    return id * 10;
}

fn render_profile(int id) {
    // If user is not found, immediately exit the function:
    user := lookup_user(id) or return;

    println("Rendering profile for user %", user);
}

fn main {
    render_profile(5);   // Prints: Rendering profile for user 50
    render_profile(-1);  // Prints nothing: exits early cleanly
}
```

---

## 4. Pattern 3: Fatal Panics (`or panic`)

For unrecoverable failures (such as missing critical assets or hardware failure), use `or panic("reason")`:

```katlin
fn open_system_config(str path) -> int {
    // Returns 0 on I/O error
    return 0;
}

fn main {
    // If the file cannot be opened, abort with a clear diagnostic:
    handle := open_system_config("/etc/app.conf") or panic("Failed to open critical configuration!");
    println("Config handle: %", handle);
}
```

When a panic occurs, Katlin halts execution immediately and outputs the panic message and diagnostic context to standard error.

---

## 5. Summary Table

| Syntax | Action on Success | Action on Failure (`0` / falsy) |
| :--- | :--- | :--- |
| `val := expr or default;` | Keeps `expr` | Assigns `default` |
| `val := expr or return;` | Keeps `expr` | Bails out of enclosing function |
| `val := expr or panic("...");` | Keeps `expr` | Halts program with fatal error |
