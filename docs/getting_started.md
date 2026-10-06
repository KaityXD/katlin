# Getting Started with Katlin

This guide covers setting up Katlin, understanding the CLI commands, and configuring your development environment.

---

## 1. Prerequisites

Katlin compiles source code through an optimizing C99 backend. You only need:

- **Clang** (recommended) or **GCC** (C99+ capable).
- **Linux x86_64**, **macOS**, or **Windows (via WSL/MinGW)**.
- **Node.js 18+** (optional, only needed if you want editor LSP diagnostics).

On Debian / Ubuntu:
```bash
sudo apt-get update && sudo apt-get install -y clang
```

On Arch Linux:
```bash
sudo pacman -S clang
```

---

## 2. Bootstrapping the Compiler

The Katlin compiler binary ([`bin/katlin`](../bin/katlin)) is pre-bootstrapped and committed directly in the repository. You can use it immediately without compiling anything first:

```bash
./bin/katlin version
```

To rebuild the native compiler from source:

```bash
./build.sh
```

To verify deterministic self-hosting convergence (building the compiler with itself in generation 2):

```bash
./build.sh --verify
```

To install the compiler system-wide:

```bash
PREFIX=~/.local ./install.sh
```

This places the `katlin` binary in `~/.local/bin` and the standard runtime headers in `~/.local/lib/katlin/std`. Ensure `~/.local/bin` is in your `$PATH`.

---

## 3. Scaffolding a New Project

Use `katlin init` to scaffold a ready-to-run Katlin project:

```bash
katlin init my_app
cd my_app
```

This creates a standard project directory:

```
my_app/
├── katlin.toml       # Build configuration
└── src/
    └── main.ktl      # Application entrypoint
```

Run your new application:

```bash
katlin run src/main.ktl
```

---

## 4. Toolchain Commands

The `katlin` CLI provides all essential developer subcommands:

### `katlin run <file.ktl> [args...]`
Compiles the specified source and immediately executes the binary in memory:
```bash
katlin run src/main.ktl
```
Any trailing arguments are passed directly to your program and accessible via `args_get(index)`.

### `katlin build <file.ktl> [options]`
Compiles your project into a standalone, statically optimized native binary:
```bash
# Builds to .build/bin/<name> with -O3 -flto by default
katlin build src/main.ktl

# Specify custom output path
katlin build src/main.ktl -o ./my_binary

# Compile with debug symbols and no optimizations (-O0 -g)
katlin build src/main.ktl --debug -o ./my_debug_bin

# Explicit release build
katlin build src/main.ktl --release -o ./my_release_bin
```

### `katlin check <file.ktl>`
Performs syntax checking, `#strict` borrow analysis, and semantic validation without producing an executable binary. This is ultra-fast and used by the language server:
```bash
katlin check src/main.ktl
```

### `katlin test [path]`
Discovers and executes all `test "name" { ... }` blocks across your project:
```bash
katlin test
katlin test tests/
```

### `katlin fmt [path]`
Idempotently auto-formats `.ktl` files:
```bash
katlin fmt src/
```

---

## 5. Configuration (`katlin.toml`)

Projects can include a `katlin.toml` configuration file in their root directory:

```toml
[package]
name = "my_app"
version = "0.1.0"

[build]
opt_level = 3   # 0 = debug (-O0), 1-3 = optimized (-O3 -flto)
```

Command-line flags like `--debug` or `--release` override `katlin.toml` settings.

---

## 6. Editor Setup

### VS Code
1. Open the repository in VS Code.
2. The extension located in `editors/vscode/` provides:
   - Live diagnostics squiggles driven by the background language server.
   - TextMate syntax highlighting.
   - Snippets and auto-closing pairs.
3. Run `node editors/vscode/server/test.js` to verify your local language server.

### Zed
1. Katlin includes a native Tree-sitter grammar and Zed extension in `editors/zed/`.
2. Follow the setup instructions in [`editors/zed/README.md`](../editors/zed/README.md) to install it as a development extension in Zed.
