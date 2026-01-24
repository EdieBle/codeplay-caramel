from .atomDelim import ATOMIC_VAL, DELIM_VAL 

class State:
    def __init__(self, chars: list[str], branches: list[int] = [], end = False, token_type=None):
        self.chars = [chars] if type(chars) is str else chars
        self.branches = [branches] if type(branches) is int else branches
        self.isEnd = end
        self.token_type = token_type



TRANSITIONS_DFA = {
    0: State('initial', [1, 31, 54, 69, 90, 98, 104, 108, 115, 119, 123, 129, 134, 147, 161, 175, 184, 188, 
                        194, 200, 207, 211, 213, 217, 221, 225, 228, 231, 233, 235, 237, 238, 240, 241, 243, 
                        245, 247, 249, 250, 291, 297, 302, 332]),

    # Backroom, batter@, bean, blend, brewed
    1: State('b', [2, 16, 20, 25]), 2: State('a', [3, 10]), 3: State('c', 4), 4: State('k', 5), 5: State('r', 6), 6: State('o', 7), 7: State('o', 8), 8: State('m', 9), 9: State(DELIM_VAL['space_delim'], end = True, token_type="BACKROOM"),
                                    10: State('t', 11), 11: State('t', 12), 12: State('e', 13), 13: State('r', 14), 14: State('@', 15), 15: State(DELIM_VAL['batter@_delim'], end = True, token_type="BATTER"),
        16: State('e', 17), 17: State('a', 18), 18: State('n', 19), 19: State(DELIM_VAL['space_delim'], end = True, token_type="BEAN"),
        20: State('l', 21), 21: State('e', 22), 22: State('n', 23), 23: State('d', 24), 24: State(DELIM_VAL['space_delim'], end = True, token_type="BLEND"),
        25: State('r', 26), 26: State('e', 27), 27: State('w', 28), 28: State('e', 29), 29: State('d', 30), 30: State(DELIM_VAL['space_delim'], end = True, token_type="BREWED"),
    
    # cafe, crema, churro, cold, crema, cup
    31: State('c', [32, 36, 42, 46, 51]), 32: State('a', 33), 33: State('f', 34), 34: State('e', 35), 35: State(DELIM_VAL['space_delim'], end = True, token_type="CAFE"),
        36: State('h', 37), 37: State('u', 38), 38: State('r', 39), 39: State('r', 40), 40: State('o', 41), 41: State(DELIM_VAL['space_delim'], end = True, token_type="CHURRO"),
        42: State('o', 43), 43: State('l', 44), 44: State('d', 45), 45: State(DELIM_VAL['temp_delim'], end = True, token_type="COLD"),
        46: State('r', 47), 47: State('e', 48), 48: State('m', 49), 49: State('a', 50), 50: State(DELIM_VAL['space_delim'], end = True, token_type="CREMA"),
        51: State('u', 52), 52: State('p', 53), 53: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="CUP"),

    # decaf, drip
    54: State('d', [55, 60, 65]),
        55: State('e', [56,60]), 56: State('c', 57), 57: State('a', 58), 58: State('f', 59), 59: State(DELIM_VAL['space_delim'], end = True, token_type="DECAF"),
                    60: State('f', 61), 61: State('o', 62), 62: State('a', 63), 63: State('m', 64), 64: State(':', end = True, token_type="DEFOAM"),
        65: State('r', 66), 66: State('i', 67), 67: State('p', 68), 68: State(DELIM_VAL['space_delim'], end = True, token_type="DRIP"),

    # elifroth, elspress, empty
    69: State('e', [70, 85]),
        70: State('l', [71,78]), 71: State('i', 72), 72: State('f', 73), 73: State('r', 74), 74: State('o', 75), 75: State('t', 76), 76: State('h', 77), 77: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="ELIFROTH"),
                    78: State('s', 79), 79: State('p', 80), 80: State('r', 81), 81: State('e', 82), 82: State('s', 83), 83: State('s', 84), 84: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="ELSPRESS"),
        85: State('m', 86), 86: State('p', 87), 87: State('t', 88), 88: State('y', 89), 89: State(DELIM_VAL['space_delim'], end = True, token_type="EMPTY"),

    # flavour
    90: State('f', 91), 91: State('l', 92), 92: State('a', 93), 93: State('v', 94), 94: State('o', 95), 95: State('u', 96), 96: State('r', 97), 97: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="FLAVOUR"),

    # glaze, hot, ifbrew, mug, new, order
    98: State('g', 99), 99: State('l', 100), 100: State('a', 101), 101: State('z', 102), 102: State('e', 103), 103: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="GLAZE"),
    104: State('h', 105), 105: State('o', 106), 106: State('t', 107), 107: State(DELIM_VAL['temp_delim'], end = True, token_type="hot"),
    108: State('i', 109), 109: State('f', 110), 110: State('b', 111), 111: State('r', 112), 112: State('e', 113), 113: State('w', 114), 114: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="ifbrew"),
    115: State('m', 116), 116: State('u', 117), 117: State('g', 118), 118: State(DELIM_VAL['space_delim'], end = True, token_type="mug"),
    119: State('n', 120), 120: State('e', 121), 121: State('w', 122), 122: State(DELIM_VAL['space_delim'], end = True, token_type="new"),
    123: State('o', 124), 124: State('r', 125), 125: State('d', 126), 126: State('e', 127), 127: State('r', 128), 128: State([*DELIM_VAL['spaceparen_delim'], '.'], end = True, token_type="order"),
    
    # pour
    129: State('p', 130), 130: State('o', 131), 131: State('u', 132), 132: State('r', 133), 133: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="pour"),
    
    # recipe and refill?
    134: State('r', 135), 135: State('e', [136, 141]), 136: State('c', 137), 137: State('i', 138), 138: State('p', 139), 139: State('e', 140), 140: State(DELIM_VAL['space_delim'], end = True, token_type="recipe"),
    141: State('f', 142), 142: State('i', 143), 143: State('l', 144), 144: State('l', 145), 145: State('?', 146), 146: State([*DELIM_VAL['refill_delim'], "\n"], end = True, token_type="refill"),
    
    # skip, snap, syrup
    147: State('s', [148, 152, 156]), 148: State('k', 149), 149: State('i', 150), 150: State('p', 151), 151: State(ATOMIC_VAL['newline'], end = True, token_type="skip"),
                    152: State('n', 153), 153: State('a', 154), 154: State('p', 155), 155: State(ATOMIC_VAL['newline'], end = True, token_type="snap"),
                    156: State('y', 157), 157: State('r', 158), 158: State('u', 159), 159: State('p', 160), 160: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="syrup"),
    
    # taste, till, temp
    161: State('t', [162, 167, 171]), 162: State('a', 163), 163: State('s', 164), 164: State('t', 165), 165: State('e', 166), 166: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="taste"),
                    167: State('i', 168), 168: State('l', 169), 169: State('l', 170), 170: State(':', end = True, token_type="till"),
                    171: State ('e', 172), 172: State('m', 173), 173: State('p', 174), 174: State(DELIM_VAL['space_delim'], end = True, token_type="temp"),
    
    # whilehot
    175: State('w', 176), 176: State('h', 177), 177: State('i', 178), 178: State('l', 179), 179: State('e', 180), 180: State('h', 181), 181: State('o', 182), 182: State('t', 183), 183: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="whilehot"),

    # Reserved Symbols
    # Equals (=)
    184: State('=', [185, 186]), 185: State(DELIM_VAL['assignment_delim'], end = True, token_type="EQUALS"),
        186: State('=', 187), 187: State(DELIM_VAL['relational_delim'], end = True, token_type="EQ_EQUALS"),
    
    # Plus (+)
    188: State('+', [189, 190, 192]), 189: State(DELIM_VAL['plus_delim'], end = True, token_type="PLUS"),
        190: State('+', 191), 191: State(DELIM_VAL['unary_delim'], end = True, token_type="INCREMENT"),
        192: State('=', 193), 193: State(DELIM_VAL['assignment_delim'], end = True, token_type="EQUAL_PLUS"),
    
    # Minus (-)
    194: State('-', [252, 195, 196, 198]), 195: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="MINUS"),
    196: State('-', 197), 197: State(DELIM_VAL['unary_delim'], end = True, token_type="DECREMENT"),
    198: State('=', 199), 199: State(DELIM_VAL['assignment_delim'], end = True, token_type="EQUAL_MINUS"),
    
    # Asterisk (*)
    200: State('*', [201, 202, 205]), 201: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="*"),
    202: State('*', 203), 203: State('*', 204), 204: State([']', *DELIM_VAL['space_delim']], end = True, token_type="FLEX_ASTERISK"),
    205: State('=', 206), 206: State(DELIM_VAL['assignment_delim'], end = True, token_type="EQUAL_ASTERISK"),
    
    # Slash (/)
    207: State('/', [209, 208]), 208: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="DIVIDE"),
    209: State('=', 210), 210: State(DELIM_VAL['assignment_delim'], end = True, token_type="EQUAL_DIVIDE"),
    
    # Modulo (%)
    211: State('%', 212), 212: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="MODULO"),
    
    # Greater than (>)
    213: State('>', [214, 215]), 214: State(DELIM_VAL['relational_delim'], end = True, token_type="GREATER_THAN"),
        215: State('=', 216), 216: State(DELIM_VAL['relational_delim'], end = True, token_type="GREATER_EQUAL"),
    
    # Lesser than (<)
    217: State('<', [218, 219]), 218: State(DELIM_VAL['relational_delim'], end = True, token_type="LESSER_THAN"),
        219: State('=', 220), 220: State(DELIM_VAL['relational_delim'], end = True, token_type="LESSER_EQUAL"), 
    
    # NOT (!)
    221: State('!', [222, 223]), 222: State(DELIM_VAL['not_delim'], end = True, token_type="NOT"),
    223: State('=', 224), 224: State(DELIM_VAL['relational_delim'], end = True, token_type="NOT_EQUAL"),
    
    # AND (&) 
    225: State('&', 226), 226: State('&', 227), 227: State(DELIM_VAL['logical_delim'], end = True, token_type="AND"),
    
    # OR (|)
    228: State('|', 229), 229: State('|', 230), 230: State(DELIM_VAL['logical_delim'], end = True, token_type="OR"),
    
    # Open Paren (
    231: State( '(', 232), 232: State(DELIM_VAL['opparen_delim'], end = True, token_type="OP_PAREN"),
    
    # Close Paren )
    233: State( ')', 234), 234: State(DELIM_VAL['clparen_delim'], end = True, token_type="CL_PAREN"),
    
    # Open Bracket [ 
    235: State( '[', 236), 236: State(DELIM_VAL['opbrackets_delim'], end = True, token_type="OP_BRACKETS"),
    
    # Close Bracket ]
    237: State( ']', end = True, token_type="CL_BRACKETS"), 
    # Deleted -> 238: State(DELIM_VAL['clbrackets_delim', ']'], end = True, token_type="CL_BRACKETS"),
    
    # Open Brace {    
    238: State( '{', 239), 239: State(DELIM_VAL['braces_delim'], end = True, token_type="OP_BRACES"),    
        
    # Close Brace }
    240: State( '}', end = True, token_type="CL_BRACES"),
    # Deleted -> 242: State(DELIM_VAL['braces_delim'], 
    
    # Dot Accessor (.)
    241: State('.', 242), 242: State(ATOMIC_VAL['alpha_small'], end = True, token_type="DOT_ACC"),

    # Comma (,)
    243: State( ',' , 244), 244: State(DELIM_VAL['comma_delim'], end = True, token_type="COMMA"),
    
    # Colon (:)
    245: State(':', 246), 246: State(DELIM_VAL['colon_delim'], end = True, token_type="COLON"),
    
    # Semicolon (;)
    247: State(';' , 248), 248: State(DELIM_VAL['semicolon_delim'], end = True, token_type="SEMICOLON"),
    
    # Newline (commented out cuz causing issues sa actual thingy)
    # 251: State('\n',  end = True, token_type="NEWLINE"), #ISSUES: CAUSING RECURSION
    
    # OLD Newline
    249: State('\n', end = True, token_type="NEWLINE"),
    
    
    # Literals
    # BEANLIT *positive number issues
    # status: messy in particular to state 253
    250: State([*ATOMIC_VAL['whole']], [251, 252, 270]), 251: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"),
        252: State(ATOMIC_VAL['whole'], [253, 254, 270]), 253: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"),
        254: State(ATOMIC_VAL['whole'], [255, 256, 270]), 255: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"),
        256: State(ATOMIC_VAL['whole'], [257, 258, 270]), 257: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        258: State(ATOMIC_VAL['whole'], [259, 260, 270]), 259: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        260: State(ATOMIC_VAL['whole'], [261, 262, 270]), 261: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        262: State(ATOMIC_VAL['whole'], [263, 264, 270]), 263: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        264: State(ATOMIC_VAL['whole'], [265, 266, 270]), 265: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        266: State(ATOMIC_VAL['whole'], [267, 268, 270]), 267: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        268: State(ATOMIC_VAL['whole'], [269, 270]), 269: State(DELIM_VAL['numeric_delim'], end = True, token_type = "BEANLIT"), 
        
        # DRIPLIT
        270: State('.' , 271),
            271: State(ATOMIC_VAL['whole'], [272, 273]), 272: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"), 
            273: State(ATOMIC_VAL['whole'], [274, 275]), 274: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"), 
            275: State(ATOMIC_VAL['whole'], [276, 277]), 276: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            277: State(ATOMIC_VAL['whole'], [278, 279]), 278: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            279: State(ATOMIC_VAL['whole'], [280, 281]), 280: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            281: State(ATOMIC_VAL['whole'], [282, 283]), 282: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            283: State(ATOMIC_VAL['whole'], [284, 285]), 284: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            285: State(ATOMIC_VAL['whole'], [286, 287]), 286: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            287: State(ATOMIC_VAL['whole'], [288, 289]), 288: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),
            289: State(ATOMIC_VAL['whole'], 290), 290: State(DELIM_VAL['numeric_delim'], end = True, token_type = "DRIPLIT"),

        # CHAR LITERAL (CHURROLIT)
        # Examples:  'a'  '\n'  '\t'
        291: State('\'', [295, 293, 292]),
            # Normal char (non-escape)
            292: State([*ATOMIC_VAL["text_content"]], 293),
            
            # closing single quote
            293: State('\'', 294), 

            # delimiter
            294: State([*DELIM_VAL["space_delim"], ',', '\n', ']'], end=True, token_type="CHURROLIT"),

            # Escape sequence
            295: State('\\', 296), 296: State(ATOMIC_VAL["escapeseq_let"], [293]),

            # Given '\j'
            # ' -> 0 to 294
            # '\ -> 294 to 298
            # '\' -> 298 to 299_1 end? error
            # '\'' -> 299_1 to 296

        
        # STRING LITERAL (BLENDLIT) AMBIGUITY
        # Examples:  "hello"  "he\nllo"  "mix\"ed"
        297: State('"', [301, 299, 298]),
            
            # Regular characters inside string                                                                                  
            298: State([*ATOMIC_VAL["text_content"], 
                        *ATOMIC_VAL["escapeseq_let"], 
                        *ATOMIC_VAL["safe_char"]], 
                        [301, 299, 298]), 
            
            # Closing quote
            299: State('"', 300),

                # Delimiter
                300: State(DELIM_VAL["string_delim"], end=True, token_type="BLENDLIT"),

            # Escape sequence
            301: State("\\", 298),



        # IDENTIFIERS (gotta limit to 15 characters lang with a starting small letter, and everything after can only be underscore or number)
        # Start with lowercase letter, can include digits or underscores
        302: State(ATOMIC_VAL["alpha_small"], [303, 304]), 
                303: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            304: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [305, 306]), 
                305: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            306: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [307, 308]), 
                307: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            308: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [309, 310]), 
                309: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            310: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [311, 312]), 
                311: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            312: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [313, 314]), # was 329 earlier, broke the id
                313: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            314: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [315, 316]), 
                315: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            316: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [317, 318]), 
                317: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            318: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [319, 320]), 
                319: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            320: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [321, 322]), 
                321: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            322: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [323, 324]), 
                323: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            324: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [325, 326]), 
                325: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            326: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [327, 328]), 
                327: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            328: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [329, 330]), 
                329: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
            330: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], 331), 
                331: State(DELIM_VAL['id_delim'], end=True, token_type="ID"),
        


        # SINGLE LINE COMMENT
        # Pattern: ~~ comment until newline
        # status: okay
        332: State('~', [333, 336]),
            333: State('~', 334),
            334: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL["escapeseq_let"]], [335, 334]),
            335: State('\n', end=True, token_type="SL_COMMENT"),

        # MULTI LINE COMMENT
        # Pattern: ~. comment content .~
        # status: ambiguity due to atomDelim
            336: State('.', 337),
            337: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL['sp_symbols'], *ATOMIC_VAL['escapeseq_let'], '\n'], [338, 337]),
                338: State('.', [339, 337]),
                339: State('~', 340),
                340: State([*DELIM_VAL['space_delim'], '\n'], end=True, token_type="ML_COMMENT")

}
