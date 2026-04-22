"""
Recursive Descent Parser for CARAMEL Language

This parser implements an LL(1) recursive descent parser that mirrors the organization
of cfg.lark. It parses tokenized CARAMEL source code into an Abstract Syntax Tree (AST).

Organization:
- Exception Classes: Custom exceptions for parse errors
- Utility Classes: ParseNode, TokenStream
- RDParser Class: Main parser with methods organized by grammar sections
  1. Program Structure & Initialization
  2. Error Handling & Helper Methods
  3. Program & Global Definitions
  4. Declarations (General & Specialized)
  5. Blend Declarations
  6. ID-Led Statements
  7. ORDER-Led Statements
  8. Unary Operations
  9. Data Types & Values
  10. Expression Hierarchy (Logic, Relational, Arithmetic, Unary, Primary)
  11. Arrays
  12. Functions & Arguments
  13. Mug (Struct) Declarations
  14. Objects
  15. Recipes (Functions)
  16. Empty (Void Functions)
  17. Crema (Classes)
  18. Main Definitions
  19. Statements
  20. Input/Output
  21. Control Flow (If/Switch/Loops)
  22. Interrupt Statements
- Parser Wrapper Class: High-level parsing interface with error handling
"""

from src.Lexer.lexer import token_final_out, OPERATOR_MAP, KEYWORD_MAP


# ============================================================================
# EXCEPTION CLASSES
# ============================================================================

class UnexpectedInput(Exception):
    """Base exception for unexpected input during parsing."""
    def __init__(self, message, index=None):
        self.index = index
        super().__init__(message)


class UnexpectedToken(UnexpectedInput):
    """Exception raised when an unexpected token is encountered."""
    def __init__(self, token, expected, index=None):
        self.token = token
        self.expected = list(expected)
        self.line = getattr(token, "line", None)
        self.column = getattr(token, "column", None)
        super().__init__("Unexpected token", index=index)


class UnexpectedEOF(UnexpectedInput):
    """Exception raised when end-of-file is reached unexpectedly."""
    def __init__(self, expected, last_token=None, index=None):
        self.token = last_token
        self.expected = list(expected)
        self.line = getattr(last_token, "line", None)
        self.column = getattr(last_token, "column", None)
        super().__init__("Unexpected end of input", index=index)


class LexerError(Exception):
    """Exception raised when lexer errors are encountered."""
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Lexer found errors")


# ============================================================================
# UTILITY CLASSES
# ============================================================================

class ParseNode:
    """Represents a node in the abstract syntax tree (AST)."""
    def __init__(self, name, children=None):
        self.name = name
        self.children = children or []

    def pretty(self, indent=0):
        """Pretty-print the parse tree with indentation."""
        lines = ["  " * indent + self.name]
        for child in self.children:
            if isinstance(child, ParseNode):
                lines.append(child.pretty(indent + 1))
            else:
                lines.append("  " * (indent + 1) + f"{child.type}\t{child.value}")
        return "\n".join(lines)


class TokenStream:
    """Manages the stream of tokens during parsing."""
    def __init__(self, tokens):
        self.tokens = list(tokens)
        self.index = 0
        self.eof = self._make_eof()

    def _make_eof(self):
        """Create an EOF token marker."""
        if self.tokens:
            last = self.tokens[-1]
            line = getattr(last, "line", None)
            column = getattr(last, "column", None)
        else:
            line = 1
            column = 1

        eof = type("EofToken", (), {})()
        eof.type = "$END"
        eof.value = ""
        eof.line = line
        eof.column = column
        eof.meta = {}
        return eof

    def peek(self, offset=0):
        """Look at a token without consuming it."""
        idx = self.index + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.eof

    def advance(self):
        """Consume and return the current token."""
        tok = self.peek(0)
        if self.index < len(self.tokens):
            self.index += 1
        return tok

    def checkpoint(self):
        """Save the current position in the stream."""
        return self.index

    def restore(self, index):
        """Restore the stream to a previously saved position."""
        self.index = index


# ============================================================================
# RD PARSER CLASS
# ============================================================================

class RDParser:
    """
    Recursive Descent Parser implementing LL(1) grammar from cfg.lark.
    
    Attributes:
        stream: TokenStream for managing input tokens
        DATA_TYPE: Set of valid data type tokens
        LOGIC_OP: Logical operators (AND, OR)
        REL_OP: Relational operators (>, <, ==, !=, etc.)
        ARITHM_OP: Arithmetic operators (+, -, *, /, %)
        UNARY_OP: Unary operators (++, --)
        PRIMARY_LITERALS: Literal token types
        EXPR_START: Tokens that can start an expression
    """

    # Token sets for predictive parsing
    DATA_TYPE = {"BEAN", "DRIP", "CHURRO", "TEMP", "BLEND"}
    LOGIC_OP = {"AND", "OR"}
    REL_OP = {
        "GREATER_THAN", "LESSER_THAN", "EQ_EQUALS", "NOT_EQUAL",
        "GREATER_EQUAL", "LESSER_EQUAL"
    }
    ARITHM_OP = {"PLUS", "MINUS", "MULTIPLY", "DIVIDE", "MODULO"}
    UNARY_OP = {"INCREMENT", "DECREMENT"}
    PRIMARY_LITERALS = {"BEANLIT", "DRIPLIT", "CHURROLIT", "HOT", "COLD", "BLENDLIT"}
    EXPR_START = {
        "NOT", "INCREMENT", "DECREMENT", "MINUS", "ID", "ORDER",
        "BEANLIT", "DRIPLIT", "CHURROLIT", "HOT", "COLD", "BLENDLIT", "OP_PAREN", "SIFT", "SQRT", "CEIL", "FLOOR", "POW", "RAND", "TYPE"
    }
    BLEND_TERM_START = {
        "BLENDLIT", "ID", "ORDER", "OP_PAREN",
        "BEANLIT", "DRIPLIT", "CHURROLIT", "HOT", "COLD"
    }

    def __init__(self, tokens):
        """Initialize the parser with a token stream."""
        self.stream = TokenStream(tokens)
        self._allow_function_calls = True
        self._allow_unary_ops = True

    # ========================================================================
    # 1. PROGRAM STRUCTURE & INITIALIZATION
    # ========================================================================\

    def parse(self):
        """Main entry point: parse the entire program."""
        node = self.parse_start()
        if self.stream.peek().type != "$END":
            self._error({"$END"})
        return node

    def parse_start(self):
        """Parse rule: start -> program"""
        return self._node("start", [self.parse_program()])

    # ========================================================================
    # 2. ERROR HANDLING & HELPER METHODS
    # ========================================================================

    def _current(self, offset=0):
        """Get the current token without consuming it."""
        return self.stream.peek(offset)

    def _accept(self, token_type):
        """Try to match and consume a token of given type."""
        if self._current().type == token_type:
            return self.stream.advance()
        return None

    def _expect(self, token_type, expected=None):
        """Match and consume a required token, or raise an error."""
        tok = self._current()
        if tok.type == token_type:
            return self.stream.advance()
        self._error(set(expected or [token_type]))

    def _error(self, expected_set):
        """Raise a parse error with the expected token set."""
        tok = self._current()
        if tok.type == "$END":
            last = self.stream.tokens[-1] if self.stream.tokens else None
            raise UnexpectedEOF(expected_set, last_token=last, index=self.stream.index)
        raise UnexpectedToken(tok, expected_set, index=self.stream.index)

    def _node(self, name, children=None):
        """Create a new AST node."""
        return ParseNode(name, children or [])

    def _is_start_statement(self):
        """Check if current token can start a statement."""
        t = self._current().type
        return t in {
            "CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP",
            "ID", "ORDER", "INCREMENT", "DECREMENT", "MUG", "NEW",
            "BATTER", "GLAZE", "IFBREW", "FLAVOUR", "POUR", "WHILEHOT", "TASTE",
            "SNAP", "SKIP", "REFILL"
        }

    def _is_start_expression(self):
        """Check if current token can start an expression."""
        return self._current().type in self.EXPR_START

    def _is_start_global_dec(self):
        """Check if current token can start a global declaration."""
        t = self._current().type
        if t == "BEAN" and self._current(1).type == "CUP":
            return False
        return t in {
            "CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP",
            "ID", "ORDER", "MUG", "NEW", "CREMA", "RECIPE", "EMPTY"
        }

    def _has_boolean_content(self, node):
        """Recursively check if a parse tree node contains boolean/relational content.

        Returns True if the node or any descendant contains a relational operator,
        logical operator, NOT operator, or boolean literal (HOT/COLD).
        """
        if isinstance(node, ParseNode):
            if node.name in ("rel_op", "logic_op", "NOT"):
                return True
            return any(self._has_boolean_content(c) for c in node.children)
        # Token node - check for boolean literals
        return getattr(node, 'type', None) in ("HOT", "COLD")

    def _merge_errors(self, primary, secondary):
        """Merge two parse errors to provide better error messages."""
        if primary.index is None:
            return secondary
        if secondary.index is None:
            return primary

        if primary.index > secondary.index:
            return primary
        if secondary.index > primary.index:
            return secondary

        expected = set(primary.expected).union(secondary.expected)
        if isinstance(primary, UnexpectedEOF):
            return UnexpectedEOF(expected, last_token=primary.token, index=primary.index)
        return UnexpectedToken(primary.token, expected, index=primary.index)

    # ========================================================================
    # 3. PROGRAM & GLOBAL DEFINITIONS
    # ========================================================================

    def parse_program(self):
        """Parse rule: program -> global_def main_def"""
        checkpoint = self.stream.checkpoint()

        # Try parsing with global definitions
        attempt1 = None
        attempt1_err = None
        try:
            attempt1 = self._node("program", [
                self.parse_global_def(),
                self.parse_main_def()
            ])
        except UnexpectedInput as err:
            attempt1_err = err

        if attempt1_err is None:
            return attempt1

        # Fallback: empty global definitions (main only)
        self.stream.restore(checkpoint)
        attempt2 = None
        attempt2_err = None
        try:
            attempt2 = self._node("program", [
                self._node("global_def", [self._node("_empty")]),
                self.parse_main_def()
            ])
        except UnexpectedInput as err:
            attempt2_err = err

        if attempt2_err is None:
            return attempt2

        merged = self._merge_errors(attempt1_err, attempt2_err)

        # If no progress was made from the starting position, the error
        # only reflects what parse_main_def expects ("BEAN").  Enrich it
        # with the full FIRST(<program>) set so the message lists every
        # token that can validly begin a program.
        if merged.index is not None and merged.index == checkpoint:
            PROGRAM_FIRST = {
                "CAFE", "BACKROOM", "BREWED", "BLEND", "ID", "ORDER",
                "BEAN", "DRIP", "CHURRO", "TEMP", "MUG", "NEW",
                "RECIPE", "EMPTY", "CREMA"
            }
            enriched = set(merged.expected).union(PROGRAM_FIRST)
            if isinstance(merged, UnexpectedEOF):
                raise UnexpectedEOF(enriched, last_token=merged.token,
                                    index=merged.index)
            raise UnexpectedToken(merged.token, enriched,
                                  index=merged.index)

        raise merged

    def parse_global_def(self):
        """Parse rule: global_def -> global_dec global_def | λ"""
        children = []
        while self._is_start_global_dec():
            children.append(self.parse_global_dec())
        if not children:
            children.append(self._node("_empty"))
        return self._node("global_def", children)

    def parse_global_dec(self):
        """Parse rule: global_dec -> various declaration types"""
        t = self._current().type
        if t in {"CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP"}:
            return self._node("global_dec", [self.parse_acc_mod_dec()])
        if t == "ID":
            return self._node("global_dec", [self.parse_id_dec_stmt()])
        if t == "ORDER":
            return self._node("global_dec", [self.parse_order_dec_stmt()])
        if t == "MUG":
            return self._node("global_dec", [self.parse_mug_dec()])
        if t == "NEW":
            return self._node("global_dec", [self.parse_object_def()])
        if t == "CREMA":
            return self._node("global_dec", [self.parse_crema_def()])
        if t == "RECIPE":
            return self._node("global_dec", [self.parse_recipe_def()])
        if t == "EMPTY":
            return self._node("global_dec", [self.parse_empty_def()])
        self._error({
            "CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP",
            "ID", "ORDER", "MUG", "NEW", "CREMA", "RECIPE", "EMPTY"
        })

    # ========================================================================
    # 4. DECLARATIONS (GENERAL & SPECIALIZED)
    # ========================================================================

    def parse_dec(self):
        """Parse rule: dec -> various declaration alternatives"""
        t = self._current().type
        if t in {"CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP"}:
            return self._node("dec", [self.parse_acc_mod_dec()])
        if t == "ID":
            return self._node("dec", [self.parse_id_dec_stmt()])
        if t == "ORDER":
            return self._node("dec", [self.parse_order_dec_stmt()])
        if t in {"INCREMENT", "DECREMENT"}:
            return self._node("dec", [self.parse_pre_unary_dec()])
        if t == "MUG":
            return self._node("dec", [self.parse_mug_dec()])
        if t == "NEW":
            return self._node("dec", [self.parse_object_def()])
        self._error({
            "CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP",
            "ID", "ORDER", "INCREMENT", "DECREMENT", "MUG", "NEW"
        })

    def parse_acc_mod_dec(self):
        """Parse rule: acc_mod_dec -> CAFE body | BACKROOM body | dtype_dec"""
        t = self._current().type
        if t == "CAFE":
            return self._node("acc_mod_dec", [
                self._expect("CAFE"),
                self.parse_acc_mod_dec_body()
            ])
        if t == "BACKROOM":
            return self._node("acc_mod_dec", [
                self._expect("BACKROOM"),
                self.parse_acc_mod_dec_body()
            ])
        return self._node("acc_mod_dec", [self.parse_dtype_dec()])

    def parse_acc_mod_dec_body(self):
        """Parse rule: acc_mod_dec_body -> BREWED body | data_type ID tail"""
        t = self._current().type
        if t == "BREWED":
            return self._node("acc_mod_dec_body", [
                self._expect("BREWED"),
                self.parse_acc_brewed_body()
            ])
        if t in self.DATA_TYPE:
            return self._node("acc_mod_dec_body", [
                self.parse_data_type(),
                self._expect("ID"),
                self.parse_acc_dtype_tail()
            ])
        self._error({"BREWED"}.union(self.DATA_TYPE))

    def parse_acc_brewed_body(self):
        """Parse rule: acc_brewed_body -> data_type const_init_list"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("acc_brewed_body", [
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        self._error(self.DATA_TYPE)

    def parse_acc_dtype_tail(self):
        """Parse rule: acc_dtype_tail -> [size] array_decl | opt_assign var_list"""
        if self._accept("OP_BRACKETS"):
            return self._node("acc_dtype_tail", [
                self._node("OP_BRACKETS", []),
                self.parse_arr_size_val(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_dec_dim()
            ])
        return self._node("acc_dtype_tail", [
            self.parse_opt_assign(),
            self.parse_var_dec_tail()
        ])

    def parse_dtype_dec(self):
        """Parse rule: dtype_dec -> BREWED body | data_type ID tail"""
        t = self._current().type
        if t == "BREWED":
            return self._node("dtype_dec", [
                self._expect("BREWED"),
                self.parse_dtype_brewed_body()
            ])
        if t in self.DATA_TYPE:
            return self._node("dtype_dec", [
                self.parse_data_type(),
                self._expect("ID"),
                self.parse_dtype_id_tail()
            ])
        self._error({"BREWED"}.union(self.DATA_TYPE))

    def parse_dtype_brewed_body(self):
        """Parse rule: dtype_brewed_body -> data_type const_init_list"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("dtype_brewed_body", [
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        self._error(self.DATA_TYPE)

    def parse_dtype_id_tail(self):
        """Parse rule: dtype_id_tail -> [size] array_decl | opt_assign var_list"""
        if self._accept("OP_BRACKETS"):
            return self._node("dtype_id_tail", [
                self._node("OP_BRACKETS", []),
                self.parse_arr_size_val(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_dec_dim()
            ])
        return self._node("dtype_id_tail", [
            self.parse_opt_assign(),
            self.parse_var_dec_tail()
        ])

    # ========================================================================
    # 5. BLEND DECLARATIONS
    # ========================================================================

    def parse_blend_const_init(self):
        """Parse rule: blend_const_init -> ID = blend_val"""
        return self._node("blend_const_init", [
            self._expect("ID"),
            self._expect("EQUALS"),
            self.parse_blend_val()
        ])

    def parse_blend_const_init_tail(self):
        """Parse rule: blend_const_init_tail -> (COMMA ID = blend_val)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self._expect("ID"))
            children.append(self._expect("EQUALS"))
            children.append(self.parse_blend_val())
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_const_init_tail", children)

    def parse_blend_id_tail(self):
        """Parse rule: blend_id_tail -> [size] array_decl | assign var_list"""
        if self._current().type == "OP_BRACKETS":
            return self._node("blend_id_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_arr_size_val(),
                self._expect("CL_BRACKETS"),
                self.parse_blend_arr_dec_dim()
            ])
        return self._node("blend_id_tail", [
            self.parse_blend_assign(),
            self.parse_blend_tail()
        ])

    def parse_blend_assign(self):
        """Parse rule: blend_assign -> = blend_val | λ"""
        if self._accept("EQUALS"):
            return self._node("blend_assign", [
                self._node("EQUALS", []),
                self.parse_blend_val()
            ])
        return self._node("blend_assign", [self._node("_empty")])

    def parse_blend_tail(self):
        """Parse rule: blend_tail -> (COMMA ID assign)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self._expect("ID"))
            children.append(self.parse_blend_assign())
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_tail", children)

    def parse_blend_val(self):
        """Parse rule: blend_val -> blend_term (+blend_term)*"""
        return self._node("blend_val", [
            self.parse_blend_term(),
            self.parse_blend_val_tail()
        ])

    def parse_blend_val_tail(self):
        """Parse rule: blend_val_tail -> (+ blend_term)* | λ"""
        children = []
        while self._accept("PLUS"):
            children.append(self._node("PLUS", []))
            children.append(self.parse_blend_term())
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_val_tail", children)

    def parse_blend_term(self):
        """Parse rule: blend_term -> BLENDLIT | ID tail | order.ID | (blend_val)"""
        t = self._current().type
        if t == "BLENDLIT":
            return self._node("blend_term", [self._expect("BLENDLIT")])
        if t == "ID":
            return self._node("blend_term", [
                self._expect("ID"),
                self.parse_blend_term_id_tail()
            ])
        if t == "ORDER":
            return self._node("blend_term", [
                self._expect("ORDER"),
                self._expect("DOT_ACC"),
                self._expect("ID")
            ])
        if t == "OP_PAREN":
            return self._node("blend_term", [
                self._expect("OP_PAREN"),
                self.parse_expression(),
                self._expect("CL_PAREN")
            ])
        if t in {"BEANLIT", "DRIPLIT", "CHURROLIT", "HOT", "COLD"}:
            return self._node("blend_term", [self._expect(t)])
        
        if t in {"SQRT", "CEIL", "FLOOR", "POW", "RAND", "TYPE", "SIFT"}:
            return self._node("blend_term", [self.parse_primary()])
        
        self._error({"BLENDLIT", "ID", "ORDER", "OP_PAREN", "BEANLIT", "DRIPLIT",
                    "CHURROLIT", "HOT", "COLD", "SQRT", "CEIL", "FLOOR", "POW", "RAND", "TYPE", "SIFT"})
        
    def parse_blend_term_id_tail(self):
        """Parse rule: blend_term_id_tail -> . ID | (args) | λ"""
        if self._accept("DOT_ACC"):
            return self._node("blend_term_id_tail", [
                self._node("DOT_ACC", []),
                self._expect("ID")
            ])
        if self._current().type == "OP_PAREN":
            return self._node("blend_term_id_tail", [
                self._expect("OP_PAREN"),
                self.parse_function_args(),
                self.parse_function_args_tail(),
                self._expect("CL_PAREN")
            ])
        if self._current().type == "OP_BRACKETS":
            return self._node("blend_term_id_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail()
            ])
        return self._node("blend_term_id_tail", [self._node("_empty")])

    def parse_blend_arr_elem(self):
        """Parse rule: blend_arr_elem -> blend_term"""
        return self._node("blend_arr_elem", [self.parse_blend_term()])

    def parse_blend_ext_arr_elem(self):
        """Parse rule: blend_ext_arr_elem -> (COMMA blend_arr_elem)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_blend_arr_elem())
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_ext_arr_elem", children)

    def parse_blend_arr_cont_1d(self):
        """Parse rule: blend_arr_cont_1d -> blend_arr_elem (, blend_arr_elem)* | λ"""
        if self._current().type in self.BLEND_TERM_START:
            return self._node("blend_arr_cont_1d", [
                self.parse_blend_arr_elem(),
                self.parse_blend_ext_arr_elem()
            ])
        return self._node("blend_arr_cont_1d", [self._node("_empty")])

    def parse_opt_blend_arr_elems(self):
        """Parse rule: opt_blend_arr_elems -> blend_arr_elem ext_blend_arr_elem | λ"""
        if self._current().type in self.BLEND_TERM_START:
            return self._node("opt_blend_arr_elems", [
                self.parse_blend_arr_elem(),
                self.parse_blend_ext_arr_elem()
            ])
        return self._node("opt_blend_arr_elems", [self._node("_empty")])

    def parse_blend_arr_cont_2d(self):
        """Parse rule: blend_arr_cont_2d -> [elems], [elems] (, [elems])*"""
        return self._node("blend_arr_cont_2d", [
            self._expect("OP_BRACKETS"),
            self.parse_opt_blend_arr_elems(),
            self._expect("CL_BRACKETS"),
            self._expect("COMMA"),
            self._expect("OP_BRACKETS"),
            self.parse_opt_blend_arr_elems(),
            self._expect("CL_BRACKETS"),
            self.parse_blend_arr_cont_2d_tail()
        ])

    def parse_blend_arr_cont_2d_tail(self):
        """Parse rule: blend_arr_cont_2d_tail -> (COMMA [blend] ...)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self._expect("OP_BRACKETS"))
            children.append(self.parse_opt_blend_arr_elems())
            children.append(self._expect("CL_BRACKETS"))
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_arr_cont_2d_tail", children)

    # ========================================================================
    # 6. ID-LED STATEMENTS
    # ========================================================================

    def parse_id_dec_stmt(self):
        """Parse rule: id_dec_stmt -> ID tail"""
        return self._node("id_dec_stmt", [
            self._expect("ID"),
            self.parse_id_dec_tail()
        ])

    def parse_id_dec_tail(self):
        """Parse rule: id_dec_tail -> = value | . ID tail | [idx] tail | postfix_op"""
        t = self._current().type
        if t in {"EQUALS", "EQUAL_PLUS", "EQUAL_MINUS", "EQUAL_ASTERISK", "EQUAL_DIVIDE"}:
            return self._node("id_dec_tail", [
                self.parse_assign_op(),
                self.parse_assign_val()
            ])
        if t == "OP_PAREN" and self._allow_function_calls:  
            return self._node("id_dec_tail", [
                self._expect("OP_PAREN"),
                self.parse_function_args(),
                self.parse_function_args_tail(),
                self._expect("CL_PAREN")
            ])
        if t == "DOT_ACC":
            return self._node("id_dec_tail", [
                self._expect("DOT_ACC"),
                self._expect("ID"),
                self.parse_id_dot_tail()
            ])
        if t == "OP_BRACKETS":
            return self._node("id_dec_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_id_bracket_tail()
            ])
        if t in self.UNARY_OP:
            return self._node("id_dec_tail", [self.parse_unary_op()])
        self._error({
            "EQUALS", "EQUAL_PLUS", "EQUAL_MINUS", "EQUAL_ASTERISK", "EQUAL_DIVIDE",
             "OP_PAREN", "DOT_ACC", "OP_BRACKETS", "INCREMENT", "DECREMENT"
        })

    def parse_assign_val(self):
        """Parse rule: assign_val -> BLENDLIT concat | expression"""
        if self._current().type == "BLENDLIT":
            return self._node("assign_val", [
                self._expect("BLENDLIT"),
                self.parse_concat()
            ])
        return self._node("assign_val", [self.parse_expression()])

    def parse_id_dot_tail(self):
        """Parse rule: id_dot_tail -> = value | . member | [idx] | (args) | λ"""
        t = self._current().type
        if t == "EQUALS":
            return self._node("id_dot_tail", [
                self._expect("EQUALS"),
                self.parse_assign_val()
            ])
        if t == "DOT_ACC":
            return self._node("id_dot_tail", [
                self._expect("DOT_ACC"),
                self.parse_crema_member_inner(),
                self.parse_id_crema_assign_tail()
            ])
        if t == "OP_BRACKETS":
            return self._node("id_dot_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail(),
                self.parse_id_crema_assign_tail()
            ])
        self._error({"EQUALS", "DOT_ACC", "OP_BRACKETS"})

    def parse_id_crema_assign_tail(self):
        """Parse rule: id_crema_assign_tail -> = value | λ"""
        return self._node("id_crema_assign_tail", [
            self._expect("EQUALS"),
            self.parse_assign_val()
        ])

    def parse_id_bracket_tail(self):
        """Parse rule: id_bracket_tail -> [idx] = elem | = elem | = [arr_cont_1d]"""
        if self._accept("OP_BRACKETS"):
            return self._node("id_bracket_tail", [
                self._node("OP_BRACKETS", []),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self._expect("EQUALS"),
                self.parse_arr_elem()
            ])
        equals_node = self._expect("EQUALS")
        # Full array reassignment: arr[size] = [elem, elem, ...]
        if self._current().type == "OP_BRACKETS":
            return self._node("id_bracket_tail", [
                equals_node,
                self._expect("OP_BRACKETS"),
                self.parse_arr_cont_1d(),
                self._expect("CL_BRACKETS")
            ])
        # Single element assignment: arr[idx] = value
        return self._node("id_bracket_tail", [
            equals_node,
            self.parse_arr_elem()
        ])

    def parse_crema_member_inner(self):
        """Parse rule: crema_member_inner -> ID tail"""
        return self._node("crema_member_inner", [
            self._expect("ID"),
            self.parse_crema_member_inner_tail()
        ])

    def parse_crema_member_inner_tail(self):
        """Parse rule: crema_member_inner_tail -> [idx] tail | (args) | λ"""
        t = self._current().type
        if t == "OP_BRACKETS":
            return self._node("crema_member_inner_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail()
            ])
        if t == "OP_PAREN" and self._allow_function_calls:
            return self._node("crema_member_inner_tail", [
                self._expect("OP_PAREN"),
                self.parse_function_args(),
                self.parse_function_args_tail(),
                self._expect("CL_PAREN")
            ])
        return self._node("crema_member_inner_tail", [self._node("_empty")])

    # ========================================================================
    # 7. ORDER-LED STATEMENTS
    # ========================================================================

    def parse_order_dec_stmt(self):
        """Parse rule: order_dec_stmt -> order . ID tail"""
        return self._node("order_dec_stmt", [
            self._expect("ORDER"),
            self._expect("DOT_ACC"),
            self._expect("ID"),
            self.parse_order_dec_tail()
        ])

    def parse_order_dec_tail(self):
        """Parse rule: order_dec_tail -> [index] = value | = value | . ID tail | λ"""
        t = self._current().type
        if t == "OP_BRACKETS":
            return self._node("order_dec_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self._expect("EQUALS"),
                self.parse_assign_val()
            ])
        if t == "EQUALS":
            return self._node("order_dec_tail", [
                self._expect("EQUALS"),
                self.parse_assign_val()
            ])
        if t == "DOT_ACC":
            return self._node("order_dec_tail", [
                self._expect("DOT_ACC"),
                self._expect("ID"),
                self.parse_order_mug_tail()
            ])
        self._error({"OP_BRACKETS", "EQUALS", "DOT_ACC"})

    def parse_order_mug_tail(self):
        """Parse rule: order_mug_tail -> = value | λ"""
        return self._node("order_mug_tail", [
            self._expect("EQUALS"),
            self.parse_assign_val()
        ])

    # ========================================================================
    # 8. UNARY OPERATIONS
    # ========================================================================

    def parse_pre_unary_dec(self):
        """Parse rule: pre_unary_dec -> unary_op ID"""
        return self._node("pre_unary_dec", [
            self.parse_unary_op(),
            self._expect("ID")
        ])

    def parse_unary_op(self):
        """Parse rule: unary_op -> ++ | --"""
        t = self._current().type
        if t in self.UNARY_OP:
            return self._node("unary_op", [self._expect(t)])
        self._error(self.UNARY_OP)

    # ========================================================================
    # 9. DATA TYPES & VALUES
    # ========================================================================

    def parse_data_type(self):
        """Parse rule: data_type -> bean | drip | churro | temp"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("data_type", [self._expect(t)])
        self._error(self.DATA_TYPE)

    def parse_var_dec_const_init(self):
        """Parse rule: var_dec_const_init -> ID = value"""
        return self._node("var_dec_const_init", [
            self._expect("ID"),
            self._expect("EQUALS"),
            self.parse_value()
        ])

    def parse_var_dec_const_tail(self):
        """Parse rule: var_dec_const_tail -> (COMMA ID = value)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self._expect("ID"))
            children.append(self._expect("EQUALS"))
            children.append(self.parse_value())
        if not children:
            children.append(self._node("_empty"))
        return self._node("var_dec_const_tail", children)

    def parse_var_dec_init(self):
        """Parse rule: var_dec_init -> ID opt_assign"""
        return self._node("var_dec_init", [
            self._expect("ID"),
            self.parse_opt_assign()
        ])

    def parse_opt_assign(self):
        """Parse rule: opt_assign -> = value | λ"""
        if self._accept("EQUALS"):
            return self._node("opt_assign", [
                self._node("EQUALS", []),
                self.parse_value()
            ])
        return self._node("opt_assign", [self._node("_empty")])

    def parse_var_dec_tail(self):
        """Parse rule: var_dec_tail -> (COMMA var_dec_init)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_var_dec_init())
        if not children:
            children.append(self._node("_empty"))
        return self._node("var_dec_tail", children)

    def parse_value(self):
        """Parse rule: value -> expression"""
        return self._node("value", [self.parse_expression()])

    # ========================================================================
    # 10. EXPRESSION HIERARCHY
    # ========================================================================
    # Precedence: Logic > Relational > Arithmetic > Unary > Primary

    def parse_expression(self):
        """Parse rule: expression -> not_factor logic_expr_tail"""
        return self._node("expression", [
            self.parse_not_factor(),
            self.parse_logic_expr_tail()
        ])

    def parse_logic_expr_tail(self):
        """Parse rule: logic_expr_tail -> (logic_op not_factor)* | λ"""
        children = []
        while self._current().type in self.LOGIC_OP:
            children.append(self.parse_logic_op())
            children.append(self.parse_not_factor())
        if not children:
            children.append(self._node("_empty"))
        return self._node("logic_expr_tail", children)

    def parse_logic_op(self):
        """Parse rule: logic_op -> && | ||"""
        t = self._current().type
        if t in self.LOGIC_OP:
            return self._node("logic_op", [self._expect(t)])
        self._error(self.LOGIC_OP)

    def parse_not_factor(self):
        """Parse rule: not_factor -> ! rel_expr | rel_expr"""
        if self._accept("NOT"):
            return self._node("not_factor", [
                self._node("NOT", []),
                self.parse_rel_expr()
            ])
        return self._node("not_factor", [self.parse_rel_expr()])

    def parse_rel_expr(self):
        """Parse rule: rel_expr -> arith_expr rel_expr_tail"""
        return self._node("rel_expr", [
            self.parse_arith_expr(),
            self.parse_rel_expr_tail()
        ])

    def parse_rel_expr_tail(self):
        """Parse rule: rel_expr_tail -> (rel_op arith_expr)* | λ"""
        children = []
        while self._current().type in self.REL_OP:
            children.append(self.parse_rel_op())
            children.append(self.parse_arith_expr())
        if not children:
            children.append(self._node("_empty"))
        return self._node("rel_expr_tail", children)

    def parse_rel_op(self):
        """Parse rule: rel_op -> > | < | == | != | >= | <="""
        t = self._current().type
        if t in self.REL_OP:
            return self._node("rel_op", [self._expect(t)])
        self._error(self.REL_OP)

    def parse_arith_expr(self):
        """Parse rule: arith_expr -> unary_expr arith_expr_tail"""
        return self._node("arith_expr", [
            self.parse_unary_expr(),
            self.parse_arith_expr_tail()
        ])

    def parse_arith_expr_tail(self):
        """Parse rule: arith_expr_tail -> (arithm_op unary_expr)* | λ"""
        children = []
        while self._current().type in self.ARITHM_OP:
            children.append(self.parse_arithm_op())
            children.append(self.parse_unary_expr())
        if not children:
            children.append(self._node("_empty"))
        return self._node("arith_expr_tail", children)

    def parse_arithm_op(self):
        """Parse rule: arithm_op -> + | - | * | / | %"""
        t = self._current().type
        if t in self.ARITHM_OP:
            return self._node("arithm_op", [self._expect(t)])
        self._error(self.ARITHM_OP)

    def parse_unary_expr(self):
        """Parse rule: unary_expr -> ++ primary | -- primary | - neg_operand | primary"""
        t = self._current().type
        if t == "INCREMENT" and self._allow_unary_ops:
            return self._node("unary_expr", [
                self._expect("INCREMENT"),
                self._expect("ID")
            ])
        if t == "DECREMENT" and self._allow_unary_ops:
            return self._node("unary_expr", [
                self._expect("DECREMENT"),
                self._expect("ID")
            ])
        if t == "MINUS":
            return self._node("unary_expr", [
                self._expect("MINUS"),
                self.parse_neg_operand()
            ])
        return self._node("unary_expr", [self.parse_primary()])

    def parse_neg_operand(self):
        """Parse rule: neg_operand -> ID | (expression)"""
        if self._accept("ID"):
            return self._node("neg_operand", [self._node("ID", [])])
        if self._accept("OP_PAREN"):
            return self._node("neg_operand", [
                self._node("OP_PAREN", []),
                self.parse_expression(),
                self._expect("CL_PAREN")
            ])
        self._error({"ID", "OP_PAREN"})

    def parse_primary(self):
        """Parse rule: primary -> ID tail | order.ID tail | literal | (expression)"""
        t = self._current().type
        if t == "ID":
            return self._node("primary", [
                self._expect("ID"),
                self.parse_primary_id_tail()
            ])
        if t == "ORDER":
            return self._node("primary", [
                self._expect("ORDER"),
                self._expect("DOT_ACC"),
                self._expect("ID"),
                self.parse_primary_order_tail()
            ])
        if t in self.PRIMARY_LITERALS:
            return self._node("primary", [self._expect(t)])
        if t == "OP_PAREN":
            return self._node("primary", [
                self._expect("OP_PAREN"),
                self.parse_expression(),
                self._expect("CL_PAREN")
            ])
        
        # =================================================
        # PRE_DEFINED FUNCTIONS HAHAHAHAHAHAHAHA YES
        # =================================================
        if t == "SIFT":
            return self._node("primary", [
                self._expect("SIFT"),
                self._expect("OP_PAREN"),
                self.parse_sift_arg(),
                self._expect("CL_PAREN")
            ])
        if t == "SQRT":
            return self._node("primary", [
                self._expect("SQRT"), 
                self._expect("OP_PAREN"),
                self.parse_expression(), 
                self._expect("CL_PAREN")
            ])
        if t == "CEIL":
            return self._node("primary", [
                self._expect("CEIL"), 
                self._expect("OP_PAREN"),
                self.parse_expression(), 
                self._expect("CL_PAREN")
            ])
        if t == "FLOOR":
            return self._node("primary", [
                self._expect("FLOOR"), 
                self._expect("OP_PAREN"),
                self.parse_expression(), 
                self._expect("CL_PAREN")
            ])
        if t == "POW":
            return self._node("primary", [
                self._expect("POW"), 
                self._expect("OP_PAREN"),
                self.parse_expression(), 
                self._expect("COMMA"), 
                self.parse_expression(),
                self._expect("CL_PAREN")
            ])
        if t == "RAND":
            return self._node("primary", [
                self._expect("RAND"), 
                self._expect("OP_PAREN"),
                self.parse_expression(), 
                self._expect("COMMA"), 
                self.parse_expression(), 
                self._expect("CL_PAREN")
            ])
        if t == "TYPE":
            return self._node("primary", [
                self._expect("TYPE"), 
                self._expect("OP_PAREN"),
                self.parse_expression(), 
                self._expect("CL_PAREN")
            ])
        self._error({
            "ID", "ORDER", "BEANLIT", "DRIPLIT", "CHURROLIT",
            "HOT", "COLD", "BLENDLIT", "OP_PAREN"
        })

    def parse_primary_id_tail(self):
        """Parse rule: primary_id_tail -> . ID dotTail | (args) | [idx] tail | op | λ"""
        t = self._current().type
        if t == "DOT_ACC":
            return self._node("primary_id_tail", [
                self._expect("DOT_ACC"),
                self._expect("ID"),
                self.parse_primary_dot_tail()
            ])
        if t == "OP_PAREN" and self._allow_function_calls:
            return self._node("primary_id_tail", [
                self._expect("OP_PAREN"),
                self.parse_function_args(),
                self.parse_function_args_tail(),
                self._expect("CL_PAREN")
            ])
        if t == "OP_BRACKETS":
            return self._node("primary_id_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail()
            ])
        if t in self.UNARY_OP and self._allow_unary_ops:
            return self._node("primary_id_tail", [self.parse_unary_op()])
        return self._node("primary_id_tail", [self._node("_empty")])

    def parse_primary_dot_tail(self):
        """Parse rule: primary_dot_tail -> . member | [idx] tail | (args) | λ"""
        t = self._current().type
        if t == "DOT_ACC":
            return self._node("primary_dot_tail", [
                self._expect("DOT_ACC"),
                self.parse_crema_member_inner()
            ])
        if t == "OP_BRACKETS":
            return self._node("primary_dot_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail()
            ])
        if t == "OP_PAREN" and self._allow_function_calls:
            return self._node("primary_dot_tail", [
                self._expect("OP_PAREN"),
                self.parse_function_args(),
                self.parse_function_args_tail(),
                self._expect("CL_PAREN")
            ])  
        return self._node("primary_dot_tail", [self._node("_empty")])

    def parse_primary_order_tail(self):
        """Parse rule: primary_order_tail -> [index] | . ID | λ"""
        if self._current().type == "OP_BRACKETS":
            return self._node("primary_order_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS")
            ])
        if self._accept("DOT_ACC"):
            return self._node("primary_order_tail", [
                self._node("DOT_ACC", []),
                self._expect("ID")
            ])
        return self._node("primary_order_tail", [self._node("_empty")])

    # ========================================================================
    # 11. ARRAYS
    # ========================================================================

    def parse_arr_call_tail(self):
        """Parse rule: arr_call_tail -> [idx] | λ"""
        if self._accept("OP_BRACKETS"):
            return self._node("arr_call_tail", [
                self._node("OP_BRACKETS", []),
                self.parse_array_index(),
                self._expect("CL_BRACKETS")
            ])
        return self._node("arr_call_tail", [self._node("_empty")])

    def parse_array_index(self):
        """Parse rule: array_index -> expression"""
        return self._node("array_index", [self.parse_expression()])

    def parse_arr_size_val(self):
        """Parse rule: arr_size_val -> BEANLIT | *** (flexible size)"""
        t = self._current().type
        if t == "BEANLIT":
            return self._node("arr_size_val", [self._expect("BEANLIT")])
        if t == "ID":
            return self._node("arr_size_val", [self._expect("ID")])
        if t == "FLEX_ASTERISK":
            return self._node("arr_size_val", [self._expect("FLEX_ASTERISK")])
        self._error({"BEANLIT", "ID", "FLEX_ASTERISK"})

    def parse_arr_dec_dim(self):
        """Parse rule: arr_dec_dim -> [size] = [2D content] | = [1D content] | λ"""
        if self._accept("OP_BRACKETS"):
            return self._node("arr_dec_dim", [
                self._node("OP_BRACKETS", []),
                self.parse_arr_size_val(),
                self._expect("CL_BRACKETS"),
                self._expect("EQUALS"),
                self._expect("OP_BRACKETS"),
                self.parse_arr_cont_2d(),
                self._expect("CL_BRACKETS")
            ])
        if self._current().type == "EQUALS":
            return self._node("arr_dec_dim", [
                self._expect("EQUALS"),
                self._expect("OP_BRACKETS"),
                self.parse_arr_cont_1d(),
                self._expect("CL_BRACKETS")
            ])
        
        # λ — standalone array declaration without initializer
        return self._node("arr_dec_dim", [self._node("_empty")])

    def parse_blend_arr_dec_dim(self):
        """Parse rule: blend_arr_dec_dim -> [size] = [2D] | = [1D] (for blend arrays)"""
        if self._accept("OP_BRACKETS"):
            return self._node("blend_arr_dec_dim", [
                self._node("OP_BRACKETS", []),
                self.parse_arr_size_val(),
                self._expect("CL_BRACKETS"),
                self._expect("EQUALS"),
                self._expect("OP_BRACKETS"),
                self.parse_blend_arr_cont_2d(),
                self._expect("CL_BRACKETS")
            ])
        return self._node("blend_arr_dec_dim", [
            self._expect("EQUALS"),
            self._expect("OP_BRACKETS"),
            self.parse_blend_arr_cont_1d(),
            self._expect("CL_BRACKETS")
        ])

    def parse_arr_elem(self):
        """Parse rule: arr_elem -> expression (no standalone ++/-- allowed)"""
        saved = self._allow_unary_ops
        self._allow_unary_ops = False
        try:
            result = self._node("arr_elem", [self.parse_expression()])
        finally:
            self._allow_unary_ops = saved
        return result

    def parse_ext_arr_elem(self):
        """Parse rule: ext_arr_elem -> (COMMA arr_elem)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_arr_elem())
        if not children:
            children.append(self._node("_empty"))
        return self._node("ext_arr_elem", children)

    def parse_arr_cont_1d(self):
        """Parse rule: arr_cont_1d -> elem array_elements | λ"""
        if self._is_start_expression():
            return self._node("arr_cont_1d", [
                self.parse_arr_elem(),
                self.parse_ext_arr_elem()
            ])
        return self._node("arr_cont_1d", [self._node("_empty")])

    def parse_opt_arr_elems(self):
        """Parse rule: opt_arr_elems -> arr_elem ext_arr_elem | λ"""
        if self._is_start_expression():
            return self._node("opt_arr_elems", [
                self.parse_arr_elem(),
                self.parse_ext_arr_elem()
            ])
        return self._node("opt_arr_elems", [self._node("_empty")])

    def parse_arr_cont_2d(self):
        """Parse rule: arr_cont_2d -> [elems], [elems] (, [elems])*"""
        return self._node("arr_cont_2d", [
            self._expect("OP_BRACKETS"),
            self.parse_opt_arr_elems(),
            self._expect("CL_BRACKETS"),
            self._expect("COMMA"),
            self._expect("OP_BRACKETS"),
            self.parse_opt_arr_elems(),
            self._expect("CL_BRACKETS"),
            self.parse_arr_cont_2d_tail()
        ])

    def parse_arr_cont_2d_tail(self):
        """Parse rule: arr_cont_2d_tail -> (COMMA [...])* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self._expect("OP_BRACKETS"))
            children.append(self.parse_opt_arr_elems())
            children.append(self._expect("CL_BRACKETS"))
        if not children:
            children.append(self._node("_empty"))
        return self._node("arr_cont_2d_tail", children)

    # ========================================================================
    # 12. FUNCTIONS & ARGUMENTS
    # ========================================================================

    def parse_function_call(self):
        """Parse rule: function_call -> ID (args)"""
        return self._node("function_call", [
            self._expect("ID"),
            self._expect("OP_PAREN"),
            self.parse_function_args(),
            self.parse_function_args_tail(),
            self._expect("CL_PAREN")
        ])

    def parse_sift_call(self): # PRE-DEFINED - is length()
        """Parse rule: function_call -> ID (args)"""
        return self._node("sift_call", [
            self._expect("ID"),
            self._expect("OP_PAREN"),
            self._expect("CL_PAREN")
        ])

    def parse_sift_arg(self):
        """Parse rule: sift_arg -> expression"""
        return self._node("sift_arg", [self.parse_expression()])
    
    def parse_function_args(self):
        """Parse rule: function_args -> BLENDLIT | expression | λ"""
        t = self._current().type
        if t == "BLENDLIT":
            return self._node("function_args", [self._expect("BLENDLIT")])
        if self._is_start_expression():
            return self._node("function_args", [self.parse_expression()])
        return self._node("function_args", [self._node("_empty")])

    def parse_function_args_tail(self):
        """Parse rule: function_args_tail -> (COMMA args)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_function_args())
        if not children:
            children.append(self._node("_empty"))
        return self._node("function_args_tail", children)

    # ========================================================================
    # 13. MUG (STRUCT) DECLARATIONS
    # ========================================================================

    def parse_mug_dec(self):
        """Parse rule: mug_dec -> mug ID [var_list]"""
        return self._node("mug_dec", [
            self._expect("MUG"),
            self._expect("ID"),
            self._expect("OP_BRACKETS"),
            self.parse_dtype_mug_var(),
            self.parse_mug_var_dec_cont(),
            self._expect("CL_BRACKETS")
        ])

    def parse_dtype_mug_var(self):
        """Parse rule: dtype_mug_var -> brewed body | data_type var_init"""
        t = self._current().type
        if t == "BREWED":
            return self._node("dtype_mug_var", [
                self._expect("BREWED"),
                self.parse_mug_brewed_body()
            ])
        if t in self.DATA_TYPE:
            return self._node("dtype_mug_var", [
                self.parse_data_type(),
                self.parse_var_dec_init(),
                self.parse_var_dec_tail()
            ])
        self._error({"BREWED"}.union(self.DATA_TYPE))

    def parse_mug_brewed_body(self):
        """Parse rule: mug_brewed_body -> data_type const_init_list"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("mug_brewed_body", [
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        self._error(self.DATA_TYPE)

    def parse_mug_var_dec_cont(self):
        """Parse rule: mug_var_dec_cont -> (dtype_mug_var)* | λ"""
        children = []
        while self._current().type in {"BREWED"}.union(self.DATA_TYPE):
            children.append(self.parse_dtype_mug_var())
        if not children:
            children.append(self._node("_empty"))
        return self._node("mug_var_dec_cont", children)

    # ========================================================================
    # 14. OBJECTS
    # ========================================================================

    def parse_object_def(self):
        """Parse rule: object_def -> new ID = ID"""
        return self._node("object_def", [
            self._expect("NEW"),
            self._expect("ID"),
            self._expect("EQUALS"),
            self._expect("ID")
        ])

    # ========================================================================
    # 15. RECIPES (FUNCTIONS)
    # ========================================================================

    def parse_recipe_def(self):
        """Parse rule: recipe_def -> recipe return_type ID (params) { body refill }"""
        return self._node("recipe_def", [
            self._expect("RECIPE"),
            self.parse_recipe_ret_type(),
            self._expect("ID"),
            self._expect("OP_PAREN"),
            self.parse_parameter(),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACKETS"),
            self.parse_recipe_body(),
            self.parse_refill_final(),
            self._expect("CL_BRACKETS")
        ])

    def parse_recipe_ret_type(self):
        """Parse rule: recipe_ret_type -> data_type"""
        if self._current().type in self.DATA_TYPE:
            return self._node("recipe_ret_type", [self.parse_data_type()])
        self._error(self.DATA_TYPE)

    def parse_parameter(self):
        """Parse rule: parameter -> dtype_param add_param | λ"""
        if self._current().type in self.DATA_TYPE:
            return self._node("parameter", [
                self.parse_dtype_param(),
                self.parse_add_param()
            ])
        return self._node("parameter", [self._node("_empty")])

    def parse_dtype_param(self):
        """Parse rule: dtype_param -> data_type ID opt_assign"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("dtype_param", [
                self.parse_data_type(),
                self.parse_var_dec_init(),
            ])
        self._error({"BLEND"}.union(self.DATA_TYPE))

    def parse_param_brewed_body(self):
        """Parse rule: param_brewed_body -> data_type const_init_list"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("param_brewed_body", [
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        self._error({"BLEND"}.union(self.DATA_TYPE))

    def parse_param_dtype_body(self):
        """Parse rule: param_dtype_body -> brewed data_type init | data_type var_init"""
        t = self._current().type
        if t == "BREWED":
            return self._node("param_dtype_body", [
                self._expect("BREWED"),
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        if t in self.DATA_TYPE:
            return self._node("param_dtype_body", [
                self.parse_data_type(),
                self.parse_var_dec_init(),
                # self.parse_var_dec_tail()
            ])
        self._error({"BREWED"}.union(self.DATA_TYPE))

    def parse_param_id_tail(self):
        """Parse rule: param_id_tail -> . ID"""
        return self._node("param_id_tail", [
            self._expect("DOT_ACC"),
            self._expect("ID")
        ])

    def parse_add_param(self):
        """Parse rule: add_param -> (COMMA dtype_param)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_dtype_param())
        if not children:
            children.append(self._node("_empty"))
        return self._node("add_param", children)

    def parse_recipe_body(self):
        """Parse rule: recipe_body -> (statement)* | λ

        Stops before REFILL so that the mandatory refill_final can parse it.
        Any refill? inside control flow blocks (ifbrew/elspress) is handled
        by parse_statement, which is called from those blocks' own contexts.
        """
        children = []
        while self._is_start_statement() and self._current().type != "REFILL":
            children.append(self.parse_statement())
        if not children:
            children.append(self._node("_empty"))
        return self._node("recipe_body", children)

    def parse_refill_final(self):
        """Parse rule: refill_final -> refill? arg"""
        return self._node("refill_final", [
            self._expect("REFILL"),
            self.parse_refill_arg()
        ])

    def parse_refill_arg(self):
        """Parse rule: refill_arg -> (refill_content, ...) | 0"""
        if self._accept("OP_PAREN"):
            return self._node("refill_arg", [
                self._node("OP_PAREN", []),
                self.parse_refill_content(),
                self.parse_extra_refill_val(),
                self._expect("CL_PAREN")
            ])
        return self._node("refill_arg", [self._expect("ZERO")])

    def parse_refill_content(self):
        """Parse rule: refill_content -> BLENDLIT | expression"""
        if self._current().type == "BLENDLIT":
            return self._node("refill_content", [self._expect("BLENDLIT")])
        return self._node("refill_content", [self.parse_expression()])

    def parse_extra_refill_val(self):
        """Parse rule: extra_refill_val -> (COMMA refill_content)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_refill_content())
        if not children:
            children.append(self._node("_empty"))
        return self._node("extra_refill_val", children)

    # ========================================================================
    # 16. EMPTY (VOID FUNCTIONS)
    # ========================================================================

    def parse_empty_def(self):
        """Parse rule: empty_def -> empty ID (params) { body refill }"""
        return self._node("empty_def", [
            self._expect("EMPTY"),
            self._expect("ID"),
            self._expect("OP_PAREN"),
            self.parse_parameter(),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACKETS"),
            self.parse_empty_body(),
            self._expect("REFILL"),
            self._expect("CL_BRACKETS")
        ])

    def parse_empty_body(self):
        """Parse rule: empty_body -> (statement)* | λ
        """
        children = []
        while self._is_start_statement() and self._current().type != "REFILL":
            children.append(self.parse_statement())
        if not children:
            children.append(self._node("_empty"))
        return self._node("empty_body", children)

    # ========================================================================
    # 17. CREMA (CLASSES)
    # ========================================================================

    def parse_crema_def(self):
        """Parse rule: crema_def -> crema ID { body }"""
        return self._node("crema_def", [
            self._expect("CREMA"),
            self._expect("ID"),
            self._expect("OP_BRACKETS"),
            self.parse_crema_body(),
            self._expect("CL_BRACKETS")
        ])

    def parse_crema_body(self):
        """Parse rule: crema_body -> (crema_body_cont)* | λ"""
        children = []
        while self._current().type in {
            "CAFE", "BACKROOM", "BREWED", "BLEND", "RECIPE", "EMPTY"
        }.union(self.DATA_TYPE):
            children.append(self.parse_crema_body_cont())
        if not children:
            children.append(self._node("_empty"))
        return self._node("crema_body", children)

    def parse_crema_body_cont(self):
        """Parse rule: crema_body_cont -> cafe body | backroom body | dtype_body"""
        t = self._current().type
        if t == "CAFE":
            return self._node("crema_body_cont", [
                self._expect("CAFE"),
                self.parse_crema_acc_body()
            ])
        if t == "BACKROOM":
            return self._node("crema_body_cont", [
                self._expect("BACKROOM"),
                self.parse_crema_acc_body()
            ])
        return self._node("crema_body_cont", [self.parse_crema_dtype_body()])

    def parse_crema_acc_body(self):
        """Parse rule: crema_acc_body -> recipe data_type declarations"""
        t = self._current().type
        if t == "RECIPE":
            return self._node("crema_acc_body", [
                self._expect("RECIPE"),
                self.parse_data_type(),
                self._expect("ID"),
                self._expect("OP_PAREN"),
                self.parse_parameter(),
                self._expect("CL_PAREN"),
                self._expect("OP_BRACKETS"),
                self.parse_recipe_body(),
                self.parse_refill_final(),
                self._expect("CL_BRACKETS")
            ])
        if t == "EMPTY":
            return self._node("crema_acc_body", [
                self._expect("EMPTY"),
                self._expect("ID"),
                self._expect("OP_PAREN"),
                self.parse_parameter(),
                self._expect("CL_PAREN"),
                self._expect("OP_BRACKETS"),
                self.parse_empty_body(),
                self._expect("REFILL"),
                self._expect("CL_BRACKETS")
            ])
        if t == "BREWED":
            return self._node("crema_acc_body", [
                self._expect("BREWED"),
                self.parse_crema_acc_brewed_body()
            ])
        if t in self.DATA_TYPE:
            return self._node("crema_acc_body", [
                self.parse_data_type(),
                self._expect("ID"),
                self.parse_crema_dtype_id_tail()
            ])
        self._error({"RECIPE", "EMPTY", "BREWED"}.union(self.DATA_TYPE))

    def parse_crema_acc_brewed_body(self):
        """Parse rule: crema_acc_brewed_body -> data_type const_init_list"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("crema_acc_brewed_body", [
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        self._error(self.DATA_TYPE)

    def parse_crema_dtype_body(self):
        """Parse rule: crema_dtype_body -> recipe | empty | brewed | data_type | blend"""
        t = self._current().type
        if t == "RECIPE":
            return self._node("crema_dtype_body", [
                self._expect("RECIPE"),
                self.parse_crema_recipe_type(),
                self._expect("ID"),
                self._expect("OP_PAREN"),
                self.parse_parameter(),
                self._expect("CL_PAREN"),
                self._expect("OP_BRACKETS"),
                self.parse_recipe_body(),
                self.parse_refill_final(),
                self._expect("CL_BRACKETS")
            ])
        if t == "EMPTY":
            return self._node("crema_dtype_body", [
                self._expect("EMPTY"),
                self._expect("ID"),
                self._expect("OP_PAREN"),
                self.parse_parameter(),
                self._expect("CL_PAREN"),
                self._expect("OP_BRACKETS"),
                self.parse_empty_body(),
                self._expect("REFILL"),
                self._expect("CL_BRACKETS")
            ])
        if t == "BREWED":
            return self._node("crema_dtype_body", [
                self._expect("BREWED"),
                self.parse_crema_dtype_brewed_body()
            ])
        if t in self.DATA_TYPE:
            return self._node("crema_dtype_body", [
                self.parse_data_type(),
                self._expect("ID"),
                self.parse_crema_dtype_id_tail()
            ])
        self._error({"RECIPE", "EMPTY", "BREWED"}.union(self.DATA_TYPE))

    def parse_crema_recipe_type(self):
        """Parse rule: crema_recipe_type -> data_type"""
        if self._current().type in self.DATA_TYPE:
            return self._node("crema_recipe_type", [self.parse_data_type()])
        self._error(self.DATA_TYPE)

    def parse_crema_dtype_brewed_body(self):
        """Parse rule: crema_dtype_brewed_body -> data_type const_init_list"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("crema_dtype_brewed_body", [
                self.parse_data_type(),
                self.parse_var_dec_const_init(),
                self.parse_var_dec_const_tail()
            ])
        self._error(self.DATA_TYPE)

    def parse_crema_dtype_id_tail(self):
        """Parse rule: crema_dtype_id_tail -> [size] array_decl | opt_assign var_list"""
        if self._accept("OP_BRACKETS"):
            return self._node("crema_dtype_id_tail", [
                self._node("OP_BRACKETS", []),
                self.parse_arr_size_val(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_dec_dim()
            ])
        return self._node("crema_dtype_id_tail", [
            self.parse_opt_assign(),
            self.parse_var_dec_tail()
        ])

    # ========================================================================
    # 18. MAIN DEFINITIONS
    # ========================================================================

    def parse_main_def(self):
        """Parse rule: main_def -> bean cup () { body }"""
        return self._node("main_def", [
            self._expect("BEAN"),
            self._expect("CUP"),
            self._expect("OP_PAREN"),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACKETS"),
            self.parse_main_body()
        ])

    def parse_refill_main(self):
        """Parse rule: refill_main -> refill? 0 tail"""
        return self._node("refill_main", [
            self._expect("REFILL"),
            self._expect("ZERO"),
            self.parse_refill_main_tail()
        ])

    def parse_refill_main_tail(self):
        """Parse rule: refill_main_tail -> main_body | }"""
        if self._current().type == "CL_BRACKETS":
            return self._node("refill_main_tail", [
                self._expect("CL_BRACKETS")
            ])
        if self._is_start_statement() or self._current().type == "REFILL":
            return self._node("refill_main_tail", [self.parse_main_body()])
        self._error({"CL_BRACKETS"})

    def parse_main_body(self):
        """Parse rule: main_body -> statement main_body | refill_main"""
        if self._is_start_statement() and self._current().type != "REFILL":
            return self._node("main_body", [
                self.parse_statement(),
                self.parse_main_body()
            ])
        return self._node("main_body", [self.parse_refill_main()])

    # ========================================================================
    # 19. STATEMENTS
    # ========================================================================

    def parse_statement(self):
        """Parse rule: statement -> dec | input | output | if | switch | loops | interrupt | refill_stmt"""
        t = self._current().type
        if t in {
            "CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP",
            "ID", "ORDER", "INCREMENT", "DECREMENT", "MUG", "NEW"
        }:
            return self._node("statement", [self.parse_dec()])
        if t == "BATTER":
            return self._node("statement", [self.parse_input_stmt()])
        if t == "GLAZE":
            return self._node("statement", [self.parse_output_stmt()])
        if t == "IFBREW":
            return self._node("statement", [self.parse_if_cond()])
        if t == "FLAVOUR":
            return self._node("statement", [self.parse_flav_switch()])
        if t == "POUR":
            return self._node("statement", [self.parse_pour_loop()])
        if t == "WHILEHOT":
            return self._node("statement", [self.parse_whilehot_loop()])
        if t == "TASTE":
            return self._node("statement", [self.parse_tastetill_loop()])
        if t in {"SNAP", "SKIP"}:
            return self._node("statement", [self.parse_intrpt_stmt()])
        if t == "REFILL":
            return self._node("statement", [self.parse_refill_stmt()])
        self._error({
            "CAFE", "BACKROOM", "BREWED", "BLEND", "BEAN", "DRIP", "CHURRO", "TEMP",
            "ID", "ORDER", "INCREMENT", "DECREMENT", "MUG", "NEW",
            "BATTER", "GLAZE", "IFBREW", "FLAVOUR", "POUR", "WHILEHOT", "TASTE",
            "SNAP", "SKIP", "REFILL"
        })

    def parse_stmt_tail(self):
        """Parse rule: stmt_tail -> (statement)* | λ"""
        children = []
        while self._is_start_statement():
            children.append(self.parse_statement())
        if not children:
            children.append(self._node("_empty"))
        return self._node("stmt_tail", children)

    def parse_stmt_tail_until_snap(self):
        """Parse rule: stmt_tail_until_snap -> (statement except snap)* | λ"""
        children = []
        while self._is_start_statement() and self._current().type != "SNAP":
            children.append(self.parse_statement())
        if not children:
            children.append(self._node("_empty"))
        return self._node("stmt_tail_until_snap", children)
    
    def parse_refill_stmt(self):
        """Parse rule: refill_stmt -> refill? refill_arg

        Allows refill? to appear as a statement inside control flow blocks
        (e.g., ifbrew/elspress), enabling early returns for recursive functions.
        """
        return self._node("refill_stmt", [
            self._expect("REFILL"),
            self.parse_refill_arg()
        ])

    # ========================================================================
    # 20. INPUT/OUTPUT
    # ========================================================================

    def parse_input_stmt(self):
        """Parse rule: input_stmt -> batter@ args input_val"""
        return self._node("input_stmt", [
            self._expect("BATTER"),
            self.parse_input_args(),
            self.parse_input_val()
        ])

    def parse_input_args(self):
        """Parse rule: input_args -> arg_unit (COMMA arg_unit)*"""
        return self._node("input_args", [
            self.parse_input_args_unit(),
            self.parse_input_args_unit_tail()
        ])

    def parse_input_args_unit(self):
        """Parse rule: input_args_unit -> order.ID tail | ID tail"""
        if self._current().type == "ORDER":
            return self._node("input_args_unit", [
                self._expect("ORDER"),
                self._expect("DOT_ACC"),
                self._expect("ID"),
                self.parse_input_order_tail()
            ])
        return self._node("input_args_unit", [
            self._expect("ID"),
            self.parse_input_id_tail()
        ])

    def parse_input_id_tail(self):
        """Parse rule: input_id_tail -> . ID tail | [idx] tail | λ"""
        t = self._current().type
        if t == "DOT_ACC":
            return self._node("input_id_tail", [
                self._expect("DOT_ACC"),
                self._expect("ID"),
                self.parse_input_dot_tail()
            ])
        if t == "OP_BRACKETS":
            return self._node("input_id_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail()
            ])
        return self._node("input_id_tail", [self._node("_empty")])

    def parse_input_dot_tail(self):
        """Parse rule: input_dot_tail -> . ID | λ"""
        if self._accept("DOT_ACC"):
            return self._node("input_dot_tail", [
                self._node("DOT_ACC", []),
                self._expect("ID")
            ])
        return self._node("input_dot_tail", [self._node("_empty")])

    def parse_input_order_tail(self):
        """Parse rule: input_order_tail -> [idx] | . ID | λ"""
        t = self._current().type
        if t == "OP_BRACKETS":
            return self._node("input_order_tail", [
                self._expect("OP_BRACKETS"),
                self.parse_array_index(),
                self._expect("CL_BRACKETS"),
                self.parse_arr_call_tail()
            ])
        if t == "DOT_ACC":
            return self._node("input_order_tail", [
                self._node("DOT_ACC", []),
                self._expect("DOT_ACC"),
                self._expect("ID")
            ])
        return self._node("input_order_tail", [self._node("_empty")])

    def parse_input_args_unit_tail(self):
        """Parse rule: input_args_unit_tail -> (COMMA unit)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_input_args_unit())
        if not children:
            children.append(self._node("_empty"))
        return self._node("input_args_unit_tail", children)

    def parse_input_val(self):
        """Parse rule: input_val -> (BLENDLIT) | λ"""
        if self._accept("OP_PAREN"):
            return self._node("input_val", [
                self._node("OP_PAREN", []),
                self._expect("BLENDLIT"),
                self._expect("CL_PAREN")
            ])
        return self._node("input_val", [self._node("_empty")])

    def parse_output_stmt(self):
        """Parse rule: output_stmt -> glaze (output_args)"""
        return self._node("output_stmt", [
            self._expect("GLAZE"),
            self._expect("OP_PAREN"),
            self.parse_output_args(),
            self._expect("CL_PAREN")
        ])

    def parse_output_args(self):
        """Parse rule: output_args -> BLENDLIT concat | expression concat | λ"""
        if self._current().type == "BLENDLIT":
            return self._node("output_args", [
                self._expect("BLENDLIT"),
                self.parse_concat()
            ])
        if self._is_start_expression():
            return self._node("output_args", [
                self.parse_expression(),
                self.parse_concat()
            ])
        return self._node("output_args", [self._node("_empty")])

    def parse_concat(self):
        """Parse rule: concat -> (+ blend_term)* | λ"""
        children = []
        while self._accept("PLUS"):
            children.append(self._node("PLUS", []))
            children.append(self.parse_blend_term())
        if not children:
            children.append(self._node("_empty"))
        return self._node("concat", children)

    # ========================================================================
    # 21. CONTROL FLOW (IF/SWITCH/LOOPS)
    # ========================================================================

    def parse_if_cond(self):
        """Parse rule: if_cond -> ifbrew (expr) { stmts } tail"""
        return self._node("if_cond", [
            self._expect("IFBREW"),
            self._expect("OP_PAREN"),
            self.parse_expression(),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACES"),
            self.parse_statement(),
            self.parse_stmt_tail(),
            self._expect("CL_BRACES"),
            self.parse_if_cond_tail()
        ])

    def parse_if_cond_tail(self):
        """Parse rule: if_cond_tail -> elifroth condition | elspress stmts | λ"""
        t = self._current().type
        if t == "ELIFROTH":
            return self._node("if_cond_tail", [
                self._expect("ELIFROTH"),
                self._expect("OP_PAREN"),
                self.parse_expression(),
                self._expect("CL_PAREN"),
                self._expect("OP_BRACES"),
                self.parse_statement(),
                self.parse_stmt_tail(),
                self._expect("CL_BRACES"),
                self.parse_if_cond_tail()
            ])
        if t == "ELSPRESS":
            return self._node("if_cond_tail", [
                self._expect("ELSPRESS"),
                self._expect("OP_BRACES"),
                self.parse_statement(),
                self.parse_stmt_tail(),
                self._expect("CL_BRACES")
            ])
        return self._node("if_cond_tail", [self._node("_empty")])

    def parse_flav_switch(self):
        """Parse rule: flav_switch -> flavour (lit) { cases }"""
        return self._node("flav_switch", [
            self._expect("FLAVOUR"),
            self._expect("OP_PAREN"),
            self.parse_flav_lit(),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACES"),
            self.parse_syrup_switch(),
            self._expect("CL_BRACES")
        ])

    def parse_flav_lit(self):
        """Parse rule: flav_lit -> BEANLIT | ID | CHURROLIT | hot | cold"""
        t = self._current().type
        if t in {"BEANLIT", "ID", "CHURROLIT", "HOT", "COLD"}:
            return self._node("flav_lit", [self._expect(t)])
        self._error({"BEANLIT", "ID", "CHURROLIT", "HOT", "COLD"})

    def parse_syrup_switch(self):
        """Parse rule: syrup_switch -> syrup lit : stmts snap defoam tail"""
        return self._node("syrup_switch", [
            self._expect("SYRUP"),
            self.parse_case_lit(),
            self._expect("COLON"),
            self.parse_statement(),
            self.parse_stmt_tail_until_snap(),
            self._expect("SNAP"),
            self.parse_defoam_stmt(),
            self.parse_syrup_switch_tail()
        ])

    def parse_syrup_switch_tail(self):
        """Parse rule: syrup_switch_tail -> syrup_switch | λ"""
        if self._current().type == "SYRUP":
            return self._node("syrup_switch_tail", [self.parse_syrup_switch()])
        return self._node("syrup_switch_tail", [self._node("_empty")])

    def parse_case_lit(self):
        """Parse rule: case_lit -> BEANLIT | CHURROLIT | hot | cold"""
        t = self._current().type
        if t in {"BEANLIT", "CHURROLIT", "HOT", "COLD"}:
            return self._node("case_lit", [self._expect(t)])
        self._error({"BEANLIT", "CHURROLIT", "HOT", "COLD"})

    def parse_defoam_stmt(self):
        """Parse rule: defoam_stmt -> defoam : stmts snap | λ"""
        if self._accept("DEFOAM"):
            return self._node("defoam_stmt", [
                self._node("DEFOAM", []),
                self._expect("COLON"),
                self.parse_statement(),
                self.parse_stmt_tail_until_snap(),
                self._expect("SNAP")
            ])
        return self._node("defoam_stmt", [self._node("_empty")])

    def parse_pour_condition(self):
        """Parse pour loop condition: must be a boolean/relational expression.

        Rejects bare identifiers or arithmetic-only expressions that lack
        relational operators (>, <, ==, !=, >=, <=), logical operators
        (&&, ||), NOT (!), or boolean literals (hot, cold).
        """
        expr = self.parse_expression()
        if not self._has_boolean_content(expr):
            tok = self._current()
            raise UnexpectedToken(
                tok,
                self.REL_OP | self.LOGIC_OP | {"NOT"},
                index=self.stream.index
            )
        return expr

    def parse_pour_loop(self):
        """Parse rule: pour_loop -> pour (init; cond; update) { body }"""
        return self._node("pour_loop", [
            self._expect("POUR"),
            self._expect("OP_PAREN"),
            self.parse_pour_init(),
            self._expect("SEMICOLON"),
            self.parse_pour_condition(),
            self._expect("SEMICOLON"),
            self.parse_update(),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACES"),
            self.parse_statement(),
            self.parse_stmt_tail(),
            self._expect("CL_BRACES")
        ])

    def parse_pour_init(self):
        """Parse rule: pour_init -> data_type ID = value (COMMA init)*  | ID = value"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("pour_init", [
                self.parse_data_type(),
                self._expect("ID"),
                self._expect("EQUALS"),
                self.parse_value(),
                self.parse_var_dec_const_tail()
            ])
        if t == "ID":
            return self._node("pour_init", [
                self._expect("ID"),
                self._expect("EQUALS"),
                self.parse_value(),
                self.parse_var_dec_const_tail()
            ])
        self._error(self.DATA_TYPE | {"ID"})

    def parse_update(self):
        """Parse rule: update -> unit (COMMA unit)*"""
        return self._node("update", [
            self.parse_update_unit(),
            self.parse_update_tail()
        ])

    def parse_update_tail(self):
        """Parse rule: update_tail -> (COMMA unit)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_update_unit())
        if not children:
            children.append(self._node("_empty"))
        return self._node("update_tail", children)

    def parse_update_unit(self):
        """Parse rule: update_unit -> ID tail | ++ ID | -- ID"""
        t = self._current().type
        if t == "ID":
            return self._node("update_unit", [
                self._expect("ID"),
                self.parse_update_id_tail()
            ])
        if t == "INCREMENT":
            return self._node("update_unit", [
                self._expect("INCREMENT"),
                self._expect("ID")
            ])
        if t == "DECREMENT":
            return self._node("update_unit", [
                self._expect("DECREMENT"),
                self._expect("ID")
            ])
        self._error({"ID", "INCREMENT", "DECREMENT"})

    def parse_update_id_tail(self):
        """Parse rule: update_id_tail -> assign_op value | ++ | --"""
        if self._current().type in {
            "EQUALS", "EQUAL_PLUS", "EQUAL_MINUS", "EQUAL_ASTERISK", "EQUAL_DIVIDE"
        }:
            return self._node("update_id_tail", [
                self.parse_assign_op(),
                self.parse_update_val()
            ])
        if self._accept("INCREMENT"):
            return self._node("update_id_tail", [self._node("INCREMENT", [])])
        if self._accept("DECREMENT"):
            return self._node("update_id_tail", [self._node("DECREMENT", [])])
        self._error({
            "EQUALS", "EQUAL_PLUS", "EQUAL_MINUS", "EQUAL_ASTERISK",
            "EQUAL_DIVIDE", "INCREMENT", "DECREMENT"
        })

    def parse_assign_op(self):
        """Parse rule: assign_op -> = | += | -= | *= | /="""
        t = self._current().type
        if t in {
            "EQUALS", "EQUAL_PLUS", "EQUAL_MINUS", "EQUAL_ASTERISK", "EQUAL_DIVIDE"
        }:
            return self._node("assign_op", [self._expect(t)])
        self._error({
            "EQUALS", "EQUAL_PLUS", "EQUAL_MINUS", "EQUAL_ASTERISK", "EQUAL_DIVIDE"
        })

    def parse_update_val(self):
        """Parse rule: update_val -> expression"""
        return self._node("update_val", [self.parse_expression()])

    def parse_whilehot_loop(self):
        """Parse rule: whilehot_loop -> whilehot (expr) { stmts }"""
        return self._node("whilehot_loop", [
            self._expect("WHILEHOT"),
            self._expect("OP_PAREN"),
            self.parse_expression(),
            self._expect("CL_PAREN"),
            self._expect("OP_BRACES"),
            self.parse_statement(),
            self.parse_stmt_tail(),
            self._expect("CL_BRACES")
        ])

    def parse_tastetill_loop(self):
        """Parse rule: tastetill_loop -> taste { stmts } till : (expr)"""
        return self._node("tastetill_loop", [
            self._expect("TASTE"),
            self._expect("OP_BRACES"),
            self.parse_statement(),
            self.parse_stmt_tail(),
            self._expect("CL_BRACES"),
            self._expect("TILL"),
            self._expect("COLON"),
            self._expect("OP_PAREN"),
            self.parse_expression(),
            self._expect("CL_PAREN")
        ])

    # ========================================================================
    # 22. INTERRUPT STATEMENTS
    # ========================================================================

    def parse_intrpt_stmt(self):
        """Parse rule: intrpt_stmt -> snap | skip"""
        t = self._current().type
        if t == "SNAP":
            return self._node("intrpt_stmt", [self._expect("SNAP")])
        if t == "SKIP":
            return self._node("intrpt_stmt", [self._expect("SKIP")])
        self._error({"SNAP", "SKIP"})


# ============================================================================
# PARSER WRAPPER CLASS
# ============================================================================

class Parser:
    """
    High-level parser interface that handles lexer errors and parse errors.
    
    Attributes:
        source_code: The input source code as a string
        ast: The abstract syntax tree (None until parsing completes)
        errors: List of errors encountered during parsing
    """

    def __init__(self, source_code):
        """Initialize the parser with source code."""
        self.source_code = source_code
        self.ast = None
        self.errors = []

    def start(self):
        """
        Main parsing routine: tokenize and parse the source code.
        
        Handles both lexer and parser errors, producing human-readable
        error messages with context about expected tokens.
        """
        # Tokenize the source code
        tokens = list(token_final_out(self.source_code))
        lex_errors = []

        # Collect lexer errors
        for tok in tokens:
            if tok.type == "ERROR":
                lex_errors.append({
                    "type": tok.type,
                    "message": tok.meta.get("message"),
                    "lexeme": tok.value,
                    "line": tok.line,
                    "column": tok.column
                })

        if lex_errors:
            self.errors.extend(lex_errors)
            return

        # Parse the token stream
        parser = RDParser(tokens)

        try:
            parse_tree = parser.parse()
            self.ast = parse_tree
            print(parse_tree.pretty())
        except (UnexpectedToken, UnexpectedEOF) as e:
            expected = list(dict.fromkeys(getattr(e, "expected", [])))
            if not expected:
                expected.append("NONE")

            # Build maps for human-readable token names
            REVERSE_OPERATOR_MAP = {
                token: symbol
                for symbol, token in OPERATOR_MAP.items()
            }

            REVERSE_KEYWORD_MAP = {
                token: lexeme.lower()
                for lexeme, token in KEYWORD_MAP.items()
            }

            def token_to_display(tok):
                """Convert a token type to a human-readable string."""
                if tok == "ZERO":
                    return "0"
                return (
                    REVERSE_OPERATOR_MAP.get(tok)
                    or REVERSE_KEYWORD_MAP.get(tok)
                    or tok
                )

            # Preferred order for displaying expected tokens
            DISPLAY_ORDER = [
                "cafe", "backroom", "brewed", "blend", "id", "[", "]", "=", ",", "+",
                "blendlit", "order", ".", "(", ")", "beanlit", "driplit", "churrolit", "hot",
                "cold", "++", "--", "bean", "drip", "churro", "temp", "&&", "||", "!",
                "<", ">", "==", "!=", "<=", ">=", "-", "*", "/", "%", "***", "mug",
                "new", "recipe", "refill?", "0", "empty", "crema", "cup", "}", "batter@",
                "glaze", "ifbrew", "{", "elifroth", "elspress", "flavour", "syrup", ":", "snap",
                "defoam", "pour", ";", "+=", "-=", "*=", "/=", "whilehot", "taste", "till",
                "skip"
            ]

            expected_readable = [token_to_display(tok) for tok in expected]

            def sort_key(token):
                """Key function for sorting tokens by display preference."""
                try:
                    return DISPLAY_ORDER.index(token)
                except ValueError:
                    return len(DISPLAY_ORDER)

            expected_readable = sorted(expected_readable, key=sort_key)

            # Construct error message
            if isinstance(e, UnexpectedEOF) and set(expected) == {"CL_BRACKETS"}:
                message = "missing ]"
            else:
                if isinstance(e, UnexpectedEOF):
                    message = "Unexpected end of input"
                else:
                    message_display = token_to_display(e.token.type)
                    message = f"Unexpected token [{message_display}, {e.token.value}]"

                if expected_readable:
                    message = f"{message}"

            self.errors.append({
                "type": "SYNTAX_ERROR",
                "message": message,
                "expected": expected_readable,
                "line": getattr(e, "line", None),
                "column": getattr(e, "column", None)
            })