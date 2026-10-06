# Katlin for Visual Studio Code

Syntax highlighting, snippets, and **live compiler diagnostics** for the
[Katlin programming language](../..) (`.ktl`).

## Features

- **Diagnostics as you type.** Errors from `katlin check` appear as you edit —
  including `#strict` borrow-checker violations, which land on the exact line.
- **Syntax highlighting** for keywords (`fn`, `mut`, `raw`, `test`, `match`,
  `case`, `or`), pragmas (`#strict`), reference types (`int &sum`), `%` format
  strings, numbers and builtins.
- **Snippets** for functions, range loops, test blocks, structs and enums.
- **Auto-closing and bracket matching.**

## Installing

The extension needs the compiler. Build it once from the repository root:

```bash
./build.sh          # produces bin/katlin
```

Then either link the extension directory into VS Code:

```bash
ln -s "$PWD/editors/vscode" ~/.vscode/extensions/katlin-lang
```

or package it:

```bash
cd editors/vscode
npm install          # pulls in vscode-languageclient
npx vsce package
```

`npm install` is only needed for the VS Code client. The language server
itself has no dependencies.

Restart VS Code. Opening any `.ktl` file starts the server.

## Configuration

| Setting | Meaning |
| :--- | :--- |
| `katlin.compilerPath` | Path to the `katlin` binary. Empty means: `bin/katlin` in the workspace, then `katlin` on `$PATH`. |

## What the diagnostics can and cannot tell you

The server runs `katlin check` on the buffer and translates the output. There
are two kinds of error, and they are treated differently on purpose:

- **Front-end errors** — borrow-checker violations, a missing `fn main`, an
  unreadable file — carry a real source line, and are shown as normal
  squiggles on that line.
- **C backend errors** — type errors and the like — do **not**. The compiler
  emits C, hands it to clang, and clang reports positions in the generated
  `.build/<name>.c` file. There is no mapping back to the `.ktl` source, so
  rather than underline a line that might be wrong, these appear as a single
  diagnostic at the top of the file carrying the raw clang message.

The message tells you *what* is wrong; running `katlin check <file>` in a
terminal tells you *where*, because it prints the generated C with clang's
own context lines.

Closing this gap means teaching the transpiler to emit `#line` directives, so
clang reports positions against the original `.ktl` file. That is on the
roadmap; until then, front-end errors are precise and backend errors are
merely accurate.

## The server is standalone

`server/server.js` is a plain Node program (no dependencies) that speaks LSP
over stdio, so any editor can drive it:

```bash
node server/server.js /path/to/bin/katlin
```

`$KATLIN_BIN` overrides the compiler path; otherwise it looks for
`bin/katlin` above the server file, then `katlin` on `$PATH`.

## Tests

The server has a test suite that drives the real thing over stdio and asserts
the diagnostics that come back:

```bash
node server/test.js      # or: npm test
```
