# Memory Management and Pointers

Katlin has **no garbage collector**. Memory allocation is explicit, cache-friendly, and predictable.

---

## 1. The Memory Strictness Dial

Katlin provides a dial of memory management techniques, letting you choose the right balance of ergonomics and control:

```
[ Safe / High-Level ]                                  [ Bare-Metal ]
Stack / Values  ──►  Arenas  ──►  Dynamic Collections  ──►  Raw Pointers
```

---

## 2. Stack Allocation (Default)

Variables, structs, and primitive types reside on the CPU stack frame by default. When the enclosing function returns, stack frames automatically unwind with zero overhead.

---

## 3. Memory Arenas (High-Performance Bulk Allocations)

An **Arena Allocator** is a monotonic bump-allocator that allocates memory rapidly in contiguous chunks. Instead of freeing individual objects, the entire arena can be wiped in a single CPU cycle:

```katlin
fn main {
    // Allocate a 1MB memory arena
    arena := arena_create(1024 * 1024);

    // Rapidly carve out buffers from the arena
    mut buf1 := arena_alloc(arena, 4096);
    mut buf2 := arena_alloc(arena, 8192);

    // Bulk reset: frees all allocated buffers instantly
    arena_reset(arena);

    // Free the underlying arena back to the OS
    arena_destroy(arena);
}
```

### Why Arenas are Superior for Systems Code
- **Zero Heap Fragmentation**: Allocations are simple pointer increments (`offset += size`).
- **O(1) Destruction**: Millions of transient allocations are recycled by resetting a single integer offset (`offset = 0`).
- **Cache Locality**: Contiguous allocation ensures optimal CPU cache prefetching.

---

## 4. Dynamic Vectors (`vec`)

For dynamically growing arrays of integer/pointer data, use the built-in `vec` system:

```katlin
fn main {
    // Create a vector with initial capacity 8
    v := vec_create(8);

    // Append elements (auto-resizes when capacity is reached)
    for i in 0..10 {
        vec_push(v, i * 10);
    }

    println("Vector length: %", vec_len(v));
    println("Element at 0: %", vec_get(v, 0));
    println("Element at 5: %", vec_get(v, 5));

    // Update an element
    vec_set(v, 5, 999);
    println("Updated element at 5: %", vec_get(v, 5));

    // Free vector memory
    vec_free(v);
}
```

---

## 5. Dynamic String Builders (`sb`)

String concatenation in loops causes heap thrashing if done with raw strings. The `sb` type provides O(1) amortized appending:

```katlin
fn main {
    mut sb := sb_create(128);

    sb_append(sb, "Katlin");
    sb_append(sb, " is ");
    sb_append(sb, "fast!");

    str result = sb_build(sb);
    println("Result: %", result);

    sb_free(sb);
}
```

---

## 6. Raw Pointers and `raw { ... }` Blocks

For low-level drivers, operating system kernels, or custom memory allocators, Katlin provides raw pointers:

- `*mut T`: Mutable raw pointer (`T*` in C).
- `*const T`: Read-only pointer (`const T*` in C).

```katlin
fn fast_memcpy(*mut byte dest, *const byte src, usize count) {
    raw {
        mut usize i = 0;
        while i < count {
            *(dest + i) = *(src + i);
            i += 1;
        }
    }
}
```

### Heap Buffer Allocation (`alloc_ints`, `free_ints`)
You can allocate contiguous integer arrays on the heap and use array index notation:

```katlin
fn main {
    // Allocate 1024 integers (4 KB) on the heap
    buf := alloc_ints(1024);

    mut i := 0;
    while i < 1024 {
        buf[i] = i * 2;
        i += 1;
    }

    println("Sample: buf[10] = %", buf[10]);

    free_ints(buf);
}
```
