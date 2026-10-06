#!/usr/bin/env bash
# Generate extension.toml with the absolute path to the bundled grammar.
#
# Zed extensions reference grammars by repository URL. For a locally installed
# development extension a `file://` URL works, but it has to be absolute, so
# this script writes the file rather than committing a path that would only be
# correct on one machine.
#
# Usage: editors/zed/setup.sh

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
GRAMMAR="$ROOT/grammars/tree-sitter-katlin"

if [ ! -f "$GRAMMAR/grammar.js" ]; then
    echo "error: grammar not found at $GRAMMAR" >&2
    exit 1
fi

if [ ! -f "$GRAMMAR/src/parser.c" ]; then
    echo "note: $GRAMMAR/src/parser.c is missing."
    echo "      Generate it first:  cd grammars/tree-sitter-katlin && tree-sitter generate"
    echo
fi

cat > "$HERE/extension.toml" <<EOF
id = "katlin"
name = "Katlin"
version = "0.1.0"
schema_version = 1
description = "Katlin language support: highlighting, brackets, outline, and live compiler diagnostics."
repository = "$ROOT"
authors = ["Katlin contributors"]
languages = ["languages/katlin"]
capabilities = []

[lib]
kind = "Rust"
version = "0.7.0"

[grammars.katlin]
# A local development extension points at the bundled grammar rather than a
# published repository. Regenerate this file if the checkout moves.
repository = "file://$GRAMMAR"
rev = "HEAD"

[language_servers.katlin]
name = "Katlin Language Server"
languages = ["Katlin"]
EOF

echo "==> Wrote $HERE/extension.toml"
echo "    grammar: file://$GRAMMAR"
echo
echo "Next steps:"
echo "  1. cd $GRAMMAR && tree-sitter generate"
echo "  2. In Zed: command palette -> 'zed: install dev extension' -> select:"
echo "       $HERE"
echo "  3. Open any .ktl file."
