from .atomDelim import ATOMIC_VAL, DELIM_VAL
from .transitionDiag import TRANSITIONS_DFA

def tokenize(code):
    tokens = []
    pos = 0
    line = 1
    column = 1

    # PUSH (for the website) 
    def push(token_type, lexeme, start_col, message=None):
        token = {
            "type": token_type,
            "lexeme": lexeme,
            "line": line,
            "column": start_col
        }
        if message:
            token["message"] = message
        tokens.append(token)

    # DFA CRAWLER 
    def crawl_dfa(start_pos, start_col):
        buffer = ""
        curr_state = 0
        pos = start_pos
        column = start_col
        last_accept_state = None
        last_accept_pos = None
        last_accept_buffer = ""

        while pos < len(code):
            ch = code[pos]
            next_state = None

            # find a transition that matches current char
            for s in TRANSITIONS_DFA[curr_state].branches:
                next_obj = TRANSITIONS_DFA.get(s)
                if next_obj and ch in next_obj.chars:
                    next_state = s
                    break

            if not next_state:
                break

            curr_state = next_state
            buffer += ch
            pos += 1
            column += 1

            if TRANSITIONS_DFA[curr_state].isEnd:
                last_accept_state = curr_state
                last_accept_pos = pos
                last_accept_buffer = buffer

        if last_accept_state is not None:
            state = TRANSITIONS_DFA[last_accept_state]
            return {
                "accepted": True,
                "token_type": state.token_type,
                "buffer": last_accept_buffer,
                "end_pos": last_accept_pos,
                "end_col": column
            }

        return {
            "accepted": False,
            "buffer": buffer,
            "end_pos": pos,
            "end_col": column
        }

    # NUMBER 
    def read_number(start_pos, start_col):
        buffer = ""
        pos = start_pos
        column = start_col

        if code[pos] in ['-', '+']:
            buffer += code[pos]
            pos += 1
            column += 1

        while pos < len(code) and code[pos].isdigit():
            buffer += code[pos]
            pos += 1
            column += 1

        if pos < len(code) and code[pos] == '.':
            buffer += '.'
            pos += 1
            column += 1
            while pos < len(code) and code[pos].isdigit():
                buffer += code[pos]
                pos += 1
                column += 1
            return "DRIPLIT", buffer, pos, column
        else:
            return "BEANLIT", buffer, pos, column

    # ---------------------- STRING ----------------------
    def read_string(start_pos, start_col):
        buffer = '"'
        pos = start_pos + 1
        column = start_col + 1
        while pos < len(code):
            ch = code[pos]
            buffer += ch
            pos += 1
            column += 1

            if ch == '\\' and pos < len(code):
                buffer += code[pos]
                pos += 1
                column += 1
            elif ch == '"':
                return "BLENDLIT", buffer, pos, column

        return "LEXICAL_ERROR", buffer, pos, column

    # ---------------------- CHAR ----------------------
    def read_char(start_pos, start_col):
        buffer = "'"
        pos = start_pos + 1
        column = start_col + 1
        state = 295  # start state
        stage = 0    # 0 = after opening quote, 1 = after body char, 2 = after closing quote

        if pos >= len(code):
            return "LEXICAL_ERROR", buffer, pos, column

        ch = code[pos]

        # CASE 1: Escape sequence path (299 -> 300 -> 297)
        if ch == '\\':
            buffer += ch
            pos += 1
            column += 1

            if pos < len(code):
                esc = code[pos]
                if esc in ATOMIC_VAL["escapeseq_let"]:
                    buffer += esc
                    pos += 1
                    column += 1
                else:
                    return "LEXICAL_ERROR", buffer, pos, column, "Identifier too long"
            else:
                return "LEXICAL_ERROR", buffer, pos, column

        # CASE 2: Normal safe char (296 -> 297)
        elif ch in ATOMIC_VAL["safe_char"]:
            buffer += ch
            pos += 1
            column += 1
        else:
            return "LEXICAL_ERROR", buffer, pos, column

        # Expect closing quote (297 -> 298)
        if pos < len(code) and code[pos] == "'":
            buffer += "'"
            pos += 1
            column += 1
            return "CHURROLIT", buffer, pos, column

        return "LEXICAL_ERROR", buffer, pos, column


    # ---------------------- MULTILINE COMMENT (~. ... .~) ----------------------
    def read_multiline_comment(start_pos, start_col):
        buffer = "~."
        pos = start_pos + 2
        column = start_col + 2
        nonlocal line

        while pos < len(code):
            ch = code[pos]
            nxt = code[pos + 1] if pos + 1 < len(code) else ''
            buffer += ch
            pos += 1

            if ch == '\n':
                line += 1
                column = 1
                continue
            else:
                column += 1

            if ch == '.' and nxt == '~':
                buffer += nxt
                pos += 1
                column += 1
                return "ML_COMMENT", buffer, pos, column

        return "LEXICAL_ERROR", buffer, pos, column

    # ---------------------- MAIN LOOP ----------------------
    while pos < len(code):
        ch = code[pos]
        token_start_column = column

        # --- whitespace ---
        if ch == " ":
            push("SPACE", "␣", column)
            pos += 1
            column += 1
            continue
        elif ch == "\t":
            push("TAB", "Tab", column)
            pos += 1
            column += 4
            continue
        elif ch == "\n":
            push("NEWLINE", "↵", column)
            pos += 1
            line += 1
            column = 1
            continue

        # --- single-line comment (~~ ...) ---
        if ch == "~" and pos + 1 < len(code) and code[pos + 1] == "~":
            buffer = "~~"
            pos += 2
            column += 2
            while pos < len(code) and code[pos] != "\n":
                buffer += code[pos]
                pos += 1
                column += 1
            push("SL_COMMENT", buffer, token_start_column)
            continue

        # --- multi-line comment (~. ... .~) ---
        if ch == "~" and pos + 1 < len(code) and code[pos + 1] == ".":
            token_type, buffer, pos, column = read_multiline_comment(pos, column)
            push(token_type, buffer, token_start_column)
            continue

        # --- string literal ("...") ---
        if ch == '"':
            token_type, buffer, pos, column = read_string(pos, column)
            push(token_type, buffer, token_start_column)
            continue

        # --- char literal ('...') ---
        if ch == "'":
            token_type, buffer, pos, column = read_char(pos, column)
            push(token_type, buffer, token_start_column)
            continue

        # --- number literal ---
        if ch in ['-'] and pos + 1 < len(code) and code[pos + 1].isdigit():
            token_type, buffer, pos, column = read_number(pos, column)
            push(token_type, buffer, token_start_column)
            continue
        elif ch.isdigit():
            token_type, buffer, pos, column = read_number(pos, column)
            push(token_type, buffer, token_start_column)
            continue

        # --- DFA-based token ---
        result = crawl_dfa(pos, column)
        if result["accepted"]:
            lexeme = result["buffer"]
            ttype = result["token_type"]

            # Identifier length check
            if ttype == "IDENTIFIER" and len(lexeme) > 15:
                push("LEXICAL_ERROR", lexeme, token_start_column, message="Identifier too long")
            else:
                push(ttype, lexeme, token_start_column)

            pos = result["end_pos"]
            column = result["end_col"]
            continue

        # --- fallback identifier (temporary) ---
        if ch.isalpha() or ch == '_':
            buffer = ""
            start_col = column
            while pos < len(code) and (code[pos].isalnum() or code[pos] == '_'):
                buffer += code[pos]
                pos += 1
                column += 1
            ttype = "IDENTIFIER" if len(buffer) <= 15 else "LEXICAL_ERROR"
            msg = "Identifier too long" if len(buffer) > 15 else None
            push(ttype, buffer, start_col, msg)
            continue

        # --- unmatched character ---
        push("LEXICAL_ERROR", ch, column, message="Unmatched Character")
        pos += 1
        column += 1

    return tokens
