; Syntax highlighting for Katlin.
;
; Order matters: in Zed a later pattern overrides an earlier one for the same
; range. So the catch-all for identifiers comes first and everything more
; specific follows it -- the same convention Zed's own grammars use. Putting
; the catch-all last would flatten every function, type and field name into
; plain @variable.

; --- catch-all ------------------------------------------------------------
(identifier) @variable

; --- literals -------------------------------------------------------------
(number) @number
(string) @string
(boolean) @boolean
(test_block name: (string) @string.special)

; --- comments and pragmas -------------------------------------------------
(line_comment) @comment
(block_comment) @comment
(pragma) @preproc

; --- keywords -------------------------------------------------------------
[
  "fn" "struct" "enum" "test" "import"
  "if" "else" "while" "for" "in" "step" "loop"
  "match" "case" "return" "break" "continue"
  "raw" "mut" "or"
] @keyword

; --- operators ------------------------------------------------------------
[
  "+" "-" "*" "/" "%"
  "==" "!=" "<" ">" "<=" ">="
  "&&" "||" "!" "&" "|" "^"
  "=" "+=" "-=" "*=" "/=" "%=" "&=" "|="
  ":=" "->" ".."
] @operator

; --- punctuation ----------------------------------------------------------
["(" ")" "[" "]" "{" "}"] @punctuation.bracket
["," ";" ":" "."] @punctuation.delimiter

; --- types ----------------------------------------------------------------
; Built-in type names are ordinary identifiers in the grammar (see the note
; in grammar.js), so they are recognised by name here rather than as nodes.
; This pattern must come after the @type one below to override it.
(type_annotation (identifier) @type)
(struct_definition name: (identifier) @type)
(enum_definition name: (identifier) @type)
(struct_initializer type: (identifier) @type)

((type_annotation (identifier) @type.builtin)
  (#match? @type.builtin "^(int|i64|u64|str|bool|float|byte|usize|vec|sb|arena)$"))

(pointer_type "*" @operator)
(pointer_type ["mut" "const"] @keyword)

; --- functions ------------------------------------------------------------
(function_definition name: (identifier) @function)
(call_expression function: (identifier) @function.call)
(parameter name: (identifier) @variable.parameter)

; --- fields and members ---------------------------------------------------
(field_declaration name: (identifier) @property)
(field_initializer name: (identifier) @property)
(member_expression property: (identifier) @property)

; `value.type` is resolved at compile time, so colour it distinctly.
((member_expression
  property: (identifier) @property.builtin)
  (#eq? @property.builtin "type"))

; --- enum variants --------------------------------------------------------
; Katlin writes variants as `Color.Red`, so the convention is upper-case.
((member_expression object: (identifier) @type)
  (#match? @type "^[A-Z]"))
((member_expression property: (identifier) @variant)
  (#match? @variant "^[A-Z]"))
(variant_pattern (identifier) @variant)
