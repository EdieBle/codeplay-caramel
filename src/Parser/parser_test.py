from lark import Lark, Token
with open("src/Parser/cfg2.lark") as f:
    grammar = f.read()

parser = Lark(
    grammar,
    parser="earley",    
    lexer="dynamic",      
    start="start"
)

tokens = [
    Token("ID", "a"),
    Token("PLUS", "+"),
    Token("ID", "b"),
    Token("MULTIPLY", "*"),
    Token("ID", "c")
]

tree = parser.parse(tokens)
print(tree.pretty())