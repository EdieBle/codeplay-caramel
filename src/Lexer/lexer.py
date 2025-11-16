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
        # must be included for column and line counter ---- start_pos = pos
        start_col = column
        curr_state = 0
        buffer = ""
        last_accept = None

        while pos < len(code):

            ch = code[pos]
            print(f"[INNER] At pos={pos}, col={column}, char='{ch}', curr_state={curr_state}") #debug

            next_state = None

            # get branches (list or single int)
            branches = TRANSITIONS_DFA[curr_state].branches
            if isinstance(branches, int):
                branches = [branches]

            print(f"[INNER] Possible branches from state {curr_state}: {branches}") #debug

            # look for a matching transition
            for nxt in branches:
                node = TRANSITIONS_DFA[nxt]
                if ch in node.chars:
                    if node.isEnd:
                        print(f"[INNER NXT IN BRANCHES #1] NEXT STATE {nxt} is accepting. Will not include '{ch}' in buffer")
                        last_accept = (nxt, pos, column, buffer)
                        next_state = None  # optional: stop DFA here if you want
                    else:
                        next_state = nxt
                        print(f"[INNER NXT IN BRANCHES #2] MATCH: char '{ch}' fits state {nxt}")
                    break

            # NO TRANSITION: stop DFA
            if next_state is None:
                print(f"[INNER] STOP: No transition found for char '{ch}' in state {curr_state}") #debug
                break

            # process character
            curr_state = next_state
            buffer += ch
            pos += 1
            column += 1

            print(f"[INNER] Transitioned → state {curr_state}, buffer='{buffer}'") #debug

            # record accepting state
            if TRANSITIONS_DFA[curr_state].isEnd:
                #buffer = buffer[:-1] # remove the character at the end as it is a delimiter 
                                     # a better fix would be to check if the given character leads to a state with end, then just push without it

                if ch == '\n': # test this should be a different issue
                   push("NEWLINE", "↵", column)
                if ch == ' ': # test this should be a different issue
                   push("SPACE", " ", column)

                last_accept = (curr_state, pos, column, buffer)
                print(f"[INNER] ACCEPTING STATE {curr_state} reached (buffer='{buffer}')") #debug

        # ----------------------------------------------------------
        # DFA FINISHED — PROCESS TOKEN
        # ----------------------------------------------------------
        print(f"=== INNER LOOP COMPLETE at pos={pos}, curr_state={curr_state} ===") #debug

    

        if last_accept is None:
            print(f"[ERROR] No accepting state reached — pushing ERROR token for '{ch}'") #debug
            push("ERROR", ch, start_col, "Unrecognized token")
            pos += 1
            column += 1
            continue

        state_id, end_pos, end_col, lexeme = last_accept
        token_type = TRANSITIONS_DFA[state_id].token_type
        print(f"[TOKEN] Accepted token type={token_type}, lexeme='{lexeme}'") #debug

        push(token_type, lexeme, start_col)

        pos = end_pos
        column = end_col

    print("\n=== OUTER LOOP COMPLETE — DFA scan finished successfully ===\n") #debug

    return tokens
