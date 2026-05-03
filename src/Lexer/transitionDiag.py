from .atomDelim import ATOMIC_VAL, DELIM_VAL 

class State:
    def __init__(self, chars: list[str], branches: list[int] = [], end = False, token_type=None):
        self.chars = [chars] if type(chars) is str else chars
        self.branches = [branches] if type(branches) is int else branches
        self.isEnd = end
        self.token_type = token_type



TRANSITIONS_DFA = {
    0: State('initial', [1, 31, 58, 69, 90, 102, 108, 112, 119, 123, 129, 136, 153, 175, 193, 
                        202, 206, 212, 218, 225, 229, 231, 235, 239, 243, 246, 249, 251, 253,
                        255, 256, 258, 259, 261, 263, 265, 267, 268, 309, 315, 320, 350]),

    # Backroom, batter@, bean, blend, brewed
    1: State('b', [2, 16, 20, 25]), 2: State('a', [3, 10]), 3: State('c', 4), 4: State('k', 5), 5: State('r', 6), 6: State('o', 7), 7: State('o', 8), 8: State('m', 9), 9: State(DELIM_VAL['space_delim'], end = True, token_type="backroom"),
                                    10: State('t', 11), 11: State('t', 12), 12: State('e', 13), 13: State('r', 14), 14: State('@', 15), 15: State(DELIM_VAL['batter@_delim'], end = True, token_type="batter@"),
        16: State('e', 17), 17: State('a', 18), 18: State('n', 19), 19: State(DELIM_VAL['space_delim'], end = True, token_type="bean"),
        20: State('l', 21), 21: State('e', 22), 22: State('n', 23), 23: State('d', 24), 24: State(DELIM_VAL['space_delim'], end = True, token_type="blend"),
        25: State('r', 26), 26: State('e', 27), 27: State('w', 28), 28: State('e', 29), 29: State('d', 30), 30: State(DELIM_VAL['space_delim'], end = True, token_type="brewed"),
    
    # cafe, ceil, crema, churro, cold, crema, cup
    31: State('c', [32, 36, 40, 46, 50, 55]), 32: State('a', 33), 33: State('f', 34), 34: State('e', 35), 35: State(DELIM_VAL['space_delim'], end = True, token_type="cafe"),
        36: State('e', 37), 37: State('i', 38), 38: State('l', 39), 39: State('(', end = True, token_type="ceil"), 
        40: State('h', 41), 41: State('u', 42), 42: State('r', 43), 43: State('r', 44), 44: State('o', 45), 45: State(DELIM_VAL['space_delim'], end = True, token_type="churro"),
        46: State('o', 47), 47: State('l', 48), 48: State('d', 49), 49: State(DELIM_VAL['temp_delim'], end = True, token_type="cold"),
        50: State('r', 51), 51: State('e', 52), 52: State('m', 53), 53: State('a', 54), 54: State(DELIM_VAL['space_delim'], end = True, token_type="crema"),
        55: State('u', 56), 56: State('p', 57), 57: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="cup"),

    # defoam, drip
    58: State('d', [59, 65]), 
        59: State('e', 60), 60: State('f', 61), 61: State('o', 62), 62: State('a', 63), 63: State('m', 64), 64: State(':', end = True, token_type="defoam"),
        65: State('r', 66), 66: State('i', 67), 67: State('p', 68), 68: State(DELIM_VAL['space_delim'], end = True, token_type="drip"),

    # elifroth, elspress, empty
    69: State('e', [70, 85]),
        70: State('l', [71,78]), 
            71: State('i', 72), 72: State('f', 73), 73: State('r', 74), 74: State('o', 75), 75: State('t', 76), 76: State('h', 77), 77: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="elifroth"),
            78: State('s', 79), 79: State('p', 80), 80: State('r', 81), 81: State('e', 82), 82: State('s', 83), 83: State('s', 84), 84: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="elspress"),
        85: State('m', 86), 86: State('p', 87), 87: State('t', 88), 88: State('y', 89), 89: State(DELIM_VAL['space_delim'], end = True, token_type="empty"),

    # flavour, floor
    90: State('f', 91), 91: State('l', [92, 98]), 92: State('a', 93), 93: State('v', 94), 94: State('o', 95), 95: State('u', 96), 96: State('r', 97), 97: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="flavour"),
                                                98: State('o', 99), 99: State('o', 100), 100: State('r', 101), 101: State('(', end = True, token_type="floor"),
    

    # glaze, hot, ifbrew, mug, new, order
    102: State('g', 103), 103: State('l', 104), 104: State('a', 105), 105: State('z', 106), 106: State('e', 107), 107: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="glaze"),
    108: State('h', 109), 109: State('o', 110), 110: State('t', 111), 111: State(DELIM_VAL['temp_delim'], end = True, token_type="hot"),
    112: State('i', 113), 113: State('f', 114), 114: State('b', 115), 115: State('r', 116), 116: State('e', 117), 117: State('w', 118), 118: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="ifbrew"),
    # 119: State('m', 120), 120: State('u', 121), 121: State('g', 122), 122: State(DELIM_VAL['space_delim'], end = True, token_type="mug"),
    119: State('n', 120), 120: State('e', 121), 121: State('w', 122), 122: State(DELIM_VAL['space_delim'], end = True, token_type="new"),
    123: State('o', 124), 124: State('r', 125), 125: State('d', 126), 126: State('e', 127), 127: State('r', 128), 128: State('.', end = True, token_type="order"),
    
    # pour, pow
    129: State('p', 130), 130: State('o', [131,134]), 
                131: State('u', 132), 132: State('r', 133), 133: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="pour"),
                134: State('w', 135), 135: State('(', end = True, token_type="pow"),
    
    
    # rand, recipe and refill?
    136: State('r', [137,141]), 137: State('a', 138), 138: State('n', 139), 139: State('d', 140), 140: State('(', end = True, token_type="rand"),
        141: State('e', [142, 147]), 
            142: State('c', 143), 143: State('i', 144), 144: State('p', 145), 145: State('e', 146), 146: State(DELIM_VAL['space_delim'], end = True, token_type="recipe"),
            147: State('f', 148), 148: State('i', 149), 149: State('l', 150), 150: State('l', 151), 151: State('?', 152), 152: State([*DELIM_VAL['refill_delim'], "\n"], end = True, token_type="refill?"),
    
    # skip, snap, sqrt, syrup
    153: State('s', [154, 158, 162, 166, 170]), 
                    154: State('i', 155), 155: State('f', 156), 156: State('t', 157), 157: State('(', end = True, token_type="sift"),
                    158: State('k', 159), 159: State('i', 160), 160: State('p', 161), 161: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="skip"),
                    162: State('n', 163), 163: State('a', 164), 164: State('p', 165), 165: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="snap"),
                    166: State('q', 167), 167: State('r', 168), 168: State('t', 169), 169: State('(', end = True, token_type="sqrt"),
                    170: State('y', 171), 171: State('r', 172), 172: State('u', 173), 173: State('p', 174), 174: State(DELIM_VAL['space_delim'], end = True, token_type="syrup"),
    
    # taste, till, temp, type
    175: State('t', [176, 181, 185, 189]), 176: State('a', 177), 177: State('s', 178), 178: State('t', 179), 179: State('e', 180), 180: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="taste"),
                    181: State('i', 182), 182: State('l', 183), 183: State('l', 184), 184: State(':', end = True, token_type="till"),
                    185: State ('e', 186), 186: State('m', 187), 187: State('p', 188), 188: State(DELIM_VAL['space_delim'], end = True, token_type="temp"),
                    189: State('y', 190), 190: State('p', 191), 191: State('e', 192), 192: State('(', end = True, token_type="type"),
    
    # whilehot
    193: State('w', 194), 194: State('h', 195), 195: State('i', 196), 196: State('l', 197), 197: State('e', 198), 198: State('h', 199), 199: State('o', 200), 200: State('t', 201), 201: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="whilehot"),

    # Reserved Symbols
    # Equals (=)
    202: State('=', [203, 204]), 203: State(DELIM_VAL['assignment_delim'], end = True, token_type="="),
        204: State('=', 205), 205: State(DELIM_VAL['relational_delim'], end = True, token_type="=="),
    
    # Plus (+)
    206: State('+', [207, 208, 210]), 207: State(DELIM_VAL['plus_delim'], end = True, token_type="+"),
        208: State('+', 209), 209: State(DELIM_VAL['unary_delim'], end = True, token_type="++"),
        210: State('=', 211), 211: State(DELIM_VAL['assignment_delim'], end = True, token_type="+="),
    
    # Minus (-) - 272 is the start of the numbers
    212: State('-', [272, 213, 214, 216]), 213: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="-"), # 250 is the literals dont forget
        214: State('-', 215), 215: State(DELIM_VAL['unary_delim'], end = True, token_type="--"),
        216: State('=', 217), 217: State(DELIM_VAL['assignment_delim'], end = True, token_type="-="),
    
    # Asterisk (*)
    218: State('*', [219, 220, 223]), 219: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="*"),
        220: State('*', 221), 221: State('*', 222), 222: State([']', *DELIM_VAL['space_delim']], end = True, token_type="***"),
        223: State('=', 224), 224: State(DELIM_VAL['assignment_delim'], end = True, token_type="*="),
    
    # Slash (/)
    225: State('/', [226, 227]), 226: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="/"),
        227: State('=', 228), 228: State(DELIM_VAL['assignment_delim'], end = True, token_type="/="),
    
    # Modulo (%)
    229: State('%', 230), 230: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="%"),
    
    # Greater than (>)
    231: State('>', [232, 233]), 232: State(DELIM_VAL['relational_delim'], end = True, token_type=">"),
        233: State('=', 234), 234: State(DELIM_VAL['relational_delim'], end = True, token_type=">="),
    
    # Lesser than (<)
    235: State('<', [236, 237]), 236: State(DELIM_VAL['relational_delim'], end = True, token_type="<"),
        237: State('=', 238), 238: State(DELIM_VAL['relational_delim'], end = True, token_type="<="), 
    
    # NOT (!)
    239: State('!', [240, 241]), 240: State(DELIM_VAL['not_delim'], end = True, token_type="!"),
        241: State('=', 242), 242: State(DELIM_VAL['relational_delim'], end = True, token_type="!="),
    
    # AND (&) 
    243: State('&', 244), 244: State('&', 245), 245: State(DELIM_VAL['logical_delim'], end = True, token_type="&&"),
    
    # OR (|)
    246: State('|', 247), 247: State('|', 248), 248: State(DELIM_VAL['logical_delim'], end = True, token_type="||"),
    
    # Open Paren (
    249: State( '(', 250), 250: State(DELIM_VAL['opparen_delim'], end = True, token_type="("),
    
    # Close Paren )
    251: State( ')', 252), 252: State(DELIM_VAL['clparen_delim'], end = True, token_type=")"),
    
    # Open Bracket [ 
    253: State( '[', 254), 254: State(DELIM_VAL['opbrackets_delim'], end = True, token_type="["),
    
    # Close Bracket ]
    255: State( ']', end = True, token_type="]"), 
    # Deleted -> 238: State(DELIM_VAL['clbrackets_delim', ']'], end = True, token_type="]"),
    
    # Open Brace {    
    256: State( '{', 257), 257: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="{"),    
        
    # Close Brace }
    258: State( '}', end = True, token_type="}"),
    # Deleted -> 242: State(DELIM_VAL['braces_delim'], 
    
    # Dot Accessor (.)
    259: State('.', 260), 260: State(ATOMIC_VAL['alpha_small'], end = True, token_type="."),

    # Comma (,)
    261: State( ',' , 262), 262: State(DELIM_VAL['comma_delim'], end = True, token_type=","),
    
    # Colon (:)
    263: State(':', 264), 264: State(DELIM_VAL['colon_delim'], end = True, token_type=":"),
    
    # Semicolon (;)
    265: State(';' , 266), 266: State(DELIM_VAL['semicolon_delim'], end = True, token_type=";"),
    
    # Newline (commented out cuz causing issues sa actual thingy)
    # 251: State('\n',  end = True, token_type="NEWLINE"), #ISSUES: CAUSING RECURSION
    
    # OLD Newline
    267: State('\n', end = True, token_type="newline"),
    
    
    # Literals
    # BEANLIT *positive number issues
    # status: messy in particular to state 253
    268: State([*ATOMIC_VAL['whole']], [269, 270, 288]), 269: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        270: State(ATOMIC_VAL['whole'], [271, 272, 288]), 271: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        272: State(ATOMIC_VAL['whole'], [273, 274, 288]), 273: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        274: State(ATOMIC_VAL['whole'], [275, 276, 288]), 275: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        276: State(ATOMIC_VAL['whole'], [277, 278, 288]), 277: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        278: State(ATOMIC_VAL['whole'], [279, 280, 288]), 279: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        280: State(ATOMIC_VAL['whole'], [281, 282, 288]), 281: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        282: State(ATOMIC_VAL['whole'], [283, 284, 288]), 283: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        284: State(ATOMIC_VAL['whole'], [285, 286, 288]), 285: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        286: State(ATOMIC_VAL['whole'], [287, 288]), 287: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        
        # DRIPLIT
        288: State('.' , 289),
            289: State(ATOMIC_VAL['whole'], [290, 291]), 290: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"), 
            291: State(ATOMIC_VAL['whole'], [292, 293]), 292: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"), 
            293: State(ATOMIC_VAL['whole'], [294, 295]), 294: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            295: State(ATOMIC_VAL['whole'], [296, 297]), 296: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            297: State(ATOMIC_VAL['whole'], [298, 299]), 298: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            299: State(ATOMIC_VAL['whole'], [300, 301]), 300: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            301: State(ATOMIC_VAL['whole'], [302, 303]), 302: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            303: State(ATOMIC_VAL['whole'], [304, 305]), 304: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            305: State(ATOMIC_VAL['whole'], [306, 307]), 306: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            307: State(ATOMIC_VAL['whole'], 308), 308: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),

        # CHAR LITERAL (CHURROLIT)
        # Examples:  'a'  '\n'  '\t'
        309: State('\'', [313, 311, 310]),
            # Normal char (non-escape)
            310: State([*ATOMIC_VAL["text_content"]], 311),
            
            # closing single quote
            311: State('\'', 312), 

            # delimiter
            312: State([*DELIM_VAL["churro_delim"]], end=True, token_type="churrolit"),

            # Escape sequence
            313: State('\\', 314), 314: State(ATOMIC_VAL["escapeseq_let"], 311),

            # Given '\j'
            # ' -> 0 to 294
            # '\ -> 294 to 298
            # '\' -> 298 to 299_1 end? error
            # '\'' -> 299_1 to 296

        
        # STRING LITERAL (BLENDLIT) AMBIGUITY
        # Examples:  "hello"  "he\nllo"  "mix\"ed"
        315: State('"', [319, 317, 316]),
            
            # Regular characters inside string                                                                                  
            316: State([*ATOMIC_VAL["text_content"], 
                        *ATOMIC_VAL["escapeseq_let"], 
                        *ATOMIC_VAL["safe_char"]], 
                        [319, 317, 316]), 
            
            # Closing quote
            317: State('"', 318),
                # Delimiter
                318: State(DELIM_VAL["string_delim"], end=True, token_type="blendlit"),

            # Escape sequence
            319: State("\\", 316),



        # IDENTIFIERS (gotta limit to 15 characters lang with a starting small letter, and everything after can only be underscore or number)
        # Start with lowercase letter, can include digits or underscores
        320: State(ATOMIC_VAL["alpha_small"], [321, 322]), 
                321: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            322: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [323, 324]), 
                323: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            324: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [325, 326]), 
                325: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            326: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [327, 328]), 
                327: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            328: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [329, 330]), 
                329: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            330: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [331, 332]), # was 329 earlier, broke the id
                331: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            332: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [333, 334]), 
                333: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            334: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [335, 336]), 
                335: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            336: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [337, 338]), 
                337: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            338: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [339, 340]), 
                339: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            340: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [341, 342]), 
                341: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            342: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [343, 344]), 
                343: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            344: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [345, 346]), 
                345: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            346: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [347, 348]), 
                347: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            348: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], 349), 
                349: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
        


        # SINGLE LINE COMMENT
        # Pattern: ~~ comment until newline
        # status: okay
        350: State('~', [351, 354]),
            351: State('~', 352),
            352: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL["escapeseq_let"]], [353, 352]),
            353: State('\n', end=True, token_type="sl_comment"),

        # MULTI LINE COMMENT
        # Pattern: ~. comment content .~
        # status: ambiguity due to atomDelim
            354: State('.', 355),
            355: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL['sp_symbols'], *ATOMIC_VAL['escapeseq_let'], '\n'], [356, 355]),
                356: State('.', [357, 355]),
                357: State('~', 358),
                358: State([*DELIM_VAL['space_delim'], '\n'], end=True, token_type="ml_comment")

}
