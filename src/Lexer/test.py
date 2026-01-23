from .lexer import tokenize, tokens_to_lark, token_final_out
from lark import Lark
from lark.lexer import Lexer

code = """average = 11 + 42
"""

class FunctionLexer(Lexer):
    def __init__(self, lexer_conf):
        pass
    
    def lex(self, data):
        yield from token_final_out(data)


print("======================== TOKENIZING FUNCTION ========================")

test = tokenize(code)

print(test)

print("\n\n\n\n======================== TOKEN-TO-LARK FUNCTION ========================")

test_lark = tokens_to_lark(test)
print(type(test_lark))
print(test_lark)


print("\n\n\n\n======================== TOKEN-TO-LARK FUNCTION ========================")

# fin_test = token_final_out(code)
# print(type(fin_test))
# print(fin_test)

# for element in test_lark:
#     print(f"{element}")



grammar = r"""
%declare IDENTIFIER1 BEANLIT DRIPLIT
WHITESPACE: "⎵"
EQUALS: "="
PLUS: "+"
MINUS: "-"
NEWLINE: "\n"

%ignore /[ \t]+/            // ignore spaces and tabs
%ignore /~\.(.|\n)*?\.~/    // ignore multi-line comments
%ignore WHITESPACE 

start: statement+
statement: assignment NEWLINE
assignment: IDENTIFIER1 EQUALS expr
expr: IDENTIFIER1
    | BEANLIT
    | DRIPLIT
    | expr PLUS expr
    | expr MINUS expr
"""


parser = Lark(grammar,parser="earley",lexer=FunctionLexer)

tree = parser.parse(code)
tree_pretty = tree.pretty()
print("\n=== Parse Tree ===")
print(tree_pretty)