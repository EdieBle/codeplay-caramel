# Regular Definition 
# Terminals 
whole = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
alpha_cap = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
alpha_small = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 
               'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
sp_symbols = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+',
              '[', ']', '{', '}', '\\', '|', ':', ';', "'", '"', '<', '>', '.']

space_delim = [' ', '\t']
newline = ['\n']

escapeseq_let = ['t', 'b', 'f', 'n', 'r', 'v', '"']
safe_char = (
    space_delim + whole + sp_symbols + 
    ['a', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 
     'o', 'p', 'q', 's', 'u', 'w', 'x', 'y', 'z',
     'A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
     'O', 'P', 'Q', 'S', 'U', 'W', 'X', 'Y', 'Z']                       
)

arithmetic_op = ['+', '-', '*', '/', '%']
assignment_op = ['=']
logical_op = ['!', '&', '|']
relational_op = ['>', '<', '=', '!']
unary_op = ['++', '--']

# Nonterminals
arithmetic_delim = list(set(space_delim + alpha_small + ['(', '-']))
plus_delim = list(set(space_delim + alpha_small + ['(', '"', "'", '-']))
assignment_delim = list(set(space_delim + alpha_small + whole + ["'", '"', '!', '(', '[']))
batter_delim = list(set(alpha_small + space_delim))
braces_delim = list(set(space_delim + newline))
clbrackets_delim = list(set(space_delim + newline + ['[', ']', ',']))
clparen_delim = list(set(space_delim + newline + ['(', ')', '{', '&', '|'] + arithmetic_op))
colon_delim = list(set(space_delim + newline + ['(']))
comma_delim = list(set(space_delim + alpha_small + whole + ['"', "'", '(']))
id_delim = list(set(space_delim + assignment_op + ['logical_op'] + arithmetic_op + ['relational_op', ';', ',', '"', "'", '{', '[']))
logical_delim = list(set(space_delim + alpha_small + whole + ['-', '(']))
numeric_delim = list(set(space_delim + newline + [',', ')', ']'] + arithmetic_op + relational_op))
opbrackets_delim = list(set(space_delim + newline + whole + alpha_small + ['"', '\'', '*', '[', ']']))
opparen_delim = list(set(space_delim + whole + alpha_small + ['"', '\'', ')', '+', '-']))
refill_delim = list(set(space_delim + '(' + '0'))
semicolon_delim = list(set(space_delim + alpha_small + whole + '('))
spacebraces_delim = list(set(space_delim + '{'))
spaceparen_delim = list(set(space_delim + '('))
string_delim = list(set(space_delim + [')'] + newline + relational_op + ['+', ',']))
temp_delim = list(set(space_delim + newline + relational_op + logical_op + [',']))
text_content = list(set(space_delim + whole + alpha_small + alpha_cap + sp_symbols))
unary_delim = list(set(space_delim + newline + alpha_small + ['1','2','3','4','5','6','7','8','9']))