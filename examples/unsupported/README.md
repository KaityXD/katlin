# Unsupported examples

Programs in this directory use language features that the **native
self-hosted compiler** (`bin/katlin`) does not implement yet. They are kept
because they are valid Katlin for the Python bootstrap compiler in `src/`,
and because they document where the two implementations diverge.

They are excluded from `tests/run_tests.sh`, which requires every file in
`examples/` to build and run.

| Example | Feature it still needs | Native support |
| :--- | :--- | :--- |
| `idkbro.ktl` | inner functions with scope capture, fluent `.start()` chaining | not implemented |
| `showcase.ktl` | inner functions with scope capture, fluent `.start()` chaining | not implemented |
| `phase1_test.ktl` | implicit return of a function's last expression, `match` on a non-enum subject | not implemented |

`strict_module.ktl` used to live here for its reference struct fields
(`int &balance`); those now work, so it has moved up to `examples/`.

Everything else these files use is handled: `idkbro.ktl` and `showcase.ktl`
get as far as their inner `fn`, and their named arguments, parameter defaults
and postfix guards all translate correctly.

You can still build these with the bootstrap compiler, which has a full
parser:

```bash
./bin/katlin_py build examples/unsupported/idkbro.ktl -o /tmp/idkbro
/tmp/idkbro
```

## Why not just fix them?

The native compiler transpiles Katlin to C with a character-level scanner
rather than a full parser. Inner functions need to know which variables the
enclosing scope declares so they can be captured into a context struct;
reference struct fields need to know that a member access goes through a
pointer. Neither can be determined without the shape of an expression, which
is exactly what a scanner does not have.

That work is tracked as item 1 in the roadmap in the top level
[`README.md`](../README.md).
