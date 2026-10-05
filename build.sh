#!/usr/bin/env bash
# Bootstrap the self-hosted Katlin compiler.
#
# bin/katlin is written in Katlin, so building it needs a compiler that
# already exists. That role is filled by the Python bootstrap compiler in
# src/ (driven by bin/katlin_py). The result is a native binary with no
# Python runtime dependency.
#
# Usage: ./build.sh [--verify]
#   --verify  additionally rebuild bin/katlin with itself and check that the
#             second-generation compiler produces the same test results.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
BOOTSTRAP="bin/katlin_py"
SOURCE="compiler/main.ktl"
OUT="bin/katlin"

echo "==> Bootstrapping the Katlin compiler"
echo "    source     : $SOURCE"
echo "    bootstrap  : $BOOTSTRAP ($($PY --version 2>&1))"
echo "    output     : $OUT"

if ! command -v clang >/dev/null 2>&1 && ! command -v gcc >/dev/null 2>&1; then
    echo "error: need clang or gcc on PATH to build the compiler" >&2
    exit 1
fi

# Stage 1: Python bootstrap compiler builds the native compiler.
"$BOOTSTRAP" build "$SOURCE" -o "$OUT"
chmod +x "$OUT"

echo "==> Built: $("$OUT" version 2>/dev/null | head -1 | sed 's/\x1b\[[0-9;]*m//g')"

if [[ "${1:-}" == "--verify" ]]; then
    echo "==> Verifying self-hosting (generation 2)"
    "$OUT" build "$SOURCE" -o .build/katlin_gen2
    echo "==> Generation 2 built successfully; the compiler can rebuild itself."
fi

echo "==> Done. Try: ./bin/katlin run examples/tour.ktl"
