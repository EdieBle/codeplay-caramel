from .atomDelim import ATOMIC_VAL, DELIM_VAL 

class State:
    def __init__(self, chars: list[str], branches: list[int] = [], end = False, token_type=None):
        self.chars = [chars] if type(chars) is str else chars
        self.branches = [branches] if type(branches) is int else branches
        self.isEnd = end
        self.token_type = token_type

TRANSITIONS_DFA = {
    0: State('initial', [1, 31, 54, 69, 90, 98, 104, 108, 115, 119, 123, 129, 134, 147, 161, 175, 184, 188, 
                        194, 200, 207, 211, 213, 217, 221, 225, 228, 231, 233, 235, 237, 239, 241, 243, 
                        245, 247, 249, 251]),

    # Backroom, batter@, bean, blend, brewed
    1: State('b', [2, 16, 20, 25]), 2: State('a', [3, 10]), 3: State('c', 4), 4: State('k', 5), 5: State('r', 6), 6: State('o', 7), 7: State('o', 8), 8: State('m', 9), 9: State(DELIM_VAL['space_delim'], end = True, token_type="ACCESS_MOD"),
                                    10: State('t', 11), 11: State('t', 12), 12: State('e', 13), 13: State('r', 14), 14: State('@', 15), 15: State(DELIM_VAL['batter@_delim'], end = True, token_type="KEYWORD"),
        16: State('e', 17), 17: State('a', 18), 18: State('n', 19), 19: State(DELIM_VAL['space_delim'], end = True, token_type="DATA_TYPE"),
        20: State('l', 21), 21: State('e', 22), 22: State('n', 23), 23: State('d', 24), 24: State(DELIM_VAL['space_delim'], end = True, token_type="DATA_TYPE"),
        25: State('r', 26), 26: State('e', 27), 27: State('w', 28), 28: State('e', 29), 29: State('d', 30), 30: State(DELIM_VAL['space_delim'], end = True, token_type="KEYWORD"),
    
    # cafe, crema, churro, cold, crema, cup, decaf, drip
    31: State('c', [32, 36, 42, 46, 51]), 32: State('a', 33), 33: State('f', 34), 34: State('e', 35), 35: State(DELIM_VAL['space_delim'], end = True, token_type="ACCESS_MOD"),
        36: State('h', 37), 37: State('u', 38), 38: State('r', 39), 39: State('r', 40), 40: State('o', 41), 41: State(DELIM_VAL['space_delim'], end = True, token_type="DATA_TYPE"),
        42: State('o', 43), 43: State('l', 44), 44: State('d', 45), 45: State(DELIM_VAL['temp_delim'], end = True, token_type="KEYWORD"),
        46: State('r', 47), 47: State('e', 48), 48: State('m', 49), 49: State('a', 50), 50: State(DELIM_VAL['space_delim'], end = True, token_type="KEYWORD"),
        51: State('u', 52), 52: State('p', 53), 53: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),

    # decaf, drip
    54: State('d', [55, 60, 65]),
        55: State('e', [56,60]), 56: State('c', 57), 57: State('a', 58), 58: State('f', 59), 59: State(DELIM_VAL['space_delim'], end = True, token_type="KEYWORD"),
                    60: State('f', 61), 61: State('o', 62), 62: State('a', 63), 63: State('m', 64), 64: State(':', end = True, token_type="KEYWORD"),
        65: State('r', 66), 66: State('i', 67), 67: State('p', 68), 68: State(DELIM_VAL['space_delim'], end = True, token_type="DATA_TYPE"),

    # elifroth, elspress, empty
    69: State('e', [70, 85]),
        70: State('l', [71,78]), 71: State('i', 72), 72: State('f', 73), 73: State('r', 74), 74: State('o', 75), 75: State('t', 76), 76: State('h', 77), 77: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),
                    78: State('s', 79), 79: State('p', 80), 80: State('r', 81), 81: State('e', 82), 82: State('s', 83), 83: State('s', 84), 84: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="KEYWORD"),
        85: State('m', 86), 86: State('p', 87), 87: State('t', 88), 88: State('y', 89), 89: State(DELIM_VAL['space_delim'], end = True, token_type="KEYWORD"),

    # flavour
    90: State('f', 91), 91: State('l', 92), 92: State('a', 93), 93: State('v', 94), 94: State('o', 95), 95: State('u', 96), 96: State('r', 97), 97: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),

    # glaze, hot, ifbrew, mug, new, pour, refill?, snap, syrup, taste, whilehot
    98: State('g', 99), 99: State('l', 100), 100: State('a', 101), 101: State('z', 102), 102: State('e', 103), 103: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),
    104: State('h', 105), 105: State('o', 106), 106: State('t', 107), 107: State(DELIM_VAL['temp_delim'], end = True, token_type="KEYWORD"),
    108: State('i', 109), 109: State('f', 110), 110: State('b', 111), 111: State('r', 112), 112: State('e', 113), 113: State('w', 114), 114: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),
    115: State('m', 116), 116: State('u', 117), 117: State('g', 118), 118: State(DELIM_VAL['space_delim'], end = True, token_type="DATA_TYPE"),
    119: State('n', 120), 120: State('e', 121), 121: State('w', 122), 122: State(DELIM_VAL['space_delim'], end = True, token_type="KEYWORD"),
    123: State('o', 124), 124: State('r', 125), 125: State('d', 126), 126: State('e', 127), 127: State('r', 128), 128: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),
    
    # pour
    129: State('p', 130), 130: State('o', 131), 131: State('u', 132), 132: State('r', 133), 133: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),
    
    # recipe and refill?
    134: State('r', 135), 135: State('e', [136, 141]), 136: State('c', 137), 137: State('i', 138), 138: State('p', 139), 139: State('e', 140), 140: State(DELIM_VAL['space_delim'], end = True, token_type="KEYWORD"),
    141: State('f', 142), 142: State('i', 143), 143: State('l', 144), 144: State('l', 145), 145: State('?', 146), 146: State(DELIM_VAL['refill_delim'], end = True, token_type="KEYWORD"),
    
    # skip, snap, syrup
    147: State('s', [148, 152, 156]), 148: State('k', 149), 149: State('i', 150), 150: State('p', 151), 151: State(ATOMIC_VAL['newline'], end = True, token_type="KEYWORD"),
                    152: State('n', 153), 153: State('a', 154), 154: State('p', 155), 155: State(ATOMIC_VAL['newline'], end = True, token_type="KEYWORD"),
                    156: State('y', 157), 157: State('r', 158), 158: State('u', 159), 159: State('p', 160), 160: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),
    
    # taste, till, temp
    161: State('t', [162, 167, 171]), 162: State('a', 163), 163: State('s', 164), 164: State('t', 165), 165: State('e', 166), 166: State(DELIM_VAL['spacebraces_delim'], end = True, token_type="KEYWORD"),
                    167: State('i', 168), 168: State('l', 169), 169: State('l', 170), 170: State('.', end = True, token_type="KEYWORD"),
                    171: State ('e', 172), 172: State('m', 173), 173: State('p', 174), 174: State(DELIM_VAL['space_delim'], end = True, token_type="DATA_TYPE"),
    
    # whilehot
    175: State('w', 176), 176: State('h', 177), 177: State('i', 178), 178: State('l', 179), 179: State('e', 180), 180: State('h', 181), 181: State('o', 182), 182: State('t', 183), 183: State(DELIM_VAL['spaceparen_delim'], end = True, token_type="KEYWORD"),

    # Reserved Symbols
    # Equals (=)
    184: State('=', [185, 186]), 185: State(DELIM_VAL['assignment_delim'], end = True, token_type="EQUALS"),
    186: State('=', 187), 197: State(DELIM_VAL['relational_delim'], end = True, token_type="RELATIONAL_OP"),
    
    # Plus (+)
    188: State('+', [189, 190, 192]), 189: State(DELIM_VAL['plus_delim'], end = True, token_type="ARITHM_OP"),
    190: State('+', 191), 191: State(DELIM_VAL['unary_delim'], end = True, token_type="UNARY_OP"),
    192: State('=', 192), 193: State(DELIM_VAL['assignment_delim'], end = True, token_type="ASSIGN_OP"),
    
    # Minus (-)
    194: State('-', [195, 196, 198]), 195: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="ARITHM_OP"),
    196: State('-', 197), 197: State(DELIM_VAL['unary_delim'], end = True, token_type="UNARY_OP"),
    198: State('=', 199), 199: State(DELIM_VAL['assignment_delim'], end = True, token_type="ASSIGN_OP"),
    
    # Asterisk (*)
    200: State('*', [201, 202, 205]), 201: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="ARITHM_OP"),
    202: State('*', 203), 203: State('*', 204), 204: State(']', end = True, token_type="FLEXIBLE_ARRAY"),
    205: State('=', 206), 206: State(DELIM_VAL['assignment_delim'], end = True, token_type="ASSIGN_OP"),
    
    # Slash (/)
    207: State('/', 208), 208: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="ARITHM_OP"),
    209: State('=', 210), 210: State(DELIM_VAL['assignment_delim'], end = True, token_type="ASSIGN_OP"),
    
    # Modulo (%)
    211: State('%', 212), 212: State(DELIM_VAL['arithmetic_delim'], end = True, token_type="ARITHM_OP"),
    
    # Greater than (>)
    213: State('>', [214, 215]), 214: State(DELIM_VAL['relational_delim'], end = True, token_type="RELATIONAL_OP"),
    215: State('=', 216), 216: State(DELIM_VAL['relational_delim'], end = True, token_type="RELATIONAL_OP"),
    
    # Lesser than (<)
    217: State('<', [218, 219]), 218: State(DELIM_VAL['relational_delim'], end = True, token_type="RELATIONAL_OP"),
    219: State('=', 220), 220: State(DELIM_VAL['relational_delim'], end = True, token_type="RELATIONAL_OP"), 
    
    # NOT (!)
    221: State('!', [222, 223]), 222: State(DELIM_VAL['logical_delim'], end = True, token_type="LOGICAL_OP"),
    223: State('=', 224), 224: State(DELIM_VAL['relational_delim'], end = True, token_type="RELATIONAL_OP"),
    
    # AND (&) 
    225: State('&', 226), 226: State('&', 227), 227: State(DELIM_VAL['logical_delim'], end = True, token_type="LOGICAL_OP"),
    
    # OR (|)
    228: State('|', 229), 229: State('|', 230), 230: State(DELIM_VAL['logical_delim'], end = True, token_type="LOGICAL_OP"),
    
    # Open Paren (
    231: State( '(', 232), 232: State(DELIM_VAL['opparen_delim'], end = True, token_type="OPEN_PAREN"),
    
    # Close Paren )
    233: State( ')', 234), 234: State(DELIM_VAL['clparen_delim'], end = True, token_type="CLOSE_PAREN"),
    
    # Open Bracket [ 
    235: State( '[', 236), 236: State(DELIM_VAL['opbrackets_delim'], end = True, token_type="OPEN_BRACKET"),
    
    # Close Bracket ]
    237: State( ']', 238), 238: State(DELIM_VAL['clbrackets_delim'], end = True, token_type="CLOSE_BRACKET"),
    
    # Open Brace {    
    239: State( '{', 240), 240: State(DELIM_VAL['braces_delim'], end = True, token_type="OPEN_BRACE"),    
        
    # Close Brace }
    241: State( '}', 242), 242: State(DELIM_VAL['braces_delim'], end = True, token_type="CLOSE_BRACE"),
    
    # Dot Accessor (.)
    243: State('.', 244), 244: State(ATOMIC_VAL['alpha_small'], end = True, token_type="DOT_ACC"),

    # Comma (,)
    245: State( ',' , 246), 246: State(DELIM_VAL['comma_delim'], end = True, token_type="COMMA"),
    
    # Colon (:)
    247: State(':', 248), 248: State(DELIM_VAL['colon_delim'], end = True, token_type="COLON"),
    
    # Semicolon (;)
    249: State(';' , 250), 250: State(DELIM_VAL['semicolon_delim'], end = True, token_type="SEMICOLON"),
    
    # Newline
    251: State('\n', 251), 251: State(ATOMIC_VAL['newline'], end = True, token_type="NEWLINE"),
    
    # Literals

    # START - BEANLIT
    # 253: State('-', ' ', 254, ['whole']), 254: State('whole', [255, 256, 274]), # 255: State(DELIM_VAL['numeric_delim'], end = True),
    # 274: State('.' , 275),
        
    # 1ST DIGIT
    # 256: State('whole', [257, 258, 274]), 257: State(DELIM_VAL['numeric_delim'], end = True),
    # 274: State('.' , 275),
            
    # 2ND DIGIT
    # 258: State('whole', [259, 260, 274]), 259: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
            
    # 3RD DIGIT        
    # 260: State('whole', [261, 262, 274]), 261: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),

    # 4TH DIGIT        
    # 262: State('whole', [263, 264, 274]), 263: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275), 
    
    # 5TH DIGIT        
    # 264: State('whole', [265, 266, 274]), 265: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
    
    # 6TH DIGIT        
    # 266: State('whole', [267, 268, 274]), 267: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
    
    # 7TH DIGIT        
    # 268: State('whole', [269, 270, 274]), 269: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
    
    # 8TH DIGIT        
    # 270: State('whole', [271, 272, 274]), 271: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
    
    # 9TH DIGIT        
    # 270: State('whole', [271, 272, 274]), 271: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
    
    # 10TH DIGIT
    # 272: State('whole', [273, 274]), 273: State(DELIM_VAL['numeric_delim'], end = True), 
    # 274: State('.' , 275),
}

      # Churro literal
      #  295: State('\'', [296, 296_1, 299]), 296: State(ATOMIC_VAL['text_content'], 297), 297: State('\'', 298), 298: State(DELIM_VAL['space_delim'], end = True, token_type = "CHURROLIT"),
       #     299: State('\\', 296_1), 296_1: State(ATOMIC_VAL['escapeseq_let'], 297),


        # Blend literal
        #300: State('"', [300_1, 303]), 300_1: State(ATOMIC_VAL['text_content'], [300_1, 301, 303]), 301: State('"', 302), 302: State(DELIM_VAL['string_delim'], end = True, token_type = "BLENDLIT"),
         #           303: State('\\', 303_1), 
          #              303_1: State([*ATOMIC_VAL['escapeseq_let'], *ATOMIC_VAL['safe_char']], 300_1),   

"""
initial states: 
0 
1  - b
31 - c
54 - d
69 - e
90 - f
98 - g
104 - h
108 - i
115 - m
119 - n
123 - o
129 - p
134 - r
147 - s
161 - t
175 - w

# reserved symbols
184 - =
188 - +
194 -  -
200 - *
207 -  /
211 - %
213 - >
217 - <
221 - !
225 - & 
228 - |
231 - (
233 - )
235 - [
237 - ]
239 - {
241 - }
243 - .
245 - ,
247 - :
249 - ;
251 - linebreak

# Literals
253 <-- (-) or whole
274 <-- literals but for drip decimals doesnt go from state 0 though
295 <-- char
300 <-- string
304 <-- identifiers
333 <-- Comment




"""