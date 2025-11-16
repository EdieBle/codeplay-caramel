# Regular Definition (includes the Delimiters and Atomic values)

ATOMIC_VAL = {
    # Atoms
    "whole": ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'],
    "alpha_cap": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                  'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'],
    "alpha_small": ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
                    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'],
    "sp_symbols": ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+',
                   '[', ']', '{', '}', '/', '|', ':', ';', "'", '<', '>', '~'], #'.' and '"' was here 
                                                                                # added '~' but becomes ambiguous, probably best to add a function that 
    "newline": ['\n'],
    "space_delim": [' ', '\t'],

    # escape sequence letters
    "escapeseq_let": ['t', 'b', 'f', 'n', 'r', 'v', '"', '\'', '\\'],

    # Operators
    "arithmetic_op": ['+', '-', '*', '/', '%'],
    "assignment_op": ['='],
    "logical_op": ['!', '&', '|'],
    "relational_op": ['>', '<', '=', '!'],
    "unary_op": ['+', '-']
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
    ['a', 'c', 'd', 'e', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'o', 'p', 'q', 's', 'u', 'w', 'x', 'y', 'z'] +
    ATOMIC_VAL["alpha_cap"]
))

# unpacking the dictionary for the delimiter value dictionary below.
whole = ATOMIC_VAL["whole"]
alpha_cap = ATOMIC_VAL["alpha_cap"]
alpha_small = ATOMIC_VAL["alpha_small"]
sp_symbols = ATOMIC_VAL["sp_symbols"]
space_delim = ATOMIC_VAL["space_delim"]
newline = ATOMIC_VAL["newline"]
arithmetic_op = ATOMIC_VAL["arithmetic_op"]
assignment_op = ATOMIC_VAL["assignment_op"]
logical_op = ATOMIC_VAL["logical_op"]
relational_op = ATOMIC_VAL["relational_op"]
unary_op = ATOMIC_VAL["unary_op"]


# delimiters
DELIM_VAL = {
    "space_delim": [' ', '\t'],
    "arithmetic_delim": list(set(space_delim + alpha_small + ['(', '-'])),
    "plus_delim": list(set(space_delim + alpha_small + ['(', '"', "'", '-'])), # holy shit bakit walang numbers dito
    "assignment_delim": list(set(space_delim + alpha_small + whole + ["'", '"', '!', '(', '['])),
    "batter@_delim": list(set(alpha_small + space_delim)),
    "braces_delim": list(set(space_delim + newline)),
    "clbrackets_delim": list(set(space_delim + newline + ['[', ']', ','])),
    "clparen_delim": list(set(space_delim + newline + ['(', ')', '{', '&', '|'] + arithmetic_op)),
    "colon_delim": list(set(space_delim + newline + ['('])),
    "comma_delim": list(set(space_delim + alpha_small + whole + ['"', "'", '('])),
    "id_delim": list(set(space_delim + assignment_op + logical_op + arithmetic_op + relational_op + [';', ',', '"', "'", '{', '['])),
    "logical_delim": list(set(space_delim + alpha_small + whole + ['-', '('])),
    "numeric_delim": list(set(space_delim + newline + [',', ')', ']'] + arithmetic_op + relational_op)),
    "opbrackets_delim": list(set(space_delim + newline + whole + alpha_small + ['"', '\'', '*', '[', ']'])),
    "opparen_delim": list(set(space_delim + whole + alpha_small + ['"', '\'', ')', '+', '-'])),
    "refill_delim": list(set(space_delim + ['(', '0'])),
    "relational_delim": list(set(space_delim + whole + alpha_small + ['-', '\'', '"', '('])), 
    "semicolon_delim": list(set(space_delim + alpha_small + whole + ['('])),
    "spacebraces_delim": list(set(space_delim + ['{'])),
    "spaceparen_delim": list(set(space_delim + ['('])),
    "string_delim": list(set(space_delim + [')'] + newline + relational_op + ['+', ','])),
    "temp_delim": list(set(space_delim + newline + relational_op + logical_op + [','])),
    "unary_delim": list(set(space_delim + newline + alpha_small)) # + ['1','2','3','4','5','6','7','8','9'] (removed these for now cuz a unary being delimited by a num makes no sense 4:17am)
}