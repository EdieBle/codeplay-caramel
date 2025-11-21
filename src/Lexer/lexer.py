from .atomDelim import ATOMIC_VAL, DELIM_VAL
from .transitionDiag import TRANSITIONS_DFA

def tokenize(code):
    code += '$' # for appending an eof haha
    tokens = []
    pos = 0
    line = 1
    column = 1

    # Unique identifier tracking
    identifier_map = {} # tried to use a list instead of map but it kept blowing up at 
                        # >100 identifiers (had noticeable slowness) so dictionaries it is!
    identifier_counter = 1

    # helps build a token object and add it to the tokens list.
    def push(token_type, lexeme, start_col, message=None):
        nonlocal identifier_counter  # update counter if identifier not in the map.

        if token_type == "IDENTIFIER":
            if lexeme not in identifier_map:
                identifier_map[lexeme] = f"IDENTIFIER{identifier_counter}"
                identifier_counter += 1

            token_type = identifier_map[lexeme]

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
        # SIMPLE CHECKS
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

        if ch == '$' and pos==(len(code) - 1):
            print(f"\n=== [EOF] detected at pos={pos}, col={column}, char='End of File sign', tokenizing... ===") #debug
            push("EOF", '$', column)
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


            # Check if '0' can move us to state 253, this is for the bean and drip literal leading zero stuff
            can_go_to_253 = any(
                nxt for nxt in branches
                if 0 in TRANSITIONS_DFA and '0' in TRANSITIONS_DFA[nxt].chars and nxt == 253
            )

            if ch == '0' and can_go_to_253:
                lookahead = pos + 1
                # first_non_zero_found = False

                while lookahead < len(code):
                    next_char = code[lookahead]
                    if next_char == '0':
                        # skip this zero
                        lookahead += 1
                        pos += 1
                        column += 1
                        print(f"[LEADING ZERO] Skipping extra '0', buffer='{buffer}'")
                    elif next_char in '123456789':
                        pos += 1
                        # first non-zero digit found
                        break
                    elif next_char == '.':
                        # decimal point found — stop skipping
                        break
                    else:
                        # invalid or number end
                        break
                ch = code[pos]  # update current char for DFA processing


            print(f"[INNER] Possible branches from state {curr_state}: {branches}") # debug

            for nxt in branches:
                node = TRANSITIONS_DFA[nxt]
                if ch in node.chars:
                    if node.isEnd:
                        print(f"[INNER NXT #1] NEXT STATE {nxt} is accepting | NOT consuming '{ch}'") # debug
                        last_accept = (nxt, pos, column, buffer)
                        next_state = None
                        break

                    next_state = nxt
                    print(f"[INNER NXT #2] MATCH: '{ch}' -> state {nxt} \n") # debug
                    break

            if next_state is None:
                print(f"[INNER] STOP: No transition for '{ch}' from state {curr_state}") # debug
                break

            curr_state = next_state
            buffer += ch
            pos += 1 # position moves 1 spot for the code list
            column += 1

            print(f"[INNER TRANSITION] Transition -> state {curr_state}, buffer='{buffer}' \n") # debug

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


             # probably a smarter way of handling identifiers so it saves some performance by not checking numbers.
            lexeme = None
            final_pos = None
            err_type = None

            def run_identifier_fallback(start_i):

                first_char = code[start_i]
                if first_char == first_char.upper():
                    print("\033[91m[ID ERROR]\033[0m Cannot start number with a capital letter.")
                    return None, start_i, "ID_ERR"

                print("\033[95m[FALLBACK] Starting identifier scan\033[0m")  # debug

                # Must be able to go 0 to 305
                # start_branches = TRANSITIONS_DFA[0].branches
                # if isinstance(start_branches, int):
                #     start_branches = [start_branches]

                # if 305 not in start_branches:
                #     print("\033[91m[FALLBACK] ERROR: 0 to 305 path missing in DFA!\033[0m")
                #     return None, start_i, "GEN_ERR"
                
                # id_start_chars = TRANSITIONS_DFA[305].chars
                # print(f"[ID FALLBACK] First char = '{first_char}', ID start chars = {repr(id_start_chars)}")

                # if first_char not in id_start_chars:
                #     print("\033[91m[ID FALLBACK] First char is NOT a valid identifier start\033[0m")
                #     return None, start_i, "BAD"

                # print(f"\033[92m[ID FALLBACK] '{first_char}' is valid at start to state 305\033[0m")

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
                        
                    if temp_state == 333:
                        # if i >= len(code):
                        #     print("\033[91m[ID FALLBACK] ERROR | identifier ended without valid delimiter\033[0m") # debug

                        #     return None, start_i, "EXCEED_LENGTH"

                        next_char = code[i]
                        valid_delims = TRANSITIONS_DFA[334].chars
                        if next_char in valid_delims: # might need to put a end state here
                            return lex, i, "OK"  # valid identifier
                        else:
                            print("\033[91m[ID FALLBACK] ERROR | identifier too long or invalid termination\033[0m")
                            return None, start_i, "EXCEED_LENGTH_ERR" # not getting called right now

                # Accept if ended on any other accepting state
                if TRANSITIONS_DFA[temp_state].isEnd:
                    print(f"\033[92m[ID FALLBACK ACCEPT]\033[0m Identifier = '{lex}', ending at pos {i}")
                    return lex, i, "OK"

                print(f"\033[91m[ID FALLBACK REJECT]\033[0m Ended on NON-END state {temp_state}")
                return None, start_i, "GEN_ERR" # might

            def run_num_handler(start_i):
                print("\033[95m[FALLBACK] Starting number scan\033[0m")  # debug

                first_char = code[start_i]

                # =============================================
                # ERROR: literal starts with a decimal point
                # =============================================
                if first_char == '.':
                    print("\033[91m[NUM ERROR]\033[0m Cannot start number with '.' | incomplete float literal")
                    return None, start_i, "INC_DRIP_ERR"

                # # must start at state 253 (whole number start)
                # start_branches = TRANSITIONS_DFA[0].branches
                # if isinstance(start_branches, int):
                #     start_branches = [start_branches]

                # if 253 not in start_branches:
                #     print("\033[91m[NUM ERROR]\033[0m 0 -> 253 missing in DFA")
                #     return None, start_i, "GEN_ERR"

                # check first digit
                # whole_chars = TRANSITIONS_DFA[253].chars
                # if first_char not in whole_chars:
                #     print("\033[91m[NUM ERROR]\033[0m First char not a whole digit")
                #     return None, start_i, "BAD"

                # print(f"\033[92m[NUM OK]\033[0m '{first_char}' valid start for whole-number state 253")

                lex = first_char
                temp_state = 253
                i = start_i + 1

                while i < len(code):
                    ch = code[i]
                    print(f"[NUM] Checking '{ch}' from state {temp_state}")

                    branches = TRANSITIONS_DFA[temp_state].branches
                    if isinstance(branches, int):
                        branches = [branches]

                    nxt = None
                    for candidate in branches:
                        node = TRANSITIONS_DFA[candidate]
                        if ch in node.chars:
                            nxt = candidate
                            break

                    if nxt is None:
                        print(f"\033[91m[NUM STOP]\033[0m '{ch}' invalid BEFORE consuming")
                        break

                    # =============================================
                    # ERROR: entered 273 ('.') but next char not digit
                    # =============================================
                    if nxt == 273:      # DOT state
                        print("[NUM] ENTERED DOT STATE 273")
                        # Lookahead: must have digit next
                        if i + 1 >= len(code) or code[i+1] not in TRANSITIONS_DFA[274].chars:
                            print("\033[91m[NUM ERROR]\033[0m Float literal has '.' but no digits after it")
                            return None, start_i, "INC_DRIP_ERR"

                    # consume
                    temp_state = nxt
                    lex += ch
                    i += 1

                    # # Accepting?
                    # if TRANSITIONS_DFA[temp_state].isEnd:
                    #     print(f"\033[92m[NUM ACCEPT]\033[0m Number accepted '{lex}'")
                    #     return lex, i, "OK"

                # End-of-input check
                # if TRANSITIONS_DFA[temp_state].isEnd:
                #     print(f"\033[92m[NUM ACCEPT]\033[0m Number accepted '{lex}' at pos {i}")
                #     return lex, i, "OK"

                # print(f"\033[91m[NUM REJECT]\033[0m Ended on NON-END state {temp_state}")
                # return None, start_i, "BAD"
                # The above return statement causes a unpack non-iterable error if it  doesnt get uncommented.

            def run_chur_handler(start_i):
                print("\033[95m[FALLBACK] Starting churro scan\033[0m")

                lex = "'"
                i = start_i + 1

                # After the opening, it MUST be either:
                #   - normal character (-> 295)
                #   - escape sequence (-> 298 -> 299)
                # Anything else -> error
                if i >= len(code):
                    print("\033[91m[CHUR ERROR]\033[0m Empty churro literal")
                    return None, start_i, "CHURRO_ERR"

                ch = code[i]
                lex += ch

                # =========================================================
                # CASE 1: normal char -> state 295
                # =========================================================
                if ch in TRANSITIONS_DFA[295].chars:
                    # Next MUST be closing '
                    i += 1
                    if i < len(code) and code[i] == "'":
                        lex += "'"
                        print(f"\033[92m[CHUR ACCEPT]\033[0m CHURROLIT = {lex}")
                        return lex, i + 1, "OK"
                    else:
                        print("\033[91m[CHUR ERROR]\033[0m Normal char NOT followed by closing quote")
                        return None, start_i, "CHURRO_ERR"

                # =========================================================
                # CASE 2: escape start -> state 298 -> 299
                # =========================================================
                if ch == "\\":  # escape start
                    i += 1
                    if i >= len(code):
                        print("\033[91m[CHUR ERROR]\033[0m Escape sequence incomplete")
                        return None, start_i, "CHURRO_ERR"

                    esc = code[i]
                    if esc not in TRANSITIONS_DFA[299].chars:
                        print("\033[91m[CHUR ERROR]\033[0m Invalid escape sequence")
                        return None, start_i, "CHURRO_ERR"

                    lex += esc
                    i += 1

                # =========================================================
                # OTHERWISE invalid second character
                # =========================================================
                print("\033[91m[CHUR ERROR]\033[0m Invalid churro literal format")
                return None, start_i, "CHURRO_ERR"

            # LEXEME is character, FINAL_POS, err_type 
            # if err_type is "OK" and lexeme and returned lexeme is NOT none, edi accepted siya

            if code[fallback_pos].isalpha() == True:
                print(f"\033[92m[IS A ALPHA CHARACTER]")
                lexeme, final_pos, err_type = run_identifier_fallback(fallback_pos)

             # can be used to handle errors related to bean and drip literals!
            if code[fallback_pos].isnumeric() == True or code[fallback_pos] == '.':
                print(f"\033[92m[IS A NUMERIC CHARACTER]")
                lexeme, final_pos, err_type = run_num_handler(fallback_pos)

            if code[fallback_pos] == '\'':
                print(f"\033[92m[IS A CHURRO LITERAL]")
                lexeme, final_pos, err_type = run_chur_handler(fallback_pos)


            if lexeme is not None and err_type == "OK":
                print(f"\033[92m[FALLBACK SUCCESS]\033[0m IDENTIFIER accepted '{lexeme}'")

                push("IDENTIFIER", lexeme, fallback_col)
                consumed = final_pos - fallback_pos
                pos = final_pos
                column += consumed
                continue
            
            if lexeme is None and err_type == "EXCEED_LENGTH_ERR" : 
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

            if lexeme is None and err_type == "INC_DRIP_ERR" : 
                print("\033[91m[ERROR]\033[0m error detected | consuming until whitespace")

                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos
                n = len(code) # just to get the current length of the code so it doesnt just keep looping LOL (end of file)

                # advance until a space, tab, or newline. The code[error_pos] ensures that it stops at EOF
                while error_pos < n and code[error_pos] not in (" ", "\t", "\n"):
                    error_pos += 1

                # whole invalid lexeme (from start_pos up to but not including the whitespace)
                error_lex = code[start_pos:error_pos] # range function that start from the start_position then records until the token can be made
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")

                push("ERROR", error_lex, start_col, "Incomplete or improper Drip literal.")

                 # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed
                continue

            if lexeme is None and err_type == "ID_ERR" : 
                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos
                n = len(code) # just to get the current length of the code so it doesnt just keep looping LOL (end of file)

                # advance until a space, tab, or newline. The code[error_pos] ensures that it stops at EOF
                while error_pos < n and code[error_pos] not in (" ", "\t", "\n"):
                    error_pos += 1

                # whole invalid lexeme (from start_pos up to but not including the whitespace)
                error_lex = code[start_pos:error_pos] # range function that start from the start_position then records until the token can be made
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")

                push("ERROR", error_lex, start_col, "Improper Identifier.")

                # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed
                continue

            if lexeme is None and err_type == "CHURRO_ERR" : 
                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos
                n = len(code) # just to get the current length of the code so it doesnt just keep looping LOL (end of file)

                # advance until a space, tab, or newline. The code[error_pos] ensures that it stops at EOF
                while error_pos < n and code[error_pos] not in (" ", "\t", "\n"):
                    error_pos += 1

                # whole invalid lexeme (from start_pos up to but not including the whitespace)
                error_lex = code[start_pos:error_pos] # range function that start from the start_position then records until the token can be made
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")

                push("ERROR", error_lex, start_col, "Unclosed or Invalid Churro.")

                # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed
                continue

            if lexeme is None and "GEN_ERR":
                print("\033[91m[ERROR]\033[0m fallback failed | consuming until whitespace")

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
                push("ERROR", error_lex, start_col, "Invalid token. Invalid symbol or unclosed Blend or Multi-line comment detected while tokenizing.")

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

    print("\n=== OUTER LOOP COMPLETE | DFA scan finished successfully ===\n")
    return tokens
