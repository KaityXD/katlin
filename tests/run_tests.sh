#!/usr/bin/env bash
# End-to-end tests for the SHIPPED compiler (bin/katlin).
#
# tests/test_compiler.py covers the Python bootstrap compiler. This script
# covers the native self-hosted binary that users actually run, which
# previously had no test coverage at all.
#
# Usage: tests/run_tests.sh

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

KATLIN="$ROOT/bin/katlin"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
FAILED_NAMES=()

# Strip ANSI colour so assertions compare plain text.
strip() { sed 's/\x1b\[[0-9;]*m//g'; }

ok()   { PASS=$((PASS+1)); printf '  \033[1;32mPASS\033[0m  %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); FAILED_NAMES+=("$1"); printf '  \033[1;31mFAIL\033[0m  %s\n' "$1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; }

# check_eq <name> <expected> <actual>
check_eq() {
    if [ "$2" = "$3" ]; then ok "$1"; else bad "$1" "expected [$2] got [$3]"; fi
}

# check_contains <name> <needle> <haystack>
check_contains() {
    case "$3" in
        *"$2"*) ok "$1" ;;
        *)      bad "$1" "missing [$2] in: $(printf '%s' "$3" | head -3 | tr '\n' ' ')" ;;
    esac
}

if [ ! -x "$KATLIN" ]; then
    echo "error: $KATLIN not found or not executable; run ./build.sh first" >&2
    exit 1
fi

echo "==> Testing $("$KATLIN" version | head -1 | strip)"

# --------------------------------------------------------------------------
echo
echo "cli contract"
# --------------------------------------------------------------------------
"$KATLIN" version >/dev/null 2>&1;                       check_eq "version exits 0" "0" "$?"
"$KATLIN" build "$WORK/nope.ktl" >/dev/null 2>&1;        check_eq "missing file exits 1" "1" "$?"
"$KATLIN" not-a-command >/dev/null 2>&1;                 check_eq "unknown command exits 1" "1" "$?"
echo 'fn main { this is not katlin }' > "$WORK/bad.ktl"
"$KATLIN" build "$WORK/bad.ktl" -o "$WORK/bad" >/dev/null 2>&1; check_eq "compile error exits 1" "1" "$?"
echo 'fn main { println("ok"); }' > "$WORK/good.ktl"
"$KATLIN" build "$WORK/good.ktl" -o "$WORK/good" >/dev/null 2>&1; check_eq "successful build exits 0" "0" "$?"

# --------------------------------------------------------------------------
echo
echo "language features"
# --------------------------------------------------------------------------
cat > "$WORK/features.ktl" <<'KTL'
struct P { int x; int y; }
enum C { Red, Green, Blue }

fn swap(int &a, int &b) { int t = a; a = b; b = t; }
fn area(P p) -> int { return p.x * p.y; }

fn main {
    mut n := 7;
    println("type=%", n.type);
    println("swap=%", 0);
    mut a := 1;
    mut b := 2;
    swap(&a, &b);
    println("a=% b=%", a, b);
    p := P{ x = 3, y = 4 };
    println("area=%", area(p));
    c := C.Blue;
    mut code = 0;
    match c {
        case .Red: { code = 1; }
        case .Blue: { code = 3; }
    }
    println("code=%", code);
}
KTL
out="$("$KATLIN" run "$WORK/features.ktl" 2>&1 | strip)"
check_contains "inferred .type resolves to int"  "type=int"  "$out"
check_contains "reference params write through"  "a=2 b=1"   "$out"
check_contains "struct member access"            "area=12"   "$out"
check_contains "enum + match"                    "code=3"    "$out"

# Regression: assignment through a & parameter used to compile silently but
# only advance the local pointer, leaving the caller's variable untouched.
cat > "$WORK/refregress.ktl" <<'KTL'
fn bump(int &a) { a = a + 1; }
fn main { mut int x = 41; bump(&x); println("%", x); }
KTL
check_eq "ref param mutates caller (regression)" "42" "$("$KATLIN" run "$WORK/refregress.ktl" 2>&1 | strip | tail -1)"

# --------------------------------------------------------------------------
echo
echo "#strict borrow checking"
# --------------------------------------------------------------------------
# Positive: valid borrows are accepted and the program runs.
"$KATLIN" run "$ROOT/examples/strict_borrows.ktl" > "$WORK/strict.out" 2>&1
check_eq "valid #strict program compiles and runs" "0" "$?"
check_contains "valid #strict program produces output" "all borrows accepted" "$(strip < "$WORK/strict.out")"

# Negative: the same variable borrowed twice in one call.
"$KATLIN" build "$ROOT/examples/borrow_fail.ktl" -o "$WORK/nope1" > "$WORK/bf.out" 2>&1
check_eq "aliased borrow is rejected" "1" "$?"
check_contains "aliased borrow reports the right rule" \
    "as mutable more than once" "$(strip < "$WORK/bf.out")"

# Negative: borrowing something that was never declared `mut`.
"$KATLIN" build "$ROOT/examples/borrow_immutable.ktl" -o "$WORK/nope2" > "$WORK/bi.out" 2>&1
check_eq "borrow of immutable is rejected" "1" "$?"
check_contains "immutable borrow reports the right rule" \
    "is not declared" "$(strip < "$WORK/bi.out")"

# Bitwise-and must not be mistaken for a borrow.
cat > "$WORK/bitand.ktl" <<'KTL'
#strict
fn main {
    mut int count = 0;
    mut i64 sum = 0;
    while count < 100 { sum += (count & 1); count += 1; }
    println("sum=%", sum);
}
KTL
out="$("$KATLIN" run "$WORK/bitand.ktl" 2>&1 | strip)"; code=$?
check_eq "bitwise-and is not treated as a borrow" "0" "$code"
check_contains "bitwise-and program computes correctly" "sum=50" "$out"

# Sequential borrows of the same variable in separate calls are fine.
cat > "$WORK/seq.ktl" <<'KTL'
#strict
fn bump(int &a) { a = a + 1; }
fn main {
    mut int n = 0;
    bump(&n);
    bump(&n);
    println("n=%", n);
}
KTL
out="$("$KATLIN" run "$WORK/seq.ktl" 2>&1 | strip)"; code=$?
check_eq "sequential borrows are accepted" "0" "$code"
check_contains "sequential borrows both take effect" "n=2" "$out"

# --------------------------------------------------------------------------
echo
echo "test runner"
# --------------------------------------------------------------------------
mkdir -p "$WORK/suites"
cat > "$WORK/suites/pass.ktl" <<'KTL'
fn add(int a, int b) -> int { return a + b; }
test "addition" { assert(add(2, 3) == 5, "2+3"); }
test "zero"     { assert(add(0, 0) == 0, "0+0"); }
KTL
out="$("$KATLIN" test "$WORK/suites" 2>&1 | strip)"; code=$?
check_eq "passing suite exits 0" "0" "$code"
check_contains "passing suite reports all tests" "all 2 test(s) passed" "$out"

cat > "$WORK/suites/fail.ktl" <<'KTL'
test "wrong on purpose" { assert(1 == 2, "one is not two"); }
KTL
"$KATLIN" test "$WORK/suites/fail.ktl" >/dev/null 2>&1
check_eq "failing suite exits 1" "1" "$?"

# --------------------------------------------------------------------------
echo
echo "formatter"
# --------------------------------------------------------------------------
printf 'fn main {   \n\n\n\n    println("hi");\t\n}\n\n\n' > "$WORK/ugly.ktl"
"$KATLIN" fmt "$WORK/ugly.ktl" >/dev/null 2>&1
check_eq "fmt strips trailing whitespace" "0" "$(grep -c ' $' "$WORK/ugly.ktl")"
before="$(cat "$WORK/ugly.ktl")"
"$KATLIN" fmt "$WORK/ugly.ktl" >/dev/null 2>&1
check_eq "fmt is idempotent" "$before" "$(cat "$WORK/ugly.ktl")"

# --------------------------------------------------------------------------
echo
echo "scaffolding"
# --------------------------------------------------------------------------
if "$KATLIN" init "$WORK/newproj" >/dev/null 2>&1; then
    check_eq "init creates src/main.ktl" "yes" "$([ -f "$WORK/newproj/src/main.ktl" ] && echo yes || echo no)"
    ( cd "$WORK/newproj" && "$KATLIN" build src/main.ktl -o out >/dev/null 2>&1 )
    check_eq "scaffolded project builds (outside repo)" "0" "$?"
else
    bad "init runs" "katlin init failed"
fi

# --------------------------------------------------------------------------
echo
echo "arguments and guards"
# --------------------------------------------------------------------------
cat > "$WORK/args.ktl" <<'KTL'
fn box(int width = 1, int height = 1, int depth = 1) -> int {
    return width * height * depth;
}
fn guard(int total) {
    return if total > 100;
    println("under");
}
fn main {
    println("d=%", box());
    println("d=%", box(2));
    println("d=%", box(depth = 3));
    println("d=%", box(2, height = 3));
    println("d=%", box(depth = 2, width = 3, height = 4));
    guard(50);
    guard(150);
}
KTL
out="$("$KATLIN" run "$WORK/args.ktl" 2>&1 | strip)"; code=$?
check_eq "default and named arguments run" "0" "$code"
check_contains "all-defaults call"       "d=1"  "$out"
check_contains "one positional argument" "d=2"  "$out"
check_contains "named argument only"     "d=3"  "$out"
check_contains "positional then named"   "d=6"  "$out"
check_contains "named in any order"      "d=24" "$out"
check_contains "guard lets the body run" "under" "$out"
check_eq "guard fires only when true" "1" "$(printf '%s' "$out" | grep -c '^under$')"

# --------------------------------------------------------------------------
echo
echo "or fallbacks"
# --------------------------------------------------------------------------
cat > "$WORK/orfb.ktl" <<'KTL'
fn lookup(int id) -> int {
    return if id < 0;
    return id * 100;
}
fn report(int id) {
    v := lookup(id) or return;
    println("hit %", v);
}
fn main {
    a := lookup(3) or -1;
    println("a=%", a);
    b := lookup(-1) or -1;
    println("b=%", b);
    report(2);
    report(-5);
}
KTL
out="$("$KATLIN" run "$WORK/orfb.ktl" 2>&1 | strip)"; code=$?
check_eq "or fallback program runs" "0" "$code"
check_contains "or uses the left side when truthy" "a=300" "$out"
check_contains "or uses the default when falsy"    "b=-1"  "$out"
check_contains "or return bails out early"         "hit 200" "$out"
check_eq "or return prints nothing when falsy" "1" "$(printf '%s' "$out" | grep -c '^hit ')"

# --------------------------------------------------------------------------
echo
echo "toolchain"
# --------------------------------------------------------------------------
# check: type-checks without producing a binary
"$KATLIN" check "$ROOT/examples/tour.ktl" >/dev/null 2>&1
check_eq "check accepts a valid file" "0" "$?"
check_eq "check produces no binary" "no" "$([ -f .build/tour ] && echo yes || echo no)"
"$KATLIN" check "$ROOT/examples/borrow_fail.ktl" >/dev/null 2>&1
check_eq "check rejects an aliased borrow" "1" "$?"

# incremental build: identical source must not re-run clang
"$KATLIN" build "$ROOT/examples/tour.ktl" -o "$WORK/inc1" >/dev/null 2>&1
out="$("$KATLIN" build "$ROOT/examples/tour.ktl" -o "$WORK/inc1" 2>&1 | strip)"
check_contains "unchanged source skips recompilation" "Up to date" "$out"

# ...but switching optimisation level must invalidate the cache
out="$("$KATLIN" build "$ROOT/examples/tour.ktl" --debug -o "$WORK/inc1" 2>&1 | strip)"
check_contains "changing flags invalidates the cache" "Successfully built" "$out"

# katlin.toml is actually read
mkdir -p "$WORK/tomlproj/src"
printf 'fn main { println("hi"); }\n' > "$WORK/tomlproj/src/main.ktl"
printf '[build]\nopt_level = 0\n' > "$WORK/tomlproj/katlin.toml"
( cd "$WORK/tomlproj" && "$KATLIN" build src/main.ktl -o out >/dev/null 2>&1 )
if readelf -S "$WORK/tomlproj/out" 2>/dev/null | grep -q "\.debug_info"; then
    ok "katlin.toml opt_level=0 selects debug build"
else
    bad "katlin.toml opt_level=0 selects debug build" "no .debug_info section"
fi
printf '[build]\nopt_level = 3\n' > "$WORK/tomlproj/katlin.toml"
rm -f "$WORK/tomlproj/out"
( cd "$WORK/tomlproj" && "$KATLIN" build src/main.ktl -o out >/dev/null 2>&1 )
if readelf -S "$WORK/tomlproj/out" 2>/dev/null | grep -q "\.debug_info"; then
    bad "katlin.toml opt_level=3 selects optimised build" "unexpected .debug_info"
else
    ok "katlin.toml opt_level=3 selects optimised build"
fi
rm -f "$WORK/tomlproj/out"
( cd "$WORK/tomlproj" && "$KATLIN" build src/main.ktl --debug -o out >/dev/null 2>&1 )
if readelf -S "$WORK/tomlproj/out" 2>/dev/null | grep -q "\.debug_info"; then
    ok "--debug overrides katlin.toml"
else
    bad "--debug overrides katlin.toml" "toml won over the command line"
fi

# install.sh: the installed compiler must find its runtime by itself
if [ -x "$ROOT/install.sh" ]; then
    PREFIX="$WORK/prefix" "$ROOT/install.sh" >/dev/null 2>&1
    if [ -x "$WORK/prefix/bin/katlin" ]; then
        ok "install.sh installs the compiler"
        mkdir -p "$WORK/elsewhere"
        printf 'fn main { println("installed"); }\n' > "$WORK/elsewhere/t.ktl"
        ( cd "$WORK/elsewhere" && env -u KATLIN_STD "$WORK/prefix/bin/katlin" run t.ktl >/dev/null 2>&1 )
        check_eq "installed compiler resolves std/ from its prefix" "0" "$?"
    else
        bad "install.sh installs the compiler" "no binary at prefix/bin"
    fi
else
    bad "install.sh exists" "not executable"
fi

# --------------------------------------------------------------------------
echo
echo "examples"
# --------------------------------------------------------------------------
for f in "$ROOT"/examples/*.ktl; do
    name="$(basename "$f" .ktl)"
    # Negative examples are expected to be REJECTED; they are asserted on in
    # the #strict borrow checking section above.
    case "$name" in
        borrow_fail|borrow_immutable) continue ;;
    esac
    # Files made only of test blocks have no entry point; run them via `test`.
    if grep -qE '^[[:space:]]*test "' "$f" && ! grep -qE '^[[:space:]]*fn main' "$f"; then
        if "$KATLIN" test "$f" >/dev/null 2>&1; then ok "example: $name (test suite)"; else bad "example: $name (test suite)"; fi
    else
        if "$KATLIN" build "$f" -o "$WORK/$name" >/dev/null 2>&1; then ok "example: $name"; else bad "example: $name" "build failed"; fi
    fi
done

if [ -x "$WORK/tour" ]; then
    out="$("$WORK/tour" 2>&1 | strip)"
    check_contains "tour example runs correctly" "swapped: 2 1" "$out"
fi

# Raw pointers: *mut T / *const T, pointer arithmetic, raw { } blocks.
cat > "$WORK/rawptr.ktl" <<'KTL'
fn copy_bytes(*mut byte dst, *const byte src, usize n) {
    raw {
        mut usize i = 0;
        while i < n { *(dst + i) = *(src + i); i += 1; }
    }
}
fn main {
    mut byte a[4];
    mut byte b[4];
    mut usize i = 0;
    while i < 4 { *(a + i) = i + 1; i += 1; }
    copy_bytes(&b[0], &a[0], 4);
    println("copied: % % % %", b[0], b[1], b[2], b[3]);
}
KTL
out="$("$KATLIN" run "$WORK/rawptr.ktl" 2>&1 | strip)"; code=$?
check_eq "raw pointer program compiles and runs" "0" "$code"
check_contains "pointer arithmetic copies bytes" "copied: 1 2 3 4" "$out"

# --------------------------------------------------------------------------
echo
printf '==> %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -ne 0 ]; then
    printf '    failed: %s\n' "${FAILED_NAMES[*]}"
    exit 1
fi
echo "==> all green"
