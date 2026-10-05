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
#include <sys/wait.h>

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
typedef size_t    ktl_usize;

// Type-generic printing helpers
static inline void ktl_print_i(long long x) { printf("%lld", x); }
static inline void ktl_print_f(double x) { printf("%g", x); }
static inline void ktl_print_s(const char* x) { printf("%s", x ? x : ""); }
static inline void ktl_print_b(bool x) { printf("%s", x ? "true" : "false"); }

#define ktl_print_any(x) _Generic((x), \
    int: ktl_print_i, \
    long: ktl_print_i, \
    long long: ktl_print_i, \
    unsigned int: ktl_print_i, \
    unsigned long: ktl_print_i, \
    unsigned long long: ktl_print_i, \
    double: ktl_print_f, \
    float: ktl_print_f, \
    char*: ktl_print_s, \
    const char*: ktl_print_s, \
    bool: ktl_print_b, \
    default: ktl_print_i \
)(x)

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
    fprintf(stderr, "\n\033[1;31mpanic\033[0m: \033[1;37m%s\033[0m\n\n", msg);
    exit(1);
}

// Assert helper
// In test mode a failed assertion is recorded and reported rather than
// aborting the process, so one bad expectation does not hide the rest of
// the suite. Outside test mode it aborts immediately, as before.
static int ktl_test_mode = 0;
static int ktl_test_failures = 0;
static const char* ktl_test_current = "";

static inline void ktl_assert(bool cond, const char* msg) {
    if (!cond) {
        if (ktl_test_mode) {
            ktl_test_failures++;
            printf("  \033[1;31m✗\033[0m %s\n      %s\n",
                   ktl_test_current, msg ? msg : "(no message)");
            return;
        }
        fprintf(stderr, "\n\033[1;31massertion failed\033[0m: \033[1;37m%s\033[0m\n\n", msg);
        exit(1);
    }
}

// CLI Argument Support
static int ktl_argc = 0;
static char** ktl_argv = NULL;

static inline void ktl_init_args(int argc, char** argv) {
    ktl_argc = argc;
    ktl_argv = argv;
}

static inline ktl_int ktl_args_count(void) {
    return ktl_argc;
}

static inline ktl_str ktl_args_get(ktl_int index) {
    if (index >= 0 && index < ktl_argc && ktl_argv) {
        return ktl_argv[index];
    }
    return "";
}

// System Command Execution
// Returns the child's real exit code (0-255), NOT the raw wait(2) status.
// libc system() returns a wait status with the exit code in bits 8-15, so a
// plain `return system(cmd)` reports a failing command as 256 and makes
// failure indistinguishable from success at the call site.
static inline ktl_int ktl_run(const char* cmd) {
    if (!cmd) return -1;
    // Flush our own buffered output first, otherwise child-process output
    // overtakes it and progress messages appear in the wrong order.
    fflush(NULL);
    int st = system(cmd);
    if (st == -1) return -1;
    if (WIFEXITED(st)) return (ktl_int)WEXITSTATUS(st);
    if (WIFSIGNALED(st)) return (ktl_int)(128 + WTERMSIG(st));
    return (ktl_int)st;
}

static inline ktl_int ktl_system(const char* cmd) {
    return ktl_run(cmd);
}

// Process termination with a status code.
static inline void ktl_exit(ktl_int code) {
    exit((int)code);
}

// Environment lookup that never returns NULL, so Katlin code can compare
// the result with "" without touching raw pointers.
static inline ktl_str ktl_env_get(const char* name) {
    const char* v = getenv(name);
    return v ? v : "";
}

// Maths helpers
static inline ktl_int ktl_abs(ktl_int x) { return x < 0 ? -x : x; }
static inline ktl_int ktl_min(ktl_int a, ktl_int b) { return a < b ? a : b; }
static inline ktl_int ktl_max(ktl_int a, ktl_int b) { return a > b ? a : b; }

// FNV-1a (32-bit, sign-cleared) content hash.
// The compiler embeds a hash of this runtime header into every generated C
// file, so an incremental build notices when the runtime changes even though
// the user's source did not.
static inline ktl_int ktl_hash(const char* s) {
    if (!s) return 0;
    uint32_t h = 2166136261u;
    while (*s) {
        h ^= (unsigned char)(*s++);
        h *= 16777619u;
    }
    return (ktl_int)(h & 0x7fffffffu);
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

static inline ktl_int ktl_str_char_at(const char* s, ktl_int index) {
    if (!s) return 0;
    ktl_int slen = (ktl_int)strlen(s);
    if (index < 0 || index >= slen) return 0;
    return (uint8_t)s[index];
}

static inline const char* ktl_str_sub(const char* s, ktl_int start, ktl_int len) {
    if (!s) return "";
    ktl_int slen = (ktl_int)strlen(s);
    if (start < 0 || start >= slen || len <= 0) return "";
    if (start + len > slen) len = slen - start;
    char* buf = (char*)malloc(len + 1);
    memcpy(buf, s + start, len);
    buf[len] = '\0';
    return buf;
}

static inline const char* ktl_str_from_char(ktl_int c) {
    char* buf = (char*)malloc(2);
    buf[0] = (char)c;
    buf[1] = '\0';
    return buf;
}

static inline bool ktl_str_starts_with(const char* s, const char* prefix) {
    if (!s || !prefix) return false;
    size_t lp = strlen(prefix);
    return strncmp(s, prefix, lp) == 0;
}

static inline bool ktl_str_ends_with(const char* s, const char* suffix) {
    if (!s || !suffix) return false;
    size_t ls = strlen(s);
    size_t lp = strlen(suffix);
    if (lp > ls) return false;
    return strcmp(s + (ls - lp), suffix) == 0;
}

static inline ktl_int ktl_str_index_of(const char* s, const char* needle, ktl_int start) {
    if (!s || !needle) return -1;
    ktl_int slen = (ktl_int)strlen(s);
    if (start < 0 || start >= slen) return -1;
    const char* p = strstr(s + start, needle);
    if (!p) return -1;
    return (ktl_int)(p - s);
}

static inline bool ktl_str_contains(const char* s, const char* needle) {
    if (!s || !needle) return false;
    return strstr(s, needle) != NULL;
}

static inline const char* ktl_str_int(ktl_int val) {
    char* buf = (char*)malloc(32);
    snprintf(buf, 32, "%d", val);
    return buf;
}

static inline ktl_int ktl_parse_int(const char* s) {
    if (!s) return 0;
    return (ktl_int)atoi(s);
}

// Path Helpers
static inline const char* ktl_path_base(const char* path) {
    if (!path) return "";
    const char* last_slash = strrchr(path, '/');
    const char* name = last_slash ? (last_slash + 1) : path;
    const char* dot = strrchr(name, '.');
    if (!dot) return name;
    size_t len = dot - name;
    char* buf = (char*)malloc(len + 1);
    memcpy(buf, name, len);
    buf[len] = '\0';
    return buf;
}

static inline const char* ktl_path_dir(const char* path) {
    if (!path) return ".";
    const char* last_slash = strrchr(path, '/');
    if (!last_slash) return ".";
    size_t len = last_slash - path;
    char* buf = (char*)malloc(len + 1);
    memcpy(buf, path, len);
    buf[len] = '\0';
    return buf;
}

// Dynamic String Builder (High-Performance O(1) Amortized Appends)
typedef struct {
    char* data;
    size_t len;
    size_t cap;
} ktl_sb;

static inline ktl_sb ktl_sb_create(size_t initial_cap) {
    ktl_sb sb;
    sb.cap = initial_cap > 0 ? initial_cap : 64;
    sb.len = 0;
    sb.data = (char*)malloc(sb.cap);
    sb.data[0] = '\0';
    return sb;
}

static inline void ktl_sb_append(ktl_sb* sb, const char* str) {
    if (!str) return;
    size_t slen = strlen(str);
    if (sb->len + slen + 1 >= sb->cap) {
        sb->cap = (sb->cap + slen) * 2 + 16;
        sb->data = (char*)realloc(sb->data, sb->cap);
    }
    memcpy(sb->data + sb->len, str, slen);
    sb->len += slen;
    sb->data[sb->len] = '\0';
}

static inline void ktl_sb_append_char(ktl_sb* sb, ktl_int c) {
    if (sb->len + 2 >= sb->cap) {
        sb->cap = sb->cap * 2 + 16;
        sb->data = (char*)realloc(sb->data, sb->cap);
    }
    sb->data[sb->len++] = (char)c;
    sb->data[sb->len] = '\0';
}

static inline const char* ktl_sb_build(ktl_sb* sb) {
    return sb->data ? sb->data : "";
}

static inline void ktl_sb_free(ktl_sb* sb) {
    if (sb->data) {
        free(sb->data);
        sb->data = NULL;
    }
    sb->len = 0;
    sb->cap = 0;
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

// Katlin Standard Function Aliases
#define str_len(s) ktl_str_len(s)
#define str_eq(a, b) ktl_str_eq(a, b)
#define str_concat(a, b) ktl_str_concat(a, b)
#define str_char_at(s, i) ktl_str_char_at(s, i)
#define str_sub(s, a, b) ktl_str_sub(s, a, b)
#define str_from_char(c) ktl_str_from_char(c)
#define str_starts_with(s, p) ktl_str_starts_with(s, p)
#define str_ends_with(s, p) ktl_str_ends_with(s, p)
#define str_contains(s, p) ktl_str_contains(s, p)
#define str_index_of(s, p, i) ktl_str_index_of(s, p, i)
#define str_int(v) ktl_str_int(v)
#define parse_int(s) ktl_parse_int(s)
#define path_base(p) ktl_path_base(p)
#define path_dir(p) ktl_path_dir(p)

#define file_read(p) ktl_file_read_str(p)
#define file_write(p, c) ktl_file_write_str(p, c)
#define file_append(p, c) ktl_file_append_str(p, c)
#define file_exists(p) ktl_file_exists(p)

#define TO_VEC_PTR(v) _Generic(&(v), ktl_vec**: *(ktl_vec**)&(v), default: (ktl_vec*)&(v))
#define TO_SB_PTR(s) _Generic(&(s), ktl_sb**: *(ktl_sb**)&(s), default: (ktl_sb*)&(s))
#define TO_ARENA_PTR(a) _Generic(&(a), ktl_arena**: *(ktl_arena**)&(a), default: (ktl_arena*)&(a))

#define vec_create(c) ktl_vec_create(c)
#define vec_push(v, x) ktl_vec_push(TO_VEC_PTR(v), (int64_t)(x))
#define vec_get(v, i) ktl_vec_get(TO_VEC_PTR(v), i)
#define vec_set(v, i, x) ktl_vec_set(TO_VEC_PTR(v), i, (int64_t)(x))
#define vec_len(v) ktl_vec_len(TO_VEC_PTR(v))
#define vec_free(v) ktl_vec_free(TO_VEC_PTR(v))

#define sb_create(c) ktl_sb_create(c)
#define sb_append(s, v) ktl_sb_append(TO_SB_PTR(s), v)
#define sb_append_char(s, c) ktl_sb_append_char(TO_SB_PTR(s), c)
#define sb_build(s) ktl_sb_build(TO_SB_PTR(s))
#define sb_free(s) ktl_sb_free(TO_SB_PTR(s))

#define arena_create(c) ktl_arena_create(c)
#define arena_alloc(a, s) ktl_arena_alloc(TO_ARENA_PTR(a), s)
#define arena_reset(a) ktl_arena_reset(TO_ARENA_PTR(a))
#define arena_destroy(a) ktl_arena_destroy(TO_ARENA_PTR(a))

#define time_now() ktl_time_now()
#define get_ram_mb() ktl_get_ram_mb()
#define abs(x) ktl_abs(x)
#define min(a, b) ktl_min(a, b)
#define max(a, b) ktl_max(a, b)
#define hash(s) ktl_hash(s)
#define alloc_ints(n) ktl_alloc_ints(n)
#define free_ints(p) ktl_free_ints(p)
#define assert(c, m) ktl_assert(c, m)
#define panic(m) ktl_panic(m)
#define system(c) ktl_run(c)
#define exit(c) ktl_exit(c)
#define env_get(n) ktl_env_get(n)
#define args_count() ktl_args_count()
#define args_get(i) ktl_args_get(i)

#endif // KATLIN_RUNTIME_H
