from atomDelim import ATOMIC_VAL, DELIM_VAL 
from transitionDiag import TRANSITIONS_DFA 


def run_dfa(code: str):
    """Simulate transitions on TRANSITIONS_DFA."""
    curr_state = 0
    lexeme = ""

    print(f"Starting DFA simulation for: '{code}'")

    for ch in code:
        print(f"\nCurrent state: {curr_state}, reading char: '{ch}'")

        curr_obj = TRANSITIONS_DFA[curr_state]
        found = False

        # Loop through each possible branch from current state
        for next_state in curr_obj.branches:
            next_obj = TRANSITIONS_DFA[next_state]
            # next_obj.chars is always a list
            if ch in next_obj.chars:
                curr_state = next_state
                lexeme += ch
                print(f" → Transitioned to state {curr_state} (accepted '{ch}')")
                found = True
                break

        if not found:
            print(" ❌ Invalid transition! No matching branch.")
            break

    # After processing all chars
    final_state = TRANSITIONS_DFA[curr_state]
    if final_state.isEnd:
        print(f"\n✅ Accepted lexeme: '{lexeme}' (Ended at state {curr_state})\n")
    else:
        print(f"\n❌ Rejected lexeme: '{lexeme}' (Ended at state {curr_state})\n")


if __name__ == "__main__":
    test_inputs = [
        "brewed ",
        "blend",
        "crema",
        "cold",
        "emptycup",
        "flavour",
        "refill?",
        "snap",
        "whilehot",
        "random"
    ]

    for word in test_inputs:
        print("=" * 60)
        print(f"Testing input: {word}")
        run_dfa(word)

def classify_char(ch):
    for key, chars in ATOMIC_VAL.items():
        if ch in chars:
            return key
    return None

def tokenize(code):
    MAX_BEAN = 9_999_999_999
    MAX_DRIP_INT = "9999999999"
    MAX_DRIP_FRAC = "9999999999"
    buffer = ""
    
    tokens = []
    pos = 0
    line = 1
    column = 1

    for ch in code:
        char_class = classify_char(ch)

        if char_class == "space_delim":
            if buffer:
                tokens.append(buffer)
                buffer = ""
        else:
            buffer += ch

    if buffer:
        tokens.append(buffer)

    """
    while pos < len(code):
        match_found = False
        for tok_type, pattern in token_specs:
            regex = re.compile(pattern)
            m = regex.match(code, pos)
            if not m:
                continue

            raw = m.group(0)

            # --- COMMENT ---
            if tok_type == "COMMENT":
                push({"type": "COMMENT", "lexeme": raw, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- NEWLINE ---
            if tok_type == "NEWLINE":
                push({"type": "NEWLINE", "lexeme": "↵", "line": line, "column": column})
                pos += len(raw)
                line += 1
                column = 1
                match_found = True
                break

            # --- SPACE ---
            if tok_type == "SPACE":
                parts = []
                for ch in raw:
                    if ch == "\t":
                        parts.append("Tab")
                    elif ch == " ":
                        parts.append("␣")
                    else:
                        parts.append(ch)
                visible = " ".join(parts)
                push({"type": "WHITESPACE", "lexeme": visible, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- IDENTIFIER ---
            if tok_type == "IDENTIFIER":
                if len(raw) > 15:
                    push({
                        "type": "LEXICAL_ERROR",
                        "lexeme": raw,
                        "line": line,
                        "column": column,
                        "message": "Identifier exceeds 15 characters"
                    })
                else:
                    push({"type": "IDENTIFIER", "lexeme": raw, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- Invalid number sep ---
            if tok_type == "INVALID_NUM_SEP":
                push({
                "type": "LEXICAL_ERROR",
                "lexeme": code[pos],
                "line": line,
                "column": column,
                "message": "Invalid Number Separator found."
                })
                pos += 1
                column += 1
                break

            if tok_type == "HYPHEN_ERROR":
                push({
                    "type": "LEXICAL_ERROR",
                    "lexeme": raw,
                    "line": line,
                    "column": column,
                    "message": "Invalid negative sign: use '-' (ASCII hyphen)."
                })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            if tok_type == "BEAN_LIT":
                normal_bean = normalize_beanRange(raw)
                push({
                    "type": "BEAN_LIT",
                    "lexeme": normal_bean,
                    "raw": raw,
                    "line": line,
                    "column": column
                })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- DRIP_LIT normalization --- WE MIGHT NEED TO TURN THE NORMALIZED INTO THE VALUE SIGURO??
            if tok_type == "DRIP_LIT":
                parts = raw.split(".", 1)
                whole = parts[0]
                dec = parts[1] if len(parts) > 1 else ""

                normal_drip = normalize_dripRange(whole, dec)
                push({
                    "type": "DRIP_LIT",
                    "lexeme": normal_drip,
                    "raw": raw,
                    "line": line,
                    "column": column
                })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- Default behavior ---
            push({"type": tok_type, "lexeme": raw, "line": line, "column": column})
            pos += len(raw)
            column += len(raw)
            match_found = True
            break

        # --- Handle unmatched characters ---
        if not match_found:
            push({
                "type": "LEXICAL_ERROR",
                "lexeme": code[pos],
                "line": line,
                "column": column,
                "message": "Unmatched Character"
            })
            pos += 1
            column += 1
    """
    return tokens