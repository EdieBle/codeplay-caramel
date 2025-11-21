from .atomDelim import ATOMIC_VAL, DELIM_VAL
from .transitionDiag import TRANSITIONS_DFA

def tokenize(code):
    tokens = []
    pos = 0
    line = 1
    column = 1

    # helps build a token object and add it to the tokens list.
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
        # SIMPLE CHECKS (temp lang toh but this should be the idea, probably best to only work if curr state is 0 is though.)
        # ----------------------------------------------------------
        if ch == (" "):
            print(f"\n=== [SPACE] space detected at pos={pos}, col={column}, char='{ch}', tokenizing... ===") #debug
            push("WHITESPACE", '⎵', column)
            pos += 1
            column += 1
            continue

        if ch == ("\t"):
            print(f"\n=== [TAB] tab detected at pos={pos}, col={column}, char='{ch}', tokenizing... ===") #debug
            push("TAB", '⎵⎵⎵⎵', column)
            pos += 1
            column += 4
            continue

        if ch == ("\n"): #would be best if any line counting logic is here
            print(f"\n=== [NEWLINE] detected at pos={pos}, col={column}, char='newline', tokenizing... ===") #debug
            push("NEWLINE", '␊', column)
            pos += 1
            column += 1
            continue


        # ----------------------------------------------------------
        # DFA CRAWLING STARTS
        # ----------------------------------------------------------
        start_col = column
        curr_state = 0
        buffer = ""
        last_accept = None
        start_pos = pos  # <-- needed for ALL fallback

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
                    print(f"[INNER NXT #2] MATCH: '{ch}' → state {nxt} \n") # debug
                    break

            if next_state is None:
                print(f"[INNER] STOP: No transition for '{ch}' from state {curr_state}") # debug
                break

            curr_state = next_state
            buffer += ch
            pos += 1 # position moves 1 spot for the code list
            column += 1

            print(f"[INNER TRANSITION] Transition → state {curr_state}, buffer='{buffer}' \n") # debug

            if TRANSITIONS_DFA[curr_state].isEnd:
                last_accept = (curr_state, pos, column, buffer)
                print(f"[INNER] ACCEPTING STATE {curr_state} (buffer='{buffer}')") # debug

        print(f"=== INNER LOOP COMPLETE at pos={pos}, curr_state={curr_state} ===\n") # debug

        #=================================================================
        # DFA FAIL - fallbacks start here and error handlers over here
        #=================================================================
        if last_accept is None:
            print("\033[91m[1] DFA FAIL - \033[0m main DFA failed, starting fallbacks.") # debug

            # Rewind to start of failed token attempt
            fallback_pos = start_pos
            fallback_col = start_col

            print(f"\033[94m[FALLBACK]\033[0m Begin at first buffer char at pos={fallback_pos}, char='{code[fallback_pos]}'") # debug

            def run_identifier_fallback(start_i):
                print("\033[95m[FALLBACK] Starting identifier scan\033[0m")  # debug

                # Must be able to go 0 to 305
                start_branches = TRANSITIONS_DFA[0].branches
                if isinstance(start_branches, int):
                    start_branches = [start_branches]

                if 305 not in start_branches:
                    print("\033[91m[FALLBACK] ERROR: 0 to 305 path missing in DFA!\033[0m")
                    return None, start_i, "BAD"

                first_char = code[start_i]
                id_start_chars = TRANSITIONS_DFA[305].chars
                print(f"[ID FALLBACK] First char = '{first_char}', ID start chars = {repr(id_start_chars)}")

                if first_char not in id_start_chars:
                    print("\033[91m[ID FALLBACK] First char is NOT a valid identifier start\033[0m")
                    return None, start_i, "BAD"

                print(f"\033[92m[ID FALLBACK] '{first_char}' is valid at start to state 305\033[0m")

                lex = first_char
                temp_state = 305
                i = start_i + 1

                while i < len(code):
                    ch = code[i]
                    print(f"[ID FALLBACK] Checking '{ch}' from state {temp_state}")
                    

                    branches = TRANSITIONS_DFA[temp_state].branches
                    if isinstance(branches, int):
                        branches = [branches]

                    nxt = None
                    for candidate in branches:
                        node = TRANSITIONS_DFA[candidate]
                        if ch in node.chars:
                            nxt = candidate
                            
                            # just p
                            if node.isEnd: 
                                print(f"[ID FALLBACK] NEXT STATE {nxt} is accepting, NOT CONSUMING '{candidate}'") # debug 
                                # last_accept = (nxt, pos, column, buffer) # placeholder 
                                return lex, i, "OK"
                            
                            break

                    if nxt is None:
                        print(f"\033[91m[FALLBACK STOP]\033[0m '{ch}' invalid so stop BEFORE consuming")
                        break

                    lex += ch
                    temp_state = nxt
                    i += 1
                        
                    if temp_state == 336:
                        # if i >= len(code):
                        #     print("\033[91m[ID FALLBACK] ERROR — identifier ended without valid delimiter\033[0m") # debug

                        #     return None, start_i, "EXCEED_LENGTH"

                        next_char = code[i]
                        valid_delims = TRANSITIONS_DFA[337].chars
                        if next_char in valid_delims: # might need to put a end state here
                            return lex, i, "OK"  # valid identifier
                        else:
                            print("\033[91m[ID FALLBACK] ERROR — identifier too long or invalid termination\033[0m")
                            return None, start_i, "EXCEED_LENGTH"

                # Accept if ended on any other accepting state
                if TRANSITIONS_DFA[temp_state].isEnd:
                    print(f"\033[92m[ID FALLBACK ACCEPT]\033[0m Identifier = '{lex}', ending at pos {i}")
                    return lex, i, "OK"

                print(f"\033[91m[ID FALLBACK REJECT]\033[0m Ended on NON-END state {temp_state}")
                return None, start_i, "BAD"

            # LEXEME is character, FINAL_POS, err_type 
            # if err_type is "OK" and lexeme or returned lex is NOT none, edi accepted siya

            # probably a smarter way of handling identifiers so it saves some performance by not checking numbers.
            lexeme = None
            final_pos = None
            err_type = None
            if code[fallback_pos].isalpha() == True:
                print(f"\033[92m[IS A ALPHA CHARACTER]")
                lexeme, final_pos, err_type = run_identifier_fallback(fallback_pos)

             # can be used to handle errors related to bean and drip literals!
            if code[fallback_pos].isnumeric() == True:
                print(f"\033[92m[IS A NUMERIC CHARACTER]")
                lexeme, final_pos, err_type = run_identifier_fallback(fallback_pos) # <--- change me to another function 


            if lexeme is not None and err_type == "OK":
                print(f"\033[92m[FALLBACK SUCCESS]\033[0m IDENTIFIER accepted '{lexeme}'")

                push("IDENTIFIER", lexeme, fallback_col)
                consumed = final_pos - fallback_pos
                pos = final_pos
                column += consumed
                continue
            
            if lexeme is None and err_type == "EXCEED_LENGTH" : 
                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos
                n = len(code) # just to get the current length of the code so it doesnt just keep looping LOL (end of file)
                # advance until a space, tab, or newline. The code[error_pos] ensures that it stops at EOF
                while error_pos < n and code[error_pos] not in (" ", "\t", "\n"):
                    error_pos += 1 
                error_lex = code[start_pos:error_pos]

                # place errors here (tentative)
                push("ERROR", error_lex, start_col, "Identifier is more than 15 characters")

                # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed

                # loop will continue from the whitespace (or EOF)
                continue
            
            if lexeme is None and "BAD":
                print("\033[91m[ERROR]\033[0m fallback failed — consuming until whitespace")

                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos
                n = len(code) # just to get the current length of the code so it doesnt just keep looping LOL (end of file)

                # advance until a space, tab, or newline. The code[error_pos] ensures that it stops at EOF
                while error_pos < n and code[error_pos] not in (" ", "\t", "\n"):
                    error_pos += 1

                # whole invalid lexeme (from start_pos up to but not including the whitespace)
                error_lex = code[start_pos:error_pos] # range function that start from the start_position then records until the token can be made
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")

                # place errors here (tentative)
                push("ERROR", error_lex, start_col, "Invalid identifier")

                # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed

                # loop will continue from the whitespace (or EOF)
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
