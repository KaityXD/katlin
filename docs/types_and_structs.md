# Structs and Enums in Katlin

Katlin provides cache-friendly, contiguous composite data types matching C struct memory layouts with zero hidden pointer chasing.

---

## 1. Structs

Declare custom record types using the `struct` keyword:

```katlin
struct Point {
    int x;
    int y;
}

struct Player {
    str name;
    int health;
    int score;
}
```

### 1.1 Struct Literals
Initialize a struct using the `TypeName{ field = val, ... }` syntax:

```katlin
p := Point{ x = 10, y = 20 };
println("Point coordinates: (%, %)", p.x, p.y);

hero := Player{ name = "Katlin", health = 100, score = 0 };
println("Player: % (HP: %, Score: %)", hero.name, hero.health, hero.score);
```

### 1.2 Mutating Struct Fields
If a struct variable is declared `mut`, its fields can be reassigned:

```katlin
mut target := Point{ x = 0, y = 0 };
target.x = 100;
target.y += 50;
println("Target updated to (%, %)", target.x, target.y);
```

---

## 2. Reference Struct Fields (`&`)

Katlin allows struct fields to hold **references** (`&`) directly to external variables:

```katlin
struct Account {
    int id;
    int &balance;
}
```

When you initialize a reference field, it binds directly to the memory address of the target variable:

```katlin
mut vault_funds := 5000;
acc := Account{ id = 42, balance = vault_funds };

// Modifying acc.balance mutates vault_funds directly!
acc.balance += 250;
println("Vault funds: %", vault_funds); // Prints 5250
```

### Reference Structs in Function Parameters
When passed as reference parameters, member accesses automatically resolve the correct pointer indirection:

```katlin
fn deposit(Account &acc, int amount) {
    acc.balance += amount;
}
```

---

## 3. Enums

Enums represent a closed set of named variants:

```katlin
enum Direction {
    North,
    South,
    East,
    West
}

enum Status {
    Idle,
    Active,
    Suspended
}
```

Access enum variants using dot notation:

```katlin
dir := Direction.North;
current_status := Status.Active;
```

---

## 4. Pattern Matching (`match`)

Use `match` with `case .Variant:` to handle enum states:

```katlin
fn describe_direction(Direction d) {
    match d {
        case .North: { println("Heading North"); }
        case .South: { println("Heading South"); }
        case .East:  { println("Heading East"); }
        case .West:  { println("Heading West"); }
    }
}

fn status_code(Status s) -> int {
    mut int code = 0;
    match s {
        case .Idle:      { code = 100; }
        case .Active:    { code = 200; }
        case .Suspended: { code = 500; }
    }
    return code;
}
```

Under the hood, `match` statements compile directly to optimized C99 `switch` jump tables with zero dispatch latency.
