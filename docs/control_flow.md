# Control Flow in Katlin

Katlin provides modern, expressive control flow statements without unnecessary punctuation.

---

## 1. Conditional Branching (`if`, `else if`, `else`)

Condition expressions do not require enclosing parentheses `()`:

```katlin
fn classify(int score) {
    if score >= 90 {
        println("Grade: A");
    } else if score >= 80 {
        println("Grade: B");
    } else if score >= 70 {
        println("Grade: C");
    } else {
        println("Grade: Failing");
    }
}
```

Parentheses around the condition are accepted if you prefer them:

```katlin
if (x > 0 && y > 0) {
    println("Quadrant 1");
}
```

---

## 2. Postfix Guard Clauses (`return if`)

To prevent "arrow code" and deep nesting, Katlin supports **postfix guard clauses**:

```katlin
fn withdraw(int balance, int amount) -> int {
    // If condition holds, return early immediately
    return if amount <= 0;
    return if amount > balance;

    // Happy path continues un-nested
    return balance - amount;
}
```

This makes input validation concise and readable at the top of functions.

---

## 3. Loops

### 3.1 Range Loops (`for ... in ...`)
Katlin range loops iterate through integer ranges with the `..` operator:

```katlin
// Iterates from 0 up to (but not including) 5: 0, 1, 2, 3, 4
for i in 0..5 {
    println("i = %", i);
}
```

### 3.2 Stepped Ranges (`step`)
You can specify a custom increment step:

```katlin
// Count by 2s: 0, 2, 4, 6, 8
for i in 0..10 step 2 {
    println("even: %", i);
}
```

### 3.3 While Loops (`while`)
Use `while` for condition-driven iteration:

```katlin
mut count := 10;
while count > 0 {
    println("%...", count);
    count -= 1;
}
println("Liftoff!");
```

### 3.4 Infinite Loops (`loop`)
The `loop` keyword executes indefinitely until interrupted by `break` or `return`:

```katlin
mut attempts := 0;
loop {
    attempts += 1;
    if attempts >= 3 {
        println("Reached max attempts!");
        break;
    }
}
```

---

## 4. Loop Jumps (`break` and `continue`)

- `break`: Exits the enclosing loop immediately.
- `continue`: Skips the remainder of the current loop iteration and advances to the next.

```katlin
for i in 0..20 {
    // Skip odd numbers
    if i % 2 != 0 {
        continue;
    }

    // Stop once we hit 10
    if i > 10 {
        break;
    }

    println("Number: %", i);
}
```
