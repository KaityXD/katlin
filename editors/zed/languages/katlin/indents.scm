; Indentation for Katlin.
;
; Every brace-delimited construct indents by one level. `match` cases indent
; their bodies and outdent so sibling `case` lines line up.

(block) @indent
(field_declaration_list) @indent

(struct_definition) @indent
(enum_definition) @indent
(match_statement) @indent

; The body of a case indents from its colon, and the next case outdents.
(match_case ":" @start) @indent
(match_statement (match_case) @outdent)
