from lark import Lark, UnexpectedInput
from lark.lexer import Lexer
from src.Lexer.lexer import token_final_out

class LexerError(Exception):
    def __init__(self, errors):
        """
        errors: list of dicts with keys: message, line, column
        """
        self.errors = errors
        super().__init__("Lexer found errors")

class FunctionLexer(Lexer):
    def __init__(self, lexer_conf):
        pass
    
    def lex(self, data):
        errors = []
        for tok in token_final_out(data):
            if tok.type == "ERROR":
                # Collect the error
                errors.append({
                    "type": tok.type,          # ERROR
                    "message": tok.meta["message"],    # e.g. "Unclosed Token"
                    "lexeme": tok.value,       # the actual text that caused the error
                    "line": tok.line,
                    "column": tok.column
                })
            else:
                yield tok
        
        # After processing all tokens, raise if there were errors
        if errors:
            raise LexerError(errors)

class Parser:
    def __init__(self, source_code):
        self.source_code = source_code
        self.ast = None
        self.errors = []

    def start(self):
        # run the lexer first
        lexer = FunctionLexer(None)
        try:
            # This will raise LexerError if any ERROR token is emitted
            list(lexer.lex(self.source_code))
        except LexerError as lex_err:
            self.errors.extend(lex_err.errors)

            # if theres a lexical error it should just not throw anything at all
            return

        # If no lexer error, continue parsing
        with open("src/Parser/cfg.lark", "r") as f:
            grammar = f.read()

        parser = Lark(grammar, parser="earley", lexer=FunctionLexer)

        try:
            parse_tree = parser.parse(self.source_code)
            self.ast = parse_tree
            print(parse_tree.pretty())
        except UnexpectedInput as e:
            # Parser error handling
            expected = list(dict.fromkeys(getattr(e, "expected", [])))

            if not expected:
                expected.append("NONE")
            
            self.errors.append({
                "type": "SYNTAX_ERROR",
                "message": "Unexpected token",
                "expected": expected,
                "line": getattr(e, "line", None),
                "column": getattr(e, "column", None)
            })
            print(f"[SYNTAX ERROR (temp)]: \n\n{self.errors}")