from .atomDelim import ATOMIC_VAL, DELIM_VAL
from .transitionDiag import TRANSITIONS_DFA

def tokenize(code):
    tokens = []
    pos = 0
    line = 1
    column = 1

    def push(token):
        tokens.append(token)

    while pos < len(code):
        ch = code[pos]
        buffer = ""
        token_start_column = column
        curr_state = 0
        last_accept_state = None
        last_accept_pos = pos
        last_accept_buffer = ""

        # DFA traversal loop
        while pos < len(code):
            matched = False
            # Iterate over possible branches
            for next_state in TRANSITIONS_DFA[curr_state].branches:
                next_obj = TRANSITIONS_DFA.get(next_state)
                if not next_obj:
                    continue

                # Handle valid character match
                if ch in next_obj.chars:
                    buffer += ch
                    curr_state = next_state
                    pos += 1
                    column += 1
                    matched = True

                    # Update acceptance checkpoint
                    if next_obj.isEnd:
                        last_accept_state = next_obj
                        last_accept_pos = pos
                        last_accept_buffer = buffer
                    break

            if not matched:
                break
            if pos < len(code):
                ch = code[pos]

        # --- If DFA found a token ---
        if last_accept_state:
            buffer = last_accept_buffer
            final_state = last_accept_state

            push({
                "type": final_state.token_type or "UNDEF",
                "lexeme": buffer,
                "line": line,
                "column": token_start_column
            })

            # Line/column adjustments
            for c in buffer:
                if c == "\n":
                    line += 1
                    column = 1
                elif c == "\t":
                    column += 4
                else:
                    column += 1

            pos = last_accept_pos
            curr_state = 0
            continue

        # --- Handle standalone whitespace not caught by DFA ---
        if ch in [" ", "\t", "\n"]:
            if ch == " ":
                push({"type": "SPACE", "lexeme": "␣", "line": line, "column": column})
                column += 1
            elif ch == "\t":
                push({"type": "TAB", "lexeme": "Tab", "line": line, "column": column})
                column += 4
            elif ch == "\n":
                push({"type": "NEWLINE", "lexeme": "↵", "line": line, "column": column})
                line += 1
                column = 1
            pos += 1
            continue

        # --- Lexical error for unmatched character ---
        push({
            "type": "LEXICAL_ERROR",
            "lexeme": ch,
            "line": line,
            "column": column,
            "message": "Unmatched Character"
        })
        pos += 1
        column += 1

    return tokens
