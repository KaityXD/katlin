# Katlin Language Extension for Visual Studio Code

Official VS Code syntax highlighting, bracket matching, and snippets for the [Katlin Programming Language](https://katlin-lang.org) (`.ktl`).

## Features

- **Rich Syntax Highlighting**: Accurate grammar for Katlin keywords (`fn`, `mut`, `strict`, `raw`, `test`, `match`, `case`, `or`), pragmas (`#strict`), type signatures (`int &sum`), `%` format strings, numbers, and builtins.
- **Snippets**: Instant tab completions for functions, step range loops, test blocks, structs, and enums.
- **Auto-Closing & Bracket Matching**: Full support for braces, parens, brackets, and quotes.

## Manual Installation

To install into your local VS Code:
```bash
# Link or copy extension directory to VS Code extensions folder
cp -r editors/vscode ~/.vscode/extensions/katlin-lang-0.1.0
```
Or package into a `.vsix` using `npx vsce package`.
