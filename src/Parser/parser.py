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

    # Precomputed FIRST sets — used by _is_start_* methods and while-loop guards
    # to make one-token lookahead decisions without backtracking (LL(1) discipline).
    # LL(1): at most one token of lookahead is needed to pick the correct alternative.
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
    # Entry point for the entire parse. Delegates to parse_program and then
    # verifies that no unconsumed tokens remain (the $END sentinel).
    # ========================================================================

    def parse(self):
        """Main entry point: parse the entire program."""
        node = self.parse_start()
        if self.stream.peek().type != "$END":
            self._error({"$END"})
        return node

    # ---------------------------------------------------------------
    # CFG#1# start -> program
    # Root nonterminal — wraps parse_program in a "start" AST node so
    # the tree always has a single named root, regardless of content.
    # ---------------------------------------------------------------
    def parse_start(self):
        """Parse rule: start -> program"""
        return self._node("start", [self.parse_program()])

    # ========================================================================
    # 2. ERROR HANDLING & HELPER METHODS
    # Internal helpers shared by every parse_* method.  _accept/_expect
    # are the two building blocks of LL(1) token matching: _accept tries a
    # token (returns it on hit, None on miss), _expect asserts the token
    # is present (raises UnexpectedToken on miss).  _error packages the
    # current stream position and the expected-token set into an exception.
    # The _is_start_* predicates test precomputed FIRST sets (the class-
    # level token-set constants) to make lookahead decisions in callers.
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
    # The top-level structure: zero or more global declarations followed by
    # the mandatory main definition (bean cup() { ... }).  parse_program
    # uses checkpoint/restore to try both paths and pick the furthest match.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#2# program -> global_def main_def
    # Two-attempt strategy: try global_def + main_def, then fall back to
    # empty global_def + main_def.  On failure, the error at the furthest
    # stream index wins (the _merge_errors heuristic) so the message
    # points to the real mistake, not a failed speculative attempt.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#3# global_def -> global_dec global_def | λ
    # Iterates (via while loop, not recursion) while _is_start_global_dec
    # holds.  The guard peeks one token ahead so "bean cup" (main_def) is
    # not mistaken for a BEAN variable declaration.
    # ---------------------------------------------------------------
    def parse_global_def(self):
        """Parse rule: global_def -> global_dec global_def | λ"""
        children = []
        while self._is_start_global_dec():
            children.append(self.parse_global_dec())
        if not children:
            children.append(self._node("_empty"))
        return self._node("global_def", children)

    # ---------------------------------------------------------------
    # CFG#4# global_dec -> acc_mod_dec | id_dec_stmt | order_dec_stmt
    #                    | mug_dec | object_def | crema_def
    #                    | recipe_def | empty_def
    # Eight-way dispatch on the first token.  Covers every top-level
    # declaration form: access-modified vars, assignments via identifier,
    # struct defs (mug), class defs (crema), and both function shapes.
    # ---------------------------------------------------------------
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
    # All statement-level declaration forms.  Access modifiers (cafe /
    # backroom) and brewed (const) are handled by acc_mod_dec / dtype_dec.
    # ID-led and ORDER-led are separate paths for assignment and member
    # access.  Pre-unary (++id / --id) is the remaining prefix form.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#5# dec -> acc_mod_dec | id_dec_stmt | order_dec_stmt
    #            |  pre_unary_dec | mug_dec | object_def
    # Statement-level dispatch.  Mirrors parse_global_dec but also allows
    # pre-unary increments/decrements (++ / --) which are not valid at
    # the global scope.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#6# acc_mod_dec -> CAFE acc_mod_dec_body
    #                    |  BACKROOM acc_mod_dec_body
    #                    |  dtype_dec
    # Peels off the optional access modifier (cafe = public, backroom =
    # private) then delegates to acc_mod_dec_body.  If neither modifier
    # appears, falls straight through to dtype_dec.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#7# acc_mod_dec_body -> BREWED acc_brewed_body
    #                         |  data_type ID acc_dtype_tail
    # After an access modifier: brewed (const) introduces a mandatory
    # initializer, while a plain data_type leads to an optional one.
    # FIRST(brewed) = {BREWED}, FIRST(data_type) = DATA_TYPE set.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#8# acc_brewed_body -> data_type var_dec_const_init var_dec_const_tail
    # Constant declaration after an access modifier: all variables must
    # be initialized (brewed = const).  var_dec_const_init requires =,
    # then var_dec_const_tail handles the comma-separated list.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#9# acc_dtype_tail -> OP_BRACKETS arr_size_val CL_BRACKETS arr_dec_dim
    #                       |  opt_assign var_dec_tail
    # After "type ID": if [ follows, this is an array declaration and
    # arr_dec_dim handles the optional initializer; otherwise it is a
    # scalar declaration with an optional assignment and sibling list.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#10# dtype_dec -> BREWED dtype_brewed_body
    #                   |  data_type ID dtype_id_tail
    # Same structure as acc_mod_dec_body but without an enclosing access
    # modifier.  Used when no cafe/backroom keyword precedes the declaration.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#11# dtype_brewed_body -> data_type var_dec_const_init var_dec_const_tail
    # Unmodified constant declaration (no cafe/backroom prefix).  All
    # variables must be given an initializer — brewed prohibits bare names.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#12# dtype_id_tail -> OP_BRACKETS arr_size_val CL_BRACKETS arr_dec_dim
    #                       |  opt_assign var_dec_tail
    # Identical pattern to acc_dtype_tail but used in unmodified type
    # declarations.  [ distinguishes array from scalar at one-token lookahead.
    # ---------------------------------------------------------------
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
    # Blend (string) type has its own declaration sub-grammar because string
    # values support concatenation with + and can contain non-numeric terms.
    # The "blend_term" nonterminal is the atom for string expressions.
    # 1D and 2D array forms are also factored here for blend arrays.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#13# blend_const_init -> ID EQUALS blend_val
    # Single constant string initializer.  Used inside brewed blend lists
    # where every variable must receive an initial value.
    # ---------------------------------------------------------------
    def parse_blend_const_init(self):
        """Parse rule: blend_const_init -> ID = blend_val"""
        return self._node("blend_const_init", [
            self._expect("ID"),
            self._expect("EQUALS"),
            self.parse_blend_val()
        ])

    # ---------------------------------------------------------------
    # CFG#14# blend_const_init_tail -> (COMMA ID EQUALS blend_val)* | λ
    # Continues a constant blend list with additional comma-separated
    # name=value pairs.  Loops while COMMA is present, then yields λ.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#15# blend_id_tail -> OP_BRACKETS arr_size_val CL_BRACKETS blend_arr_dec_dim
    #                       |  blend_assign blend_tail
    # After a blend ID: [ triggers the array path; otherwise opt-assign
    # then a comma-separated sibling list (blend_tail).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#16# blend_assign -> EQUALS blend_val | λ
    # Optional initializer for a single blend variable.  If = is present,
    # the value is a blend_val (string expression); otherwise λ (unset).
    # ---------------------------------------------------------------
    def parse_blend_assign(self):
        """Parse rule: blend_assign -> = blend_val | λ"""
        if self._accept("EQUALS"):
            return self._node("blend_assign", [
                self._node("EQUALS", []),
                self.parse_blend_val()
            ])
        return self._node("blend_assign", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#17# blend_tail -> (COMMA ID blend_assign)* | λ
    # Comma-separated list of additional blend variables after the first.
    # Each may optionally be initialized via blend_assign.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#18# blend_val -> blend_term blend_val_tail
    # String expression: one or more blend_terms joined by +.  This is
    # the string-concatenation expression level; arithmetic/logic are not
    # valid here, so the production stops at the + operator.
    # ---------------------------------------------------------------
    def parse_blend_val(self):
        """Parse rule: blend_val -> blend_term (+blend_term)*"""
        return self._node("blend_val", [
            self.parse_blend_term(),
            self.parse_blend_val_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#19# blend_val_tail -> (PLUS blend_term)* | λ
    # Right-associative tail for string concatenation.  Loops while PLUS
    # is the lookahead, consuming one blend_term per iteration.
    # ---------------------------------------------------------------
    def parse_blend_val_tail(self):
        """Parse rule: blend_val_tail -> (+ blend_term)* | λ"""
        children = []
        while self._accept("PLUS"):
            children.append(self._node("PLUS", []))
            children.append(self.parse_blend_term())
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_val_tail", children)

    # ---------------------------------------------------------------
    # CFG#20# blend_term -> BLENDLIT
    #                    |  ID blend_term_id_tail
    #                    |  ORDER DOT_ACC ID
    #                    |  OP_PAREN expression CL_PAREN
    #                    |  BEANLIT | DRIPLIT | CHURROLIT | HOT | COLD
    #                    |  builtin_call (SQRT | CEIL | FLOOR | ...)
    # Atom for string expressions. Numeric/boolean literals are allowed
    # so they can be coerced to string at runtime by the code generator.
    # ---------------------------------------------------------------
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
        
    # ---------------------------------------------------------------
    # CFG#21# blend_term_id_tail -> DOT_ACC ID
    #                            |  OP_PAREN function_args function_args_tail CL_PAREN
    #                            |  OP_BRACKETS array_index CL_BRACKETS arr_call_tail
    #                            |  λ
    # After an ID inside a blend expression: member access (.field),
    # function call (args), array indexing ([idx]), or just the bare name.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#22# blend_arr_elem -> blend_term
    # Single element of a blend (string) array initializer.  Wraps
    # blend_term in its own node so the IR generator can identify it.
    # ---------------------------------------------------------------
    def parse_blend_arr_elem(self):
        """Parse rule: blend_arr_elem -> blend_term"""
        return self._node("blend_arr_elem", [self.parse_blend_term()])

    # ---------------------------------------------------------------
    # CFG#23# blend_ext_arr_elem -> (COMMA blend_arr_elem)* | λ
    # Additional comma-separated elements in a 1D blend array literal.
    # Loops while COMMA is present; an empty array body yields λ.
    # ---------------------------------------------------------------
    def parse_blend_ext_arr_elem(self):
        """Parse rule: blend_ext_arr_elem -> (COMMA blend_arr_elem)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_blend_arr_elem())
        if not children:
            children.append(self._node("_empty"))
        return self._node("blend_ext_arr_elem", children)

    # ---------------------------------------------------------------
    # CFG#24# blend_arr_cont_1d -> blend_arr_elem blend_ext_arr_elem | λ
    # Contents of a 1D blend array literal.  If the lookahead is in
    # BLEND_TERM_START, one element is parsed then zero or more additional
    # comma-separated elements follow via blend_ext_arr_elem.
    # ---------------------------------------------------------------
    def parse_blend_arr_cont_1d(self):
        """Parse rule: blend_arr_cont_1d -> blend_arr_elem (, blend_arr_elem)* | λ"""
        if self._current().type in self.BLEND_TERM_START:
            return self._node("blend_arr_cont_1d", [
                self.parse_blend_arr_elem(),
                self.parse_blend_ext_arr_elem()
            ])
        return self._node("blend_arr_cont_1d", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#25# opt_blend_arr_elems -> blend_arr_elem blend_ext_arr_elem | λ
    # Optional element list for one row of a 2D blend array.  Used inside
    # parse_blend_arr_cont_2d for each [row] sub-literal.
    # ---------------------------------------------------------------
    def parse_opt_blend_arr_elems(self):
        """Parse rule: opt_blend_arr_elems -> blend_arr_elem ext_blend_arr_elem | λ"""
        if self._current().type in self.BLEND_TERM_START:
            return self._node("opt_blend_arr_elems", [
                self.parse_blend_arr_elem(),
                self.parse_blend_ext_arr_elem()
            ])
        return self._node("opt_blend_arr_elems", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#26# blend_arr_cont_2d -> OP_BRACKETS opt_blend_arr_elems CL_BRACKETS
    #                              COMMA
    #                              OP_BRACKETS opt_blend_arr_elems CL_BRACKETS
    #                              blend_arr_cont_2d_tail
    # At least two row sub-literals ([...],[...]) are required to form a
    # 2D array — the grammar mandates the first two rows explicitly before
    # delegating remaining rows to blend_arr_cont_2d_tail.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#27# blend_arr_cont_2d_tail -> (COMMA OP_BRACKETS opt_blend_arr_elems CL_BRACKETS)* | λ
    # Third and subsequent rows of a 2D blend array literal.  Loops while
    # COMMA is present, parsing each additional [row] sub-literal.
    # ---------------------------------------------------------------
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
    # When an identifier is the first token of a statement, the parser
    # cannot tell from that token alone whether it is an assignment, a
    # function call, an array store, or a member-access chain.  The
    # id_dec_tail dispatch uses the NEXT token (one-token lookahead) to
    # pick the correct LL(1) alternative.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#28# id_dec_stmt -> ID id_dec_tail
    # Consumes the leading identifier then delegates to id_dec_tail which
    # uses the following token to select the correct parse path.
    # ---------------------------------------------------------------
    def parse_id_dec_stmt(self):
        """Parse rule: id_dec_stmt -> ID tail"""
        return self._node("id_dec_stmt", [
            self._expect("ID"),
            self.parse_id_dec_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#29# id_dec_tail -> assign_op assign_val          (assignment)
    #                     |  OP_PAREN function_args ... CL_PAREN  (call)
    #                     |  DOT_ACC ID id_dot_tail        (member access)
    #                     |  OP_BRACKETS array_index ... id_bracket_tail (array store)
    #                     |  unary_op                      (postfix ++ / --)
    # Five-way LL(1) split keyed on the token after the identifier:
    # =, +=, etc. → assignment; ( → call; . → member; [ → array; ++/-- → postfix.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#30# assign_val -> BLENDLIT concat | expression
    # RHS of an assignment.  BLENDLIT as lookahead means a string literal
    # (possibly concatenated); everything else is a numeric/boolean expression.
    # ---------------------------------------------------------------
    def parse_assign_val(self):
        """Parse rule: assign_val -> BLENDLIT concat | expression"""
        if self._current().type == "BLENDLIT":
            return self._node("assign_val", [
                self._expect("BLENDLIT"),
                self.parse_concat()
            ])
        return self._node("assign_val", [self.parse_expression()])

    # ---------------------------------------------------------------
    # CFG#31# id_dot_tail -> EQUALS assign_val
    #                     |  DOT_ACC crema_member_inner id_crema_assign_tail
    #                     |  OP_BRACKETS array_index CL_BRACKETS arr_call_tail id_crema_assign_tail
    # After "ID.ID": the next token selects member assignment (=), deeper
    # nested member access (.), or array element on the member ([]).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#32# id_crema_assign_tail -> EQUALS assign_val
    # Mandatory assignment after a member chain (ID.member or ID.arr[idx]).
    # This rule has no λ alternative — a member access in a statement
    # position must be followed by = and a value to be syntactically valid.
    # ---------------------------------------------------------------
    def parse_id_crema_assign_tail(self):
        """Parse rule: id_crema_assign_tail -> = value | λ"""
        return self._node("id_crema_assign_tail", [
            self._expect("EQUALS"),
            self.parse_assign_val()
        ])

    # ---------------------------------------------------------------
    # CFG#33# id_bracket_tail -> OP_BRACKETS array_index CL_BRACKETS EQUALS arr_elem
    #                         |  EQUALS OP_BRACKETS arr_cont_1d CL_BRACKETS
    #                         |  EQUALS arr_elem
    # After "ID[idx]": a second [ signals a 2D element assignment; = alone
    # can be a full 1D array reassignment ([...]) or a single-element store.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#34# crema_member_inner -> ID crema_member_inner_tail
    # Parses the inner member name in a chained access expression
    # (obj.inner or obj.inner[idx] or obj.inner()).
    # ---------------------------------------------------------------
    def parse_crema_member_inner(self):
        """Parse rule: crema_member_inner -> ID tail"""
        return self._node("crema_member_inner", [
            self._expect("ID"),
            self.parse_crema_member_inner_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#35# crema_member_inner_tail -> OP_BRACKETS array_index CL_BRACKETS arr_call_tail
    #                                 |  OP_PAREN function_args function_args_tail CL_PAREN
    #                                 |  λ
    # After the inner member name: [ signals array indexing on the member,
    # ( signals a method call, or λ means plain field access.
    # ---------------------------------------------------------------
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
    # ORDER is the keyword for the implicit "this" object reference inside
    # crema (class) methods.  ORDER-led statements assign to or read from
    # fields of the current instance via the ORDER.field access pattern.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#36# order_dec_stmt -> ORDER DOT_ACC ID order_dec_tail
    # Consumes "order.ID" then delegates to order_dec_tail to handle
    # assignment (=), array indexing ([idx]), or deeper member access (.field).
    # ---------------------------------------------------------------
    def parse_order_dec_stmt(self):
        """Parse rule: order_dec_stmt -> order . ID tail"""
        return self._node("order_dec_stmt", [
            self._expect("ORDER"),
            self._expect("DOT_ACC"),
            self._expect("ID"),
            self.parse_order_dec_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#37# order_dec_tail -> OP_BRACKETS array_index CL_BRACKETS EQUALS assign_val
    #                        |  EQUALS assign_val
    #                        |  DOT_ACC ID order_mug_tail
    # Three-way LL(1) split on the token after "order.field":
    # [ = array element assignment, = = field assignment, . = deeper member.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#38# order_mug_tail -> EQUALS assign_val
    # Assignment to a doubly-nested order member (order.outer.inner = val).
    # No λ alternative — reaching this rule means an assignment is required.
    # ---------------------------------------------------------------
    def parse_order_mug_tail(self):
        """Parse rule: order_mug_tail -> = value | λ"""
        return self._node("order_mug_tail", [
            self._expect("EQUALS"),
            self.parse_assign_val()
        ])

    # ========================================================================
    # 8. UNARY OPERATIONS
    # Prefix unary forms (++id, --id) as standalone statements.  These are
    # distinct from the postfix unary inside expressions because at the
    # statement level the result is discarded and only the side effect matters.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#39# pre_unary_dec -> unary_op ID
    # Statement-level prefix increment/decrement: ++ or -- followed by a
    # single identifier.  The _allow_unary_ops flag guards this in contexts
    # where in-place mutation is not safe (e.g., array element positions).
    # ---------------------------------------------------------------
    def parse_pre_unary_dec(self):
        """Parse rule: pre_unary_dec -> unary_op ID"""
        return self._node("pre_unary_dec", [
            self.parse_unary_op(),
            self._expect("ID")
        ])

    # ---------------------------------------------------------------
    # CFG#40# unary_op -> INCREMENT | DECREMENT
    # Matches either ++ or -- and wraps it in a "unary_op" node.
    # Shared by both prefix and postfix unary contexts.
    # ---------------------------------------------------------------
    def parse_unary_op(self):
        """Parse rule: unary_op -> ++ | --"""
        t = self._current().type
        if t in self.UNARY_OP:
            return self._node("unary_op", [self._expect(t)])
        self._error(self.UNARY_OP)

    # ========================================================================
    # 9. DATA TYPES & VALUES
    # data_type matches CARAMEL's four base numeric types: bean (int),
    # drip (float), churro (char), temp (bool).  The value / opt_assign /
    # var_dec_* family covers all scalar initializer shapes.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#41# data_type -> BEAN | DRIP | CHURRO | TEMP
    # Matches exactly one type keyword token from DATA_TYPE and wraps it.
    # blend (string) is deliberately excluded here — it has its own
    # sub-grammar because its expressions differ structurally.
    # ---------------------------------------------------------------
    def parse_data_type(self):
        """Parse rule: data_type -> bean | drip | churro | temp"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("data_type", [self._expect(t)])
        self._error(self.DATA_TYPE)

    # ---------------------------------------------------------------
    # CFG#42# var_dec_const_init -> ID EQUALS value
    # Single mandatory-initializer variable in a brewed (const) declaration.
    # Unlike opt_assign, this form requires = and a value — no bare names.
    # ---------------------------------------------------------------
    def parse_var_dec_const_init(self):
        """Parse rule: var_dec_const_init -> ID = value"""
        return self._node("var_dec_const_init", [
            self._expect("ID"),
            self._expect("EQUALS"),
            self.parse_value()
        ])

    # ---------------------------------------------------------------
    # CFG#43# var_dec_const_tail -> (COMMA ID EQUALS value)* | λ
    # Additional const-initialized variables in the same brewed declaration.
    # Every variable in the list must have an initializer (= value).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#44# var_dec_init -> ID opt_assign
    # Single variable with an optional initializer.  Used for mutable
    # declarations (non-brewed) where = val is allowed but not required.
    # ---------------------------------------------------------------
    def parse_var_dec_init(self):
        """Parse rule: var_dec_init -> ID opt_assign"""
        return self._node("var_dec_init", [
            self._expect("ID"),
            self.parse_opt_assign()
        ])

    # ---------------------------------------------------------------
    # CFG#45# opt_assign -> EQUALS value | λ
    # Optional initializer: if EQUALS is present, consume it and parse
    # the RHS value; otherwise emit λ (variable is declared but unset).
    # ---------------------------------------------------------------
    def parse_opt_assign(self):
        """Parse rule: opt_assign -> = value | λ"""
        if self._accept("EQUALS"):
            return self._node("opt_assign", [
                self._node("EQUALS", []),
                self.parse_value()
            ])
        return self._node("opt_assign", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#46# var_dec_tail -> (COMMA var_dec_init)* | λ
    # Comma-separated additional variables in a mutable type declaration.
    # Each sibling may carry its own optional initializer via var_dec_init.
    # ---------------------------------------------------------------
    def parse_var_dec_tail(self):
        """Parse rule: var_dec_tail -> (COMMA var_dec_init)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_var_dec_init())
        if not children:
            children.append(self._node("_empty"))
        return self._node("var_dec_tail", children)

    # ---------------------------------------------------------------
    # CFG#47# value -> expression
    # Thin wrapper that promotes any expression to the "value" nonterminal.
    # Providing a named wrapper keeps the AST readable and matches the CFG.
    # ---------------------------------------------------------------
    def parse_value(self):
        """Parse rule: value -> expression"""
        return self._node("value", [self.parse_expression()])

    # ========================================================================
    # 10. EXPRESSION HIERARCHY
    # Operator-precedence cascade implemented as a chain of mutually-calling
    # rules.  Each level handles one precedence tier and delegates up:
    #   expression (logic &&/||)
    #     -> not_factor (prefix !)
    #       -> rel_expr (> < == != >= <=)
    #         -> arith_expr (+ - * / %)
    #           -> unary_expr (prefix ++/--, unary -)
    #             -> primary (literal, ID, call, array, parenthesized)
    # "_tail" suffixed rules avoid left recursion while preserving
    # left-associativity: each tail loops (not recurses) over operators.
    # LL(1) — FIRST set: the class-level LOGIC_OP / REL_OP / ARITHM_OP constants.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#48# expression -> not_factor logic_expr_tail
    # Lowest-precedence level: logical operators && and ||.  Delegates to
    # not_factor for its left operand, then logic_expr_tail for the rest.
    # ---------------------------------------------------------------
    def parse_expression(self):
        """Parse rule: expression -> not_factor logic_expr_tail"""
        return self._node("expression", [
            self.parse_not_factor(),
            self.parse_logic_expr_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#49# logic_expr_tail -> (logic_op not_factor)* | λ
    # Right tail for logical expressions.  Loops while AND/OR are present,
    # consuming one operator + not_factor per iteration (left-associative).
    # ---------------------------------------------------------------
    def parse_logic_expr_tail(self):
        """Parse rule: logic_expr_tail -> (logic_op not_factor)* | λ"""
        children = []
        while self._current().type in self.LOGIC_OP:
            children.append(self.parse_logic_op())
            children.append(self.parse_not_factor())
        if not children:
            children.append(self._node("_empty"))
        return self._node("logic_expr_tail", children)

    # ---------------------------------------------------------------
    # CFG#50# logic_op -> AND | OR
    # Matches exactly one logical operator token and wraps it in a node
    # so the IR generator can identify the operation without inspecting
    # the raw token value.
    # ---------------------------------------------------------------
    def parse_logic_op(self):
        """Parse rule: logic_op -> && | ||"""
        t = self._current().type
        if t in self.LOGIC_OP:
            return self._node("logic_op", [self._expect(t)])
        self._error(self.LOGIC_OP)

    # ---------------------------------------------------------------
    # CFG#51# not_factor -> NOT rel_expr | rel_expr
    # Handles the prefix ! (logical negation).  If NOT is absent the rule
    # falls straight through to rel_expr — no alternative AST node created.
    # ---------------------------------------------------------------
    def parse_not_factor(self):
        """Parse rule: not_factor -> ! rel_expr | rel_expr"""
        if self._accept("NOT"):
            return self._node("not_factor", [
                self._node("NOT", []),
                self.parse_rel_expr()
            ])
        return self._node("not_factor", [self.parse_rel_expr()])

    # ---------------------------------------------------------------
    # CFG#52# rel_expr -> arith_expr rel_expr_tail
    # Relational comparison level.  Left operand is an arithmetic expression;
    # rel_expr_tail chains zero or more relational operators.
    # ---------------------------------------------------------------
    def parse_rel_expr(self):
        """Parse rule: rel_expr -> arith_expr rel_expr_tail"""
        return self._node("rel_expr", [
            self.parse_arith_expr(),
            self.parse_rel_expr_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#53# rel_expr_tail -> (rel_op arith_expr)* | λ
    # Loops while REL_OP tokens (>, <, ==, !=, >=, <=) are present.
    # Left-associative: each iteration produces a pair (op, right-operand).
    # ---------------------------------------------------------------
    def parse_rel_expr_tail(self):
        """Parse rule: rel_expr_tail -> (rel_op arith_expr)* | λ"""
        children = []
        while self._current().type in self.REL_OP:
            children.append(self.parse_rel_op())
            children.append(self.parse_arith_expr())
        if not children:
            children.append(self._node("_empty"))
        return self._node("rel_expr_tail", children)

    # ---------------------------------------------------------------
    # CFG#54# rel_op -> GREATER_THAN | LESSER_THAN | EQ_EQUALS
    #                |  NOT_EQUAL | GREATER_EQUAL | LESSER_EQUAL
    # Matches one relational operator from the REL_OP set.
    # ---------------------------------------------------------------
    def parse_rel_op(self):
        """Parse rule: rel_op -> > | < | == | != | >= | <="""
        t = self._current().type
        if t in self.REL_OP:
            return self._node("rel_op", [self._expect(t)])
        self._error(self.REL_OP)

    # ---------------------------------------------------------------
    # CFG#55# arith_expr -> unary_expr arith_expr_tail
    # Arithmetic level: + - * / %.  Left operand is a unary expression;
    # arith_expr_tail loops over additive/multiplicative operators.
    # ---------------------------------------------------------------
    def parse_arith_expr(self):
        """Parse rule: arith_expr -> unary_expr arith_expr_tail"""
        return self._node("arith_expr", [
            self.parse_unary_expr(),
            self.parse_arith_expr_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#56# arith_expr_tail -> (arithm_op unary_expr)* | λ
    # Loops while ARITHM_OP tokens are the lookahead.  Mixing + with * in
    # the same tail is intentional — operator precedence is handled by the
    # IR generator, not the parser.
    # ---------------------------------------------------------------
    def parse_arith_expr_tail(self):
        """Parse rule: arith_expr_tail -> (arithm_op unary_expr)* | λ"""
        children = []
        while self._current().type in self.ARITHM_OP:
            children.append(self.parse_arithm_op())
            children.append(self.parse_unary_expr())
        if not children:
            children.append(self._node("_empty"))
        return self._node("arith_expr_tail", children)

    # ---------------------------------------------------------------
    # CFG#57# arithm_op -> PLUS | MINUS | MULTIPLY | DIVIDE | MODULO
    # Matches one arithmetic operator from ARITHM_OP and wraps it.
    # ---------------------------------------------------------------
    def parse_arithm_op(self):
        """Parse rule: arithm_op -> + | - | * | / | %"""
        t = self._current().type
        if t in self.ARITHM_OP:
            return self._node("arithm_op", [self._expect(t)])
        self._error(self.ARITHM_OP)

    # ---------------------------------------------------------------
    # CFG#58# unary_expr -> INCREMENT ID   (prefix ++ inside expression)
    #                    |  DECREMENT ID   (prefix --)
    #                    |  MINUS neg_operand  (arithmetic negation)
    #                    |  primary
    # Prefix operators bind tighter than arithmetic but looser than primary.
    # _allow_unary_ops is False inside array element positions to prevent
    # side effects (e.g. arr[i++] = x changing i unexpectedly).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#59# neg_operand -> ID | OP_PAREN expression CL_PAREN
    # The operand of a unary minus: either a bare identifier or a
    # parenthesized expression.  This restriction avoids ambiguity with
    # the binary minus operator in arith_expr.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#60# primary -> ID primary_id_tail
    #                 |  ORDER DOT_ACC ID primary_order_tail
    #                 |  literal  (BEANLIT | DRIPLIT | CHURROLIT | HOT | COLD | BLENDLIT)
    #                 |  OP_PAREN expression CL_PAREN
    #                 |  SIFT OP_PAREN sift_arg CL_PAREN    (length())
    #                 |  SQRT | CEIL | FLOOR | POW | RAND | TYPE (builtins)
    # Highest-precedence atom.  The funny # comment below is the original
    # developer's excitement comment; kept to preserve history.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#61# primary_id_tail -> DOT_ACC ID primary_dot_tail
    #                         |  OP_PAREN function_args function_args_tail CL_PAREN
    #                         |  OP_BRACKETS array_index CL_BRACKETS arr_call_tail
    #                         |  unary_op
    #                         |  λ
    # After an ID in an expression: . = member, ( = call, [ = array read,
    # ++/-- = postfix increment, or λ = plain variable reference.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#62# primary_dot_tail -> DOT_ACC crema_member_inner
    #                          |  OP_BRACKETS array_index CL_BRACKETS arr_call_tail
    #                          |  OP_PAREN function_args function_args_tail CL_PAREN
    #                          |  λ
    # After "ID.ID" in an expression: deeper member access, array on member,
    # or method call.  λ means the member reference is the final expression.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#63# primary_order_tail -> OP_BRACKETS array_index CL_BRACKETS
    #                            |  DOT_ACC ID
    #                            |  λ
    # After "order.ID" in an expression: read an array element ([idx]),
    # access a nested field (.field), or use the field directly (λ).
    # ---------------------------------------------------------------
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
    # Array declarations (1D and 2D), initializer literals, and element
    # access.  arr_dec_dim handles both the shape declaration ([size])
    # and the optional initializer (= [...]).  arr_call_tail handles
    # the second dimension when reading or assigning a 2D element.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#64# arr_call_tail -> OP_BRACKETS array_index CL_BRACKETS | λ
    # Optional second-dimension index after an array read: arr[i][j].
    # If [ is absent, the preceding single-index access is the full reference.
    # ---------------------------------------------------------------
    def parse_arr_call_tail(self):
        """Parse rule: arr_call_tail -> [idx] | λ"""
        if self._accept("OP_BRACKETS"):
            return self._node("arr_call_tail", [
                self._node("OP_BRACKETS", []),
                self.parse_array_index(),
                self._expect("CL_BRACKETS")
            ])
        return self._node("arr_call_tail", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#65# array_index -> expression
    # The index inside [ ] is any full expression (constant, variable, or
    # arithmetic).  Thin wrapper keeps the AST node labelled "array_index".
    # ---------------------------------------------------------------
    def parse_array_index(self):
        """Parse rule: array_index -> expression"""
        return self._node("array_index", [self.parse_expression()])

    # ---------------------------------------------------------------
    # CFG#66# arr_size_val -> BEANLIT | ID | FLEX_ASTERISK
    # The size between [ ] in an array declaration.  BEANLIT is a literal
    # integer, ID allows a named constant, and *** (FLEX_ASTERISK) means
    # the size is inferred from the initializer list at runtime.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#67# arr_dec_dim -> OP_BRACKETS arr_size_val CL_BRACKETS EQUALS
    #                        OP_BRACKETS arr_cont_2d CL_BRACKETS   (2D)
    #                     |  EQUALS OP_BRACKETS arr_cont_1d CL_BRACKETS   (1D)
    #                     |  λ   (declaration without initializer)
    # Determines the array's shape after the first dimension's size token.
    # A second [ means 2D; = alone means 1D; λ means the array is
    # declared but left uninitialized (default values filled by codegen).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#68# blend_arr_dec_dim -> OP_BRACKETS arr_size_val CL_BRACKETS EQUALS
    #                              OP_BRACKETS blend_arr_cont_2d CL_BRACKETS
    #                           |  EQUALS OP_BRACKETS blend_arr_cont_1d CL_BRACKETS
    # Same shape as arr_dec_dim but delegates to the blend-specific content
    # rules (blend_arr_cont_*) whose atoms are blend_terms, not expressions.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#69# arr_elem -> expression  (with _allow_unary_ops = False)
    # An expression used as an array element value.  _allow_unary_ops is
    # temporarily set to False so ++ / -- cannot appear as side-effects
    # inside an array literal (prevents accidental mutation).
    # ---------------------------------------------------------------
    def parse_arr_elem(self):
        """Parse rule: arr_elem -> expression (no standalone ++/-- allowed)"""
        saved = self._allow_unary_ops
        self._allow_unary_ops = False
        try:
            result = self._node("arr_elem", [self.parse_expression()])
        finally:
            self._allow_unary_ops = saved
        return result

    # ---------------------------------------------------------------
    # CFG#70# ext_arr_elem -> (COMMA arr_elem)* | λ
    # Comma-separated additional elements in a 1D numeric array literal.
    # Loops while COMMA is present; an empty array body yields λ.
    # ---------------------------------------------------------------
    def parse_ext_arr_elem(self):
        """Parse rule: ext_arr_elem -> (COMMA arr_elem)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_arr_elem())
        if not children:
            children.append(self._node("_empty"))
        return self._node("ext_arr_elem", children)

    # ---------------------------------------------------------------
    # CFG#71# arr_cont_1d -> arr_elem ext_arr_elem | λ
    # Full contents of a 1D numeric array literal.  Guarded by
    # _is_start_expression so an empty [] resolves to λ cleanly.
    # ---------------------------------------------------------------
    def parse_arr_cont_1d(self):
        """Parse rule: arr_cont_1d -> elem array_elements | λ"""
        if self._is_start_expression():
            result = self._node("arr_cont_1d", [
                self.parse_arr_elem(),
                self.parse_ext_arr_elem()
            ])
            if self._current().type not in {"CL_BRACKETS"}:
                self._error({"CL_BRACKETS", "COMMA"})
            return result
        return self._node("arr_cont_1d", [self._node("_empty")])
    
    # ---------------------------------------------------------------
    # CFG#72# opt_arr_elems -> arr_elem ext_arr_elem | λ
    # Optional element list for one row of a 2D numeric array.
    # Used inside parse_arr_cont_2d for each [row] sub-literal.
    # ---------------------------------------------------------------
    def parse_opt_arr_elems(self):
        """Parse rule: opt_arr_elems -> arr_elem ext_arr_elem | λ"""
        if self._is_start_expression():
            return self._node("opt_arr_elems", [
                self.parse_arr_elem(),
                self.parse_ext_arr_elem()
            ])
        return self._node("opt_arr_elems", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#73# arr_cont_2d -> OP_BRACKETS opt_arr_elems CL_BRACKETS
    #                        COMMA
    #                        OP_BRACKETS opt_arr_elems CL_BRACKETS
    #                        arr_cont_2d_tail
    # Two mandatory rows then zero or more extra rows.  The first two
    # rows are parsed inline (not via a loop) to guarantee at least 2×N.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#74# arr_cont_2d_tail -> (COMMA OP_BRACKETS opt_arr_elems CL_BRACKETS)* | λ
    # Third and subsequent rows of a 2D numeric array literal.
    # Loops while COMMA is present, parsing each additional [row].
    # ---------------------------------------------------------------
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
    # Argument list parsing shared by recipe calls, empty calls, and the
    # built-in sift (length) function.  parse_function_call is a standalone
    # helper used when the caller has not yet consumed the function ID.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#75# function_call -> ID OP_PAREN function_args function_args_tail CL_PAREN
    # Standalone function call (ID + arg list).  Used when the parser
    # encounters a call that is not handled by an ID-led statement path.
    # ---------------------------------------------------------------
    def parse_function_call(self):
        """Parse rule: function_call -> ID (args)"""
        return self._node("function_call", [
            self._expect("ID"),
            self._expect("OP_PAREN"),
            self.parse_function_args(),
            self.parse_function_args_tail(),
            self._expect("CL_PAREN")
        ])

    # ---------------------------------------------------------------
    # CFG#76# sift_call -> ID OP_PAREN CL_PAREN
    # The built-in sift() (length) call with no arguments — only the
    # target variable is passed via the outer sift_arg node.
    # ---------------------------------------------------------------
    def parse_sift_call(self): # PRE-DEFINED - is length()
        """Parse rule: function_call -> ID (args)"""
        return self._node("sift_call", [
            self._expect("ID"),
            self._expect("OP_PAREN"),
            self._expect("CL_PAREN")
        ])

    # ---------------------------------------------------------------
    # CFG#77# sift_arg -> expression
    # The single argument to sift() — the array or string whose length
    # is requested.  Any expression is syntactically valid here.
    # ---------------------------------------------------------------
    def parse_sift_arg(self):
        """Parse rule: sift_arg -> expression"""
        return self._node("sift_arg", [self.parse_expression()])
    
    # ---------------------------------------------------------------
    # CFG#78# function_args -> BLENDLIT | expression | λ
    # First (or only) argument in a call.  BLENDLIT is a separate LL(1)
    # branch because string literals are not in EXPR_START (they are not
    # part of the numeric expression hierarchy).  λ = no arguments.
    # ---------------------------------------------------------------
    def parse_function_args(self):
        """Parse rule: function_args -> BLENDLIT | expression | λ"""
        t = self._current().type
        if t == "BLENDLIT":
            return self._node("function_args", [self._expect("BLENDLIT")])
        if self._is_start_expression():
            return self._node("function_args", [self.parse_expression()])
        return self._node("function_args", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#79# function_args_tail -> (COMMA function_args)* | λ
    # Additional comma-separated arguments after the first.  Loops while
    # COMMA is present; each additional argument uses the same function_args
    # rule (allowing BLENDLIT or expression or λ per slot).
    # ---------------------------------------------------------------
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
    # mug is CARAMEL's struct keyword.  A mug declaration names the struct
    # and lists its typed fields inside [ ].  Fields may be brewed (const),
    # plain data types, or blend types.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#80# mug_dec -> MUG ID OP_BRACKETS dtype_mug_var mug_var_dec_cont CL_BRACKETS
    # Struct definition: MUG keyword, name, then one or more typed fields
    # inside [ ].  At least one field is required (dtype_mug_var is mandatory).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#81# dtype_mug_var -> BREWED mug_brewed_body
    #                       |  data_type var_dec_init var_dec_tail
    # Single field group in a mug: brewed (const) fields require = init;
    # plain data-type fields may be uninitialized (opt_assign).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#82# mug_brewed_body -> data_type var_dec_const_init var_dec_const_tail
    # A brewed field group inside a mug: all variables must have initializers.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#83# mug_var_dec_cont -> (dtype_mug_var)* | λ
    # Second and subsequent field groups inside a mug declaration.
    # Loops while BREWED or any DATA_TYPE token is the lookahead.
    # ---------------------------------------------------------------
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
    # Object instantiation: "new VarName = ClassName".  This creates an
    # instance of a crema (class) and binds it to VarName.  The syntax
    # mirrors many C-family "new" expressions but is statement-level only.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#84# object_def -> NEW ID EQUALS ID
    # Object instantiation statement.  First ID is the variable name,
    # second ID is the crema class name.  The = is required (not optional).
    # ---------------------------------------------------------------
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
    # recipe = typed (non-void) function.  The definition always ends with
    # a mandatory refill? (return) statement parsed by parse_refill_final.
    # Parameters use the dtype_param / add_param pair; the body stops
    # before REFILL so refill_final can claim it.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#85# recipe_def -> RECIPE recipe_ret_type ID OP_PAREN parameter CL_PAREN
    #                       OP_BRACKETS recipe_body refill_final CL_BRACKETS
    # Typed function definition.  recipe_ret_type constrains the return
    # type to DATA_TYPE; refill_final enforces a mandatory return value.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#86# recipe_ret_type -> data_type
    # The return type of a recipe.  Only the four base numeric/bool types
    # are allowed; blend (string) returns are handled differently.
    # ---------------------------------------------------------------
    def parse_recipe_ret_type(self):
        """Parse rule: recipe_ret_type -> data_type"""
        if self._current().type in self.DATA_TYPE:
            return self._node("recipe_ret_type", [self.parse_data_type()])
        self._error(self.DATA_TYPE)

    # ---------------------------------------------------------------
    # CFG#87# parameter -> dtype_param add_param | λ
    # Formal parameter list.  If DATA_TYPE is the lookahead, parse the
    # first parameter then add_param handles comma-separated siblings.
    # λ means no parameters (empty parentheses).
    # ---------------------------------------------------------------
    def parse_parameter(self):
        """Parse rule: parameter -> dtype_param add_param | λ"""
        if self._current().type in self.DATA_TYPE:
            return self._node("parameter", [
                self.parse_dtype_param(),
                self.parse_add_param()
            ])
        return self._node("parameter", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#88# dtype_param -> data_type var_dec_init
    # Single typed parameter.  The name and optional default value are
    # parsed together by var_dec_init (ID opt_assign).
    # ---------------------------------------------------------------
    def parse_dtype_param(self):
        """Parse rule: dtype_param -> data_type ID opt_assign"""
        t = self._current().type
        if t in self.DATA_TYPE:
            return self._node("dtype_param", [
                self.parse_data_type(),
                self.parse_var_dec_init(),
            ])
        self._error({"BLEND"}.union(self.DATA_TYPE))

    # ---------------------------------------------------------------
    # CFG#89# param_brewed_body -> data_type var_dec_const_init var_dec_const_tail
    # Brewed (const) parameter group — all parameters in the group
    # must be given default values (mandatory = init).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#90# param_dtype_body -> BREWED data_type var_dec_const_init var_dec_const_tail
    #                          |  data_type var_dec_init
    # A parameter group that may be const (BREWED prefix) or mutable.
    # Commented-out var_dec_tail call intentionally left as is — single
    # param per group is the intended design in this rule.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#91# param_id_tail -> DOT_ACC ID
    # Member access tail used inside parameter contexts (e.g. order.field
    # as a parameter default or type hint).
    # ---------------------------------------------------------------
    def parse_param_id_tail(self):
        """Parse rule: param_id_tail -> . ID"""
        return self._node("param_id_tail", [
            self._expect("DOT_ACC"),
            self._expect("ID")
        ])

    # ---------------------------------------------------------------
    # CFG#92# add_param -> (COMMA dtype_param)* | λ
    # Additional formal parameters after the first.  Each is a typed
    # parameter (dtype_param).  Loops while COMMA is the lookahead.
    # ---------------------------------------------------------------
    def parse_add_param(self):
        """Parse rule: add_param -> (COMMA dtype_param)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_dtype_param())
        if not children:
            children.append(self._node("_empty"))
        return self._node("add_param", children)

    # ---------------------------------------------------------------
    # CFG#93# recipe_body -> statement* | λ  (stops before REFILL)
    # The body of a recipe: zero or more statements, halting when the
    # next token is REFILL (so refill_final can own that token) or when
    # _is_start_statement() returns False (end of block).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#94# refill_final -> REFILL refill_arg
    # Mandatory return statement at the end of a recipe.  Called by
    # parse_recipe_def after parse_recipe_body stops consuming statements.
    # ---------------------------------------------------------------
    def parse_refill_final(self):
        """Parse rule: refill_final -> refill? arg"""
        return self._node("refill_final", [
            self._expect("REFILL"),
            self.parse_refill_arg()
        ])

    # ---------------------------------------------------------------
    # CFG#95# refill_arg -> OP_PAREN refill_content extra_refill_val CL_PAREN
    #                    |  ZERO
    # The value(s) returned: a parenthesized expression/string list, or
    # the literal 0 (used by main and void returns to signal "no value").
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#96# refill_content -> BLENDLIT | expression
    # The actual value being returned.  BLENDLIT is a separate LL(1)
    # branch so string literals can be returned from blend-typed recipes.
    # ---------------------------------------------------------------
    def parse_refill_content(self):
        """Parse rule: refill_content -> BLENDLIT | expression"""
        if self._current().type == "BLENDLIT":
            return self._node("refill_content", [self._expect("BLENDLIT")])
        return self._node("refill_content", [self.parse_expression()])

    # ---------------------------------------------------------------
    # CFG#97# extra_refill_val -> (COMMA refill_content)* | λ
    # Supports multiple return values: refill?(a, b, c).  Loops while
    # COMMA is present after the first refill_content.
    # ---------------------------------------------------------------
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
    # empty is CARAMEL's void keyword.  The definition ends with a required
    # REFILL token (without a return value) to close the function body.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#98# empty_def -> EMPTY ID OP_PAREN parameter CL_PAREN
    #                      OP_BRACKETS empty_body REFILL CL_BRACKETS
    # Void function definition.  The REFILL at the end is consumed here
    # (not by a separate refill_final rule) since void functions return no value.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#99# empty_body -> statement* | λ  (stops before REFILL)
    # Body of a void function.  Stops when the next token is REFILL or
    # is not a valid statement start, leaving REFILL for parse_empty_def.
    # ---------------------------------------------------------------
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
    # crema is CARAMEL's class keyword.  A crema body may contain methods
    # (recipe / empty) and fields (brewed or plain data-type) with optional
    # access modifiers (cafe = public, backroom = private).  The crema_body_cont
    # dispatcher uses a four-way LL(1) split on the first token of each member.
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#100# crema_def -> CREMA ID OP_BRACKETS crema_body CL_BRACKETS
    # Class definition: CREMA keyword, name, then members inside { }.
    # ---------------------------------------------------------------
    def parse_crema_def(self):
        """Parse rule: crema_def -> crema ID { body }"""
        return self._node("crema_def", [
            self._expect("CREMA"),
            self._expect("ID"),
            self._expect("OP_BRACKETS"),
            self.parse_crema_body(),
            self._expect("CL_BRACKETS")
        ])

    # ---------------------------------------------------------------
    # CFG#101# crema_body -> crema_body_cont* | λ
    # Zero or more member definitions inside a class.  Loops while the
    # current token is a valid member-start: access modifier (CAFE /
    # BACKROOM), method keyword (RECIPE / EMPTY), or data type.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#102# crema_body_cont -> CAFE crema_acc_body
    #                          |  BACKROOM crema_acc_body
    #                          |  crema_dtype_body
    # Single member of a class.  CAFE/BACKROOM are optional access modifiers;
    # crema_dtype_body handles all unmodified member shapes.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#103# crema_acc_body -> RECIPE crema_recipe_type ID OP_PAREN parameter CL_PAREN
    #                            OP_BRACKETS recipe_body refill_final CL_BRACKETS
    #                         |  EMPTY ID OP_PAREN parameter CL_PAREN
    #                            OP_BRACKETS empty_body REFILL CL_BRACKETS
    #                         |  BREWED crema_acc_brewed_body
    #                         |  data_type ID crema_dtype_id_tail
    # Four-way dispatch for access-modified class members: recipe method,
    # empty method, constant field (brewed), or plain typed field.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#104# crema_acc_brewed_body -> data_type var_dec_const_init var_dec_const_tail
    # Constant field group in an access-modified context.  All fields must
    # have initializers (brewed = const semantic).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#105# crema_dtype_body -> RECIPE crema_recipe_type ID OP_PAREN ... CL_BRACKETS
    #                           |  EMPTY ID OP_PAREN ... CL_BRACKETS
    #                           |  BREWED crema_dtype_brewed_body
    #                           |  data_type ID crema_dtype_id_tail
    # Same four-way dispatch as crema_acc_body but without an access modifier.
    # Used when the member is not prefixed by cafe or backroom.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#106# crema_recipe_type -> data_type
    # Return type of a method inside a class.  Equivalent to
    # parse_recipe_ret_type — a thin named wrapper for AST clarity.
    # ---------------------------------------------------------------
    def parse_crema_recipe_type(self):
        """Parse rule: crema_recipe_type -> data_type"""
        if self._current().type in self.DATA_TYPE:
            return self._node("crema_recipe_type", [self.parse_data_type()])
        self._error(self.DATA_TYPE)

    # ---------------------------------------------------------------
    # CFG#107# crema_dtype_brewed_body -> data_type var_dec_const_init var_dec_const_tail
    # Constant field group without access modifier.  All fields must be
    # initialized — same semantics as acc_brewed_body.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#108# crema_dtype_id_tail -> OP_BRACKETS arr_size_val CL_BRACKETS arr_dec_dim
    #                              |  opt_assign var_dec_tail
    # After "type ID" in a class body: [ means the field is an array;
    # otherwise it is a scalar with an optional default and sibling list.
    # ---------------------------------------------------------------
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
    # The program entry point: "bean cup() { ... refill? 0 }".  The return
    # statement refill? 0 is mandatory but may appear anywhere in the body
    # (parse_main_body recurses into itself until it finds the REFILL).
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#109# main_def -> BEAN CUP OP_PAREN CL_PAREN OP_BRACKETS main_body
    # Parses the mandatory program entry point.  bean cup is the fixed
    # signature; the body is handled by parse_main_body which enforces
    # that refill? 0 is present.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#110# refill_main -> REFILL ZERO refill_main_tail
    # The exit point of main: "refill? 0" (equivalent to C's "return 0;").
    # refill_main_tail handles whether the closing } follows or more
    # statements follow the zero (which would be unreachable).
    # ---------------------------------------------------------------
    def parse_refill_main(self):
        """Parse rule: refill_main -> refill? 0 tail"""
        return self._node("refill_main", [
            self._expect("REFILL"),
            self._expect("ZERO"),
            self.parse_refill_main_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#111# refill_main_tail -> CL_BRACKETS | main_body
    # After "refill? 0": if } follows, close the main block; if another
    # statement or REFILL follows, continue parsing main_body (handles
    # patterns like "refill? 0 \n bean x = 1 \n refill? 0 }").
    # ---------------------------------------------------------------
    def parse_refill_main_tail(self):
        """Parse rule: refill_main_tail -> main_body | }"""
        if self._current().type == "CL_BRACKETS":
            return self._node("refill_main_tail", [
                self._expect("CL_BRACKETS")
            ])
        if self._is_start_statement() or self._current().type == "REFILL":
            return self._node("refill_main_tail", [self.parse_main_body()])
        self._error({"CL_BRACKETS"})

    # ---------------------------------------------------------------
    # CFG#112# main_body -> statement main_body | refill_main
    # Recursive descent through main statements, terminating when REFILL
    # is encountered (which triggers refill_main for the "return 0" token).
    # Left-recursion-free: the base case (refill_main) is REFILL-guarded.
    # ---------------------------------------------------------------
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
    # Top-level statement dispatcher.  Uses _is_start_statement() to guard
    # the outer while loops and this method as the inner routing switch.
    # Every non-declaration statement keyword (BATTER, GLAZE, IFBREW, etc.)
    # is unambiguous at one-token lookahead, making this fully LL(1).
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#113# statement -> dec | input_stmt | output_stmt | if_cond
    #                    |  flav_switch | pour_loop | whilehot_loop
    #                    |  tastetill_loop | intrpt_stmt | refill_stmt
    # Main statement router — 10 alternatives all disambiguated by the
    # first token.  Declaration-starting tokens (type keywords, ID, ORDER,
    # ++, --, mug, new) route to parse_dec.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#114# stmt_tail -> statement* | λ
    # Zero or more additional statements after the first one in a block.
    # Loops while _is_start_statement() holds; used by if/while/loop bodies.
    # ---------------------------------------------------------------
    def parse_stmt_tail(self):
        """Parse rule: stmt_tail -> (statement)* | λ"""
        children = []
        while self._is_start_statement():
            children.append(self.parse_statement())
        if not children:
            children.append(self._node("_empty"))
        return self._node("stmt_tail", children)

    # ---------------------------------------------------------------
    # CFG#115# stmt_tail_until_snap -> (statement \ {snap})* | λ
    # Variant of stmt_tail used inside switch case bodies.  Stops when the
    # next token is SNAP (break) so the case terminator is not consumed
    # inside the statement loop.
    # ---------------------------------------------------------------
    def parse_stmt_tail_until_snap(self):
        """Parse rule: stmt_tail_until_snap -> (statement except snap)* | λ"""
        children = []
        while self._is_start_statement() and self._current().type != "SNAP":
            children.append(self.parse_statement())
        if not children:
            children.append(self._node("_empty"))
        return self._node("stmt_tail_until_snap", children)
    
    # ---------------------------------------------------------------
    # CFG#116# refill_stmt -> REFILL refill_arg
    # Early-return statement that can appear inside any control-flow block
    # (ifbrew, whilehot, pour, etc.).  Consumes REFILL then delegates to
    # refill_arg for the return value or 0.
    # ---------------------------------------------------------------
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
    # batter@ is the input keyword (scanf-like); glaze is the output keyword
    # (printf-like).  Both accept comma-separated variable targets/values.
    # input also accepts an optional prompt string: batter@(x)("Enter x: ").
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#117# input_stmt -> BATTER input_args input_val
    # Read input into one or more variables.  input_args names the targets;
    # input_val is the optional prompt string in parentheses.
    # ---------------------------------------------------------------
    def parse_input_stmt(self):
        """Parse rule: input_stmt -> batter@ args input_val"""
        return self._node("input_stmt", [
            self._expect("BATTER"),
            self.parse_input_args(),
            self.parse_input_val()
        ])

    # ---------------------------------------------------------------
    # CFG#118# input_args -> input_args_unit input_args_unit_tail
    # One or more comma-separated input target variables.  The first is
    # mandatory (input_args_unit), the rest loop via input_args_unit_tail.
    # ---------------------------------------------------------------
    def parse_input_args(self):
        """Parse rule: input_args -> arg_unit (COMMA arg_unit)*"""
        return self._node("input_args", [
            self.parse_input_args_unit(),
            self.parse_input_args_unit_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#119# input_args_unit -> ORDER DOT_ACC ID input_order_tail
    #                          |  ID input_id_tail
    # Single input target: ORDER-prefixed (instance field) or plain ID.
    # The tail handles optional array indexing or member access on the target.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#120# input_id_tail -> DOT_ACC ID input_dot_tail
    #                        |  OP_BRACKETS array_index CL_BRACKETS arr_call_tail
    #                        |  λ
    # After the ID in an input target: member access, array element, or
    # plain variable (λ).  The target must be writable (lvalue).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#121# input_dot_tail -> DOT_ACC ID | λ
    # Optional second-level member access after "ID.member" in an input
    # target: "ID.outer.inner" reads the inner field.
    # ---------------------------------------------------------------
    def parse_input_dot_tail(self):
        """Parse rule: input_dot_tail -> . ID | λ"""
        if self._accept("DOT_ACC"):
            return self._node("input_dot_tail", [
                self._node("DOT_ACC", []),
                self._expect("ID")
            ])
        return self._node("input_dot_tail", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#122# input_order_tail -> OP_BRACKETS array_index CL_BRACKETS arr_call_tail
    #                           |  DOT_ACC ID
    #                           |  λ
    # After "order.field" in an input target: array element, deeper member,
    # or just the field itself.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#123# input_args_unit_tail -> (COMMA input_args_unit)* | λ
    # Second and subsequent input targets after the first.  Loops while
    # COMMA is present; each additional target uses input_args_unit.
    # ---------------------------------------------------------------
    def parse_input_args_unit_tail(self):
        """Parse rule: input_args_unit_tail -> (COMMA unit)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_input_args_unit())
        if not children:
            children.append(self._node("_empty"))
        return self._node("input_args_unit_tail", children)

    # ---------------------------------------------------------------
    # CFG#124# input_val -> OP_PAREN BLENDLIT CL_PAREN | λ
    # Optional prompt string shown to the user before reading input.
    # If OP_PAREN is not present, no prompt is displayed (λ).
    # ---------------------------------------------------------------
    def parse_input_val(self):
        """Parse rule: input_val -> (BLENDLIT) | λ"""
        if self._accept("OP_PAREN"):
            return self._node("input_val", [
                self._node("OP_PAREN", []),
                self._expect("BLENDLIT"),
                self._expect("CL_PAREN")
            ])
        return self._node("input_val", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#125# output_stmt -> GLAZE OP_PAREN output_args CL_PAREN
    # Print statement.  Arguments are inside parentheses; the argument
    # list may be empty (glaze() prints nothing) or contain values and
    # string literals concatenated with +.
    # ---------------------------------------------------------------
    def parse_output_stmt(self):
        """Parse rule: output_stmt -> glaze (output_args)"""
        return self._node("output_stmt", [
            self._expect("GLAZE"),
            self._expect("OP_PAREN"),
            self.parse_output_args(),
            self._expect("CL_PAREN")
        ])

    # ---------------------------------------------------------------
    # CFG#126# output_args -> BLENDLIT concat
    #                      |  expression concat
    #                      |  λ
    # The content of a glaze() call.  BLENDLIT is the separate branch for
    # string literals; expression covers numeric/boolean values.  The
    # trailing concat handles + concatenation onto either kind of value.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#127# concat -> (PLUS blend_term)* | λ
    # String concatenation suffix in output_args.  Loops while PLUS is
    # present; each step appends another blend_term to the printed value.
    # ---------------------------------------------------------------
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
    # Three control-flow families:
    #   • if / elif / else  — ifbrew / elifroth / elspress
    #   • switch / case     — flavour / syrup / defoam
    #   • loops             — pour (for), whilehot (while), tastetill (do-while)
    # The pour loop also enforces that its condition contains a relational
    # or boolean operator (parse_pour_condition post-validates the AST).
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#128# if_cond -> IFBREW OP_PAREN expression CL_PAREN
    #                     OP_BRACES statement stmt_tail CL_BRACES
    #                     if_cond_tail
    # Parses the "if" clause.  At least one statement is required inside
    # the body (statement + stmt_tail).  if_cond_tail handles elifroth/elspress.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#129# if_cond_tail -> ELIFROTH OP_PAREN expression CL_PAREN
    #                          OP_BRACES statement stmt_tail CL_BRACES
    #                          if_cond_tail        (recursive: chains elif)
    #                       |  ELSPRESS OP_BRACES statement stmt_tail CL_BRACES
    #                       |  λ
    # The recursive self-call on the ELIFROTH branch models a chain of
    # elif clauses.  ELSPRESS is the base case; λ means no else at all.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#130# flav_switch -> FLAVOUR OP_PAREN flav_lit CL_PAREN
    #                         OP_BRACES syrup_switch CL_BRACES
    # Switch statement.  The match value (flav_lit) is limited to literals
    # and IDs — not arbitrary expressions — to keep the grammar LL(1).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#131# flav_lit -> BEANLIT | ID | CHURROLIT | HOT | COLD
    # The switch expression: an integer literal, identifier, char literal,
    # or boolean literal.  String literals (BLENDLIT) are not supported
    # as switch values.
    # ---------------------------------------------------------------
    def parse_flav_lit(self):
        """Parse rule: flav_lit -> BEANLIT | ID | CHURROLIT | hot | cold"""
        t = self._current().type
        if t in {"BEANLIT", "ID", "CHURROLIT", "HOT", "COLD"}:
            return self._node("flav_lit", [self._expect(t)])
        self._error({"BEANLIT", "ID", "CHURROLIT", "HOT", "COLD"})

    # ---------------------------------------------------------------
    # CFG#132# syrup_switch -> SYRUP case_lit COLON statement stmt_tail_until_snap
    #                          SNAP defoam_stmt syrup_switch_tail
    # A single case clause.  The body must be followed by SNAP (break).
    # defoam_stmt parses the optional default (defoam:) clause; the
    # recursive syrup_switch_tail chains additional cases.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#133# syrup_switch_tail -> syrup_switch | λ
    # Chains additional case clauses.  If SYRUP is not the lookahead the
    # switch block ends (λ); otherwise parse another syrup_switch.
    # ---------------------------------------------------------------
    def parse_syrup_switch_tail(self):
        """Parse rule: syrup_switch_tail -> syrup_switch | λ"""
        if self._current().type == "SYRUP":
            return self._node("syrup_switch_tail", [self.parse_syrup_switch()])
        return self._node("syrup_switch_tail", [self._node("_empty")])

    # ---------------------------------------------------------------
    # CFG#134# case_lit -> BEANLIT | CHURROLIT | HOT | COLD
    # The literal that a syrup (case) matches against.  Note: IDs are
    # excluded (case labels must be compile-time constants), unlike flav_lit.
    # ---------------------------------------------------------------
    def parse_case_lit(self):
        """Parse rule: case_lit -> BEANLIT | CHURROLIT | hot | cold"""
        t = self._current().type
        if t in {"BEANLIT", "CHURROLIT", "HOT", "COLD"}:
            return self._node("case_lit", [self._expect(t)])
        self._error({"BEANLIT", "CHURROLIT", "HOT", "COLD"})

    # ---------------------------------------------------------------
    # CFG#135# defoam_stmt -> DEFOAM COLON statement stmt_tail_until_snap SNAP | λ
    # Optional default clause in a switch.  If DEFOAM is present, a body
    # and SNAP (break) are required.  λ means no default case.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#136# pour_condition -> expression  (with boolean content required)
    # Parses the loop condition permissively as an expression then validates
    # post-parse that the tree contains a relational/logical operator or
    # boolean literal.  This "parse wide, validate narrow" approach keeps
    # the grammar LL(1) while giving a precise error for "pour(i=0; i; i++)".
    # ---------------------------------------------------------------
    def parse_pour_condition(self):
        """Parse pour loop condition: must be a boolean/relational expression.

        Rejects bare identifiers or arithmetic-only expressions that lack
        relational operators (>, <, ==, !=, >=, <=), logical operators
        (&&, ||), NOT (!), or boolean literals (hot, cold).
        """
        # Why: parse permissively first, then validate — keeps grammar LL(1)
        # while giving the user a targeted "expected relational operator" error.
        expr = self.parse_expression()
        if not self._has_boolean_content(expr):
            tok = self._current()
            raise UnexpectedToken(
                tok,
                self.REL_OP | self.LOGIC_OP | {"NOT"},
                index=self.stream.index
            )
        return expr

    # ---------------------------------------------------------------
    # CFG#137# pour_loop -> POUR OP_PAREN pour_init SEMICOLON pour_condition SEMICOLON
    #                       update CL_PAREN OP_BRACES statement stmt_tail CL_BRACES
    # For-loop: three-part header (init ; cond ; update) plus a required
    # body.  The condition is validated to be boolean by parse_pour_condition.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#138# pour_init -> data_type ID EQUALS value var_dec_const_tail
    #                    |  ID EQUALS value var_dec_const_tail
    # Loop counter initialization.  DATA_TYPE branch declares a new variable;
    # ID branch reuses an existing one.  The trailing var_dec_const_tail
    # allows multiple init expressions: pour(bean i=0, j=1; ...).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#139# update -> update_unit update_tail
    # The third clause of a pour header: one or more comma-separated
    # update expressions (assignment, increment, decrement).
    # ---------------------------------------------------------------
    def parse_update(self):
        """Parse rule: update -> unit (COMMA unit)*"""
        return self._node("update", [
            self.parse_update_unit(),
            self.parse_update_tail()
        ])

    # ---------------------------------------------------------------
    # CFG#140# update_tail -> (COMMA update_unit)* | λ
    # Additional update expressions after the first in a pour header.
    # Loops while COMMA is present.
    # ---------------------------------------------------------------
    def parse_update_tail(self):
        """Parse rule: update_tail -> (COMMA unit)* | λ"""
        children = []
        while self._accept("COMMA"):
            children.append(self._node("COMMA", []))
            children.append(self.parse_update_unit())
        if not children:
            children.append(self._node("_empty"))
        return self._node("update_tail", children)

    # ---------------------------------------------------------------
    # CFG#141# update_unit -> ID update_id_tail
    #                      |  INCREMENT ID
    #                      |  DECREMENT ID
    # A single update expression: ID followed by an assign or postfix op,
    # or a prefix ++ / -- before the ID.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#142# update_id_tail -> assign_op update_val
    #                         |  INCREMENT
    #                         |  DECREMENT
    # After an ID in an update clause: compound assignment (+=, -=, etc.),
    # postfix ++, or postfix --.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#143# assign_op -> EQUALS | EQUAL_PLUS | EQUAL_MINUS
    #                    |  EQUAL_ASTERISK | EQUAL_DIVIDE
    # Matches one assignment operator.  Shared by update clauses and
    # the general id_dec_tail assignment branch.
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#144# update_val -> expression
    # The RHS of a compound assignment in an update clause.  Any full
    # expression is valid (arithmetic, relational, function call, etc.).
    # ---------------------------------------------------------------
    def parse_update_val(self):
        """Parse rule: update_val -> expression"""
        return self._node("update_val", [self.parse_expression()])

    # ---------------------------------------------------------------
    # CFG#145# whilehot_loop -> WHILEHOT OP_PAREN expression CL_PAREN
    #                           OP_BRACES statement stmt_tail CL_BRACES
    # While loop: condition first, body second (pre-test).  The condition
    # is any full expression (no boolean-content enforcement unlike pour).
    # ---------------------------------------------------------------
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

    # ---------------------------------------------------------------
    # CFG#146# tastetill_loop -> TASTE OP_BRACES statement stmt_tail CL_BRACES
    #                            TILL COLON OP_PAREN expression CL_PAREN
    # Do-while loop: body executes first, then the condition is tested.
    # The condition appears AFTER the closing } — the reversed order vs.
    # whilehot is intentional and mirrors C's do { ... } while(...) semantics.
    # ---------------------------------------------------------------
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
    # snap = break, skip = continue.  Both are single-token statements
    # with no operands.  They may appear inside any loop body or switch
    # case (the grammar does not enforce loop-nesting context — that is
    # left to semantic analysis in the IR generator).
    # ========================================================================

    # ---------------------------------------------------------------
    # CFG#147# intrpt_stmt -> SNAP | SKIP
    # Loop interrupt statement.  snap exits the nearest enclosing loop or
    # switch; skip skips the remainder of the current loop iteration.
    # ---------------------------------------------------------------
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

        Two-phase pipeline:
          Phase 1 — Lex: collect all tokens and surface any ERROR-typed
          tokens as lexer errors.  If any exist, abort before parsing so
          the user sees clean lex errors rather than cascading parse errors.
          Phase 2 — Parse: run RDParser on the clean token list.  Any
          UnexpectedToken / UnexpectedEOF is caught here and converted into
          a human-readable error dict with sorted expected-token display names.

        Handles both lexer and parser errors, producing human-readable
        error messages with context about expected tokens.
        """
        # Phase 1: tokenize — abort immediately if the lexer found any errors
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

        # Phase 2: parse the clean token stream
        parser = RDParser(tokens)

        try:
            parse_tree = parser.parse()
            self.ast = parse_tree
            print(parse_tree.pretty())
        except (UnexpectedToken, UnexpectedEOF) as e:
            expected = list(dict.fromkeys(getattr(e, "expected", [])))
            if not expected:
                expected.append("NONE")

            # Build reverse maps so internal token type names (e.g. "PLUS")
            # display as the character the user typed (e.g. "+").
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