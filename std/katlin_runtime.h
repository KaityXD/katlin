// std/katlin_runtime.h
// Katlin Minimal Bare-Metal Runtime
// Zero-cost abstractions, static C99/LLVM compatibility.

#ifndef KATLIN_RUNTIME_H
#define KATLIN_RUNTIME_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#include <time.h>

// Katlin Primitive Types
typedef int32_t   ktl_int;
typedef int64_t   ktl_i64;
typedef uint32_t  ktl_uint;
typedef uint64_t  ktl_u64;
typedef uint8_t   ktl_byte;
typedef float     ktl_float;
typedef double    ktl_f64;
typedef bool      ktl_bool;
typedef const char* ktl_str;

#include <unistd.h>

// High-resolution monotonic timer (seconds)
static inline double ktl_time_now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

// Measure physical RAM (Resident Set Size) in Megabytes
static inline double ktl_get_ram_mb(void) {
    FILE* f = fopen("/proc/self/statm", "r");
    if (!f) return 0.0;
    long pages = 0;
    if (fscanf(f, "%*s%ld", &pages) != 1) {
        fclose(f);
        return 0.0;
    }
    fclose(f);
    long page_size = sysconf(_SC_PAGESIZE);
    return (double)(pages * page_size) / (1024.0 * 1024.0);
}

// Bare-metal memory block helpers
static inline int32_t* ktl_alloc_ints(size_t count) {
    return (int32_t*)malloc(count * sizeof(int32_t));
}

static inline void ktl_free_ints(int32_t* ptr) {
    free(ptr);
}

// Panic helper
static inline void ktl_panic(const char* msg) {
    fprintf(stderr, "\n[KATLIN PANIC]: %s\n", msg);
    exit(1);
}

// Assert helper
static inline void ktl_assert(bool cond, const char* msg) {
    if (!cond) {
        fprintf(stderr, "\n[ASSERTION FAILED]: %s\n", msg);
        exit(1);
    }
}

// String Utilities
static inline ktl_int ktl_str_len(const char* s) {
    if (!s) return 0;
    return (ktl_int)strlen(s);
}

static inline bool ktl_str_eq(const char* a, const char* b) {
    if (a == b) return true;
    if (!a || !b) return false;
    return strcmp(a, b) == 0;
}

static inline const char* ktl_str_concat(const char* a, const char* b) {
    if (!a) a = "";
    if (!b) b = "";
    size_t la = strlen(a);
    size_t lb = strlen(b);
    char* buf = (char*)malloc(la + lb + 1);
    memcpy(buf, a, la);
    memcpy(buf + la, b, lb + 1);
    return buf;
}

// File I/O
static inline bool ktl_file_exists(const char* path) {
    return access(path, F_OK) == 0;
}

static inline const char* ktl_file_read_str(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return "";
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc(sz + 1);
    if (!buf) {
        fclose(f);
        return "";
    }
    size_t read_bytes = fread(buf, 1, sz, f);
    buf[read_bytes] = '\0';
    fclose(f);
    return buf;
}

static inline bool ktl_file_write_str(const char* path, const char* content) {
    FILE* f = fopen(path, "wb");
    if (!f) return false;
    if (content) {
        fputs(content, f);
    }
    fclose(f);
    return true;
}

static inline bool ktl_file_append_str(const char* path, const char* content) {
    FILE* f = fopen(path, "ab");
    if (!f) return false;
    if (content) {
        fputs(content, f);
    }
    fclose(f);
    return true;
}

// Math Helpers
static inline ktl_int ktl_math_abs(ktl_int x) {
    return x < 0 ? -x : x;
}

static inline ktl_int ktl_math_min(ktl_int a, ktl_int b) {
    return a < b ? a : b;
}

static inline ktl_int ktl_math_max(ktl_int a, ktl_int b) {
    return a > b ? a : b;
}

// Dynamic Vector / List
typedef struct {
    int64_t* data;
    size_t len;
    size_t cap;
} ktl_vec;

static inline ktl_vec ktl_vec_create(size_t initial_cap) {
    ktl_vec v;
    v.cap = initial_cap > 0 ? initial_cap : 8;
    v.len = 0;
    v.data = (int64_t*)malloc(v.cap * sizeof(int64_t));
    return v;
}

static inline void ktl_vec_push(ktl_vec* v, int64_t item) {
    if (v->len >= v->cap) {
        v->cap = (v->cap * 3) / 2 + 8;
        v->data = (int64_t*)realloc(v->data, v->cap * sizeof(int64_t));
    }
    v->data[v->len++] = item;
}

static inline int64_t ktl_vec_get(ktl_vec* v, size_t index) {
    if (index >= v->len) {
        ktl_panic("Vector index out of bounds!");
    }
    return v->data[index];
}

static inline void ktl_vec_set(ktl_vec* v, size_t index, int64_t val) {
    if (index >= v->len) {
        ktl_panic("Vector index out of bounds!");
    }
    v->data[index] = val;
}

static inline ktl_int ktl_vec_len(ktl_vec* v) {
    return (ktl_int)v->len;
}

static inline void ktl_vec_free(ktl_vec* v) {
    if (v->data) {
        free(v->data);
        v->data = NULL;
    }
    v->len = 0;
    v->cap = 0;
}

// -------------------------------------------------------------
// Arena Bump-Allocator (0-overhead, bulk wipe in 1 CPU cycle)
// -------------------------------------------------------------
typedef struct {
    uint8_t* buffer;
    size_t capacity;
    size_t offset;
} ktl_arena;

static inline ktl_arena ktl_arena_create(size_t capacity) {
    ktl_arena a;
    a.buffer = (uint8_t*)malloc(capacity);
    a.capacity = capacity;
    a.offset = 0;
    return a;
}

static inline void* ktl_arena_alloc(ktl_arena* a, size_t size) {
    size_t aligned = (size + 7) & ~7;
    if (a->offset + aligned > a->capacity) {
        ktl_panic("Arena out of memory!");
    }
    void* ptr = (void*)(&a->buffer[a->offset]);
    a->offset += aligned;
    return ptr;
}

static inline void ktl_arena_reset(ktl_arena* a) {
    a->offset = 0; // 0-cycle bulk wipe!
}

static inline void ktl_arena_destroy(ktl_arena* a) {
    if (a->buffer) {
        free(a->buffer);
        a->buffer = NULL;
    }
    a->capacity = 0;
    a->offset = 0;
}

#endif // KATLIN_RUNTIME_H
