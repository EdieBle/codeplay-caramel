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

code = f'print " hello " \n'   # <-- newline terminator is required

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

    print("\nExpected (human-readable):")
    print(", ".join(sorted(e.expected)))
