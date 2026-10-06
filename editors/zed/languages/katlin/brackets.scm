; Bracket pairs for Katlin: matching and rainbow brackets.
;
; Quotes are deliberately absent: a Katlin string is a single `string` token,
; so there is no `"` node for a query to match. Auto-closing of quotes is
; configured in config.toml instead.
("(" @open ")" @close)
("[" @open "]" @close)
("{" @open "}" @close)
