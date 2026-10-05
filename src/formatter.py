# src/formatter.py
# Official Katlin Source Code Formatter (katlin fmt)

import re

def format_katlin_code(source: str) -> str:
    lines = source.splitlines()
    formatted_lines = []
    indent_level = 0
    blank_line_count = 0

    for raw_line in lines:
        line = raw_line.strip()

        # Handle empty lines
        if not line:
            blank_line_count += 1
            if blank_line_count <= 1 and formatted_lines:
                formatted_lines.append("")
            continue
        blank_line_count = 0

        # Adjust indentation if line begins with closing brace
        closing_count = line.count("}") - line.count("{")
        if line.startswith("}"):
            indent_level = max(0, indent_level - 1)

        # Normalize spaces around assignments and operators (outside strings and comments)
        line = format_line_tokens(line)

        # Append indented line
        indent_str = "    " * indent_level
        formatted_lines.append(f"{indent_str}{line}")

        # Adjust indentation for next line
        if not line.startswith("}"):
            indent_level = max(0, indent_level + (line.count("{") - line.count("}")))
        else:
            # If line started with } but had more { than }
            net = line.count("{") - (line.count("}") - 1)
            indent_level = max(0, indent_level + net)

    return "\n".join(formatted_lines) + "\n"

def format_line_tokens(line: str) -> str:
    # If line is a pure comment, keep it as is
    if line.startswith("//"):
        return line

    # Check if there is an inline comment
    comment_part = ""
    code_part = line
    if "//" in line:
        parts = line.split("//", 1)
        code_part = parts[0]
        comment_part = " // " + parts[1].strip()

    # Format code part:
    # Normalize ':='
    code_part = re.sub(r'\s*:=\s*', ' := ', code_part)
    # Normalize '==' '!=' '<=' '>='
    code_part = re.sub(r'\s*([=!<>]=[=]?)\s*', r' \1 ', code_part)
    # Normalize single '=' (not preceded by !, <, >, :)
    code_part = re.sub(r'(?<![=!<>:])=(?!=)', ' = ', code_part)
    # Normalize '..'
    code_part = re.sub(r'\s*\.\.\s*', '..', code_part)
    # Normalize commas
    code_part = re.sub(r'\s*,\s*', ', ', code_part)
    # Normalize semicolons
    code_part = re.sub(r'\s*;\s*', ';', code_part)
    # Normalize single space before '{'
    code_part = re.sub(r'\s*\{', ' {', code_part)

    # Collapse any accidental double spaces (except strings)
    code_part = re.sub(r' {2,}', ' ', code_part).strip()

    return code_part + comment_part
