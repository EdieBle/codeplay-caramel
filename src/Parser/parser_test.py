from lark import Lark, UnexpectedInput

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
    drip y = 2
    bean cup()[
    mug x [
        bean g = 5, v = 4, p = 9
        bean x = 3
    ]
    bean number
    drip average = 1.75
    blend greeting = "Hello"
    churro choice = 'A'
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
    print("Expected:", e.expected)

    print("\n=== OFFENDING TOKEN ===")
    print("Token:", e.token)
    print("Type :", e.token.type)
    print("Value:", e.token.value)
    print("Line :", e.line)
    print("Col  :", e.column)
    

    print("\nExpected (human-readable):")
    print(", ".join(sorted(e.expected)))
