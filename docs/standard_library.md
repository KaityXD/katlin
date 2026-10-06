# Katlin Standard Library Reference

The Katlin Standard Library is provided as zero-dependency inline C primitives in [`std/katlin_runtime.h`](../std/katlin_runtime.h), automatically linked into every compiled binary.

Every function below also works as a **dot-method** on its first argument — `str_len(s)` ⇄ `s.len()`, `vec_push(v, x)` ⇄ `v.push(x)`, `map_get(m, k)` ⇄ `m.get(k)`, `sb_append(sb, s)` ⇄ `sb.append(s)`, `arena_alloc(a, n)` ⇄ `a.alloc(n)`. Both spellings compile to identical C; see [Functions & Arguments](functions.md) §5.

---

## 1. Advanced String Utilities

Strings in Katlin are immutable, UTF-8 zero-terminated pointers (`str`).

| Function | Signature | Description |
| :--- | :--- | :--- |
| `str_len` | `(str s) -> int` | Returns the byte length of string `s` |
| `str_eq` | `(str a, str b) -> bool` | Returns `true` if `a` and `b` contain identical content |
| `str_concat` | `(str a, str b) -> str` | Allocates and returns the concatenation of `a` and `b` |
| `str_trim` | `(str s) -> str` | Trims leading and trailing whitespace |
| `str_to_lower` | `(str s) -> str` | Returns a lowercase copy of `s` |
| `str_to_upper` | `(str s) -> str` | Returns an uppercase copy of `s` |
| `str_replace` | `(str s, str old_s, str new_s) -> str` | Replaces all occurrences of `old_s` with `new_s` |
| `str_repeat` | `(str s, int count) -> str` | Repeats string `s` `count` times |
| `str_split_at` | `(str s, str delim, int idx) -> str` | Splits `s` by `delim` and returns token at 0-indexed `idx` |
| `str_count` | `(str s, str needle) -> int` | Counts occurrences of `needle` in `s` |
| `str_char_at` | `(str s, int idx) -> int` | Returns the ASCII/byte value at 0-based index `idx` |
| `str_sub` | `(str s, int start, int len) -> str` | Extracts a substring of length `len` starting at `start` |
| `str_from_char` | `(int c) -> str` | Creates a 1-character string from an ASCII code |
| `str_starts_with` | `(str s, str prefix) -> bool` | Checks if `s` begins with `prefix` |
| `str_ends_with` | `(str s, str suffix) -> bool` | Checks if `s` ends with `suffix` |
| `str_contains` | `(str s, str needle) -> bool` | Checks if `needle` occurs anywhere inside `s` |
| `str_index_of` | `(str s, str needle, int start) -> int` | Returns the first index of `needle` at or after `start` (-1 if not found) |
| `str_int` | `(int v) -> str` | Formats integer `v` into a string |
| `parse_int` | `(str s) -> int` | Parses a decimal integer string into an `int` |

---

## 2. TCP Networking & Web Services (`net_*`)

Native Berkeley sockets for creating web servers, microservices, TCP proxies, and client applications.

| Function | Signature | Description |
| :--- | :--- | :--- |
| `net_tcp_listen` | `(int port) -> int` | Creates and binds a TCP server listening on `port`. Returns socket fd or `-1` |
| `net_tcp_accept` | `(int server_fd) -> int` | Accepts an incoming client connection. Returns client fd or `-1` |
| `net_tcp_read` | `(int client_fd, int max_bytes) -> str` | Reads incoming request payload as a string |
| `net_tcp_write` | `(int client_fd, str data) -> int` | Sends string `data` to the socket. Returns bytes written |
| `net_tcp_connect` | `(str host, int port) -> int` | Connects as a client to `host:port`. Returns connected socket fd or `-1` |
| `net_close` | `(int fd)` | Closes socket descriptor |

---

## 3. Filesystem & Directory Utilities

| Function | Signature | Description |
| :--- | :--- | :--- |
| `file_exists` | `(str path) -> bool` | Checks if a file exists on the filesystem |
| `file_read` | `(str path) -> str` | Reads an entire file into memory as a string |
| `file_write` | `(str path, str content) -> bool` | Overwrites a file with `content` |
| `file_append` | `(str path, str content) -> bool` | Appends `content` to the end of a file |
| `file_size` | `(str path) -> i64` | Returns file size in bytes (-1 if file does not exist) |
| `file_remove` | `(str path) -> bool` | Deletes a file from the filesystem |
| `file_is_dir` | `(str path) -> bool` | Checks if `path` is a directory |
| `dir_create` | `(str path) -> bool` | Creates a directory (`mkdir -p` semantics) |
| `dir_list` | `(str path) -> str` | Returns newline-separated list of filenames in `path` |
| `path_base` | `(str path) -> str` | Extracts the filename without parent directories or extension |
| `path_dir` | `(str path) -> str` | Returns the directory portion of a file path |

---

## 4. Subprocess Execution & Output Capture

| Function | Signature | Description |
| :--- | :--- | :--- |
| `cmd_output` | `(str cmd) -> str` | Executes a shell command and captures its standard output into a string |
| `system` | `(str cmd) -> int` | Executes a shell command and returns its real exit code (0–255) |

---

## 5. Dynamic String Vector (`vec_str`)

A resizable list of dynamic strings with O(1) amortized appends.

| Function | Signature | Description |
| :--- | :--- | :--- |
| `vec_str_create` | `(int cap) -> vec_str` | Allocates a string vector with initial capacity |
| `vec_str_push` | `(vec_str v, str item)` | Appends string `item` to the vector |
| `vec_str_get` | `(vec_str v, int idx) -> str` | Gets string at 0-based index `idx` |
| `vec_str_len` | `(vec_str v) -> int` | Returns count of items in vector |
| `vec_str_join` | `(vec_str v, str delim) -> str` | Joins all vector strings separated by `delim` |
| `vec_str_free` | `(vec_str v)` | Deallocates vector memory |

---

## 6. Key-Value String Map (`map`)

An associative dictionary mapping string keys to string values for configurations, HTTP headers, caches, and lookup tables.

| Function | Signature | Description |
| :--- | :--- | :--- |
| `map_create` | `(int cap) -> map` | Allocates a hash map |
| `map_set` | `(map m, str key, str val)` | Sets or updates `key` with value `val` |
| `map_get` | `(map m, str key) -> str` | Returns the value associated with `key` (or `""` if not found) |
| `map_has` | `(map m, str key) -> bool` | Returns `true` if `key` exists in map |
| `map_len` | `(map m) -> int` | Returns number of entries in map |
| `map_free` | `(map m)` | Deallocates map memory |

---

## 7. Dynamic Vector (`vec`)

A dynamic array of 64-bit integer or pointer values that resizes automatically.

| Function | Signature | Description |
| :--- | :--- | :--- |
| `vec_create` | `(int cap) -> vec` | Creates a new vector with initial capacity `cap` |
| `vec_push` | `(vec v, int x)` | Appends element `x` to the vector (auto-resizes if needed) |
| `vec_get` | `(vec v, int idx) -> int` | Returns the element at 0-based index `idx` |
| `vec_set` | `(vec v, int idx, int val)` | Overwrites the element at `idx` |
| `vec_len` | `(vec v) -> int` | Returns the current count of elements in the vector |
| `vec_free` | `(vec v)` | Deallocates vector memory |

---

## 8. String Builder (`sb`)

Optimized for high-performance string accumulation.

| Function | Signature | Description |
| :--- | :--- | :--- |
| `sb_create` | `(int cap) -> sb` | Allocates a string builder with initial capacity `cap` |
| `sb_append` | `(sb s, str text)` | Appends `text` to the buffer |
| `sb_append_char` | `(sb s, int c)` | Appends a single character/byte `c` to the buffer |
| `sb_build` | `(sb s) -> str` | Finalizes and returns the null-terminated string |
| `sb_len` | `(sb s) -> int` | Returns the current buffered length in bytes |
| `sb_free` | `(sb s)` | Deallocates string builder memory |

---

## 9. Memory Arena (`arena`)

A high-performance linear bump-allocator with O(1) bulk reset.

| Function | Signature | Description |
| :--- | :--- | :--- |
| `arena_create` | `(int cap) -> arena` | Allocates an arena with capacity in bytes |
| `arena_alloc` | `(arena a, int bytes) -> *mut byte` | Carves out a contiguous slice of `bytes` from the arena |
| `arena_reset` | `(arena a)` | Resets the allocation offset to 0 (frees all blocks instantly) |
| `arena_destroy` | `(arena a)` | Releases the entire arena to the OS |

---

## 10. Timing, Random & Process Control

| Function | Signature | Description |
| :--- | :--- | :--- |
| `sleep_ms` | `(int ms)` | Suspends the current thread for `ms` milliseconds |
| `time_unix` | `() -> i64` | Returns current Unix epoch timestamp in seconds |
| `time_now` | `() -> float` | Returns high-resolution monotonic time in seconds |
| `rand_seed` | `(int seed)` | Seeds the pseudo-random number generator |
| `rand_int` | `(int min, int max) -> int` | Returns random integer in range `[min, max]` |
| `get_ram_mb` | `() -> float` | Returns current resident set size (RAM consumption) in megabytes |
| `args_count` | `() -> int` | Returns count of CLI arguments passed to binary |
| `args_get` | `(int idx) -> str` | Retrieves CLI argument string at index `idx` |
| `assert` | `(bool cond, str msg)` | Aborts execution if `cond` is false |
| `panic` | `(str msg)` | Halts execution immediately with diagnostic message `msg` |
| `exit` | `(int code)` | Terminates process with exit status `code` |

---

## Real-World Example: HTTP Microservice

Here is a complete, working HTTP Web Server written in Katlin:

```katlin
fn handle_client(int client_fd) {
    req := net_tcp_read(client_fd, 2048);
    if str_len(req) == 0 {
        net_close(client_fd);
        return;
    }

    first_line := str_split_at(req, "\r\n", 0);
    method := str_split_at(first_line, " ", 0);
    path := str_split_at(first_line, " ", 1);

    body := "{\"message\": \"Hello from Katlin!\", \"status\": \"online\"}";
    resp_len := str_len(body);

    mut resp := sb_create(512);
    sb_append(resp, "HTTP/1.1 200 OK\r\n");
    sb_append(resp, "Content-Type: application/json\r\n");
    sb_append(resp, str_concat("Content-Length: ", str_concat(str_int(resp_len), "\r\n")));
    sb_append(resp, "Connection: close\r\n\r\n");
    sb_append(resp, body);

    net_tcp_write(client_fd, sb_build(resp));
    sb_free(resp);
    net_close(client_fd);
}

fn main {
    server := net_tcp_listen(8080);
    println("🚀 Katlin server listening on http://localhost:8080");

    while true {
        client := net_tcp_accept(server);
        if client >= 0 {
            handle_client(client);
        }
    }
}
```
