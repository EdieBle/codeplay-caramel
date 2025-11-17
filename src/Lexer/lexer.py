from .atomDelim import ATOMIC_VAL, DELIM_VAL
from .transitionDiag import TRANSITIONS_DFA

def tokenize(code):
    tokens = []
    pos = 0
    line = 1
    column = 1

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

    while pos < len(code):
        ch = code[pos]

        print(f"\n=== OUTER LOOP: scanning new token at pos={pos}, col={column}, char='{ch}' ===") #debug

        # ----------------------------------------------------------
        # DFA CRAWLING STARTS
        # ----------------------------------------------------------
        start_col = column
        curr_state = 0
        buffer = ""
        last_accept = None
        start_pos = pos  # <-- needed for identifier fallback

        while pos < len(code):

            ch = code[pos]
            print(f"[INNER] At pos={pos}, col={column}, char='{ch}', curr_state={curr_state}") # debug

            next_state = None

            branches = TRANSITIONS_DFA[curr_state].branches
            if isinstance(branches, int):
                branches = [branches]

            print(f"[INNER] Possible branches from state {curr_state}: {branches}") # debug

            for nxt in branches:
                node = TRANSITIONS_DFA[nxt]

                if ch in node.chars:

                    if node.isEnd:
                        print(f"[INNER NXT #1] NEXT STATE {nxt} is accepting — NOT consuming '{ch}'") # debug
                        last_accept = (nxt, pos, column, buffer)
                        next_state = None
                        break

                    next_state = nxt
                    print(f"[INNER NXT #2] MATCH: '{ch}' → state {nxt}") # debug
                    break

            if next_state is None:
                print(f"[INNER] STOP: No transition for '{ch}' from state {curr_state}") # debug
                break

            curr_state = next_state
            buffer += ch
            pos += 1
            column += 1

            print(f"[INNER] Transition → state {curr_state}, buffer='{buffer}'") # debug

            if TRANSITIONS_DFA[curr_state].isEnd:
                last_accept = (curr_state, pos, column, buffer)
                print(f"[INNER] ACCEPTING STATE {curr_state} (buffer='{buffer}')") # debug

        print(f"=== INNER LOOP COMPLETE at pos={pos}, curr_state={curr_state} ===\n\n") # debug

        #=================================================================
        # #1 DFA FAIL - Identifier fallback
        #=================================================================
        if last_accept is None:
            print("\033[91m[[1] DFA FAIL]\033[0m main DFA failed starting identifier fallback") # debug

            # Rewind to start of failed token attempt
            fallback_pos = start_pos
            fallback_col = start_col

            print(f"\033[94m[FALLBACK]\033[0m Begin at first buffer char at pos={fallback_pos}, char='{code[fallback_pos]}'") # debug

            def run_identifier_fallback(start_i):
                print("\033[95m[FALLBACK] Starting identifier scan\033[0m") # debug

                # 1. Must be able to go 0 to 308
                start_branches = TRANSITIONS_DFA[0].branches
                if isinstance(start_branches, int):
                    start_branches = [start_branches]

                if 308 not in start_branches:
                    print("\033[91m[FALLBACK] ERROR: 0 to 308 path missing in DFA!\033[0m") # debug
                    return None, start_i

                id_start_chars = TRANSITIONS_DFA[308].chars

                first_char = code[start_i]
                print(f"[FALLBACK] First char = '{first_char}', ID start chars = {repr(id_start_chars)}") # debug

                if first_char not in id_start_chars:
                    print("\033[91m[FALLBACK] First char is NOT a valid identifier start\033[0m") # debug
                    return None, start_i

                print(f"\033[92m[FALLBACK] '{first_char}' is valid at start to state 308\033[0m") # debug

                temp_state = 308
                i = start_i + 1  # move to next char

                # Build final lexeme
                lex = first_char

                # Continue reading actual input stream
                while i < len(code):
                    chx = code[i]
                    print(f"[FALLBACK] Checking '{chx}' from state {temp_state}")

                    branches = TRANSITIONS_DFA[temp_state].branches
                    if isinstance(branches, int):
                        branches = [branches]
                    
                    print(f"[ID RECOVER] Possible branches from state {temp_state}: {branches}") # debug

                    nxt = None
                    for b in branches:
                        node = TRANSITIONS_DFA[b]
                        if chx in node.chars:
                            nxt = b
                            break

                    if nxt is None:
                        print(f"\033[91m[FALLBACK STOP]\033[0m '{chx}' invalid → stop BEFORE consuming") # debug
                        break

                    print(f"\033[92m[FALLBACK MATCH]\033[0m '{chx}' -> {nxt}") # debug

                    temp_state = nxt
                    lex += chx
                    i += 1

                # Must end on an accepting identifier state
                if TRANSITIONS_DFA[temp_state].isEnd:
                    print(f"\033[92m[FALLBACK ACCEPT]\033[0m Identifier = '{lex}', ending at pos {i}")
                    return lex, i

                print(f"\033[91m[FALLBACK REJECT]\033[0m Ended on NON-END state {temp_state}")
                return None, start_i

            lexeme, final_pos = run_identifier_fallback(fallback_pos)

            if lexeme is not None:
                print(f"\033[92m[FALLBACK SUCCESS]\033[0m IDENTIFIER accepted '{lexeme}'")

                push("IDENTIFIER", lexeme, fallback_col)
                consumed = final_pos - fallback_pos
                pos = final_pos
                column += consumed
                continue

            print("\033[91m[ERROR]\033[0m Identifier fallback failed")

            # fallback error token
            error_lex = code[start_pos:pos+1]
            push("ERROR", error_lex, start_col, "Invalid token")
            pos += 1
            column += 1
            continue

        #=================================================================
        # VALID TOKEN FROM MAIN DFA (only happens if everything goes well.)
        #=================================================================
        state_id, end_pos, end_col, lexeme = last_accept
        token_type = TRANSITIONS_DFA[state_id].token_type

        print(f"[TOKEN] Accepted type={token_type}, lexeme='{lexeme}'")

        push(token_type, lexeme, start_col)

        pos = end_pos
        column = end_col

    print("\n=== OUTER LOOP COMPLETE — DFA scan finished successfully ===\n")
    return tokens
