#!/usr/bin/env bash
# Generate extension.toml with the absolute path to the bundled grammar.
#
# Zed extensions reference grammars by repository URL. For a locally installed
# development extension a `file://` URL works, but it has to be absolute, so
# this script writes the file rather than committing a path that would only be
# correct on one machine.
#
# Usage:
#   editors/zed/setup.sh                 full extension (highlighting + diagnostics)
#   editors/zed/setup.sh --grammar-only  no Rust, so no wasm target needed
#
# --grammar-only omits the [lib] and [language_servers] sections. Zed then
# installs the extension without compiling any Rust, which needs no
# wasm32-wasip2 target -- but the language server is not registered, so you
# get highlighting, brackets, indentation and outline, and no diagnostics.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
GRAMMAR="$ROOT/grammars/tree-sitter-katlin"

MODE="full"
if [ "${1:-}" = "--grammar-only" ]; then
    MODE="grammar-only"
fi

if [ ! -f "$GRAMMAR/grammar.js" ]; then
    echo "error: grammar not found at $GRAMMAR" >&2
    exit 1
fi

if [ ! -f "$GRAMMAR/src/parser.c" ]; then
    echo "note: $GRAMMAR/src/parser.c is missing."
    echo "      Generate it first:  cd grammars/tree-sitter-katlin && tree-sitter generate"
    echo
fi

if [ "$MODE" = "full" ]; then
    DESCRIPTION="Katlin language support: highlighting, brackets, outline, and live compiler diagnostics."
else
    DESCRIPTION="Katlin language support: highlighting, brackets and outline (no language server)."
fi

cat > "$HERE/extension.toml" <<EOF
id = "katlin"
name = "Katlin"
version = "0.1.0"
schema_version = 1
description = "$DESCRIPTION"
repository = "$ROOT"
authors = ["Katlin contributors"]
languages = ["languages/katlin"]
capabilities = []
EOF

# The Rust library is what launches the language server. Without a
# wasm32-wasip2 target it cannot be built, so --grammar-only leaves it out
# entirely and Zed installs the extension as a pure grammar.
if [ "$MODE" = "full" ]; then
    cat >> "$HERE/extension.toml" <<EOF

[lib]
kind = "Rust"
version = "0.7.0"
EOF
fi

cat >> "$HERE/extension.toml" <<EOF

[grammars.katlin]
# A local development extension points at the bundled grammar rather than a
# published repository. Regenerate this file if the checkout moves.
repository = "file://$GRAMMAR"
rev = "HEAD"

EOF

if [ "$MODE" = "full" ]; then
    cat >> "$HERE/extension.toml" <<EOF

[language_servers.katlin]
name = "Katlin Language Server"
languages = ["Katlin"]
EOF
fi

echo "==> Wrote $HERE/extension.toml ($MODE)"
echo "    grammar: file://$GRAMMAR"
echo
echo "Next steps:"
echo "  1. cd $GRAMMAR && tree-sitter generate"
echo "  2. In Zed: command palette -> 'zed: install dev extension' -> select:"
echo "       $HERE"
echo "  3. Open any .ktl file."
