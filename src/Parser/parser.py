from lark import Lark, UnexpectedInput
from lark.lexer import Lexer
from src.Lexer.lexer import token_final_out

class FunctionLexer(Lexer):
    def __init__(self, lexer_conf):
        pass
    
    def lex(self, data):
        yield from token_final_out(data)

class Parser:
    def __init__(self, source_code):
        self.log = ''
        self._source_code = source_code
        self.ast = ''
        self.errors = []
   
    def start(self): 
        with open("src/Parser/cfg.lark", "r") as file:
            grammar = file.read()
            
        parser = Lark(grammar, parser = "earley", lexer = FunctionLexer)
        
        try:
            parse_tree = parser.parse(self._source_code)
            self.ast = parse_tree
            print(parse_tree.pretty())
            # self.ast = parser.parse(self._source_code)
        
        except Exception as e:
            source = self._source_code.split("\n")
            source[-1] += " "
            
            # index = (e.line if e.line > 0 else len(source), e.column if e.column > 0 else len(source[-1]))
            # unexpected = UnexpectedError(source[index[0]-1], index)

            line = e.line if e.line > 0 else len(source)
            column = e.column if e.column > 0 else len(source[-1])
            
            try:
                expected = e.allowed
            except:
                expected = e.expected

            # expected = self.clean_expected(expected)
            # self.log = f'Unexpected token at line {index[0]} column {index[1]}: {unexpected}\nExpected any: {expected}'
            
            if isinstance(expected, str):
                expected = [expected]
            elif isinstance(expected, set):
                expected = list(expected)
            
            self.errors.append({
                "type": "SYNTAX_ERROR",
                "message": "Unexpected token",
                "expected": self.clean_expected(expected),
                "line": line,
                "column": column
            })