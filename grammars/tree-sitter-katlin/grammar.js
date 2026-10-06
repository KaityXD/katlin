/**
 * Tree-sitter grammar for Katlin (.ktl).
 *
 * Written for editor support — Zed uses it for syntax highlighting, bracket
 * matching, indentation and the outline panel — not as a validator. It is
 * deliberately permissive: a slightly loose tree still highlights correctly,
 * while an ERROR node loses colour.
 *
 * One ambiguity is worth calling out. Katlin has both a struct literal
 * (`Point{ x = 1 }`) and a block after a condition (`if is_nl { ... }`), so
 * `IDENT {` is ambiguous on its own. It is resolved lexically: a struct
 * literal requires the brace to follow the type name with no space, which is
 * how the syntax is written throughout the repository. Without that rule,
 * `if is_nl {` — of which the compiler's own source has hundreds — would
 * parse as a struct literal.
 *
 * The authoritative grammar, such as it is, lives in compiler/main.ktl.
 */

module.exports = grammar({
    name: 'katlin',

    extras: $ => [/\s/, $.line_comment, $.block_comment],

    word: $ => $.identifier,

    conflicts: $ => [
        // `Account &from` (a reference parameter) and `a & b` (bitwise and)
        // both start `identifier &`. Which one it is depends on whether the
        // surrounding context is a declaration or an expression, which is
        // beyond LR(1) — so the parser explores both and keeps the one that
        // completes.
        [$.type_annotation, $._expression]
    ],

    rules: {
        source_file: $ => repeat($._top_level),

        // Declarations are statements; only the file-scoped forms are extra
        // here. Repeating them in both lists would make the two rules
        // indistinguishable and cost a conflict.
        _top_level: $ => choice(
            $.pragma,
            $.import_statement,
            $._statement
        ),

        // `#strict` and friends.
        pragma: $ => token(seq('#', /[a-zA-Z_][a-zA-Z0-9_]*/)),

        line_comment: $ => token(seq('//', /[^\n]*/)),

        block_comment: $ => token(seq('/*', /[^*]*\*+([^/*][^*]*\*+)*/, '/')),

        import_statement: $ => seq(
            'import',
            repeat1(choice($.identifier, '.', ',', '{', '}')),
            ';'
        ),

        // ---------------------------------------------------------------
        // Declarations
        // ---------------------------------------------------------------

        function_definition: $ => seq(
            optional('strict'),
            'fn',
            field('name', $.identifier),
            optional($.parameter_list),
            optional(seq('->', field('return_type', $.type_annotation))),
            field('body', $.block)
        ),

        parameter_list: $ => seq(
            '(',
            optional(seq($.parameter, repeat(seq(',', $.parameter)), optional(','))),
            ')'
        ),

        parameter: $ => seq(
            field('type', $.type_annotation),
            optional('&'),
            field('name', $.identifier),
            optional(seq('=', field('default', $._expression)))
        ),

        struct_definition: $ => seq(
            'struct',
            field('name', $.identifier),
            field('body', $.field_declaration_list)
        ),

        field_declaration_list: $ => seq('{', repeat($.field_declaration), '}'),

        field_declaration: $ => seq(
            field('type', $.type_annotation),
            optional('&'),
            field('name', $.identifier),
            ';'
        ),

        enum_definition: $ => seq(
            'enum',
            field('name', $.identifier),
            '{',
            optional(seq($.identifier, repeat(seq(',', $.identifier)), optional(','))),
            '}'
        ),

        test_block: $ => seq('test', field('name', $.string), field('body', $.block)),

        // ---------------------------------------------------------------
        // Types
        // ---------------------------------------------------------------

        // A rule named `type` would collide with the `type` token that
        // `.type` would otherwise produce, so this is type_annotation.
        //
        // Built-in type names are NOT keywords here. `int` is a type, but
        // `arena`, `vec`, `sb` and `byte` are ordinary identifiers too, and
        // treating them as keywords makes `mut arena := arena_create(...)`
        // unparseable -- the same collision the compiler itself hit. They are
        // coloured as builtins by a pattern in highlights.scm instead.
        type_annotation: $ => choice(
            $.pointer_type,
            $.identifier
        ),

        pointer_type: $ => seq('*', choice('mut', 'const'), $.type_annotation),

        // ---------------------------------------------------------------
        // Statements
        // ---------------------------------------------------------------

        block: $ => seq('{', repeat($._statement), '}'),

        _statement: $ => choice(
            $.variable_declaration,
            $.assignment,
            $.augmented_assignment,
            $.expression_statement,
            $.if_statement,
            $.while_statement,
            $.for_statement,
            $.loop_statement,
            $.match_statement,
            $.return_statement,
            $.break_statement,
            $.continue_statement,
            $.raw_block,
            $.block,
            $.test_block,
            $.function_definition,
            $.struct_definition,
            $.enum_definition
        ),

        variable_declaration: $ => choice(
            // int x = 1;   mut int x = 1;   int &sum = 0;   mut byte buf[16];
            seq(
                optional('mut'),
                field('type', $.type_annotation),
                optional('&'),
                field('name', $.identifier),
                optional(seq('[', field('size', $._expression), ']')),
                optional(seq('=', field('value', $._expression))),
                ';'
            ),
            // mut x := 1;   x := 1;
            seq(
                optional('mut'),
                field('name', $.identifier),
                ':=',
                field('value', $._expression),
                ';'
            ),
            // mut x = 1;   (inferred, mutable, no annotation)
            seq(
                'mut',
                field('name', $.identifier),
                '=',
                field('value', $._expression),
                ';'
            )
        ),

        assignment: $ => seq(field('left', $.assignable), '=', field('right', $._expression), ';'),

        augmented_assignment: $ => seq(
            field('left', $.assignable),
            field('operator', choice('+=', '-=', '*=', '/=', '%=', '&=', '|=')),
            field('right', $._expression),
            ';'
        ),

        assignable: $ => choice(
            $.identifier,
            $.member_expression,
            $.index_expression,
            $.unary_expression,
            $.parenthesized_expression
        ),

        expression_statement: $ => seq($._expression, optional(';')),

        if_statement: $ => seq(
            'if',
            field('condition', $._expression),
            field('consequence', $.block),
            optional(seq('else', field('alternative', choice($.block, $.if_statement))))
        ),

        while_statement: $ => seq('while', field('condition', $._expression), field('body', $.block)),

        for_statement: $ => seq(
            'for',
            field('variable', $.identifier),
            'in',
            field('start', $._expression),
            '..',
            field('end', $._expression),
            optional(seq('step', field('step', $._expression))),
            field('body', $.block)
        ),

        loop_statement: $ => seq('loop', $.block),

        match_statement: $ => seq(
            'match',
            field('subject', $._expression),
            '{',
            repeat($.match_case),
            '}'
        ),

        // `_statement` already covers a `{ ... }` body, so listing block
        // separately here would be ambiguous.
        match_case: $ => seq('case', $.variant_pattern, ':', $._statement),

        variant_pattern: $ => seq(optional('.'), $.identifier),

        return_statement: $ => choice(
            seq('return', ';'),
            seq('return', 'if', field('guard', $._expression), ';'),
            seq('return', field('value', $._expression), ';')
        ),

        break_statement: $ => seq('break', ';'),
        continue_statement: $ => seq('continue', ';'),

        raw_block: $ => seq('raw', $.block),

        // ---------------------------------------------------------------
        // Expressions
        // ---------------------------------------------------------------

        _expression: $ => choice(
            $.or_expression,
            $.binary_expression,
            $.unary_expression,
            $.call_expression,
            $.member_expression,
            $.index_expression,
            $.struct_initializer,
            $.parenthesized_expression,
            $.identifier,
            $.number,
            $.string,
            $.boolean
        ),

        or_expression: $ => prec.left(1, seq(
            field('value', $._expression),
            'or',
            field('fallback', choice($._expression, 'return'))
        )),

        binary_expression: $ => choice(
            ...[
                ['||', 2],
                ['&&', 3],
                ['|', 4],
                ['^', 5],
                ['&', 6],
                ['==', 7],
                ['!=', 7],
                ['<', 8],
                ['>', 8],
                ['<=', 8],
                ['>=', 8],
                ['+', 10],
                ['-', 10],
                ['*', 11],
                ['/', 11],
                ['%', 11]
            ].map(([op, p]) => prec.left(p, seq(
                field('left', $._expression),
                field('operator', op),
                field('right', $._expression)
            )))
        ),

        unary_expression: $ => prec(12, seq(
            field('operator', choice('-', '!', '*', '&')),
            field('operand', $._expression)
        )),

        call_expression: $ => prec(13, seq(
            field('function', $._expression),
            field('arguments', $.argument_list)
        )),

        argument_list: $ => seq(
            '(',
            optional(seq($.argument, repeat(seq(',', $.argument)), optional(','))),
            ')'
        ),

        // Positional, named (`f(x = 1)`) or colon-style (`f(x: 1)`).
        argument: $ => choice(
            seq(field('name', $.identifier), choice('=', ':'), field('value', $._expression)),
            $._expression
        ),

        member_expression: $ => prec(13, seq(
            field('object', $._expression),
            '.',
            field('property', $.identifier)
        )),

        index_expression: $ => prec(13, seq(
            field('object', $._expression),
            '[',
            field('index', $._expression),
            ']'
        )),

        // `token.immediate` is the disambiguator described at the top of the
        // file: the brace must follow the type name with no space.
        struct_initializer: $ => prec(13, seq(
            field('type', $.identifier),
            token.immediate('{'),
            optional(seq($.field_initializer, repeat(seq(',', $.field_initializer)), optional(','))),
            '}'
        )),

        field_initializer: $ => seq(
            field('name', $.identifier),
            choice('=', ':'),
            field('value', $._expression)
        ),

        parenthesized_expression: $ => seq('(', $._expression, ')'),

        identifier: $ => /[a-zA-Z_][a-zA-Z0-9_]*/,

        number: $ => token(choice(
            /0[xX][0-9a-fA-F_]+/,
            /0[bB][01_]+/,
            /[0-9][0-9_]*\.[0-9][0-9_]*([eE][+-]?[0-9]+)?/,
            /[0-9][0-9_]*[eE][+-]?[0-9]+/,
            /[0-9][0-9_]*/
        )),

        string: $ => token(seq(
            '"',
            repeat(choice(
                /\\./,
                /[^"\\\n]/
            )),
            '"'
        )),

        boolean: $ => choice('true', 'false')
    }
});
