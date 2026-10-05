#!/usr/bin/env bash
# Install the Katlin compiler and its runtime.
#
# Layout produced (relative to the prefix, /usr/local by default):
#
#   <prefix>/bin/katlin            the compiler
#   <prefix>/lib/katlin/std/       katlin_runtime.h
#
# katlin locates its runtime relative to its own executable, so the layout
# above is what makes `katlin build` work from any directory. $KATLIN_STD
# overrides the search entirely.
#
# Usage:
#   ./install.sh                     # install to /usr/local (may need sudo)
#   PREFIX=~/.local ./install.sh     # install to a user prefix
#   ./install.sh --uninstall

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-/usr/local}"
BIN_DIR="$PREFIX/bin"
STD_DIR="$PREFIX/lib/katlin/std"

if [[ "${1:-}" == "--uninstall" ]]; then
    echo "==> Removing Katlin from $PREFIX"
    rm -f  "$BIN_DIR/katlin"
    rm -rf "$PREFIX/lib/katlin"
    echo "==> Done."
    exit 0
fi

if [ ! -x "$ROOT/bin/katlin" ]; then
    echo "error: $ROOT/bin/katlin not found. Run ./build.sh first." >&2
    exit 1
fi

echo "==> Installing Katlin"
echo "    compiler : $BIN_DIR/katlin"
echo "    runtime  : $STD_DIR/katlin_runtime.h"

install -d "$BIN_DIR" "$STD_DIR"
install -m 0755 "$ROOT/bin/katlin"          "$BIN_DIR/katlin"
install -m 0644 "$ROOT/std/katlin_runtime.h" "$STD_DIR/katlin_runtime.h"

echo "==> Installed: $("$BIN_DIR/katlin" version 2>/dev/null | head -1 | sed 's/\x1b\[[0-9;]*m//g')"
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "note: add $BIN_DIR to your PATH to run 'katlin' directly" ;;
esac
