# Unsupported examples

Programs in this directory use language features that the **native
self-hosted compiler** (`bin/katlin`) does not implement yet. They are kept
because they are valid Katlin for the Python bootstrap compiler in `src/`,
and because they document where the two implementations diverge.

They are excluded from `tests/run_tests.sh`, which requires every file in
`examples/` to build and run.

| Example | Feature it needs | Native support |
| :--- | :--- | :--- |
| `idkbro.ktl` | default arguments, named arguments, inner functions + fluent `.start()` chaining | not implemented |
| `showcase.ktl` | default arguments | not implemented |
| `phase1_test.ktl` | `or` fallback expressions | not implemented |
| `strict_module.ktl` | reference struct fields (`int &balance`), member access through `&` parameters | not implemented |

You can still build these with the bootstrap compiler:

```bash
./bin/katlin_py build examples/unsupported/idkbro.ktl -o /tmp/idkbro
/tmp/idkbro
```

## Why not just fix them?

The native compiler transpiles Katlin to C with a character-level scanner
rather than a full parser, so features that need the shape of an expression —
inner functions that capture their enclosing scope, `or` fallbacks, argument
defaults resolved at call sites — cannot be added without redesigning the
front end around a real AST. That work is tracked in the roadmap in the top
level `README.md`.
