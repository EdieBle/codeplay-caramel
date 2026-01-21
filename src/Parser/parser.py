from lark import Lark
from .error_handler import UnexpectedError

class Parser:
    def __init__(self, source_code):
        self.log = ''
        self._source_code = source_code
        self.ast = ''
        self.errors = []
    
    def clean_expected(self, expected: list):
        temp = []
        for allowed in expected:
            # token = allowed.lower()
            token = str(allowed).lower()
            
            # Token - Reserved Words
            if token == 'backroom': token = 'backroom'
            elif token == 'batter': token = 'batter'
            elif token == 'bean': token = 'bean'
            elif token == 'blend': token = 'blend'
            elif token == 'brewed': token = 'brewed'
            elif token == 'cafe': token = 'cafe'
            elif token == 'crema': token = 'crema'
            elif token == 'churro': token = 'churro'
            elif token == 'cold': token = 'cold'
            elif token == 'cup': token = 'cup'
            elif token == 'decaf': token = 'decaf'
            elif token == 'defoam': token = 'defoam'
            elif token == 'drip': token = 'drip'
            elif token == 'elifroth': token = 'elifroth'
            elif token == 'elspress': token = 'elspress'
            elif token == 'empty': token = 'empty'
            elif token == 'flavour': token = 'flavour'
            elif token == 'glaze': token = 'glaze'
            elif token == 'hot': token = 'hot'
            elif token == 'ifbrew': token = 'ifbrew'
            elif token == 'mug': token = 'mug'
            elif token == 'new': token = 'new'
            elif token == 'order': token = 'order'
            elif token == 'pour': token = 'pour'
            elif token == 'recipe': token = 'recipe'
            elif token == 'refill': token = 'refill?'
            elif token == 'skip': token = 'skip'
            elif token == 'snap': token = 'snap'
            elif token == 'syrup': token = 'syrup'
            elif token == 'taste': token = 'taste'
            elif token == 'till': token = 'till'
            elif token == 'temp': token = 'temp'
            elif token == 'whilehot': token = 'whilehot'
            
            # Token - Reserved Symbols
            elif token == 'equals': token = '='
            elif token == 'plus': token = '+'
            elif token == 'increment': token = '++'
            elif token == 'equal_plus': token = '+='
            elif token == 'minus': token = '-'
            elif token == 'decrement': token = '--'
            elif token == 'equal_minus': token = '-='
            elif token == 'multiply': token = '*'
            elif token == 'flex_asterisk': token = '***'
            elif token == 'equal_asterisk': token = '*='
            elif token == 'divide': token = '/'
            elif token == 'equal_divide': token = '/='
            elif token == 'modulo': token = '%'
            elif token == 'greater_than': token = '>'
            elif token == 'greater_equal': token = '>='
            elif token == 'lesser_than': token = '<'
            elif token == 'lesser_equal': token = '<='
            elif token == 'not': token = '!'
            elif token == 'not_equal': token = '!='
            elif token == 'eq_equals': token = '=='
            elif token == 'and': token = '&&'
            elif token == 'or': token = '||'
            elif token == 'op_paren': token = '('
            elif token == 'cl_paren': token = ')'
            elif token == 'op_brackets': token = '['
            elif token == 'cl_brackets': token = ']'
            elif token == 'op_braces': token = '{'
            elif token == 'cl_braces': token = '}'
            elif token == 'dot_acc': token = '.'
            elif token == 'comma': token = ','
            elif token == 'colon': token = ':'
            elif token == 'semicolon': token = ';'
            elif token == 'zero': token = '0'
            temp.append(token)
        return temp 
    
    def start(self): 
        with open("Parser/cfg.lark", "r") as file:
            grammar = file.read()
            
        parser = Lark(grammar, parser = "earley", lexer = "basic")
        
        try:
            parse_tree = parser.parse(self._source_code)
            self.ast = parse_tree
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