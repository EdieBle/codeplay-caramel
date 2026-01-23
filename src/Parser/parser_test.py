from lark import Token, Lark, UnexpectedInput
from src.Lexer.lexer import tokenize


def adapt_tokens_for_lark(tokens_from_lexer):
    """
    Converts lexer tokens into Lark tokens.
    """
    lark_tokens = []

    for tok in tokens_from_lexer:
        # Lark's Token takes (type, value)
        lark_tokens.append(Token(tok["type"], tok["lexeme"]))

    return lark_tokens


with open("src/Parser/cfg.lark") as f:
    grammar = f.read()

parser = Lark(
    grammar,
    parser="earley",
    lexer="basic",
    start="start",
    debug=True 
)

# code = f'print " hello " \n'   # <-- newline terminator is required
code = '''bean x = 4
    drip y = 2-3*4/5+10+10+10+10+(4+5)
    bean cup()[
    mug x [
        bean g = 5, v = 4, p = 9
        bean x = 3
    ]
    ifbrew(age < 18){
        glaze("MINOR")
        glaze("MINOR1")
        x = 4+4
    }
    elifroth(age >= 18){
        glaze("ADULT")
        glaze("MINOR1")
        x = 4+4
    }
    elspress{
        glaze("INVALID!")
        glaze("MINOR1")
        x = 4+4
    }
    bean number
    drip average = 1.75
    blend greeting = "Hello"
    churro choice = 'A'
    refill? 0
]
'''

# print("=== Tokens ===")
# for token in parser.lex(code):
#     print(f"{token.type:12} -> {token.value!r}")

try:
    lexer_tokens = tokenize(code)
    lark_tokens = adapt_tokens_for_lark(lexer_tokens)

    tree = parser.parse(lark_tokens)
    print("\n=== Parse Tree ===")
    print(tree.pretty())

except UnexpectedInput as e:
    print("\n=== PARSE ERROR ===")
    print("Error at position:", e.pos_in_stream)
    print("Line:", e.line, "Column:", e.column)
    print("Got token:", e.get_context(code))
    print("Expected:", e.expected)

    print("\n=== OFFENDING TOKEN ===")
    print("Token:", e.token)
    print("Type :", e.token.type)
    print("Value:", e.token.value)
    print("Line :", e.line)
    print("Col  :", e.column)
    

    print("\nExpected (human-readable):")
    print(", ".join(sorted(e.expected)))
