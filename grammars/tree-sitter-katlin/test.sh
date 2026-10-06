#!/usr/bin/env bash
# Verify the Katlin tree-sitter grammar.
#
# Three checks, all against real code rather than hand-written trees:
#
#   1. Every .ktl file in the repository parses with no ERROR or MISSING
#      nodes. This is exactly the input the grammar sees in an editor.
#   2. Every query file compiles, so a typo in a node or capture name fails
#      here rather than silently losing colour.
#   3. Specific captures land on specific text. "Produces 341 captures" would
#      still pass if every one of them were @variable.
#
# Requires the tree-sitter CLI: cargo install tree-sitter-cli --locked
#
# Usage: grammars/tree-sitter-katlin/test.sh

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
QUERIES="$ROOT/editors/zed/languages/katlin"

if ! command -v tree-sitter >/dev/null 2>&1; then
    if [ -x "$HOME/.cargo/bin/tree-sitter" ]; then
        PATH="$HOME/.cargo/bin:$PATH"
    else
        echo "error: tree-sitter CLI not found. Install it with:" >&2
        echo "  cargo install tree-sitter-cli --locked" >&2
        exit 1
    fi
fi

cd "$HERE"

PASS=0
FAIL=0
fail() {
    FAIL=$((FAIL + 1))
    printf '  \033[1;31mFAIL\033[0m  %s\n' "$1"
    if [ -n "${2:-}" ]; then
        printf '%s\n' "$2" | head -6 | sed 's/^/        /'
    fi
}
pass() { PASS=$((PASS + 1)); printf '  \033[1;32mPASS\033[0m  %s\n' "$1"; }

echo "==> $(tree-sitter --version 2>&1 | head -1)"

echo
echo "==> Generating parser"
if ! tree-sitter generate 2>&1 | tail -20; then
    echo "error: tree-sitter generate failed" >&2
    exit 1
fi
echo "    src/parser.c regenerated"

echo
echo "==> Parsing repository sources"
# Deliberately includes examples/unsupported/ and the compiler's own source:
# the grammar should cope with syntax the compiler cannot yet compile.
mapfile -t FILES < <(find "$ROOT/examples" "$ROOT/compiler" -name '*.ktl' -type f | sort)

for f in "${FILES[@]}"; do
    rel="${f#"$ROOT"/}"
    out="$(tree-sitter parse "$f" 2>/dev/null)"
    if printf '%s' "$out" | grep -qE "ERROR|MISSING"; then
        first="$(printf '%s' "$out" | grep -oE '\((ERROR|MISSING)[^)]*\)' | head -1)"
        fail "$rel" "$first"
    else
        pass "$rel"
    fi
done

echo
echo "==> Validating queries"
for q in highlights brackets indents outline; do
    qf="$QUERIES/$q.scm"
    if [ ! -f "$qf" ]; then
        fail "$q.scm missing"
        continue
    fi
    # Capture stderr properly: the CLI emits a multi-line "not configured any
    # parser directories" warning first, which would otherwise mask the real
    # "Query error at L:C" message. Only error lines are kept.
    err="$(tree-sitter query "$qf" "$ROOT/examples/tour.ktl" 2>&1 >/dev/null \
        | grep -E 'Error|error at' || true)"
    if [ -z "$err" ]; then
        pass "$q.scm compiles"
    else
        fail "$q.scm does not compile" "$err"
    fi
done

echo
echo "==> Capture correctness"
FIXTURE="$(mktemp -t katlin-hl-XXXXXX.ktl)"
trap 'rm -f "$FIXTURE"' EXIT
cat > "$FIXTURE" <<'KTL'
#strict

struct Point {
    int x;
    int &balance;
}

enum Color { Red, Green }

fn bump(int &a, int count) -> int {
    mut total := 0;
    if a < count {
        total = total + 1;
    }
    p := Point{ x = 1 };
    c := Color.Red;
    println("hi %", total);
    return total;
}
KTL

# Reduce `pattern: N, capture: M - kind, ... text: `foo`` to "kind<TAB>text".
CAPTURES="$(tree-sitter query --captures "$QUERIES/highlights.scm" "$FIXTURE" 2>/dev/null \
    | sed -nE 's/.*- ([a-z][a-z.]*), .*text: `(.*)`$/\1\t\2/p')"

if [ -z "$CAPTURES" ]; then
    fail "highlights.scm produced no captures at all"
else
    # expect_capture <capture-name> <exact text>
    expect_capture() {
        if printf '%s\n' "$CAPTURES" | grep -qxF "$(printf '%s\t%s' "$1" "$2")"; then
            pass "$2 -> @$1"
        else
            local got
            got="$(printf '%s\n' "$CAPTURES" | grep -F "$(printf '\t%s' "$2")" | tr '\n' ' ')"
            fail "$2 should be @$1" "got: ${got:-<no capture>}"
        fi
    }

    expect_capture keyword           "fn"
    expect_capture keyword           "if"
    expect_capture keyword           "struct"
    expect_capture preproc           "#strict"
    expect_capture function          "bump"
    expect_capture function.call     "println"
    expect_capture type.builtin      "int"
    expect_capture type              "Point"
    expect_capture property          "x"
    expect_capture variant           "Red"
    expect_capture number            "0"
    expect_capture variable          "total"
    expect_capture operator          ":="
    expect_capture punctuation.bracket "{"
fi

echo
printf '==> %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "==> all green"
