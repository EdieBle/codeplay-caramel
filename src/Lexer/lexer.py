from .atomDelim import ATOMIC_VAL, DELIM_VAL, KEYWORDS_TABLE
from .transitionDiag import TRANSITIONS_DFA

def tokenize(code):
    # code += '$' # for appending an eof haha
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

        # Below check was for the now less simple newline tokenizer
        # if ch == ("\n"): #would be best if any line counting logic is here
        #     print(f"\n=== [NEWLINE] detected at pos={pos}, col={column}, char='newline', tokenizing... ===") #debug
        #     push("NEWLINE", '␊', column)
        #     pos += 1
        #     column += 1
        #     continue
        # Below check was for the now dead EOF
        # if ch == '$' and pos==(len(code) - 1):
        #     print(f"\n=== [EOF] detected at pos={pos}, col={column}, char='End of File sign', tokenizing... ===") #debug
        #     push("EOF", '$', column)
        #     pos += 1
        #     column += 1
        #     continue


        # ----------------------------------------------------------
        # DFA CRAWLING STARTS
        # ----------------------------------------------------------
        start_col = column
        curr_state = 0
        buffer = "" # container for our characters to get appended to before they get removed if either it throws an error or a proper token.
        last_accept = None
        start_pos = pos  # <-- needed for ALL error + fallback

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
                if 0 in TRANSITIONS_DFA and '0' in TRANSITIONS_DFA[nxt].chars and nxt == 252
            )

            # Check if any current DFA branch can move us to state 273 (the '.' state), WIP 
            can_go_to_273 = any(
                nxt == 272 and '.' in TRANSITIONS_DFA[nxt].chars
                for nxt in branches
            )

            if can_go_to_273:
                look = pos
                while look < len(code):
                    c = code[look]
                    if c in '123456789':
                        # pos = look  # track last meaningful digit after decimal
                        print(c)

                    look += 1

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
                        print(f"[BEAN PREPROCESS] Skipping extra '0', buffer='{buffer}'")
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

            handled = None
            for nxt in branches:
                node = TRANSITIONS_DFA[nxt]
                if curr_state == 0 and nxt == 251 and ch == "\n": # check might be unnecessary for ch but might as well just to make sure amirite
                    print("\033[92m[NEWLINE]\033[0m Consuming newline")
                    push(node.token_type, "␊", column)

                    pos += 1      # consume newline
                    line += 1
                    column = 1

                    handled = True 
                    next_state = None
                    # IMPORTANT: break out of inner loop to restart outer loop
                    break

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
        if handled:
            continue

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
            ch_bl_err_range = None
            def run_identifier_handler(start_i):
                nonlocal ch_bl_err_range 
                ch_bl_err_range = start_i
                first_char = code[start_i]
                if first_char == first_char.upper():
                    print("\033[91m[ID ERROR]\033[0m Cannot have a identifier or keyword with a capital letter.")
                    return None, start_i, "ID_ERR"

                print("\033[95m[FALLBACK] Starting identifier scan\033[0m")  # debug

                lex = first_char
                temp_state = 304
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
                                print(lex)
                                return lex, i, "OK"
                            break

                    if nxt is None:
                        print(i)
                        print(lex + "\n")
                        print(f"\033[91m[FALLBACK STOP]\033[0m '{ch}' invalid so stop BEFORE consuming")
                        return None, i, "ID_ERR"


                    lex += ch
                    temp_state = nxt
                    i += 1
                        
                    if temp_state == 332:
                        next_char = code[i]
                        valid_delims = TRANSITIONS_DFA[333].chars
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
                nonlocal ch_bl_err_range 
                ch_bl_err_range = start_i
                print("\033[95m[FALLBACK] Starting number scan\033[0m")  # debug

                first_char = code[start_i]

                # =============================================
                # ERROR: literal starts with a decimal point
                # =============================================
                if first_char == '.':
                    print("\033[91m[NUM ERROR]\033[0m Cannot start number with '.' | incomplete float literal")
                    return None, start_i, "INC_DRIP_ERR"

                lex = first_char
                temp_state = 252
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

                return None, start_i, "INC_DRIP_ERR"
                # The above return statement causes a unpack non-iterable error if commented.

            def run_incomp_handler(start_i):
                nonlocal ch_bl_err_range 
                ch_bl_err_range = start_i
                if code[start_i] == '\'':
                    print("\033[91m[CHUR ERROR]\033[0m Invalid churro literal format")
                    return None, start_i, "CH_BL_ERR"
                if code[start_i] == '"':
                    print("\033[91m[BLND ERROR]\033[0m Invalid blend literal format")
                    return None, start_i, "CH_BL_ERR"
                if code[start_i:start_i+2] == '~.':
                    print("\033[91m[MLCM ERROR]\033[0m Unclosed Multi-line comment.")
                    return None, start_i, "CH_BL_ERR"

            # LEXEME is character, FINAL_POS, err_type 
            # if err_type is "OK" and lexeme and returned lexeme is NOT none, edi accepted siya
            # this spot decides what kinda error it should be handled by.
            if code[fallback_pos].isalpha() == True:
                print(f"\033[92m[IS A ALPHA CHARACTER]")
                lexeme, final_pos, err_type = run_identifier_handler(fallback_pos)

             # can be used to handle errors related to bean and drip literals!
            
            if code[fallback_pos].isnumeric() == True or code[fallback_pos] == '.':
                print(f"\033[92m[IS A NUMERIC CHARACTER]")
                lexeme, final_pos, err_type = run_num_handler(fallback_pos)
            
            if code[fallback_pos] == '\'' or code[fallback_pos] == '"' or code[fallback_pos:fallback_pos+2] == "~.":
                print(f"\033[92m[IS A CHURRO/BLEND LITERAL or AN UNCLOSED MULTILINE COMMENT]")
                lexeme, final_pos, err_type = run_incomp_handler(fallback_pos)

            # error type handlers.
            if lexeme is not None and err_type == "OK":
                print(f"\033[92m[FALLBACK SUCCESS]\033[0m IDENTIFIER accepted! Will now check if'{lexeme}' is a keyword...")
                print("OKAY STATUS REACHED")
                # just a final a check just in case a stray keyword gets lodged into the identifier section, which i mean it can be a proper flow.
                if lexeme in KEYWORDS_TABLE["KEYWORDS"]:
                    print("LEXEME IN KEYWORDS TABLE! IS A KEYWORD!")
                    print(lexeme)
                    
                    # just a small while loop to recheck the lexeme and see if its a keyword a properly delimited
                    
                    
                    #push("KEYWORD", lexeme, fallback_col)
                else:
                    print("LEXEME NOT IN KEYWORDS TABLE!")
                    push("IDENTIFIER", lexeme, fallback_col)
                
                consumed = final_pos - fallback_pos
                pos = final_pos
                column += consumed
                continue
            
            if lexeme is None and err_type == "EXCEED_LENGTH_ERR" : 
                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos+15 # why +15? because its the start position +15 character and this only triggers if it exceeds length
               
                while error_pos < pos:
                    error_pos += 1
                error_lex = code[start_pos:error_pos] # range function that start from the start_position then records until the token can be made
                # print("\033[91m[DEBUG]\033[0m ")
                # print(error_pos)
                
                #push("ERROR", error_lex, start_col, "Identifier is more than 15 characters")
                push("ERROR", error_lex, start_col, "Invalid Delimiter for possible token")

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

                while error_pos < pos:
                    error_pos += 1
                error_lex = code[start_pos:error_pos]
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")

                # push("ERROR", error_lex, start_col, "Incomplete or out-of-range Numeric literal.")
                push("ERROR", error_lex, start_col, "Incomplete Token")

                 # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed
                continue

            if lexeme is None and err_type == "ID_ERR" : 
                # Consume the entire invalid run starting from the original token start (start_pos)
                print(final_pos)
                error_pos = final_pos # this SHOULD fix the infinite recursion problem with capital letters considering it would fall under run_identifier_handle
                print("start of id error")
                while error_pos < pos:
                    error_pos += 1
                
                error_lex = code[start_pos:error_pos] 
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")
                first_char = code[start_pos]
                print("The first char")
                print(first_char)
                if first_char == first_char.upper() and first_char.isalpha() and not first_char.isnumeric():
                    print("\033[91m[ID ERROR]\033[0m Cannot have identifier with a capital letter.")
                    error_lex = code[start_pos:error_pos+1] 
                    #push("ERROR", error_lex, start_col, "Cannot have identifier with a capital letter.")
                    push("ERROR", error_lex, start_col, "Cannot begin token with capital letter")
                    consumed = error_pos - start_pos
                    pos = error_pos+1
                    column += consumed
                    continue
                
                push("ERROR", error_lex, start_col, "Invalid Delimiter for Possible Token")
                #push("ERROR", error_lex, start_col, "Improperly delimited Identifier.")

                # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed
                continue

            if lexeme is None and err_type == "CH_BL_ERR" : 
                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos

                while error_pos < pos:
                    error_pos += 1

                error_lex = code[start_pos:error_pos]
                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")

                if code[ch_bl_err_range] == '\'':
                    print("\033[91m[CHUR ERROR]\033[0m Invalid churro literal format")
                    #push("ERROR", error_lex, start_col, "Unclosed or Invalid Churro")
                    push("ERROR", error_lex, start_col, "Unclosed Token")
                if code[ch_bl_err_range] == '"':
                    print("\033[91m[BLND ERROR]\033[0m Invalid blend literal format")
                    #push("ERROR", error_lex, start_col, "Unclosed or Undelimited Blend Literal")
                    push("ERROR", error_lex, start_col, "Unclosed Token")
                if code[ch_bl_err_range:ch_bl_err_range+2] == '~.':
                    print("\033[91m[MCLN ERROR]\033[0m Unclosed Multi-line comment.")
                    #push("ERROR", error_lex, start_col, "Unclosed Multi-line comment.")
                    push("ERROR", error_lex, start_col, "Unclosed Token")

                # advance pos/column to after the consumed invalid chunk
                consumed = error_pos - start_pos
                pos = error_pos
                column += consumed
                continue

            if lexeme is None and "GEN_ERR":
                print("\033[91m[ERROR]\033[0m fallback failed")

                # Consume the entire invalid run starting from the original token start (start_pos)
                error_pos = start_pos+1 #max(pos + 1, start_pos + 1) # place this here, same issue as ID_ERR with the loop stuff

                print(start_pos)
                print(error_pos)
                while error_pos < pos:
                    error_pos += 1
                
                error_lex = code[start_pos:error_pos] 
                print(error_lex) #debug

                # debug statement for error stuff: print(f"\033[91m[ERROR]\033[0m Emitting single ERROR token for full invalid chunk: '{error_lex}' (cols {start_col}..{start_col + len(error_lex) - 1})")
                push("ERROR", error_lex, start_col, "Invalid Character")

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
