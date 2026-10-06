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
#include <ctype.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
#include <unistd.h>
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

static inline ktl_int ktl_sb_len(ktl_sb* sb) {
    return sb ? (ktl_int)sb->len : 0;
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

// -------------------------------------------------------------
// Advanced String Utilities
// -------------------------------------------------------------
static inline const char* ktl_str_trim(const char* s) {
    if (!s) return "";
    while (*s && isspace((unsigned char)*s)) s++;
    if (*s == 0) return "";
    const char* end = s + strlen(s) - 1;
    while (end > s && isspace((unsigned char)*end)) end--;
    size_t len = (size_t)(end - s + 1);
    char* buf = (char*)malloc(len + 1);
    memcpy(buf, s, len);
    buf[len] = '\0';
    return buf;
}

static inline const char* ktl_str_to_lower(const char* s) {
    if (!s) return "";
    size_t len = strlen(s);
    char* buf = (char*)malloc(len + 1);
    for (size_t i = 0; i < len; i++) {
        buf[i] = (char)tolower((unsigned char)s[i]);
    }
    buf[len] = '\0';
    return buf;
}

static inline const char* ktl_str_to_upper(const char* s) {
    if (!s) return "";
    size_t len = strlen(s);
    char* buf = (char*)malloc(len + 1);
    for (size_t i = 0; i < len; i++) {
        buf[i] = (char)toupper((unsigned char)s[i]);
    }
    buf[len] = '\0';
    return buf;
}

static inline const char* ktl_str_replace(const char* s, const char* old_sub, const char* new_sub) {
    if (!s) return "";
    if (!old_sub || strlen(old_sub) == 0) return s;
    if (!new_sub) new_sub = "";
    size_t old_len = strlen(old_sub);
    ktl_sb sb = ktl_sb_create(strlen(s) + 16);
    const char* cur = s;
    while (*cur) {
        const char* p = strstr(cur, old_sub);
        if (!p) {
            ktl_sb_append(&sb, cur);
            break;
        }
        size_t dist = (size_t)(p - cur);
        if (dist > 0) {
            char* part = (char*)malloc(dist + 1);
            memcpy(part, cur, dist);
            part[dist] = '\0';
            ktl_sb_append(&sb, part);
            free(part);
        }
        ktl_sb_append(&sb, new_sub);
        cur = p + old_len;
    }
    return ktl_sb_build(&sb);
}

static inline const char* ktl_str_repeat(const char* s, ktl_int count) {
    if (!s || count <= 0) return "";
    size_t slen = strlen(s);
    char* buf = (char*)malloc(slen * count + 1);
    buf[0] = '\0';
    for (int i = 0; i < count; i++) {
        memcpy(buf + i * slen, s, slen);
    }
    buf[slen * count] = '\0';
    return buf;
}

static inline const char* ktl_str_split_at(const char* s, const char* delim, ktl_int idx) {
    if (!s || !delim || idx < 0) return "";
    size_t dlen = strlen(delim);
    if (dlen == 0) return idx == 0 ? s : "";
    const char* cur = s;
    ktl_int cur_idx = 0;
    while (cur) {
        const char* next = strstr(cur, delim);
        if (cur_idx == idx) {
            size_t part_len = next ? (size_t)(next - cur) : strlen(cur);
            char* buf = (char*)malloc(part_len + 1);
            memcpy(buf, cur, part_len);
            buf[part_len] = '\0';
            return buf;
        }
        if (!next) break;
        cur = next + dlen;
        cur_idx++;
    }
    return "";
}

static inline ktl_int ktl_str_count(const char* s, const char* needle) {
    if (!s || !needle || strlen(needle) == 0) return 0;
    ktl_int count = 0;
    size_t nlen = strlen(needle);
    const char* p = s;
    while ((p = strstr(p, needle)) != NULL) {
        count++;
        p += nlen;
    }
    return count;
}

// -------------------------------------------------------------
// File & Directory Operations
// -------------------------------------------------------------
static inline ktl_i64 ktl_file_size(const char* path) {
    if (!path) return -1;
    struct stat st;
    if (stat(path, &st) != 0) return -1;
    return (ktl_i64)st.st_size;
}

static inline bool ktl_file_remove(const char* path) {
    if (!path) return false;
    return remove(path) == 0;
}

static inline bool ktl_file_is_dir(const char* path) {
    if (!path) return false;
    struct stat st;
    if (stat(path, &st) != 0) return false;
    return S_ISDIR(st.st_mode);
}

static inline bool ktl_dir_create(const char* path) {
    if (!path) return false;
    struct stat st;
    if (stat(path, &st) == 0) return S_ISDIR(st.st_mode);
    return mkdir(path, 0755) == 0;
}

static inline const char* ktl_dir_list(const char* path) {
    if (!path) return "";
    DIR* d = opendir(path);
    if (!d) return "";
    ktl_sb sb = ktl_sb_create(256);
    struct dirent* entry;
    bool first = true;
    while ((entry = readdir(d)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) continue;
        if (!first) ktl_sb_append_char(&sb, '\n');
        ktl_sb_append(&sb, entry->d_name);
        first = false;
    }
    closedir(d);
    return ktl_sb_build(&sb);
}

// -------------------------------------------------------------
// Subprocess Command Output Capture
// -------------------------------------------------------------
static inline const char* ktl_cmd_output(const char* cmd) {
    if (!cmd) return "";
    FILE* pipe = popen(cmd, "r");
    if (!pipe) return "";
    ktl_sb sb = ktl_sb_create(512);
    char chunk[256];
    while (fgets(chunk, sizeof(chunk), pipe) != NULL) {
        ktl_sb_append(&sb, chunk);
    }
    pclose(pipe);
    return ktl_sb_build(&sb);
}

// -------------------------------------------------------------
// Networking & Sockets (Web Services / Microservices)
// -------------------------------------------------------------
static inline ktl_int ktl_net_tcp_listen(ktl_int port) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons((uint16_t)port);
    if (bind(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    if (listen(fd, 64) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static inline ktl_int ktl_net_tcp_accept(ktl_int server_fd) {
    if (server_fd < 0) return -1;
    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);
    int client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
    return client_fd;
}

static inline const char* ktl_net_tcp_read(ktl_int client_fd, ktl_int max_len) {
    if (client_fd < 0 || max_len <= 0) return "";
    char* buf = (char*)malloc(max_len + 1);
    if (!buf) return "";
    ssize_t n = recv(client_fd, buf, max_len, 0);
    if (n <= 0) {
        free(buf);
        return "";
    }
    buf[n] = '\0';
    return buf;
}

static inline ktl_int ktl_net_tcp_write(ktl_int client_fd, const char* data) {
    if (client_fd < 0 || !data) return -1;
    size_t len = strlen(data);
    ssize_t sent = send(client_fd, data, len, 0);
    return (ktl_int)sent;
}

static inline ktl_int ktl_net_tcp_connect(const char* host, ktl_int port) {
    if (!host || port <= 0) return -1;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    struct hostent* he = gethostbyname(host);
    if (!he) {
        close(fd);
        return -1;
    }
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port);
    memcpy(&addr.sin_addr, he->h_addr_list[0], he->h_length);
    if (connect(fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

static inline void ktl_net_close(ktl_int fd) {
    if (fd >= 0) close(fd);
}

// -------------------------------------------------------------
// Dynamic String Vector (vec_str)
// -------------------------------------------------------------
typedef struct {
    char** data;
    size_t len;
    size_t cap;
} ktl_vec_str;

typedef ktl_vec_str vec_str;

static inline ktl_vec_str ktl_vec_str_create(size_t initial_cap) {
    ktl_vec_str v;
    v.cap = initial_cap > 0 ? initial_cap : 8;
    v.len = 0;
    v.data = (char**)malloc(v.cap * sizeof(char*));
    return v;
}

static inline void ktl_vec_str_push(ktl_vec_str* v, const char* item) {
    if (!item) item = "";
    if (v->len >= v->cap) {
        v->cap = (v->cap * 3) / 2 + 8;
        v->data = (char**)realloc(v->data, v->cap * sizeof(char*));
    }
    size_t slen = strlen(item);
    char* copy = (char*)malloc(slen + 1);
    memcpy(copy, item, slen + 1);
    v->data[v->len++] = copy;
}

static inline const char* ktl_vec_str_get(ktl_vec_str* v, size_t index) {
    if (index >= v->len) {
        ktl_panic("String vector index out of bounds!");
    }
    return v->data[index];
}

static inline ktl_int ktl_vec_str_len(ktl_vec_str* v) {
    return (ktl_int)v->len;
}

static inline const char* ktl_vec_str_join(ktl_vec_str* v, const char* delim) {
    if (!delim) delim = "";
    if (v->len == 0) return "";
    ktl_sb sb = ktl_sb_create(128);
    for (size_t i = 0; i < v->len; i++) {
        if (i > 0) ktl_sb_append(&sb, delim);
        ktl_sb_append(&sb, v->data[i]);
    }
    return ktl_sb_build(&sb);
}

static inline void ktl_vec_str_free(ktl_vec_str* v) {
    if (v->data) {
        for (size_t i = 0; i < v->len; i++) {
            if (v->data[i]) free(v->data[i]);
        }
        free(v->data);
        v->data = NULL;
    }
    v->len = 0;
    v->cap = 0;
}

// -------------------------------------------------------------
// Key-Value String Map (map)
// -------------------------------------------------------------
typedef struct {
    char* key;
    char* val;
} ktl_map_entry;

typedef struct {
    ktl_map_entry* entries;
    size_t len;
    size_t cap;
} ktl_map;

typedef ktl_map map;

static inline ktl_map ktl_map_create(size_t initial_cap) {
    ktl_map m;
    m.cap = initial_cap > 0 ? initial_cap : 16;
    m.len = 0;
    m.entries = (ktl_map_entry*)calloc(m.cap, sizeof(ktl_map_entry));
    return m;
}

static inline void ktl_map_set(ktl_map* m, const char* key, const char* val) {
    if (!key) return;
    if (!val) val = "";
    for (size_t i = 0; i < m->len; i++) {
        if (m->entries[i].key && strcmp(m->entries[i].key, key) == 0) {
            free(m->entries[i].val);
            size_t vlen = strlen(val);
            char* vcopy = (char*)malloc(vlen + 1);
            memcpy(vcopy, val, vlen + 1);
            m->entries[i].val = vcopy;
            return;
        }
    }
    if (m->len >= m->cap) {
        m->cap = m->cap * 2 + 8;
        m->entries = (ktl_map_entry*)realloc(m->entries, m->cap * sizeof(ktl_map_entry));
    }
    size_t klen = strlen(key);
    char* kcopy = (char*)malloc(klen + 1);
    memcpy(kcopy, key, klen + 1);

    size_t vlen = strlen(val);
    char* vcopy = (char*)malloc(vlen + 1);
    memcpy(vcopy, val, vlen + 1);

    m->entries[m->len].key = kcopy;
    m->entries[m->len].val = vcopy;
    m->len++;
}

static inline const char* ktl_map_get(ktl_map* m, const char* key) {
    if (!key) return "";
    for (size_t i = 0; i < m->len; i++) {
        if (m->entries[i].key && strcmp(m->entries[i].key, key) == 0) {
            return m->entries[i].val ? m->entries[i].val : "";
        }
    }
    return "";
}

static inline bool ktl_map_has(ktl_map* m, const char* key) {
    if (!key) return false;
    for (size_t i = 0; i < m->len; i++) {
        if (m->entries[i].key && strcmp(m->entries[i].key, key) == 0) {
            return true;
        }
    }
    return false;
}

static inline ktl_int ktl_map_len(ktl_map* m) {
    return (ktl_int)m->len;
}

static inline void ktl_map_free(ktl_map* m) {
    if (m->entries) {
        for (size_t i = 0; i < m->len; i++) {
            if (m->entries[i].key) free(m->entries[i].key);
            if (m->entries[i].val) free(m->entries[i].val);
        }
        free(m->entries);
        m->entries = NULL;
    }
    m->len = 0;
    m->cap = 0;
}

// -------------------------------------------------------------
// Time, Sleep & Random Numbers
// -------------------------------------------------------------
static inline void ktl_sleep_ms(ktl_int ms) {
    if (ms > 0) {
        usleep((useconds_t)ms * 1000);
    }
}

static inline ktl_i64 ktl_time_unix(void) {
    return (ktl_i64)time(NULL);
}

static inline void ktl_rand_seed(ktl_int seed) {
    srand((unsigned int)seed);
}

static inline ktl_int ktl_rand_int(ktl_int min_val, ktl_int max_val) {
    if (min_val >= max_val) return min_val;
    return min_val + (rand() % (max_val - min_val + 1));
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

#define str_trim(s) ktl_str_trim(s)
#define str_to_lower(s) ktl_str_to_lower(s)
#define str_to_upper(s) ktl_str_to_upper(s)
#define str_replace(s, o, n) ktl_str_replace(s, o, n)
#define str_repeat(s, c) ktl_str_repeat(s, c)
#define str_split_at(s, d, i) ktl_str_split_at(s, d, i)
#define str_count(s, n) ktl_str_count(s, n)

#define file_read(p) ktl_file_read_str(p)
#define file_write(p, c) ktl_file_write_str(p, c)
#define file_append(p, c) ktl_file_append_str(p, c)
#define file_exists(p) ktl_file_exists(p)
#define file_size(p) ktl_file_size(p)
#define file_remove(p) ktl_file_remove(p)
#define file_is_dir(p) ktl_file_is_dir(p)
#define dir_create(p) ktl_dir_create(p)
#define dir_list(p) ktl_dir_list(p)

#define cmd_output(c) ktl_cmd_output(c)

#define net_tcp_listen(p) ktl_net_tcp_listen(p)
#define net_tcp_accept(s) ktl_net_tcp_accept(s)
#define net_tcp_read(c, m) ktl_net_tcp_read(c, m)
#define net_tcp_write(c, d) ktl_net_tcp_write(c, d)
#define net_tcp_connect(h, p) ktl_net_tcp_connect(h, p)
#define net_close(f) ktl_net_close(f)

#define TO_VEC_PTR(v) _Generic(&(v), ktl_vec**: *(ktl_vec**)&(v), default: (ktl_vec*)&(v))
#define TO_VEC_STR_PTR(v) _Generic(&(v), ktl_vec_str**: *(ktl_vec_str**)&(v), default: (ktl_vec_str*)&(v))
#define TO_MAP_PTR(m) _Generic(&(m), ktl_map**: *(ktl_map**)&(m), default: (ktl_map*)&(m))
#define TO_SB_PTR(s) _Generic(&(s), ktl_sb**: *(ktl_sb**)&(s), default: (ktl_sb*)&(s))
#define TO_ARENA_PTR(a) _Generic(&(a), ktl_arena**: *(ktl_arena**)&(a), default: (ktl_arena*)&(a))

#define vec_create(c) ktl_vec_create(c)
#define vec_push(v, x) ktl_vec_push(TO_VEC_PTR(v), (int64_t)(x))
#define vec_get(v, i) ktl_vec_get(TO_VEC_PTR(v), i)
#define vec_set(v, i, x) ktl_vec_set(TO_VEC_PTR(v), i, (int64_t)(x))
#define vec_len(v) ktl_vec_len(TO_VEC_PTR(v))
#define vec_free(v) ktl_vec_free(TO_VEC_PTR(v))

#define vec_str_create(c) ktl_vec_str_create(c)
#define vec_str_push(v, s) ktl_vec_str_push(TO_VEC_STR_PTR(v), s)
#define vec_str_get(v, i) ktl_vec_str_get(TO_VEC_STR_PTR(v), i)
#define vec_str_len(v) ktl_vec_str_len(TO_VEC_STR_PTR(v))
#define vec_str_join(v, d) ktl_vec_str_join(TO_VEC_STR_PTR(v), d)
#define vec_str_free(v) ktl_vec_str_free(TO_VEC_STR_PTR(v))

#define map_create(c) ktl_map_create(c)
#define map_set(m, k, v) ktl_map_set(TO_MAP_PTR(m), k, v)
#define map_get(m, k) ktl_map_get(TO_MAP_PTR(m), k)
#define map_has(m, k) ktl_map_has(TO_MAP_PTR(m), k)
#define map_len(m) ktl_map_len(TO_MAP_PTR(m))
#define map_free(m) ktl_map_free(TO_MAP_PTR(m))

#define sb_create(c) ktl_sb_create(c)
#define sb_append(s, v) ktl_sb_append(TO_SB_PTR(s), v)
#define sb_append_char(s, c) ktl_sb_append_char(TO_SB_PTR(s), c)
#define sb_build(s) ktl_sb_build(TO_SB_PTR(s))
#define sb_free(s) ktl_sb_free(TO_SB_PTR(s))
#define sb_len(s) ktl_sb_len(TO_SB_PTR(s))

#define arena_create(c) ktl_arena_create(c)
#define arena_alloc(a, s) ktl_arena_alloc(TO_ARENA_PTR(a), s)
#define arena_reset(a) ktl_arena_reset(TO_ARENA_PTR(a))
#define arena_destroy(a) ktl_arena_destroy(TO_ARENA_PTR(a))

#define sleep_ms(m) ktl_sleep_ms(m)
#define time_unix() ktl_time_unix()
#define rand_seed(s) ktl_rand_seed(s)
#define rand_int(a, b) ktl_rand_int(a, b)

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
