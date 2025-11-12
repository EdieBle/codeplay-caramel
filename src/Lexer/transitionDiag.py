from atomDelim import ATOMIC_VAL, DELIM_VAL 

class State:
    def __init__(self, chars: list[str], branches: list[int] = [], end = False):
        self.chars = [chars] if type(chars) is str else chars
        self.branches = [branches] if type(branches) is int else branches
        self.isEnd = end

TRANSITIONS_DFA = {
    0: State('initial', [1, 31, 54, 69, 90, 98, 104, 108, 115, 119, 123, 129, 134, 147, 161, 175]),

    # Backroom, batter@, bean, blend, brewed
    1: State('b', [16, 20, 25]), 2: State('a', [3, 10]), 3: State('c', 4), 4: State('k', 5), 5: State('r', 6), 6: State('o', 7), 7: State('o', 8), 8: State('m', 9), 9: State(DELIM_VAL['space_delim'], end = True),
                                    10: State('t', 11), 11: State('t', 12), 12: State('e', 13), 13: State('r', 14), 14: State('@', 15), 15: State(DELIM_VAL['batter@_delim'], end = True),
        16: State('e', 17), 17: State('a', 18), 18: State('n', 19), 19: State(DELIM_VAL['space_delim'], end = True),
        20: State('l', 21), 21: State('e', 22), 22: State('n', 23), 23: State('d', 24), 24: State(DELIM_VAL['space_delim'], end = True),
        25: State('r', 26), 26: State('e', 27), 27: State('w', 28), 28: State('e', 29), 29: State('d', 30), 30: State(DELIM_VAL['space_delim'], end = True),
    
    # crema, churro, cold, crema, cup, decaf, drip
    31: State('c', [32, 36, 42, 46, 51]),
        32: State('a', 33), 33: State('f', 34), 34: State(DELIM_VAL['space_delim'], end = True),
        36: State('h', 37), 37: State('u', 38), 38: State('r', 39), 39: State('r', 40), 40: State('o', 41), 41: State(DELIM_VAL['space_delim'], end = True),
        42: State('o', 43), 43: State('l', 44), 44: State('d', 45), 45: State(DELIM_VAL['temp_delim'], end = True),
        46: State('r', 47), 47: State('e', 48), 48: State('m', 49), 49: State('a', 50), 50: State(DELIM_VAL['space_delim'], end = True),
        51: State('u', 52), 52: State('p', 53), 53: State(DELIM_VAL['spaceparen_delim'], end = True),

    # decaf, drip
    54: State('d', [55, 60, 65]),
        55: State('e', 56), 56: State('c', 57), 57: State('a', 58), 58: State('f', 59), 59: State(DELIM_VAL['space_delim'], end = True),
        60: State('r', 61), 61: State('i', 62), 62: State('p', 63), 63: State(DELIM_VAL['space_delim'], end = True),
        65: State('r', 66), 66: State('e', 67), 67: State(DELIM_VAL['space_delim'], end = True),

    # elifroth, elspress, empty
    69: State('e', [70, 85]),
        70: State('l', [71,78]), 71: State('i', 72), 72: State('f', 73), 73: State('r', 74), 74: State('o', 75), 75: State('t', 76), 76: State('h', 77), 77: State(DELIM_VAL['spaceparen_delim'], end = True),
                    78: State('s', 79), 79: State('p', 80), 80: State('r', 81), 81: State('e', 82), 82: State('s', 83), 83: State('s', 84), 84: State(DELIM_VAL['spacebraces_delim'], end = True),
        85: State('m', 86), 86: State('p', 87), 87: State('t', 88), 88: State('y', 89), 89: State(DELIM_VAL['space_delim'], end = True),

    # flavour
    90: State('f', 91), 91: State('l', 92), 92: State('a', 93), 93: State('v', 94), 94: State('o', 95), 95: State('u', 96), 96: State('r', 97), 97: State(DELIM_VAL['spaceparen_delim'], end = True),

    # glaze, hot, ifbrew, mug, new, pour, refill?, snap, syrup, taste, whilehot
    98: State('g', 99), 99: State('l', 100), 100: State('a', 101), 101: State('z', 102), 102: State('e', 103), 103: State(DELIM_VAL['spaceparen_delim'], end = True),
    104: State('h', 105), 105: State('o', 106), 106: State('t', 107), 107: State(DELIM_VAL['temp_delim'], end = True),
    108: State('i', 109), 109: State('f', 110), 110: State('b', 111), 111: State('r', 112), 112: State('e', 113), 113: State('w', 114), 114: State(DELIM_VAL['spaceparen_delim'], end = True),
    115: State('m', 116), 116: State('u', 117), 117: State('g', 118), 118: State(DELIM_VAL['space_delim'], end = True),
    119: State('n', 120), 120: State('e', 121), 121: State('w', 122), 122: State(DELIM_VAL['space_delim'], end = True),
    123: State('o', 124), 124: State('r', 125), 125: State('d', 126), 126: State('e', 127), 127: State('r', 128), 128: State(DELIM_VAL['spaceparen_delim'], end = True)
    
    # pour
    #129: State('p', 130), 130: State('o', 131), 131: State('u', 132), 132: State('r', 133), 133: State(DELIM_VAL['spaceparen_delim'], end = True),
    
    # recipe and refill?
    #134: State('r', 135), 135: State('e', [136, 141]), 136: State('c', 137), 137: State('i', 138), 138: State('p', 139), 139: State('e', 140), 140: State(DELIM_VAL['space_delim'], end = True),
    #141: State('f', 142), 142: State('i', 143), 143: State('l', 144), 144: State('l', 145), 145: State('?', 146), 146: State(DELIM_VAL['refill_delim'], end = True),
    
    # skip, snap, syrup
    #147: State('s', [148, 152, 156]), 148: State('k', 149), 149: State('i', 150), 150: State('p', 151), 151: State(DELIM_VAL['newline'], end = True),
                    # 152: State('n', 153), 153: State('a', 154), 154: State('p', 155), 155: State(DELIM_VAL['newline'], end = True),
                    # 156: State('y', 157), 157: State('r', 158), 158: State('u', 159), 159: State('p', 160), 160: State(DELIM_VAL['spaceparen_delim'], end = True),
    
    # taste, till, temp
    #161: State('t', [162, 167, 171]), 162: State('a', 163), 163: State('s', 164), 164: State('t', 165), 165: State('e', 166), 166: State(DELIM_VAL['spacebraces_delim'], end = True),
                    # 167: State('i', 168), 168: State('l', 169), 169: State('l', 170), 170: State(DELIM_VAL['.'], end = True),
                    # 171: State ('e', 172), 172: State('m', 173), 173: State('p', 174), 174: State(DELIM_VAL['space_delim'], end = True),
    
    # whilehot
    #175: State('w', 176), 176: State('h', 177), 177: State('i', 178), 178: State('l', 179), 179: State('e', 180), 180: State('h', 181), 181: State('o', 182), 182: State('t', 183), 183: State(DELIM_VAL['spaceparen_delim'], end = True),

    # Reserved Symbols
    # Equals (=)
    # 184: State('=', [185, 186]), 185: State(DELIM_VAL['assignment_delim'], end = True),
    # 186: State('=', 187), 197: State(DELIM_VAL['relational_delim'], end = True),
    
    # Plus (+)
    # 188: State('+', [189, 190, 192]), 189: State(DELIM_VAL['plus_delim'], end = True),
    # 190: State('+', 191), 191: State(DELIM_VAL['unary_delim'], end = True),
    # 192: State('=', 192), 193: State(DELIM_VAL['assignment_delim'], end = True),
    
    # Minus (-)
    # 194: State('-', [195, 196, 198]), 195: State(DELIM_VAL['arithmetic_delim'], end = True),
    # 196: State('-', 197), 197: State(DELIM_VAL['unary_delim'], end = True),
    # 198: State('=', 199), 199: State(DELIM_VAL['assignment_delim', end = True),
    
    # Asterisk (*)
    # 200: State('*', [201, 202, 205]), 201: State(DELIM_VAL['arithmetic_delim'], end = True)
    # 202: State('*', 203), 203: State('*', 204), 204: State(DELIM_VAL['wait']
    
    # Slash (/)
    
    
    # Modulo (%)
    
    
    # Greater than (>)
    
    
    # NOT (!)
    
    
    # AND (&) 
    
    
    # OR (|)
    
    
    
    # Open Paren (
        
    
    
    # Close Paren )
    
    
    # Open Bracket [ 
    
    
    
    # Close Bracket ]
    
    
    
    # Open Brace {
    
        
        
    # Close Brace }
    
    
    # Dot Accessor (.)



    # Comma (,)
    
    
    
    # Colon (:)
    
    
    
    # Semicolon (;)
    
    
    
    # Newline
    
    
    
}




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