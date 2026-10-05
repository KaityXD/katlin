# src/diagnostics.py
# High-Definition, Color-Coded Compiler Diagnostics for Katlin
# Inspired by Rust, Clang, and Zig diagnostic engines.

import sys
import os
from typing import Optional, List, Tuple

# ANSI Terminal Color Codes
class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    UNDER   = "\033[4m"
    
    RED     = "\033[1;31m"
    GREEN   = "\033[1;32m"
    YELLOW  = "\033[1;33m"
    BLUE    = "\033[1;34m"
    MAGENTA = "\033[1;35m"
    CYAN    = "\033[1;36m"
    WHITE   = "\033[1;37m"
    
    BG_RED  = "\033[41m"

def is_color_enabled() -> bool:
    # Disable color if NO_COLOR environment variable is set or output is redirected
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stderr.isatty() or os.environ.get("FORCE_COLOR") == "1"

class KatlinError(Exception):
    def __init__(
        self,
        message: str,
        line: int = 1,
        col: int = 1,
        length: int = 1,
        file_path: Optional[str] = None,
        note: Optional[str] = None,
        help_text: Optional[str] = None,
        secondary_spans: Optional[List[Tuple[int, int, int, str]]] = None # list of (line, col, len, label)
    ):
        super().__init__(message)
        self.message = message
        self.line = max(1, line)
        self.col = max(1, col)
        self.length = max(1, length)
        self.file_path = file_path
        self.note = note
        self.help_text = help_text
        self.secondary_spans = secondary_spans or []

class KatlinLexerError(KatlinError):
    pass

class KatlinParseError(KatlinError):
    pass

class KatlinSemanticError(KatlinError):
    pass

def render_diagnostic(
    source_path: str,
    source_code: str,
    err: KatlinError,
    severity: str = "error"
) -> str:
    color = is_color_enabled()
    
    c_red     = Color.RED if color else ""
    c_yellow  = Color.YELLOW if color else ""
    c_blue    = Color.CYAN if color else ""
    c_white   = Color.WHITE if color else ""
    c_bold    = Color.BOLD if color else ""
    c_dim     = Color.DIM if color else ""
    c_reset   = Color.RESET if color else ""
    c_green   = Color.GREEN if color else ""

    lines = source_code.splitlines()
    err_line_idx = err.line - 1
    
    # Calculate gutter width
    max_line_num = min(len(lines), err.line + 1)
    gutter_w = max(len(str(max_line_num)), 2)

    output = []
    output.append("")

    # Header: error: message
    sev_color = c_red if severity == "error" else c_yellow
    output.append(f"{sev_color}{c_bold}{severity}{c_reset}{c_bold}: {err.message}{c_reset}")

    # Location link: --> file.ktl:line:col
    gutter_pad = " " * gutter_w
    output.append(f"{c_blue}{gutter_pad}--> {c_reset}{source_path}:{err.line}:{err.col}")
    output.append(f"{c_blue}{gutter_pad} |{c_reset}")

    # Context Line Before (if available)
    if err_line_idx > 0 and err_line_idx - 1 < len(lines):
        prev_num = str(err.line - 1).rjust(gutter_w)
        prev_src = lines[err_line_idx - 1]
        output.append(f"{c_blue}{prev_num} | {c_reset}{c_dim}{prev_src}{c_reset}")

    # Main Error Line
    if 0 <= err_line_idx < len(lines):
        line_num = str(err.line).rjust(gutter_w)
        code_line = lines[err_line_idx]
        output.append(f"{c_blue}{line_num} | {c_reset}{code_line}")

        # Primary Pointer Underline: ^^^^^^
        col_offset = max(0, err.col - 1)
        pointer_len = err.length
        # Clamp length to not extend wildly past line end
        pointer_len = max(1, min(pointer_len, max(1, len(code_line) - col_offset)))
        
        # Check if there are secondary spans on the same line
        same_line_secondary = [s for s in err.secondary_spans if s[0] == err.line]
        
        if same_line_secondary:
            # Multi-span underline on the same line
            first_span = same_line_secondary[0] # (line, col, len, label)
            s_col = max(0, first_span[1] - 1)
            s_len = max(1, first_span[2])
            
            # If secondary span comes before primary
            if s_col < col_offset:
                space_before = " " * s_col
                sec_dash = "-" * s_len
                space_mid = " " * max(0, col_offset - (s_col + s_len))
                prim_caret = "^" * pointer_len
                underline = f"{space_before}{c_blue}{sec_dash}{c_reset}{space_mid}{c_red}{prim_caret}{c_reset} {c_red}second mutable borrow occurs here{c_reset}"
                output.append(f"{c_blue}{gutter_pad} | {c_reset}{underline}")
                
                # Secondary label underneath
                sec_pipe = f"{' ' * s_col}{c_blue}|{c_reset}"
                output.append(f"{c_blue}{gutter_pad} | {c_reset}{sec_pipe}")
                sec_label = f"{' ' * s_col}{c_blue}|{c_reset}\n{c_blue}{gutter_pad} | {c_reset}{' ' * s_col}{c_blue}{first_span[3]}{c_reset}"
                output.append(f"{c_blue}{gutter_pad} | {c_reset}{' ' * s_col}{c_blue}{first_span[3]}{c_reset}")
            else:
                space_before = " " * col_offset
                prim_caret = "^" * pointer_len
                underline = f"{space_before}{c_red}{prim_caret}{c_reset}"
                output.append(f"{c_blue}{gutter_pad} | {c_reset}{underline}")
        else:
            space_pad = " " * col_offset
            caret = "^" * pointer_len
            output.append(f"{c_blue}{gutter_pad} | {c_reset}{space_pad}{c_red}{c_bold}{caret}{c_reset}")

    # Context Line After (if available)
    if err_line_idx + 1 < len(lines):
        next_num = str(err.line + 1).rjust(gutter_w)
        next_src = lines[err_line_idx + 1]
        output.append(f"{c_blue}{next_num} | {c_reset}{c_dim}{next_src}{c_reset}")

    output.append(f"{c_blue}{gutter_pad} |{c_reset}")

    # Note section
    if err.note:
        output.append(f"{c_blue}{gutter_pad} = {c_bold}note{c_reset}: {err.note}")

    # Help section
    if err.help_text:
        output.append(f"{c_yellow}{gutter_pad} = {c_bold}help{c_reset}: {err.help_text}")

    output.append("")
    return "\n".join(output)

def render_backend_error(c_output: str, source_path: str, source_code: str) -> str:
    color = is_color_enabled()
    c_red   = Color.RED if color else ""
    c_bold  = Color.BOLD if color else ""
    c_blue  = Color.CYAN if color else ""
    c_reset = Color.RESET if color else ""
    c_dim   = Color.DIM if color else ""

    # Parse Clang/GCC error message lines
    cleaned_lines = []
    for line in c_output.splitlines():
        if "warning:" in line:
            continue # suppress minor backend C warnings
        if "error:" in line or "note:" in line:
            # Filter out internal compiler path and highlight cleanly
            parts = line.split(":", 4)
            if len(parts) >= 4:
                kind = parts[3].strip()
                msg = parts[4].strip() if len(parts) > 4 else ""
                col_sev = c_red if kind == "error" else c_blue
                cleaned_lines.append(f"{col_sev}{c_bold}{kind}{c_reset}: {msg}")
            else:
                cleaned_lines.append(f"{c_red}{line}{c_reset}")
        elif line.strip().startswith("^"):
            cleaned_lines.append(f"{c_red}{line}{c_reset}")
        else:
            cleaned_lines.append(f"{c_dim}{line}{c_reset}")

    formatted_c = "\n".join(cleaned_lines)
    return f"\n{c_red}{c_bold}backend error{c_reset}: Low-level C99/LLVM code generation failed\n{formatted_c}\n"
