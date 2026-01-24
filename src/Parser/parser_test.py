from lark import Token, Lark, UnexpectedInput
from lark.lexer import Lexer
from src.Lexer.lexer import token_final_out

class FunctionLexer(Lexer):
    def __init__(self, lexer_conf):
        pass
    
    def lex(self, data):
        yield from token_final_out(data)


with open("src/Parser/cfg.lark") as f:
    grammar = f.read()


parser = Lark(
    grammar,
    parser="earley",
    lexer=FunctionLexer,
    start="start",
    debug=True 
)

# code = f'print " hello " \n'   # <-- newline terminator is required
# code = '''bean x = 4
#     drip y = 4+5*6/7-8+(4)-(6+4)*(8/2)/(2)
#     bean cup()[
#     mug x [
#         bean g = 5, v = 4, p = 9
#         bean x = 3
#     ]
#     ifbrew(age < 18){
#         glaze("MINOR")
#         glaze("MINOR1")
#         x = 4+4
#     }
#     elifroth(age >= 18){
#         glaze("ADULT")
#         glaze("MINOR1")
#         x = 4+4
#     }
#     elspress{
#         glaze("INVALID!")
#         glaze("MINOR1")
#         x = 4+4
#     }
#     bean number
#     drip average = 1.75
#     blend greeting = "Hello"
#     churro choice = 'A'
#     refill? 0
# ]
# '''

code = '''bean cup()[
temp p = hot
refill? 0
]'''

print("=== Tokens ===")
for token in parser.lex(code):
    print(f"{token.type:12} -> {token.value!r}")

try:
    tree = parser.parse(code)
    print("\n=== Parse Tree ===")
    print(tree.pretty())

except UnexpectedInput as e:
    print("\n=== PARSE ERROR ===")
    print("Error at position:", e.pos_in_stream)
    print("Line:", e.line, "Column:", e.column)
    print("Got token:", e.get_context(code))
    expected = sorted(set(e.expected))
    print("Expected:", list(set(expected)))

    print("\n=== OFFENDING TOKEN ===")
    print("Token:", e.token)
    print("Type :", e.token.type)
    print("Value:", e.token.value)
    print("Line :", e.line)
    print("Col  :", e.column)
    

    print("\nExpected (human-readable, also dont panic if may dupe, those are differing branches):")
    print(", ".join(sorted(e.expected)))
