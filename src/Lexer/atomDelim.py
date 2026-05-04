# Regular Definition (includes the Delimiters and Atomic values)
"""
atomDelim.py is where we derive the regular definition and the delimiters of our language. 
Technically, we are using python's dictionary, where it uses a pair of {key:value} to store data, in this case our regdef.
Every key is unique and acts as an index to its associated value. We have created three (3) dictionaries to define.

    1. ATOMIC_VAL - Character groups that are defined as sets for the DFA to reference instead of manually encoding it.
    2. DELIM_VAL - This is where our DELIMITERES are defined.
    3. KEYWORDS_TABLE - This is the masterlist of our RESERVED KEYWORDS.
"""

""" Set of grouped characters that the DFA transition states used to reference instead of hardcoding it."""
ATOMIC_VAL = {
    # Atoms
    "whole": ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'],                            # Whole Numbers
    "alpha_cap": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',          # Capital Letters
                  'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'],     
    "alpha_small": ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',        # Small Letters
                    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'],   
    "sp_symbols": ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+',    # Special symbols
                   '[', ']', '{', '}', '/', '|', ':', ';', '<', '>', '~', '?', ',', 
                   '.', '—', '`'], 
                                                                    
    "newline": ['\n'],
    "space_delim": [' ', '\t'],
    "spacenew_delim": [' ', '\t', '\n'],    # Space and newline combination

    # escape sequence letters
    "escapeseq_let": ['t', 'n', '\'', '\\', '"'],

    # Operators
    "arithmetic_op": ['+', '-', '*', '/', '%'],
    "assignment_op": ['='],
    "logical_op": ['!', '&', '|'],
    "relational_op": ['>', '<', '=', '!'],
    "unary_op": ['+', '-'],

    # ASCII values
    'ascii': {chr(i) for i in range(255)}
}


# Values usually acceptable for text content and a safe char that limits
ATOMIC_VAL["text_content"] = list(set(
    ATOMIC_VAL["space_delim"] + 
    ATOMIC_VAL["whole"] +
    ATOMIC_VAL["alpha_small"] +
    ATOMIC_VAL["alpha_cap"] +
    ATOMIC_VAL["sp_symbols"]
))

# safe characters for text that dont really include the escapeseq_let set
ATOMIC_VAL["safe_char"] = list(set(
    ATOMIC_VAL["space_delim"] +
    ATOMIC_VAL["whole"] +
    ATOMIC_VAL["sp_symbols"] +
    ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z'] +
    ATOMIC_VAL["alpha_cap"]
))

# unpacking the dictionary for the delimiter value dictionary below. These variables will be used to reference the set in our DFA transition states
whole = ATOMIC_VAL["whole"]
alpha_cap = ATOMIC_VAL["alpha_cap"]
alpha_small = ATOMIC_VAL["alpha_small"]
sp_symbols = ATOMIC_VAL["sp_symbols"]
space_delim = ATOMIC_VAL["space_delim"]
spacenew_delim = ATOMIC_VAL["spacenew_delim"]
newline = ATOMIC_VAL["newline"]
arithmetic_op = ATOMIC_VAL["arithmetic_op"]
assignment_op = ATOMIC_VAL["assignment_op"]
logical_op = ATOMIC_VAL["logical_op"]
relational_op = ATOMIC_VAL["relational_op"]
unary_op = ATOMIC_VAL["unary_op"]


# Delimiters: This is where we define what are the valid characters allowed after each token is read. 
# Take note that, this is used to determine if each token is properly terminated or not.
# If it is not properly terminated, it will throw an error in the lexer.py
DELIM_VAL = {
    "space_delim": [' ', '\t'],
    "not_delim": list(set(alpha_small + whole + ['('])), 
    "arithmetic_delim": list(set(space_delim + alpha_small + whole + ['(','\''])), # '-' shouldnt have minus
    "plus_delim": list(set(space_delim + alpha_small + whole + ['(', '"', "'", '-'])), 
    "assignment_delim": list(set(space_delim + alpha_small + whole + ["'", '"', '-', '!', '(', '['])),
    "batter@_delim": list(set(alpha_small + space_delim)),
    "churro_delim": list(set(spacenew_delim + arithmetic_op + [',', ']', ')', ':',';'])),
    "clparen_delim": list(set(spacenew_delim + [';', '[', ']', ',', ')', '{', '&', '|'] + arithmetic_op + relational_op)), # added semicolon
    "colon_delim": list(set(spacenew_delim + ['('])),
    "comma_delim": list(set(space_delim + alpha_small + whole + ['"', "'", '(','[', '-'])),
    "id_delim": list(set(spacenew_delim + assignment_op + arithmetic_op + relational_op + [';', ',', '[', ']', '(', ')', '.', '&','|'])), # had ", ' initially
    "logical_delim": list(set(space_delim + alpha_small + whole + ['-', '('])),
    "numeric_delim": list(set(spacenew_delim + [',', ')', ']', ':', ';','&','|'] + arithmetic_op + relational_op)), # added colon. ':'
    "opbrackets_delim": list(set(spacenew_delim + whole + alpha_small + ['"', '\'', '*', '[', ']', '-'])),
    "opparen_delim": list(set(space_delim + whole + alpha_small + ['"', '\'', ')', '+', '-', '(', '!'])), # added opening parenthesis. '(' and exclamation for not '!'
    "refill_delim": list(set(space_delim + ['(', '0'])),
    "relational_delim": list(set(space_delim + whole + alpha_small + ['-', '\'', '"', '('])), 
    "semicolon_delim": list(set(space_delim + alpha_small + whole + ['('])),
    "spacebraces_delim": list(set(space_delim + ['{'])),
    "spaceparen_delim": list(set(space_delim + ['('])),
    "string_delim": list(set(spacenew_delim + [')', ']', '+', ','])),
    "temp_delim": list(set(spacenew_delim + relational_op + [',', '&', '|', ':', ';', ')',']'])),
    "unary_delim": list(set(spacenew_delim + alpha_small + [')']))
}

""" Keywords Table for our Reserved Words
    How it works: If the DFA finds any matched words followed by its valid delimiter, then it is a RESERVED WORD.
    Else it becomes an IDENTIFIER. """

KEYWORDS_TABLE = {
    "KEYWORDS": [
        "bean","drip","temp","blend","churro","ifbrew","elifroth","elspress","pour","whilehot","taste","till",
        "snap","skip","flavour","syrup","brewed","defoam","cup","hot","cold","recipe","empty","crema","new",
        "batter@","glaze","refill?","cafe","backroom","order", "ceil", "floor", "pow", "rand", "sift", "sqrt", "type"
    ]
}