from .atomDelim import ATOMIC_VAL, DELIM_VAL 

class State:
    def __init__(self, chars: list[str], branches: list[int] = [], end = False, token_type=None):
        self.chars = [chars] if type(chars) is str else chars
        self.branches = [branches] if type(branches) is int else branches
        self.isEnd = end
        self.token_type = token_type



TRANSITIONS_DFA = {
    0: State('initial', [1, 31, 58, 69, 90, 102, 108, 112, 119, 123, 127, 133, 140, 157, 179, 197, 
                        206, 210, 216, 222, 229, 233, 235, 239, 243, 247, 250, 253, 255, 
                        257, 259, 260, 262, 263, 265, 267, 269, 271, 272, 313, 319, 324, 354]),

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
    119: State('m', 120), 120: State('u', 121), 121: State('g', 122), 122: State(DELIM_VAL['space_delim'], end = True, token_type="mug"),
    123: State('n', 123), 124: State('e', 125), 125: State('w', 126), 126: State(DELIM_VAL['space_delim'], end = True, token_type="new"),
    127: State('o', 128), 128: State('r', 129), 129: State('d', 130), 130: State('e', 131), 131: State(132), 132: State('.', end = True, token_type="order"),
    
    # pour, pow
    133: State('p', 134), 134: State('o', [135,138]), 
                135: State('u', 136), 136: State('r', 137), 137: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="pour"),
                138: State('w', 139), 139: State('(', end = True, token_type="pow"),
    
    
    # rand, recipe and refill?
    140: State('r', [141,145]), 141: State('a', 142), 142: State('n', 143), 143: State('d', 144), 144: State('(', end = True, token_type="rand"),
        145: State('e', [146, 151]), 
            146: State('c', 147), 147: State('i', 148), 148: State('p', 149), 149: State('e', 150), 150: State(DELIM_VAL['space_delim'], end = True, token_type="recipe"),
            151: State('f', 152), 152: State('i', 153), 153: State('l', 154), 154: State('l', 155), 155: State('?', 156), 156: State([*DELIM_VAL['refill_delim'], "\n"], end = True, token_type="refill?"),
    
    # skip, snap, sqrt, syrup
    157: State('s', [158, 162, 166, 170, 174]), 
                    158: State('i', 159), 159: State('f', 160), 160: State('t', 161), 161: State('(', end = True, token_type="sift"),
                    162: State('k', 163), 163: State('i', 164), 164: State('p', 165), 165: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="skip"),
                    166: State('n', 167), 167: State('a', 168), 168: State('p', 169), 169: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="snap"),
                    170: State('q', 171), 171: State('r', 172), 172: State('t', 173), 173: State('(', end = True, token_type="sqrt"),
                    174: State('y', 175), 175: State('r', 176), 176: State('u', 177), 177: State('p', 178), 178: State(DELIM_VAL['space_delim'], end = True, token_type="syrup"),
    
    # taste, till, temp, type
    179: State('t', [180, 185, 189, 193]), 180: State('a', 181), 181: State('s', 182), 182: State('t', 183), 183: State('e', 184), 184: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="taste"),
                    185: State('i', 186), 186: State('l', 187), 187: State('l', 188), 188: State(':', end = True, token_type="till"),
                    189: State ('e', 190), 190: State('m', 191), 191: State('p', 192), 192: State(DELIM_VAL['space_delim'], end = True, token_type="temp"),
                    193: State('y', 194), 194: State('p', 195), 195: State('e', 196), 196: State('(', end = True, token_type="type"),
    
    # whilehot
    197: State('w', 198), 198: State('h', 199), 199: State('i', 200), 200: State('l', 201), 201: State('e', 202), 202: State('h', 203), 203: State('o', 204), 204: State('t', 205), 205: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="whilehot"),

    # Reserved Symbols
    # Equals (=)
    206: State('=', [207, 208]), 207: State(DELIM_VAL['assignment_delim'], end = True, token_type="="),
        208: State('=', 209), 209: State(DELIM_VAL['relational_delim'], end = True, token_type="=="),
    
    # Plus (+)
    210: State('+', [211, 212, 214]), 211: State(DELIM_VAL['plus_delim'], end = True, token_type="+"),
        212: State('+', 213), 213: State(DELIM_VAL['unary_delim'], end = True, token_type="++"),
        214: State('=', 215), 215: State(DELIM_VAL['assignment_delim'], end = True, token_type="+="),
    
    # Minus (-)
    216: State('-', [272, 217, 218, 220]), 217: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="-"), # 250 is the literals dont forget
        218: State('-', 219), 219: State(DELIM_VAL['unary_delim'], end = True, token_type="--"),
        220: State('=', 221), 221: State(DELIM_VAL['assignment_delim'], end = True, token_type="-="),
    
    # Asterisk (*)
    222: State('*', [223, 224, 227]), 223: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="*"),
        224: State('*', 225), 225: State('*', 226), 226: State([']', *DELIM_VAL['space_delim']], end = True, token_type="***"),
        227: State('=', 228), 228: State(DELIM_VAL['assignment_delim'], end = True, token_type="*="),
    
    # Slash (/)
    229: State('/', [230, 231]), 230: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="/"),
        231: State('=', 232), 232: State(DELIM_VAL['assignment_delim'], end = True, token_type="/="),
    
    # Modulo (%)
    233: State('%', 234), 234: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="%"),
    
    # Greater than (>)
    235: State('>', [236, 237]), 236: State(DELIM_VAL['relational_delim'], end = True, token_type=">"),
        237: State('=', 238), 238: State(DELIM_VAL['relational_delim'], end = True, token_type=">="),
    
    # Lesser than (<)
    239: State('<', [240, 241]), 240: State(DELIM_VAL['relational_delim'], end = True, token_type="<"),
        241: State('=', 242), 242: State(DELIM_VAL['relational_delim'], end = True, token_type="<="), 
    
    # NOT (!)
    243: State('!', [244, 245]), 244: State(DELIM_VAL['not_delim'], end = True, token_type="!"),
        245: State('=', 246), 246: State(DELIM_VAL['relational_delim'], end = True, token_type="!="),
    
    # AND (&) 
    247: State('&', 248), 248: State('&', 249), 249: State(DELIM_VAL['logical_delim'], end = True, token_type="&&"),
    
    # OR (|)
    250: State('|', 251), 251: State('|', 252), 252: State(DELIM_VAL['logical_delim'], end = True, token_type="||"),
    
    # Open Paren (
    253: State( '(', 254), 254: State(DELIM_VAL['opparen_delim'], end = True, token_type="("),
    
    # Close Paren )
    255: State( ')', 256), 256: State(DELIM_VAL['clparen_delim'], end = True, token_type=")"),
    
    # Open Bracket [ 
    257: State( '[', 258), 258: State(DELIM_VAL['opbrackets_delim'], end = True, token_type="["),
    
    # Close Bracket ]
    259: State( ']', end = True, token_type="]"), 
    # Deleted -> 238: State(DELIM_VAL['clbrackets_delim', ']'], end = True, token_type="]"),
    
    # Open Brace {    
    260: State( '{', 261), 261: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="{"),    
        
    # Close Brace }
    262: State( '}', end = True, token_type="}"),
    # Deleted -> 242: State(DELIM_VAL['braces_delim'], 
    
    # Dot Accessor (.)
    263: State('.', 264), 264: State(ATOMIC_VAL['alpha_small'], end = True, token_type="."),

    # Comma (,)
    265: State( ',' , 266), 266: State(DELIM_VAL['comma_delim'], end = True, token_type=","),
    
    # Colon (:)
    267: State(':', 268), 268: State(DELIM_VAL['colon_delim'], end = True, token_type=":"),
    
    # Semicolon (;)
    269: State(';' , 270), 270: State(DELIM_VAL['semicolon_delim'], end = True, token_type=";"),
    
    # Newline (commented out cuz causing issues sa actual thingy)
    # 251: State('\n',  end = True, token_type="NEWLINE"), #ISSUES: CAUSING RECURSION
    
    # OLD Newline
    271: State('\n', end = True, token_type="newline"),
    
    
    # Literals
    # BEANLIT *positive number issues
    # status: messy in particular to state 253
    272: State([*ATOMIC_VAL['whole']], [273, 274, 292]), 273: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        274: State(ATOMIC_VAL['whole'], [275, 276, 292]), 275: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        276: State(ATOMIC_VAL['whole'], [277, 278, 292]), 277: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        278: State(ATOMIC_VAL['whole'], [279, 280, 292]), 279: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        280: State(ATOMIC_VAL['whole'], [281, 282, 292]), 281: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        282: State(ATOMIC_VAL['whole'], [283, 284, 292]), 283: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        284: State(ATOMIC_VAL['whole'], [285, 286, 292]), 285: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        286: State(ATOMIC_VAL['whole'], [287, 288, 292]), 287: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        288: State(ATOMIC_VAL['whole'], [289, 290, 292]), 289: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        290: State(ATOMIC_VAL['whole'], [291, 292]), 291: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        
        # DRIPLIT
        292: State('.' , 293),
            293: State(ATOMIC_VAL['whole'], [294, 295]), 294: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"), 
            295: State(ATOMIC_VAL['whole'], [296, 297]), 296: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"), 
            297: State(ATOMIC_VAL['whole'], [298, 299]), 298: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            299: State(ATOMIC_VAL['whole'], [300, 301]), 300: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            301: State(ATOMIC_VAL['whole'], [302, 303]), 302: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            303: State(ATOMIC_VAL['whole'], [304, 305]), 304: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            305: State(ATOMIC_VAL['whole'], [306, 307]), 306: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            307: State(ATOMIC_VAL['whole'], [308, 309]), 308: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            309: State(ATOMIC_VAL['whole'], [310, 311]), 310: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            311: State(ATOMIC_VAL['whole'], 312), 312: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),

        # CHAR LITERAL (CHURROLIT)
        # Examples:  'a'  '\n'  '\t'
        313: State('\'', [317, 315, 314]),
            # Normal char (non-escape)
            314: State([*ATOMIC_VAL["text_content"]], 315),
            
            # closing single quote
            315: State('\'', 316), 

            # delimiter
            316: State([*DELIM_VAL["churro_delim"]], end=True, token_type="churrolit"),

            # Escape sequence
            317: State('\\', 318), 318: State(ATOMIC_VAL["escapeseq_let"], [322]),

            # Given '\j'
            # ' -> 0 to 294
            # '\ -> 294 to 298
            # '\' -> 298 to 299_1 end? error
            # '\'' -> 299_1 to 296

        
        # STRING LITERAL (BLENDLIT) AMBIGUITY
        # Examples:  "hello"  "he\nllo"  "mix\"ed"
        319: State('"', [323, 321, 320]),
            
            # Regular characters inside string                                                                                  
            320: State([*ATOMIC_VAL["text_content"], 
                        *ATOMIC_VAL["escapeseq_let"], 
                        *ATOMIC_VAL["safe_char"]], 
                        [323, 321, 320]), 
            
            # Closing quote
            321: State('"', 322),
                # Delimiter
                322: State(DELIM_VAL["string_delim"], end=True, token_type="blendlit"),

            # Escape sequence
            323: State("\\", 320),



        # IDENTIFIERS (gotta limit to 15 characters lang with a starting small letter, and everything after can only be underscore or number)
        # Start with lowercase letter, can include digits or underscores
        324: State(ATOMIC_VAL["alpha_small"], [325, 326]), 
                325: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            326: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [327, 328]), 
                327: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            328: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [329, 330]), 
                329: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            330: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [331, 332]), 
                331: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            332: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [333, 334]), 
                333: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            334: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [335, 336]), # was 329 earlier, broke the id
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
            348: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [349, 350]), 
                349: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            350: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [351, 352]), 
                351: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            352: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], 353), 
                353: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
        


        # SINGLE LINE COMMENT
        # Pattern: ~~ comment until newline
        # status: okay
        354: State('~', [355, 358]),
            355: State('~', 356),
            356: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL["escapeseq_let"]], [357, 356]),
            357: State('\n', end=True, token_type="sl_comment"),

        # MULTI LINE COMMENT
        # Pattern: ~. comment content .~
        # status: ambiguity due to atomDelim
            358: State('.', 359),
            359: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL['sp_symbols'], *ATOMIC_VAL['escapeseq_let'], '\n'], [360, 359]),
                360: State('.', [361, 359]),
                361: State('~', 362),
                362: State([*DELIM_VAL['space_delim'], '\n'], end=True, token_type="ml_comment")

}
