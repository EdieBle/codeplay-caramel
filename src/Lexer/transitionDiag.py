from .atomDelim import ATOMIC_VAL, DELIM_VAL 

class State:
    def __init__(self, chars: list[str], branches: list[int] = [], end = False, token_type=None):
        self.chars = [chars] if type(chars) is str else chars
        self.branches = [branches] if type(branches) is int else branches
        self.isEnd = end
        self.token_type = token_type



TRANSITIONS_DFA = {
    0: State('initial', [1, 31, 58, 69, 90, 102, 108, 119, 126, 130, 134, 140, 147, 164, 186, 204, 
                        213, 217, 223, 229, 236, 240, 242, 246, 250, 254, 257, 260, 262, 
                        264, 266, 267, 269, 270, 272, 274, 276, 278, 279, 320, 326, 331, 361]),

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

    # decaf, drip
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
    119: State('i', 120), 120: State('f', 121), 121: State('b', 122), 122: State('r', 123), 123: State('e', 124), 124: State('w', 125), 125: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="ifbrew"),
    126: State('m', 127), 127: State('u', 128), 128: State('g', 129), 129: State(DELIM_VAL['space_delim'], end = True, token_type="mug"),
    130: State('n', 131), 131: State('e', 132), 132: State('w', 133), 133: State(DELIM_VAL['space_delim'], end = True, token_type="new"),
    134: State('o', 135), 135: State('r', 136), 136: State('d', 137), 137: State('e', 138), 138: State('r', 139), 139: State('.', end = True, token_type="order"),
    
    # pour, pow
    140: State('p', 141), 141: State('o', [142,145]), 
                142: State('u', 143), 143: State('r', 144), 144: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="pour"),
                145: State('w', 146), 146: State('(', end = True, token_type="pow"),
    
    
    # rand, recipe and refill?
    147: State('r', [148,152]), 148: State('a', 149), 149: State('n', 150), 150: State('d', 151), 151: State('(', end = True, token_type="rand"),
        152: State('e', [153, 158]), 
            153: State('c', 154), 154: State('i', 155), 155: State('p', 156), 156: State('e', 157), 157: State(DELIM_VAL['space_delim'], end = True, token_type="recipe"),
            158: State('f', 159), 159: State('i', 160), 160: State('l', 161), 161: State('l', 162), 162: State('?', 163), 163: State([*DELIM_VAL['refill_delim'], "\n"], end = True, token_type="refill?"),
    
    # skip, snap, sqrt, syrup
    164: State('s', [165, 169, 173, 177, 181]), 
                    165: State('i', 166), 166: State('f', 167), 167: State('t', 168), 168: State('(', end = True, token_type="sift"),
                    169: State('k', 170), 170: State('i', 171), 171: State('p', 172), 172: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="skip"),
                    173: State('n', 174), 174: State('a', 175), 175: State('p', 176), 176: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="snap"),
                    177: State('q', 178), 178: State('r', 179), 179: State('t', 180), 180: State('(', end = True, token_type="sqrt"),
                    181: State('y', 182), 182: State('r', 183), 183: State('u', 184), 184: State('p', 185), 185: State(DELIM_VAL['space_delim'], end = True, token_type="syrup"),
    
    # taste, till, temp, type
    186: State('t', [187, 192, 196, 200]), 187: State('a', 188), 188: State('s', 189), 189: State('t', 190), 190: State('e', 191), 191: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="taste"),
                    192: State('i', 193), 193: State('l', 194), 194: State('l', 195), 195: State(':', end = True, token_type="till"),
                    196: State ('e', 197), 197: State('m', 198), 198: State('p', 199), 199: State(DELIM_VAL['space_delim'], end = True, token_type="temp"),
                    200: State('y', 201), 201: State('p', 202), 202: State('e', 203), 203: State('(', end = True, token_type="type"),
    
    # whilehot
    204: State('w', 205), 205: State('h', 206), 206: State('i', 207), 207: State('l', 208), 208: State('e', 209), 209: State('h', 210), 210: State('o', 211), 211: State('t', 212), 212: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="whilehot"),

    # Reserved Symbols
    # Equals (=)
    213: State('=', [214, 215]), 214: State(DELIM_VAL['assignment_delim'], end = True, token_type="="),
        215: State('=', 216), 216: State(DELIM_VAL['relational_delim'], end = True, token_type="=="),
    
    # Plus (+)
    217: State('+', [218, 219, 221]), 218: State(DELIM_VAL['plus_delim'], end = True, token_type="+"),
        219: State('+', 220), 220: State(DELIM_VAL['unary_delim'], end = True, token_type="++"),
        221: State('=', 222), 222: State(DELIM_VAL['assignment_delim'], end = True, token_type="+="),
    
    # Minus (-)
    223: State('-', [279, 224, 225, 227]), 224: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="-"), # 250 is the literals dont forget
        225: State('-', 226), 226: State(DELIM_VAL['unary_delim'], end = True, token_type="--"),
        227: State('=', 228), 228: State(DELIM_VAL['assignment_delim'], end = True, token_type="-="),
    
    # Asterisk (*)
    229: State('*', [230, 231, 234]), 230: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="*"),
        231: State('*', 232), 232: State('*', 233), 233: State([']', *DELIM_VAL['space_delim']], end = True, token_type="***"),
        234: State('=', 235), 235: State(DELIM_VAL['assignment_delim'], end = True, token_type="*="),
    
    # Slash (/)
    236: State('/', [237, 238]), 237: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="/"),
        238: State('=', 239), 239: State(DELIM_VAL['assignment_delim'], end = True, token_type="/="),
    
    # Modulo (%)
    240: State('%', 241), 241: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="%"),
    
    # Greater than (>)
    242: State('>', [243, 244]), 243: State(DELIM_VAL['relational_delim'], end = True, token_type=">"),
        244: State('=', 245), 245: State(DELIM_VAL['relational_delim'], end = True, token_type=">="),
    
    # Lesser than (<)
    246: State('<', [247, 248]), 247: State(DELIM_VAL['relational_delim'], end = True, token_type="<"),
        248: State('=', 249), 249: State(DELIM_VAL['relational_delim'], end = True, token_type="<="), 
    
    # NOT (!)
    250: State('!', [251, 252]), 251: State(DELIM_VAL['not_delim'], end = True, token_type="!"),
        252: State('=', 253), 253: State(DELIM_VAL['relational_delim'], end = True, token_type="!="),
    
    # AND (&) 
    254: State('&', 255), 255: State('&', 256), 256: State(DELIM_VAL['logical_delim'], end = True, token_type="&&"),
    
    # OR (|)
    257: State('|', 258), 258: State('|', 259), 259: State(DELIM_VAL['logical_delim'], end = True, token_type="||"),
    
    # Open Paren (
    260: State( '(', 261), 261: State(DELIM_VAL['opparen_delim'], end = True, token_type="("),
    
    # Close Paren )
    262: State( ')', 263), 263: State(DELIM_VAL['clparen_delim'], end = True, token_type=")"),
    
    # Open Bracket [ 
    264: State( '[', 265), 265: State(DELIM_VAL['opbrackets_delim'], end = True, token_type="["),
    
    # Close Bracket ]
    266: State( ']', end = True, token_type="]"), 
    # Deleted -> 238: State(DELIM_VAL['clbrackets_delim', ']'], end = True, token_type="]"),
    
    # Open Brace {    
    267: State( '{', 268), 268: State(ATOMIC_VAL['spacenew_delim'], end = True, token_type="{"),    
        
    # Close Brace }
    269: State( '}', end = True, token_type="}"),
    # Deleted -> 242: State(DELIM_VAL['braces_delim'], 
    
    # Dot Accessor (.)
    270: State('.', 271), 271: State(ATOMIC_VAL['alpha_small'], end = True, token_type="."),

    # Comma (,)
    272: State( ',' , 273), 273: State(DELIM_VAL['comma_delim'], end = True, token_type=","),
    
    # Colon (:)
    274: State(':', 275), 275: State(DELIM_VAL['colon_delim'], end = True, token_type=":"),
    
    # Semicolon (;)
    276: State(';' , 277), 277: State(DELIM_VAL['semicolon_delim'], end = True, token_type=";"),
    
    # Newline (commented out cuz causing issues sa actual thingy)
    # 251: State('\n',  end = True, token_type="NEWLINE"), #ISSUES: CAUSING RECURSION
    
    # OLD Newline
    278: State('\n', end = True, token_type="newline"),
    
    
    # Literals
    # BEANLIT *positive number issues
    # status: messy in particular to state 253
    279: State([*ATOMIC_VAL['whole']], [280, 281, 299]), 280: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        281: State(ATOMIC_VAL['whole'], [282, 283, 299]), 282: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        283: State(ATOMIC_VAL['whole'], [284, 285, 299]), 284: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"),
        285: State(ATOMIC_VAL['whole'], [286, 287, 299]), 286: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        287: State(ATOMIC_VAL['whole'], [288, 289, 299]), 288: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        289: State(ATOMIC_VAL['whole'], [290, 291, 299]), 290: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        291: State(ATOMIC_VAL['whole'], [292, 293, 299]), 292: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        293: State(ATOMIC_VAL['whole'], [294, 295, 299]), 294: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        295: State(ATOMIC_VAL['whole'], [296, 297, 299]), 296: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        297: State(ATOMIC_VAL['whole'], [298, 299]), 298: State(DELIM_VAL['numeric_delim'], end = True, token_type = "beanlit"), 
        
        # DRIPLIT
        299: State('.' , 300),
            300: State(ATOMIC_VAL['whole'], [301, 302]), 301: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"), 
            302: State(ATOMIC_VAL['whole'], [303, 304]), 303: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"), 
            304: State(ATOMIC_VAL['whole'], [305, 306]), 305: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            306: State(ATOMIC_VAL['whole'], [307, 308]), 307: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            308: State(ATOMIC_VAL['whole'], [309, 310]), 309: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            310: State(ATOMIC_VAL['whole'], [311, 312]), 311: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            312: State(ATOMIC_VAL['whole'], [313, 314]), 313: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            314: State(ATOMIC_VAL['whole'], [315, 316]), 315: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            316: State(ATOMIC_VAL['whole'], [317, 318]), 317: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),
            318: State(ATOMIC_VAL['whole'], 319), 319: State(DELIM_VAL['numeric_delim'], end = True, token_type = "driplit"),

        # CHAR LITERAL (CHURROLIT)
        # Examples:  'a'  '\n'  '\t'
        320: State('\'', [324, 322, 321]),
            # Normal char (non-escape)
            321: State([*ATOMIC_VAL["text_content"]], 322),
            
            # closing single quote
            322: State('\'', 323), 

            # delimiter
            323: State([*DELIM_VAL["churro_delim"]], end=True, token_type="churrolit"),

            # Escape sequence
            324: State('\\', 325), 325: State(ATOMIC_VAL["escapeseq_let"], [322]),

            # Given '\j'
            # ' -> 0 to 294
            # '\ -> 294 to 298
            # '\' -> 298 to 299_1 end? error
            # '\'' -> 299_1 to 296

        
        # STRING LITERAL (BLENDLIT) AMBIGUITY
        # Examples:  "hello"  "he\nllo"  "mix\"ed"
        326: State('"', [330, 328, 327]),
            
            # Regular characters inside string                                                                                  
            327: State([*ATOMIC_VAL["text_content"], 
                        *ATOMIC_VAL["escapeseq_let"], 
                        *ATOMIC_VAL["safe_char"]], 
                        [330, 328, 327]), 
            
            # Closing quote
            328: State('"', 329),

                # Delimiter
                329: State(DELIM_VAL["string_delim"], end=True, token_type="blendlit"),

            # Escape sequence
            330: State("\\", 327),



        # IDENTIFIERS (gotta limit to 15 characters lang with a starting small letter, and everything after can only be underscore or number)
        # Start with lowercase letter, can include digits or underscores
        331: State(ATOMIC_VAL["alpha_small"], [332, 333]), 
                332: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            333: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [334, 335]), 
                334: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            335: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [336, 337]), 
                336: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            337: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [338, 339]), 
                338: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            339: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [340, 341]), 
                340: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            341: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [342, 343]), # was 329 earlier, broke the id
                342: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            343: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [344, 345]), 
                344: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            345: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [346, 347]), 
                346: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            347: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [348, 349]), 
                348: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            349: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [350, 351]), 
                350: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            351: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [352, 353]), 
                352: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            353: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [354, 355]), 
                354: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            355: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [356, 357]), 
                356: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            357: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], [358, 359]), 
                358: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
            359: State([*ATOMIC_VAL["alpha_small"], *ATOMIC_VAL["whole"], "_"], 360), 
                360: State(DELIM_VAL['id_delim'], end=True, token_type="id"),
        


        # SINGLE LINE COMMENT
        # Pattern: ~~ comment until newline
        # status: okay
        361: State('~', [362, 365]),
            362: State('~', 363),
            363: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL["escapeseq_let"]], [364, 363]),
            364: State('\n', end=True, token_type="sl_comment"),

        # MULTI LINE COMMENT
        # Pattern: ~. comment content .~
        # status: ambiguity due to atomDelim
            365: State('.', 366),
            366: State([*ATOMIC_VAL['text_content'], *ATOMIC_VAL['sp_symbols'], *ATOMIC_VAL['escapeseq_let'], '\n'], [367, 366]),
                367: State('.', [368, 366]),
                368: State('~', 369),
                369: State([*DELIM_VAL['space_delim'], '\n'], end=True, token_type="ml_comment")

}
