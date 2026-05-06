"""
Intermediate Representation (IR) Generator for CARAMEL Language

Translates the AST (ParseNode tree) from the parser into a linear sequence of
Three-Address Code (TAC) instructions. Each instruction is an IRInstruction object
with an op field and operand fields.

PIPELINE POSITION:
  Parser → [AST] → IRGenerator → [IR list] → Optimizer → CodeGenerator

HOW IT WORKS:
  1. IRGenerator.generate() calls _visit(ast) which dispatches to _visit_<nodename>()
     for every node in the AST tree.
  2. Each visitor either:
     a) Emits one or more IR instructions via _emit()
     b) Returns a value (variable name or temp) to its parent visitor
     c) Both
  3. Expressions are evaluated bottom-up: leaf nodes return literals/var names,
     operators emit BINOP and return a temp variable name.
  4. Statements (assignments, calls, loops) emit side-effect instructions and
     return nothing.

IR Instruction Format:
    IRInstruction(op, dest, arg1, arg2, **extra)

    op    — the operation name (string)
    dest  — destination variable, label name, or function name
    arg1  — first operand (variable name, literal value, or label)
    arg2  — second operand (optional)
    extra — dict of additional named fields (type, binop, param, etc.)

Operations:
    DECLARE     - variable declaration          (dest=var, type=dtype)
    ASSIGN      - simple assignment             (dest=var, arg1=value)
    BINOP       - binary operation              (dest=temp, arg1, arg2, binop=op)
    UNARYOP     - unary operation               (dest=temp, arg1, unaryop=op)
    LABEL       - label marker                  (dest=label_name)
    GOTO        - unconditional jump            (dest=label)
    IF_FALSE    - conditional jump if false     (arg1=cond, dest=label)
    IF_TRUE     - conditional jump if true      (arg1=cond, dest=label)
    CALL        - function call                 (dest=temp, arg1=func_name, arg_count=n)
    METHOD_CALL - object method call            (dest=temp, arg1=obj, arg2=method, arg_count=n)
    PARAM       - push parameter before CALL    (arg1=value)
    RETURN      - return from function          (arg1=value, return_type=dtype)
    FUNC_BEGIN  - function entry point          (dest=func_name, [method_of=class])
    FUNC_END    - function exit point           (dest=func_name)
    PRINT       - glaze() output                (args=[val, val, ...])
    INPUT       - batter@ input                 (dest=var, prompt=str)
    ARR_DECLARE - array declaration             (dest=var, type=dtype, dims=[size])
    ARR_STORE   - array element write           (dest=arr, arg1=index, arg2=value)
    ARR_LOAD    - array element read            (dest=temp, arg1=arr, arg2=index)
    CONCAT      - string concatenation          (dest=temp, arg1, arg2)
    CAST        - type conversion               (dest=temp, arg1=source, type=target)
    MEMBER_ACC  - object field read             (dest=temp, arg1=obj, arg2=field)
    MEMBER_SET  - object field write            (dest=obj, arg1=field, arg2=value)
    CLASS_DEF   - class definition start        (dest=class_name)
    CLASS_FIELD - class field declaration       (dest=field, type=dtype, class_name=name)
    CLASS_END   - class definition end          (dest=class_name)
    NOP         - no operation placeholder
"""

import traceback

class IRInstruction:
    """
    A single three-address code (TAC) instruction in the Caramel IR.

    Slots (for memory efficiency):
      op    — operation name string (e.g. 'ASSIGN', 'BINOP', 'IF_FALSE')
      dest  — destination: variable name, temp name (_t1), label, or function name
      arg1  — first operand: variable, literal value, or label name
      arg2  — second operand (optional, used by BINOP, MEMBER_SET, ARR_STORE, etc.)
      extra — dict of additional keyword fields passed at construction time
              Common extra keys by op:
                DECLARE:    type (str), param (bool), constant (bool)
                BINOP:      binop (operator string: '+', '==', '&&', etc.)
                UNARYOP:    unaryop ('-' or '!')
                ARR_DECLARE: dims (list), init (list of values)
                ARR_LOAD:   is_2d (bool)
                CALL:       arg_count (int), use_float (bool for rand)
                METHOD_CALL: arg_count (int), method_of (class name)
                FUNC_BEGIN: method_of (class name, if this is a method)
                RETURN:     return_type (Caramel dtype string)
                INPUT:      array_elem_type (dtype), prompt (str)
                CLASS_FIELD: type, access, class_name, init, array_size
                PRINT:      args (list of values)
    """

    """
        DECLARE     - variable declaration          (dest=var, type=dtype)
        ASSIGN      - simple assignment             (dest=var, arg1=value)
        BINOP       - binary operation              (dest=temp, arg1, arg2, binop=op)
        UNARYOP     - unary operation               (dest=temp, arg1, unaryop=op)
        LABEL       - label marker                  (dest=label_name)
        GOTO        - unconditional jump            (dest=label)
        IF_FALSE    - conditional jump if false     (arg1=cond, dest=label)
        IF_TRUE     - conditional jump if true      (arg1=cond, dest=label)
        CALL        - function call                 (dest=temp, arg1=func_name, arg_count=n)
        METHOD_CALL - object method call            (dest=temp, arg1=obj, arg2=method, arg_count=n)
        PARAM       - push parameter before CALL    (arg1=value)
        RETURN      - return from function          (arg1=value, return_type=dtype)
        FUNC_BEGIN  - function entry point          (dest=func_name, [method_of=class])
        FUNC_END    - function exit point           (dest=func_name)
        PRINT       - glaze() output                (args=[val, val, ...])
        INPUT       - batter@ input                 (dest=var, prompt=str)
        ARR_DECLARE - array declaration             (dest=var, type=dtype, dims=[size])
        ARR_STORE   - array element write           (dest=arr, arg1=index, arg2=value)
        ARR_LOAD    - array element read            (dest=temp, arg1=arr, arg2=index)
        CONCAT      - string concatenation          (dest=temp, arg1, arg2)
        CAST        - type conversion               (dest=temp, arg1=source, type=target)
        MEMBER_ACC  - object field read             (dest=temp, arg1=obj, arg2=field)
        MEMBER_SET  - object field write            (dest=obj, arg1=field, arg2=value)
        CLASS_DEF   - class definition start        (dest=class_name)
        CLASS_FIELD - class field declaration       (dest=field, type=dtype, class_name=name)
        CLASS_END   - class definition end          (dest=class_name)
        NOP         - no operation placeholder
    """

    __slots__ = ("op", "dest", "arg1", "arg2", "extra")

    def __init__(self, op, dest=None, arg1=None, arg2=None, **extra):
        """
        Create an IR instruction.
        All keyword arguments beyond op/dest/arg1/arg2 are stored in self.extra.
        Example: IRInstruction('BINOP', dest='_t1', arg1='x', arg2=3, binop='+')
        """
        self.op = op
        self.dest = dest
        self.arg1 = arg1
        self.arg2 = arg2
        self.extra = extra

    def to_dict(self):
        """
        Serialize to a plain dict for JSON output / debugging.
        Only includes fields that are not None, plus all extra kwargs.
        """
        d = {"op": self.op}
        if self.dest is not None:
            d["dest"] = self.dest
        if self.arg1 is not None:
            d["arg1"] = self.arg1
        if self.arg2 is not None:
            d["arg2"] = self.arg2
        d.update(self.extra)
        return d

    def __repr__(self):
        """Human-readable string, used in DEBUG IRGEN LIST output: IR(op, dest=..., arg1=..., ...)"""
        parts = [self.op]
        if self.dest is not None:
            parts.append(f"dest={self.dest}")
        if self.arg1 is not None:
            parts.append(f"arg1={self.arg1}")
        if self.arg2 is not None:
            parts.append(f"arg2={self.arg2}")
        for k, v in self.extra.items():
            parts.append(f"{k}={v}")
        return f"IR({', '.join(parts)})"


class IRGenerator:
    """
    Walks the CARAMEL AST and emits three-address code IR instructions.

    The generator maintains:
      - A list of IR instructions (self.instructions)
      - A temp variable counter for intermediate results
      - A label counter for control flow
      - A scope-aware variable type map
    """

    # Map token types to CARAMEL types
    DTYPE_MAP = {
        "BEAN": "bean", "DRIP": "drip", "CHURRO": "churro",
        "TEMP": "temp", "BLEND": "blend"
    }

    # Map token types to Python-friendly operator strings
    BINOP_MAP = {
        "PLUS": "+", "MINUS": "-", "MULTIPLY": "*",
        "DIVIDE": "/", "MODULO": "%",
        "AND": "&&", "OR": "||",
        "GREATER_THAN": ">", "LESSER_THAN": "<",
        "EQ_EQUALS": "==", "NOT_EQUAL": "!=",
        "GREATER_EQUAL": ">=", "LESSER_EQUAL": "<=",
    }

    ASSIGN_OP_MAP = {
        "EQUALS": "=",
        "EQUAL_PLUS":     "+",
        "EQUAL_MINUS":    "-",
        "EQUAL_ASTERISK": "*",
        "EQUAL_DIVIDE":   "/",
    }

    LITERAL_TYPES = {
        "BEANLIT": "bean", "DRIPLIT": "drip",
        "CHURROLIT": "churro", "HOT": "temp", "COLD": "temp",
        "BLENDLIT": "blend",
    }

    def __init__(self, ast):
        """
        Initialize the IR generator with the root AST node.

        State variables — what they track and why:

        self.ast               — root ParseNode from the parser; starting point for _visit()
        self.instructions      — the output: flat list of IRInstruction objects built
                                  incrementally as _visit() walks the AST
        self._temp_count       — monotonic counter for generating unique temp variable names
                                  (_t1, _t2, ...). Temps hold intermediate expression results.
        self._label_count      — monotonic counter for generating unique control-flow labels
                                  (WHILE_START_1, IF_END_2, etc.)
        self._var_types        — maps variable name → Caramel type string ('bean', 'drip', etc.)
                                  Set when DECLARE is emitted, read during assignment coercion
                                  to decide if a value needs to be converted (e.g. bool→int)
        self._current_func     — name of the function currently being compiled, or None at
                                  global scope. Used by refill? to know its context.
        self._loop_stack       — stack of (continue_label, break_label) tuples, one entry
                                  per active loop. Pushed by pour/whilehot, popped when the
                                  loop ends. Lets 'skip' (continue) and 'snap' (break) find
                                  their target label without searching the IR.
        self._current_return_type — Caramel dtype of the current function's return type,
                                  or None for void. Attached to RETURN instructions so the
                                  codegen can coerce the return value.
        self._current_class    — name of the class currently being defined (set inside
                                  _visit_crema_def, cleared after). Tells _visit_crema_acc_body
                                  and _visit_acc_mod_dec that we're in class context.
        self._current_field_access — 'public' or 'private', set when CAFE/BACKROOM token
                                  is seen in _visit_crema_body_cont. Used as access level
                                  for the next field/method emitted.
        self._class_fields     — dict: class_name → list of field/method dicts.
                                  Each dict has 'name', 'type', 'access', optional 'kind'.
                                  Built during class definition. Used by _visit_crema_method
                                  to populate _class_field_names for sibling method resolution.
        self._class_field_names — set of field/method names for the class currently being
                                  visited inside a method body. Set at method entry, cleared
                                  at method exit. Lets bare 'increment()' inside a method
                                  emit METHOD_CALL instead of CALL.
        self._scope_depth      — integer depth of nested pour loops. Incremented on pour
                                  entry, decremented on exit. Used to generate unique
                                  scoped variable names to avoid shadowing bugs.
        self._shadow_map       — dict: original_var_name → scoped_var_name.
                                  When a pour loop declares a variable that already exists
                                  in an outer scope, the inner variable is renamed to
                                  '_s{depth}_{name}' and the mapping is stored here so
                                  all references inside the loop use the scoped name.
        self._shadow_stack     — stack of _shadow_map snapshots, one per active pour loop.
                                  On loop exit, the previous shadow_map is restored from
                                  this stack, undoing the inner scope's renames.
        self._errors           — list of error messages (currently unused, errors are raised
                                  or printed directly)
        """
        self.ast = ast
        self.instructions = []
        self._temp_count = 0
        self._label_count = 0
        self._var_types = {}
        self._current_func = None
        self._loop_stack = []
        self._current_return_type = None
        self._current_class = None
        self._current_field_access = "public"
        self._class_fields = {}
        self._class_field_names = set()
        self._scope_depth = 0
        self._shadow_map = {}
        self._shadow_stack = []
        self._errors = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self):
        """
        Entry point. Walk the AST and return the complete IR instruction list.
        Calls _visit(self.ast) which recursively dispatches to all _visit_<name> methods.
        The DEBUG IRGEN LIST output is printed here for development visibility.
        Returns: list of IRInstruction, or empty string on fatal crash.
        """
        
        try:
            if not self.ast:
                return []
            self._visit(self.ast)

            # print("[IR_GEN] Starting generation")
            # if not self.ast:
            #     return []
            # try:
            #     self._visit(self.ast)
            # except Exception as e:
            #     import traceback
            #     print(f"[IR_GEN CRASH] {e}")
            #     traceback.print_exc()
            #     return self.instructions
            # debug
            for i, instr in enumerate(self.instructions):
                print(f"DEBUG IRGEN LIST [{i:03}]: {instr}")
            return self.instructions
        except Exception as e:
            print(f"[IR_GEN FATAL] {type(e).__name__}: {e}")
            traceback.print_exc()
            return ""
    
    def get_ir_dicts(self):
        """Return IR as a list of plain dictionaries (for JSON serialization)."""
        return [instr.to_dict() for instr in self.instructions]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, op, **kwargs):
        """
        Create an IRInstruction and append it to self.instructions.
        This is the only way instructions are added — all _visit_* methods call this.
        Returns the created instruction (occasionally used to retroactively modify it,
        e.g. upgrading DECLARE→ARR_DECLARE in _visit_dtype_id_tail).
        """
        instr = IRInstruction(op, **kwargs)
        # DEBUG
        # if op == "DECLARE" and kwargs.get("constant") and kwargs.get("type") is None:
        #     import traceback
        #     print(f"[DECLARE type=None constant=True] dest={kwargs.get('dest')}")
        #     traceback.print_stack(limit=6)
        self.instructions.append(instr)
        return instr


    def _new_temp(self):
        """
        Generate a new unique temporary variable name: _t1, _t2, _t3, ...
        Temps hold intermediate expression results that don't correspond to
        any user-declared variable. They're consumed by the next instruction
        and never declared — the codegen treats them as local Python variables.
        """
        self._temp_count += 1
        return f"_t{self._temp_count}"


    def _new_label(self, hint="L"):
        """
        Generate a new unique label name: hint_N (e.g. WHILE_START_1, IF_END_2).
        Labels mark positions in the IR for control flow (GOTO, IF_FALSE targets).
        The hint makes the generated IR more readable in debug output.
        """
        self._label_count += 1
        return f"{hint}_{self._label_count}"


    def _is_node(self, obj):
        """
        Returns True if obj is a ParseNode (has both .name and .children attributes).
        ParseNodes are the internal nodes of the AST (rules like 'expression', 'primary').
        Used throughout to distinguish AST nodes from leaf tokens.
        """
        return hasattr(obj, "name") and hasattr(obj, "children")


    def _is_token(self, obj):
        """
        Returns True if obj is a Token (has .type but NOT .children).
        Tokens are the leaf nodes of the AST (identifiers, literals, keywords).
        Example: ID token has .type='ID' and .value='myVar'.
        """
        return not self._is_node(obj) and hasattr(obj, "type")


    def _get_children(self, node):
        """
        Safely return node.children, or [] if the node has no children attribute.
        Always use this instead of node.children directly to avoid AttributeError
        on token nodes that may accidentally be passed as nodes.
        """
        return node.children if hasattr(node, "children") else []


    def _find_child_node(self, node, name):
        """
        Return the first direct child ParseNode whose .name matches.
        Non-recursive — only searches immediate children.
        Returns None if not found.
        """
        for c in self._get_children(node):
            if self._is_node(c) and c.name == name:
                return c
        return None


    def _find_child_token(self, node, token_type):
        """
        Return the first direct child Token whose .type matches.
        Non-recursive — use _find_child_token_deep() for full tree search.
        Returns None if not found.
        """
        for c in self._get_children(node):
            if self._is_token(c) and c.type == token_type:
                return c
        return None


    def _find_all_child_tokens(self, node, token_type):
        """
        Return a list of all direct child Tokens with the given type.
        Example use: _visit_object_def uses this to extract both 'point' and 'p'
        from 'new point = p' since both are ID tokens.
        """
        return [c for c in self._get_children(node)
                if self._is_token(c) and c.type == token_type]


    def _extract_dtype(self, node):
        """
        Recursively search a node tree for a Caramel type token and return its string.
        Looks for a 'data_type' node first (the grammar wraps type keywords in this),
        then falls back to any token in DTYPE_MAP.
        Returns: 'bean', 'drip', 'churro', 'temp', 'blend', or None.
        """
        if not self._is_node(node):
            if self._is_token(node) and node.type in self.DTYPE_MAP:
                return self.DTYPE_MAP[node.type]
            return None
        if node.name == "data_type":
            for c in node.children:
                if self._is_token(c) and c.type in self.DTYPE_MAP:
                    return self.DTYPE_MAP[c.type]
        for c in node.children:
            result = self._extract_dtype(c)
            if result:
                return result
        return None


    def _token_to_literal(self, tok):
        """
        Convert a literal Token to its Python IR value.
        The IR stores values as Python native types wherever possible:
          BEANLIT   → int        (used directly in BINOP arithmetic)
          DRIPLIT   → float
          HOT/COLD  → True/False
          CHURROLIT → str with quotes e.g. "'a'"  (quotes kept so codegen can detect churro)
          BLENDLIT  → str with quotes e.g. '"hello"' (quotes kept for same reason)
        """
        if tok.type == "BEANLIT":
            return int(tok.value)
        if tok.type == "DRIPLIT":
            return float(tok.value)
        if tok.type == "CHURROLIT":
            return tok.value  # includes quotes e.g. 'a'
        if tok.type == "HOT":
            return True
        if tok.type == "COLD":
            return False
        if tok.type == "BLENDLIT":
            return tok.value  # includes quotes e.g. "hello"
        return tok.value

    # ------------------------------------------------------------------
    # AST Visitor Dispatch
    # ------------------------------------------------------------------


    def _token_to_literal(self, tok):
        """
        Convert a literal Token to its Python IR value.
        The IR stores values as Python native types wherever possible:
          BEANLIT   → int        (used directly in BINOP arithmetic)
          DRIPLIT   → float
          HOT/COLD  → True/False
          CHURROLIT → str with quotes e.g. "'a'"  (quotes kept so codegen can detect churro)
          BLENDLIT  → str with quotes e.g. '"hello"' (quotes kept for same reason)
        """
        if tok.type == "BEANLIT":
            return int(tok.value)
        if tok.type == "DRIPLIT":
            return float(tok.value)
        if tok.type == "CHURROLIT":
            return tok.value  # includes quotes e.g. 'a'
        if tok.type == "HOT":
            return True
        if tok.type == "COLD":
            return False
        if tok.type == "BLENDLIT":
            return tok.value  # includes quotes e.g. "hello"
        return tok.value

    # ------------------------------------------------------------------
    # AST Visitor Dispatch
    # ------------------------------------------------------------------

    def _visit(self, node):
        """
        Central dispatch method — the engine of the IR generator.

        For each AST node, tries to call self._visit_{node.name}(node).
        If no specific visitor exists, falls back to visiting all children
        and returning the last non-None result.

        Special cases:
          - Non-node objects (tokens) → return None immediately
          - _empty productions → return None (no-op nodes from the parser)

        Return value convention:
          - Expression visitors (primary, arith_expr, etc.) return a value:
            either a literal (int/float/bool/str) or a temp variable name string.
          - Statement visitors (id_dec_stmt, output_stmt, etc.) return None;
            they produce IR as a side effect via _emit().
          - The return value propagates upward until consumed by a parent that
            calls _emit() with it as an operand.
        """
        if self._is_node(node) and self._current_class:
            print(f"[VISIT IN CLASS] node={node.name}")
        if not self._is_node(node):
            return None

        # skip empty productions
        if node.name == "_empty":
            return None
        
        # if node.name.isupper():   # token type names are all-caps
        #     return None
        
        # print(f"[IR] visiting node: {node.name}")

        method = getattr(self, f"_visit_{node.name}", None)
        if method:
            return method(node)

        # default: visit all children
        result = None
        for child in node.children:
            r = self._visit(child)
            if r is not None:
                result = r
        return result

    # ------------------------------------------------------------------
    # Program Structure
    # ------------------------------------------------------------------

    def _visit_start(self, node):
        """Root of the AST. Just walks all children to start the traversal."""
        self._visit_children_all(node)


    def _visit_program(self, node):
        """Program node — contains global_def and main_def. Walks all children."""
        self._visit_children_all(node)


    def _visit_global_def(self, node):
        """Global definition scope — contains function defs, class defs, global vars."""
        self._visit_children_all(node)


    def _visit_global_dec(self, node):
        """Individual global declaration — routes to the appropriate def visitor."""
        self._visit_children_all(node)


    def _visit_children_all(self, node):
        """
        Visit all children of a node without returning anything.
        Used by pass-through nodes that don't need special handling.
        Different from _visit() fallback — this explicitly iterates all children
        even when a _visit_<name> method exists and would normally handle it.
        """
        for child in self._get_children(node):
            self._visit(child)

    # ------------------------------------------------------------------
    # Main Function
    # ------------------------------------------------------------------


    def _visit_main_def(self, node):
        """
        Generate IR for the main function cup().
        Emits FUNC_BEGIN 'cup', visits the body, then FUNC_END 'cup'.
        Sets _current_func='cup' while visiting so refill? knows its context.
        """
        self._emit("FUNC_BEGIN", dest="cup")
        self._current_func = "cup"
        self._visit_children_all(node)
        self._current_func = None
        self._emit("FUNC_END", dest="cup")


    def _visit_main_body(self, node):
        """Pass-through — visits all statement children inside cup()."""
        self._visit_children_all(node)


    def _visit_refill_main(self, node):
        """
        Handle 'refill? 0' at the end of cup().
        Always emits RETURN arg1=0 (main always returns integer 0).
        """
        # refill? 0  in main
        self._emit("RETURN", arg1=0)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _visit_dec(self, node):
        """Pass-through dispatch node for all declaration types."""
        self._visit_children_all(node)


    def _visit_acc_mod_dec(self, node):
        """
        Handle declarations inside a class body (cafe/backroom qualified).
        Two paths:
          1. Inside a class (_current_class is set):
             - Detects CAFE/BACKROOM token to set access level
             - Extracts dtype and field name
             - Emits CLASS_FIELD and registers in _class_fields
             - Returns early without emitting a regular DECLARE
          2. Outside a class: pass-through to children (normal declaration)
        This visitor is reached when a declaration has an access modifier token
        as a sibling — i.e. it's inside a crema body but the grammar routes it
        through acc_mod_dec rather than crema_acc_body directly.
        """
        # If inside a class, collect field info
        # print(f"[IRGEN DEBUG ACC_MOD_DEC] _current_class={self._current_class}")
        
        if self._current_class:
            access = "public"
            for child in self._get_children(node):
                if self._is_token(child) and child.type == "CAFE":
                    access = "public"
                elif self._is_token(child) and child.type == "BACKROOM":
                    access = "private"
            # Collect dtype and field name
            dtype = self._extract_dtype(node)
            id_tok = self._find_child_token_deep(node, "ID")
            if dtype and id_tok:
                field_name = id_tok.value
                if self._current_class not in self._class_fields:
                    self._class_fields[self._current_class] = []
                self._class_fields[self._current_class].append({
                    "name": field_name, "type": dtype, "access": access
                })
                self._emit("CLASS_FIELD", dest=field_name, 
                        type=dtype, access=access, class_name=self._current_class)
            return  # don't emit regular DECLARE for class fields
        self._visit_children_all(node)

    def _visit_acc_mod_dec_body(self, node):
        """Pass-through for the body content of an access-modified declaration."""
        self._visit_children_all(node)


    def _visit_dtype_dec(self, node):
        """Handle typed declaration: data_type ID tail"""
        dtype = self._extract_dtype(node)
        id_tok = self._find_child_token(node, "ID")
        if id_tok and dtype:
            var_name = id_tok.value
            self._var_types[var_name] = dtype

            # print(f"[IR_GEN DTYPE_DEC DEBUG] registered '{var_name}' as '{dtype}' in _var_types")
            self._emit("DECLARE", dest=var_name, type=dtype)

            # process the tail (opt_assign, array, etc.)
            for child in self._get_children(node):
                if self._is_node(child) and child.name not in ("data_type",):
                    self._visit(child)
        else:
            self._visit_children_all(node)

    def _visit_dtype_brewed_body(self, node):
        """Handle constant declaration: brewed data_type ID = value.
        Must store dtype in _var_types BEFORE visiting children so
        _visit_var_dec_const_init can look it up by var name."""
        dtype = self._extract_dtype(node)
        if dtype:
            # Recursively find ID token in children
            def find_id(n):
                """Recursively search for the first ID token in a subtree."""
                for c in self._get_children(n):
                    if self._is_token(c) and c.type == "ID":
                        return c
                    if self._is_node(c):
                        result = find_id(c)
                        if result:
                            return result
                return None
            id_tok = find_id(node)
            if id_tok:
                self._var_types[id_tok.value] = dtype
        self._visit_children_all(node)


    def _visit_acc_brewed_body(self, node):
        """Handle 'brewed' (constant) declarations with access modifiers. Pass-through."""
        dtype = self._extract_dtype(node)
        self._visit_children_all(node)


    def _visit_acc_dtype_tail(self, node):
        """Tail of an access-modified declaration — contains the actual variable init. Pass-through."""
        self._visit_children_all(node)


    def _visit_dtype_id_tail(self, node):
        """Handle dtype ID tail: opt_assign, array decl, etc."""
        children = self._get_children(node)
        # Check if this is an array declaration (has OP_BRACKETS)
        has_brackets = False
        for child in children:
            if (self._is_node(child) and child.name == "OP_BRACKETS") or \
               (self._is_token(child) and child.type == "OP_BRACKETS"):
                has_brackets = True
                break

        if has_brackets:
            arr_size = None
            col_size = None
            pre_collect_count = len(self.instructions)
            init_vals = self._collect_arr_init_values(child)
            for child in children:
                if self._is_node(child) and child.name == "arr_size_val":
                    for c2 in self._get_children(child):
                        if self._is_token(c2) and c2.type == "BEANLIT":
                            arr_size = int(c2.value)
                        elif self._is_token(c2) and c2.type == "FLEX_ASTERISK":
                            arr_size = "***"
                        elif self._is_token(c2) and c2.type == "ID":
                            # Variable size — store name, code generator will reference it
                            arr_size = c2.value
                if self._is_node(child) and child.name == "arr_dec_dim":
                    init_vals = self._collect_arr_init_values(child)
                    # Check for 2D: arr_dec_dim starts with OP_BRACKETS + arr_size_val
                    for dc in self._get_children(child):
                        if self._is_node(dc) and dc.name == "arr_size_val":
                            for sc in self._get_children(dc):
                                if self._is_token(sc) and sc.type == "BEANLIT":
                                    col_size = int(sc.value)
                                elif self._is_token(sc) and sc.type == "FLEX_ASTERISK":
                                    col_size = "***"
                                elif self._is_token(sc) and sc.type == "ID":
                                    col_size = sc.value
                                    
            for instr in reversed(self.instructions[:pre_collect_count]):
                if instr.op == "DECLARE":
                    instr.op = "ARR_DECLARE"
                    instr.extra["dims"] = [arr_size] if arr_size else []
                    if init_vals:
                        instr.extra["init"] = init_vals
                    # Move this instruction to end (after the CALL instructions)
                    self.instructions.remove(instr)
                    self.instructions.append(instr)
                    break
        else:
            self._visit_children_all(node)

    def _visit_opt_assign(self, node):
        """Handle optional assignment: = value"""
        children = self._get_children(node)
        if not children or (len(children) == 1 and self._is_node(children[0])
                            and children[0].name == "_empty"):
            return None

        declare_dest = None
        for instr in reversed(self.instructions):
            if instr.op == "DECLARE":
                declare_dest = instr.dest
                break

        for child in children:
            if self._is_node(child) and child.name in ("value", "assign_val", "expression", "blend_val"):
                val = self._visit(child)
                if val is not None:
                    if declare_dest is not None:
                        # Coerce based on declared type vs value type
                        dest_type = self._var_types.get(declare_dest)
                        if dest_type == "bean" and isinstance(val, bool):
                            val = 1 if val else 0
                        elif dest_type == "drip" and isinstance(val, bool):
                            val = 1.0 if val else 0.0
                        elif dest_type == "temp" and isinstance(val, (int, float)) and not isinstance(val, bool):
                            val = True if val != 0 else False
                        self._emit("ASSIGN", dest=declare_dest, arg1=val)
                    return val
                
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                val = self._token_to_literal(child)
                if declare_dest is not None:
                    # Same coercion for token literals
                    dest_type = self._var_types.get(declare_dest)
                    if dest_type == "bean" and isinstance(val, bool):
                        val = 1 if val else 0
                    elif dest_type == "drip" and isinstance(val, bool):
                        val = 1.0 if val else 0.0
                    elif dest_type == "temp" and isinstance(val, (int, float)) and not isinstance(val, bool):
                        val = True if val != 0 else False
                    self._emit("ASSIGN", dest=declare_dest, arg1=val)
                return val
        
        return None
    
    def _visit_var_dec_const_init(self, node):
        """Handle constant variable initialization: ID = value.
        Only emits DECLARE if dtype is known — skips if None to avoid
        a global DECLARE being emitted before FUNC_BEGIN."""
        id_tok = self._find_child_token(node, "ID")
        if id_tok:
            var_name = id_tok.value
            # Prefer type from _var_types (set by _visit_dtype_brewed_body)
            # over _extract_dtype which may return None for nested nodes
            dtype = self._var_types.get(var_name)
            if not dtype:
                dtype = self._extract_dtype(node)
            if dtype:
                self._var_types[var_name] = dtype
            # Only emit DECLARE when dtype is known — if None, parent
            # _visit_dtype_dec will emit the proper DECLARE instead
            if dtype is not None:
                self._emit("DECLARE", dest=var_name, type=dtype, constant=True)
            # Visit value/expression child to emit ASSIGN
            for child in self._get_children(node):
                if self._is_node(child) and child.name in ("value", "assign_val",
                                                            "expression", "opt_assign"):
                    val = self._visit(child)
                    if val is not None:
                        self._emit("ASSIGN", dest=var_name, arg1=val)
                    return
        self._visit_children_all(node)

    def _visit_var_dec_const_tail(self, node):
        """Tail of a constant variable declaration (after the ID). Pass-through."""
        self._visit_children_all(node)


    def _visit_var_dec_tail(self, node):
        """Handle additional variable declarations after comma."""
        children = self._get_children(node)
        for child in children:
            if self._is_node(child) and child.name == "var_dec_init":
                self._visit(child)
            elif self._is_node(child):
                self._visit(child)

    def _visit_var_dec_init(self, node):
        """Handle: ID opt_assign in a comma-separated declaration list."""
        id_tok = self._find_child_token(node, "ID")
        if id_tok:
            var_name = id_tok.value
            # Inherit type from the last DECLARE instruction's type
            dtype = None
            for instr in reversed(self.instructions):
                if instr.op == "DECLARE" and instr.extra.get("type"):
                    dtype = instr.extra["type"]
                    break
            if dtype:
                self._var_types[var_name] = dtype
            self._emit("DECLARE", dest=var_name, type=dtype)

        for child in self._get_children(node):
            if self._is_node(child) and child.name == "opt_assign":
                self._visit(child)

    # ------------------------------------------------------------------
    # Blend (String) Declarations
    # ------------------------------------------------------------------

    def _visit_blend_id_tail(self, node):
        """Tail after a blend (string) variable name — handles array access or concat. Pass-through."""
        self._visit_children_all(node)


    def _visit_blend_val(self, node):
        """Handle string value with possible concatenation."""
        parts = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "blend_term":
                val = self._visit_blend_term(child)
                if val is not None:
                    parts.append(val)
            elif self._is_node(child) and child.name == "blend_val_tail":
                tail_parts = self._visit_blend_val_tail(child)
                parts.extend(tail_parts)
            elif self._is_node(child):
                val = self._visit(child)
                if val is not None:
                    parts.append(val)

        if len(parts) == 0:
            return '""'
        if len(parts) == 1:
            return parts[0]

        # chain concatenation
        result = parts[0]
        for p in parts[1:]:
            t = self._new_temp()
            self._emit("CONCAT", dest=t, arg1=result, arg2=p)
            result = t
        return result

    def _visit_blend_term(self, node):
        """
        Evaluate a single term in a string concatenation expression.
        A blend_term can be: ID, BLENDLIT, BEANLIT, DRIPLIT, CHURROLIT, HOT, COLD,
        an ORDER (global) reference, or a parenthesized expression.
        Returns the value (literal or variable name) for this term.
        If the ID has a tail (array access, function call, member access),
        delegates to _visit_blend_term_id_tail().
        """
        children = self._get_children(node)
        for i, child in enumerate(children):
            if self._is_token(child) and child.type == "ID":
                var_name = child.value
                var_name = self._shadow_map.get(var_name, var_name)
                for c2 in children[i + 1:]:
                    if self._is_node(c2) and c2.name == "blend_term_id_tail":
                        return self._visit_blend_term_id_tail(var_name, c2)
                return var_name
            if self._is_token(child) and child.type == "BLENDLIT":
                return child.value
            if self._is_token(child) and child.type == "BEANLIT":   
                return int(child.value)
            if self._is_token(child) and child.type == "DRIPLIT":   
                return float(child.value)
            if self._is_token(child) and child.type == "CHURROLIT": 
                return child.value
            if self._is_token(child) and child.type == "HOT":
                return True
            if self._is_token(child) and child.type == "COLD":
                return False
            if self._is_node(child):
                return self._visit(child)
            if self._is_token(child) and child.type == "ORDER":
                # order.field or order.field[idx]
                id_tok = None
                indices = []
                for c2 in children[i + 1:]:
                    if self._is_token(c2) and c2.type == "ID":
                        id_tok = c2
                    if self._is_token(c2) and c2.type == "OP_BRACKETS":
                        # collect index
                        pass
                if id_tok:
                    arr_name = f"order.{id_tok.value}"
                    # Check for array indices in remaining children
                    idx_list = []
                    j = i + 1
                    while j < len(children):
                        if self._is_token(children[j]) and children[j].type == "OP_BRACKETS":
                            j += 1
                            if j < len(children) and self._is_node(children[j]):
                                idx = self._visit(children[j])
                                idx_list.append(idx)
                            j += 1  # skip CL_BRACKETS
                        else:
                            j += 1
                    if idx_list:
                        t = self._new_temp()
                        current = arr_name
                        for idx in idx_list:
                            t = self._new_temp()
                            self._emit("ARR_LOAD", dest=t, arg1=current, arg2=idx)
                            current = t
                        return current
                    return arr_name 
                
        return None


    def _visit_blend_term_id_tail(self, var_name, tail_node):
        """
        Process the tail after an ID inside a string concatenation context (blend_term).
        This is the blend-specific version of _visit_primary_id_tail — same logic but
        called from _visit_blend_term instead of _visit_primary.

        Handles:
          arr[idx]      → emits ARR_LOAD, returns temp
          arr[row][col] → emits two ARR_LOADs, returns temp
          func(args)    → emits PARAMs + CALL, returns temp
          obj.member    → emits MEMBER_ACC, returns temp
          obj.method()  → emits PARAMs + METHOD_CALL, returns temp
          (empty)       → returns var_name unchanged

        Parameters:
          var_name  — the variable name whose tail is being processed
          tail_node — the blend_term_id_tail ParseNode
        """
        #"""Process blend_term ID tail: array access or function call in string concat context."""
        children = self._get_children(tail_node)
        if not children:
            return var_name

        first = children[0]

        # Empty tail — just the variable itself
        if self._is_node(first) and first.name == "_empty":
            return var_name

        # Array access: [index] with optional second dimension
        if (self._is_token(first) and first.type == "OP_BRACKETS") or \
        (self._is_node(first) and first.name == "OP_BRACKETS"):
            idx = self._extract_array_index(tail_node)
            t = self._new_temp()
            self._emit("ARR_LOAD", dest=t, arg1=var_name, arg2=idx, is_2d=False)
            # Check for second dimension in arr_call_tail
            for c in children:
                if self._is_node(c) and c.name == "arr_call_tail":
                    for c2 in self._get_children(c):
                        if self._is_node(c2) and c2.name == "array_index":
                            col_idx = self._visit(c2)
                            t2 = self._new_temp()
                            self._emit("ARR_LOAD", dest=t2, arg1=t, arg2=col_idx)
                            return t2
            return t

        # Function call: (args)
        if (self._is_token(first) and first.type == "OP_PAREN") or \
        (self._is_node(first) and first.name == "OP_PAREN"):
            args = self._collect_function_args(tail_node)
            for a in args:
                self._emit("PARAM", arg1=a)
            t = self._new_temp()
            self._emit("CALL", dest=t, arg1=var_name, arg_count=len(args))
            return t

        # Member access: DOT_ACC ID (e.g. point.x in string concat)
        if (self._is_token(first) and first.type == "DOT_ACC") or \
        (self._is_node(first) and first.name == "DOT_ACC"):
            member_id = None
            for c in children[1:]:
                if self._is_token(c) and c.type == "ID":
                    member_id = c.value
                    break
            if member_id:
                # check for method call via primary_dot_tail
                for c in children[1:]:
                    if self._is_node(c) and c.name == "primary_dot_tail":
                        dot_children = self._get_children(c)
                        first_dc = next((dc for dc in dot_children
                                        if not (self._is_node(dc) and dc.name == "_empty")), None)
                        if first_dc and self._is_token(first_dc) and first_dc.type == "OP_PAREN":
                            args = self._collect_function_args(c)
                            for a in args:
                                self._emit("PARAM", arg1=a)
                            t = self._new_temp()
                            self._emit("METHOD_CALL", dest=t, arg1=var_name,
                                       arg2=member_id, arg_count=len(args))
                            return t
                # plain field access
                t = self._new_temp()
                self._emit("MEMBER_ACC", dest=t, arg1=var_name, arg2=member_id)
                return t

        # Default: just return the variable name
        return var_name


    def _visit_blend_val_tail(self, node):
        """
        Collect additional blend_term values from the tail of a string concat.
        Returns a list of values to be appended to the running concat in _visit_blend_val.
        """
        parts = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "blend_term":
                val = self._visit_blend_term(child)
                if val is not None:
                    parts.append(val)
            elif self._is_node(child) and child.name != "_empty":
                val = self._visit(child)
                if val is not None:
                    parts.append(val)
        return parts

    def _visit_blend_assign(self, node):
        """Pass-through for blend (string) assignment statements."""
        self._visit_children_all(node)


    def _visit_blend_const_init(self, node):
        """
        Handle 'brewed blend name = value' constant string declaration.
        Emits: DECLARE dest=name type=blend constant=True, then ASSIGN dest=name arg1=value.
        """
        id_tok = self._find_child_token(node, "ID")
        if id_tok:
            var_name = id_tok.value
            self._var_types[var_name] = "blend"
            self._emit("DECLARE", dest=var_name, type="blend", constant=True)
            for child in self._get_children(node):
                if self._is_node(child) and child.name in ("blend_val", "value"):
                    val = self._visit(child)
                    if val is not None:
                        self._emit("ASSIGN", dest=var_name, arg1=val)
        else:
            self._visit_children_all(node)

    def _visit_blend_const_init_tail(self, node):
        """Tail for comma-separated constant blend declarations. Pass-through."""
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # ID-Led Statements (assignments, calls, etc.)
    # ------------------------------------------------------------------


    def _visit_id_dec_stmt(self, node):
        """
        Handle any statement that starts with an identifier.
        This is the most common statement type — dispatches based on what follows:
          ID = value         → ASSIGN via _visit_id_dec_tail (EQUALS branch)
          ID += value        → BINOP + ASSIGN (compound assignment)
          ID++               → BINOP + ASSIGN (increment)
          ID[idx] = value    → ARR_STORE
          ID[r][c] = value   → ARR_LOAD + ARR_STORE (2D)
          ID.member = value  → MEMBER_SET
          ID.method(args)    → PARAMs + METHOD_CALL
          ID(args)           → PARAMs + CALL (or METHOD_CALL if sibling method)

        Applies _shadow_map lookup so loop-scoped variables use their renamed version.
        Delegates to _visit_id_dec_tail() for the actual IR emission.
        """
        id_tok = self._find_child_token(node, "ID")
        if not id_tok:
            self._visit_children_all(node)
            return

        var_name = id_tok.value
        var_name = self._shadow_map.get(var_name, var_name)
        # print(f"\n[DEBUG id_dec_stmt] var_name={var_name}")
        for child in self._get_children(node):
            print(f"  child: is_node={self._is_node(child)}, is_token={self._is_token(child)}, "
                f"name={getattr(child, 'name', None)}, type={getattr(child, 'type', None)}, "
                f"value={getattr(child, 'value', None)}")
            if self._is_node(child) and child.name == "id_dec_tail":
                for gc in self._get_children(child):
                    print(f"    tail_child: is_node={self._is_node(gc)}, is_token={self._is_token(gc)}, "
                        f"name={getattr(gc, 'name', None)}, type={getattr(gc, 'type', None)}, "
                        f"value={getattr(gc, 'value', None)}")

    # Visit the tail to determine what kind of statement this is
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "id_dec_tail":
                self._visit_id_dec_tail(node, var_name, child)
                return
        self._visit_children_all(node)

    def _visit_id_dec_tail(self, parent, var_name, tail_node):
        """Process the tail of an ID-led statement."""
        children = self._get_children(tail_node)
        if not children:
            return

        first = children[0]

        # Assignment: = value
        if self._is_token(first) and first.type == "EQUALS":
            val = None
            for c in children[1:]:
                if self._is_node(c):
                    val = self._visit(c)
                    break
            if val is not None:
                # Coerce based on declared type vs value type
                dest_type = self._var_types.get(var_name)
                if dest_type == "bean" and isinstance(val, bool):
                    val = 1 if val else 0
                elif dest_type == "drip" and isinstance(val, bool):
                    val = 1.0 if val else 0.0
                elif dest_type == "temp" and isinstance(val, (int, float)) and not isinstance(val, bool):
                    val = True if val != 0 else False
                self._emit("ASSIGN", dest=var_name, arg1=val)
            return

        # Array element assignment: [index] = value  (via id_bracket_tail)
        if (self._is_token(first) and first.type == "OP_BRACKETS") or \
        (self._is_node(first) and first.name == "OP_BRACKETS"):
            idx = self._extract_array_index_expr(tail_node)
            val = None
            col_idx = None
            for c in children:
                if self._is_node(c) and c.name == "id_bracket_tail":
                    # Check if id_bracket_tail has a nested [col] before the =
                    ibt_children = self._get_children(c)
                    ibt_first = ibt_children[0] if ibt_children else None
                    if ibt_first and ((self._is_token(ibt_first) and ibt_first.type == "OP_BRACKETS") or
                                    (self._is_node(ibt_first) and ibt_first.name == "OP_BRACKETS")):
                        # 2D: extract col index then RHS
                        for c2 in ibt_children:
                            if self._is_node(c2) and c2.name == "array_index":
                                col_idx = self._visit(c2)
                                break
                        val = self._visit_id_bracket_tail_rhs(c)
                    else:
                        val = self._visit_id_bracket_tail_rhs(c)
                    break
            if val is not None:
                if col_idx is not None:
                    # 2D store: triangle[row][col] = val
                    # Get the row subarray first, then store into it
                    t1 = self._new_temp()
                    #  2D write, ARR_LOAD gets is_2d=True  
                    self._emit("ARR_LOAD", dest=t1, arg1=var_name, arg2=idx, is_2d=True)
                    self._emit("ARR_STORE", dest=t1, arg1=col_idx, arg2=val)
                else:
                    self._emit("ARR_STORE", dest=var_name, arg1=idx, arg2=val)
            return

        # Compound assignment: +=, -=, *=, /= (first child is assign_op node)
        if self._is_node(first) and first.name == "assign_op":
            # Extract the operator token from inside the assign_op node
            op_token = None
            for ac in self._get_children(first):
                if self._is_token(ac) and ac.type in self.ASSIGN_OP_MAP:
                    op_token = ac
                    break
            if op_token is None:
                return
            # plain = handled separately
            if op_token.type == "EQUALS":
                val = None
                for c in children[1:]:
                    if self._is_node(c):
                        val = self._visit(c)
                        break
                if val is not None:
                    self._emit("ASSIGN", dest=var_name, arg1=val)
                return
            # compound op
            base_op = self.ASSIGN_OP_MAP[op_token.type]
            val = None
            for c in children[1:]:
                if self._is_node(c):
                    val = self._visit(c)
                    break
            if val is not None:
                t = self._new_temp()
                self._emit("BINOP", dest=t, arg1=var_name, arg2=val, binop=base_op)
                self._emit("ASSIGN", dest=var_name, arg1=t)
            return

        # Post-increment/decrement (might functionally be useless lmao but the post increment handles stuff pag nag unary_op node muna as first child)
        if self._is_node(first) and first.name in ("INCREMENT", "DECREMENT"):
            op = "++" if first.name == "INCREMENT" else "--"
            t = self._new_temp()
            inc_val = 1 if op == "++" else -1
            self._emit("BINOP", dest=t, arg1=var_name, arg2=inc_val, binop="+")
            self._emit("ASSIGN", dest=var_name, arg1=t)
            return

        if self._is_token(first) and first.type in ("INCREMENT", "DECREMENT"):
            op = "++" if first.type == "INCREMENT" else "--"
            t = self._new_temp()
            inc_val = 1 if op == "++" else -1
            self._emit("BINOP", dest=t, arg1=var_name, arg2=inc_val, binop="+")
            self._emit("ASSIGN", dest=var_name, arg1=t)
            return

        # Post-increment/decrement wrapped in unary_op node
        if self._is_node(first) and first.name == "unary_op":
            for uc in self._get_children(first):
                if self._is_token(uc) and uc.type in ("INCREMENT", "DECREMENT"):
                    t = self._new_temp()
                    inc_val = 1 if uc.type == "INCREMENT" else -1
                    self._emit("BINOP", dest=t, arg1=var_name, arg2=inc_val, binop="+")
                    self._emit("ASSIGN", dest=var_name, arg1=t)
                    return
            return
         
        # Function call: (args)
        if (self._is_node(first) and first.name == "OP_PAREN") or \
        (self._is_token(first) and first.type == "OP_PAREN"):
            args = self._collect_function_args(tail_node)
            for a in args:
                self._emit("PARAM", arg1=a)
            t = self._new_temp()
            if self._class_field_names and var_name in self._class_field_names \
                    and self._current_class is None:
                self._emit("METHOD_CALL", dest=t, arg1="__self__",
                        arg2=var_name, arg_count=len(args))
            else:
                self._emit("CALL", dest=t, arg1=var_name, arg_count=len(args))
            return

        # Dot access: obj.member = value (MEMBER_SET)
        if (self._is_node(first) and first.name == "DOT_ACC") or \
        (self._is_token(first) and first.type == "DOT_ACC"):
            # Find member name (ID after DOT_ACC)
            member_id = None
            assign_val = None
            for i, c in enumerate(children):
                if self._is_token(c) and c.type == "ID":
                    member_id = c.value
                if self._is_node(c) and c.name == "id_dot_tail":
                    dot_children = self._get_children(c)
                    # check if it's a method call (OP_PAREN) vs assignment
                    is_call = any(self._is_token(dc) and dc.type == "OP_PAREN" for dc in dot_children)
                    if is_call:
                        args = self._collect_function_args(c)
                        for a in args:
                            self._emit("PARAM", arg1=a)
                        t = self._new_temp()
                        self._emit("METHOD_CALL", dest=t, arg1=var_name, arg2=member_id, arg_count=len(args))
                        return
                    for dc in dot_children:
                        if self._is_node(dc) and dc.name in ("assign_val", "value", "expression"):
                            assign_val = self._visit(dc)
                            break
            if member_id and assign_val is not None:
                self._emit("MEMBER_SET", dest=var_name, arg1=member_id, arg2=assign_val)
            else:
                self._visit_children_all(tail_node)
            return

        # Array element assignment: [index] = value
        if (self._is_token(first) and first.type == "OP_BRACKETS") or \
        (self._is_node(first) and first.name == "OP_BRACKETS"):
            idx = self._extract_array_index_expr(tail_node)
            val = None
            for c in children:
                if self._is_node(c) and c.name in ("assign_val", "value", "expression"):
                    val = self._visit(c)
                    break
            if val is not None:
                self._emit("ARR_STORE", dest=var_name, arg1=idx, arg2=val)
            return
        

        # Default: visit all
        self._visit_children_all(tail_node)

    def _visit_update_id(self, node):
        """Visit update_id: ID with assignment or unary op."""
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # ORDER (Global Access) Statements
    # ------------------------------------------------------------------

    def _visit_order_dec_stmt(self, node):
        """Handle order. statements (global access)."""
        children = self._get_children(node)
        id_tok = self._find_child_token(node, "ID")
        arr_name = f"order.{id_tok.value}" if id_tok else "order"
        for child in children:
            if self._is_node(child) and child.name == "order_dec_tail":
                self._visit_order_dec_tail_with_context(child, arr_name)
                return
        self._visit_children_all(node)

    def _visit_order_dec_tail(self, node):
        """
        Fallback tail handler for order.field statements.
        The real work is done by _visit_order_dec_tail_with_context() which
        receives the field name from the parent. This is only reached if
        the parent routing fails — pass-through.
        """
        self._visit_children_all(node)


    def _visit_order_dec_tail_with_context(self, node, arr_name):
        """Handle order.field[index] = value or order.field = value."""
        children = self._get_children(node)
        if not children:
            return
        first = children[0]
        # Array store: OP_BRACKETS index CL_BRACKETS EQUALS assign_val
        if (self._is_token(first) and first.type == "OP_BRACKETS") or \
           (self._is_node(first) and first.name == "OP_BRACKETS"):
            idx = self._extract_array_index_expr(node)
            val = None
            for child in children:
                if self._is_node(child) and child.name in ("assign_val", "value", "expression"):
                    val = self._visit(child)
                    break
            self._emit("ARR_STORE", dest=arr_name, arg1=idx, arg2=val)
            return
        # Simple assignment: EQUALS assign_val
        if self._is_token(first) and first.type == "EQUALS":
            for child in children:
                if self._is_node(child) and child.name in ("assign_val", "value", "expression"):
                    val = self._visit(child)
                    self._emit("ASSIGN", dest=arr_name, arg1=val)
                    return
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def _visit_expression(self, node):
        """Visit expression: not_factor logic_expr_tail"""
        children = self._get_children(node)
        if not children:
            return None

        # Evaluate the first child (not_factor or directly a rel_expr)
        left = self._visit(children[0])

        # Process logic tail: && / || operations
        for child in children[1:]:
            if self._is_node(child) and child.name == "logic_expr_tail":
                left = self._visit_logic_tail(left, child)
            elif self._is_node(child) and child.name != "_empty":
                r = self._visit(child)
                if r is not None and left is None:
                    left = r

        return left

    def _visit_logic_tail(self, left, node):
        """
        Process && / || operations in the logic_expr_tail.
        Takes the already-evaluated left operand and chains BINOP instructions
        for each logic_op + operand pair found in the tail.
        Returns the final temp holding the combined boolean result.
        Parameters:
          left — temp var or value from the left side of the expression
          node — the logic_expr_tail ParseNode
        """
        children = self._get_children(node)
        i = 0
        while i < len(children):
            child = children[i]
            if self._is_node(child) and child.name == "logic_op":
                op_tok = child.children[0] if child.children else None
                op = "&&" if (op_tok and getattr(op_tok, "type", "") == "AND") else "||"
                # Next child should be the right operand (not_factor)
                if i + 1 < len(children):
                    right = self._visit(children[i + 1])
                    t = self._new_temp()
                    self._emit("BINOP", dest=t, arg1=left, arg2=right, binop=op)
                    left = t
                    i += 2
                    continue
            i += 1
        return left

    def _visit_logic_expr_tail(self, node):
        """
        No-op stub — logic_expr_tail is consumed by _visit_logic_tail() which
        receives it as a direct argument from _visit_expression(). This method
        exists only to prevent the default _visit() fallback from processing it.
        """
        # Handled by _visit_logic_tail from parent
        return None


    def _visit_not_factor(self, node):
        """Handle NOT factor: ! expression or just rel_expr."""
        children = self._get_children(node)
        has_not = False
        for child in children:
            if self._is_token(child) and child.type == "NOT":
                has_not = True
            elif self._is_node(child) and child.name == "NOT":
                has_not = True

        val = None
        for child in children:
            if self._is_node(child) and child.name not in ("NOT", "_empty"):
                val = self._visit(child)
                break

        if has_not and val is not None:
            t = self._new_temp()
            self._emit("UNARYOP", dest=t, arg1=val, unaryop="!")
            return t

        return val

    def _visit_rel_expr(self, node):
        """Handle relational expression: arith_expr rel_expr_tail"""
        children = self._get_children(node)
        left = None
        for child in children:
            if self._is_node(child) and child.name == "arith_expr":
                left = self._visit(child)
            elif self._is_node(child) and child.name == "rel_expr_tail":
                left = self._visit_rel_tail(left, child)
            elif self._is_node(child) and child.name != "_empty":
                r = self._visit(child)
                if r is not None and left is None:
                    left = r
        return left

    def _visit_rel_tail(self, left, node):
        """
        Process relational operators (>, <, >=, <=, ==, !=) in rel_expr_tail.
        Same pattern as _visit_logic_tail — chains BINOP instructions.
        Parameters:
          left — already-evaluated left operand
          node — rel_expr_tail ParseNode
        Returns the final temp holding the boolean comparison result.
        """
        children = self._get_children(node)
        i = 0
        while i < len(children):
            child = children[i]
            if self._is_node(child) and child.name == "rel_op":
                op = self._extract_rel_op(child)
                if i + 1 < len(children):
                    right = self._visit(children[i + 1])
                    t = self._new_temp()
                    self._emit("BINOP", dest=t, arg1=left, arg2=right, binop=op)
                    left = t
                    i += 2
                    continue
            i += 1
        return left

    def _visit_rel_expr_tail(self, node):
        """No-op stub — consumed by _visit_rel_tail() called from _visit_rel_expr()."""
        return None

    def _extract_rel_op(self, node):
        """Extract the operator string from a rel_op node using BINOP_MAP. Defaults to '=='."""
        for child in self._get_children(node):
            if self._is_token(child) and child.type in self.BINOP_MAP:
                return self.BINOP_MAP[child.type]
        return "=="


    def _visit_arith_expr(self, node):
        """Handle arithmetic expression: unary_expr arith_expr_tail"""
        children = self._get_children(node)
        left = None
        for child in children:
            if self._is_node(child) and child.name == "unary_expr":
                left = self._visit(child)
            elif self._is_node(child) and child.name == "arith_expr_tail":
                left = self._visit_arith_tail(left, child)
            elif self._is_node(child) and child.name != "_empty":
                r = self._visit(child)
                if r is not None and left is None:
                    left = r
        return left

    def _visit_arith_tail(self, left, node):
        """Process arith_expr_tail with correct operator precedence (* / % before + -)."""
        children = self._get_children(node)
        
        # Collect all (op, operand) pairs
        pairs = []
        i = 0
        while i < len(children):
            child = children[i]
            if self._is_node(child) and child.name == "arithm_op":
                op = self._extract_arith_op(child)
                if i + 1 < len(children):
                    right = self._visit(children[i + 1])
                    pairs.append((op, right))
                    i += 2
                    continue
            i += 1

        if not pairs:
            return left

        # Build operand list: [left, op, right, op, right, ...]
        # First pass: collapse * / % 
        operands = [left]
        ops = []
        for op, val in pairs:
            operands.append(val)
            ops.append(op)

        # Process high-precedence operators first (* / %)
        HIGH = {"*", "/", "%"}
        i = 0
        while i < len(ops):
            if ops[i] in HIGH:
                a = operands[i]
                b = operands[i + 1]
                t = self._new_temp()
                self._emit("BINOP", dest=t, arg1=a, arg2=b, binop=ops[i])
                # print(f"[IR_GEN VISIT ARITH TAIL HI DEBUG] dest = {t} and arg1 = {a} and arg 2 = {b} and the binop is {ops[i]}")
                operands[i] = t
                operands.pop(i + 1)
                ops.pop(i)
            else:
                i += 1

        # Process remaining low-precedence operators (+ -)
        result = operands[0]
        for i, op in enumerate(ops):
            t = self._new_temp()
            self._emit("BINOP", dest=t, arg1=result, arg2=operands[i + 1], binop=op)
            # print(f"[IR_GEN VISIT ARITH TAIL LOW DEBUG] dest = {t} and arg1 = {result} and arg 2 = {operands[i + 1]} and the binop is {op}")
            result = t

        return result

    def _visit_arith_expr_tail(self, node):
        """No-op stub — consumed by _visit_arith_tail() called from _visit_arith_expr()."""
        return None

    def _extract_arith_op(self, node):
        """Extract operator string from arithm_op node using BINOP_MAP. Defaults to '+'."""
        for child in self._get_children(node):
            if self._is_token(child) and child.type in self.BINOP_MAP:
                return self.BINOP_MAP[child.type]
        return "+"

    def _visit_unary_expr(self, node):
        """Handle unary expression: ++ID, --ID, -expr, or primary."""
        children = self._get_children(node)

        # Check for prefix ++/--
        for i, child in enumerate(children):
            if self._is_token(child) and child.type in ("INCREMENT", "DECREMENT"):
                # Next should be ID
                if i + 1 < len(children):
                    next_c = children[i + 1]
                    if self._is_token(next_c) and next_c.type == "ID":
                        var = next_c.value
                        t = self._new_temp()
                        inc = 1 if child.type == "INCREMENT" else -1
                        self._emit("BINOP", dest=t, arg1=var, arg2=inc, binop="+")
                        self._emit("ASSIGN", dest=var, arg1=t)
                        return var

            # Unary minus
            if self._is_token(child) and child.type == "MINUS":
                for c2 in children[i + 1:]:
                    if self._is_node(c2):
                        val = self._visit(c2)
                        if val is not None:
                            t = self._new_temp()
                            # print(f"[DEBUG IRGEN] dest={t}, arg1={val}, unaryop="-"")
                            self._emit("UNARYOP", dest=t, arg1=val, unaryop="-")
                            return t

        # Default: visit primary or sub-expression
        for child in children:
            if self._is_node(child) and child.name in ("primary", "neg_operand"):
                return self._visit(child)
            if self._is_node(child) and child.name != "_empty":
                r = self._visit(child)
                if r is not None:
                    return r

        return None

    def _visit_neg_operand(self, node):
        """
        Handle the operand of a unary minus expression.
        Visits the first node child or returns an ID token's value directly.
        Called by _visit_unary_expr after detecting a MINUS token.
        """
        for child in self._get_children(node):
            # Skip paren delimiters — they're structural, not values
            if self._is_node(child) and child.name in ("OP_PAREN", "CL_PAREN"):
                continue
            if self._is_token(child) and child.type in ("OP_PAREN", "CL_PAREN"):
                continue
            if self._is_node(child):
                return self._visit(child)
            if self._is_token(child) and child.type == "ID":
                return child.value
        return None

    def _visit_primary(self, node):
        """Handle primary expression: ID, literal, function call, array access, etc."""
        children = self._get_children(node)

        for i, child in enumerate(children):
            # Literal tokens
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                return self._token_to_literal(child)

            # Identifier
            if self._is_token(child) and child.type == "ID":
                var_name = child.value
                # Check if next child is a tail (function call, array, member)
                var_name = self._shadow_map.get(var_name, var_name)
                tail = None
                for c2 in children[i + 1:]:
                    if self._is_node(c2) and c2.name == "primary_id_tail":
                        tail = c2
                        break
                if tail:
                    return self._visit_primary_id_tail(var_name, tail)
                return var_name

            # ORDER (global access)
            if self._is_token(child) and child.type == "ORDER":
                # Find the ID after DOT_ACC
                order_field = None
                order_tail = None
                for c2 in children[i + 1:]:
                    if self._is_token(c2) and c2.type == "ID":
                        order_field = c2.value
                    if self._is_node(c2) and c2.name == "primary_order_tail":
                        order_tail = c2
                var_name = f"order.{order_field}" if order_field else "order"
                if order_tail:
                    return self._visit_primary_order_tail_with_context(order_tail, var_name)
                return var_name

            # Parenthesized expression
            if (self._is_node(child) and child.name == "OP_PAREN") or \
               (self._is_token(child) and child.type == "OP_PAREN"):
                for c2 in children[i + 1:]:
                    if self._is_node(c2) and c2.name in ("expression", "blend_val"):
                        return self._visit(c2)
                continue
            
            # PRE-DEFINED FUNCTIONSSSSSSSSSSSSS
            # sift(expr)
            if self._is_token(child) and child.type == "SIFT":
                for c2 in children:
                    if self._is_node(c2) and c2.name == "sift_arg":
                        arg_val = self._visit(c2)
                        self._emit("PARAM", arg1=arg_val)
                        t = self._new_temp()
                        self._emit("CALL", dest=t, arg1="__sift__", arg_count=1)
                        return t
                    
            # sqrt(expr) math.sqrt
            if self._is_token(child) and child.type == "SQRT":
                for c2 in children:
                    if self._is_node(c2) and c2.name == "expression":
                        arg_val = self._visit(c2)
                        self._emit("PARAM", arg1=arg_val)
                        t = self._new_temp()
                        self._emit("CALL", dest=t, arg1="__sqrt__", arg_count=1)
                        return t

            # ceil(expr) is math.ceil
            if self._is_token(child) and child.type == "CEIL":
                for c2 in children:
                    if self._is_node(c2) and c2.name == "expression":
                        arg_val = self._visit(c2)
                        self._emit("PARAM", arg1=arg_val)
                        t = self._new_temp()
                        self._emit("CALL", dest=t, arg1="__ceil__", arg_count=1)
                        return t

            # floor(expr) is math.floor
            if self._is_token(child) and child.type == "FLOOR":
                for c2 in children:
                    if self._is_node(c2) and c2.name == "expression":
                        arg_val = self._visit(c2)
                        self._emit("PARAM", arg1=arg_val)
                        t = self._new_temp()
                        self._emit("CALL", dest=t, arg1="__floor__", arg_count=1)
                        return t

            # pow(base, exp) is math.pow — two expression children
            if self._is_token(child) and child.type == "POW":
                exprs = [c2 for c2 in children if self._is_node(c2) and c2.name == "expression"]
                if len(exprs) >= 2:
                    arg1 = self._visit(exprs[0])
                    arg2 = self._visit(exprs[1])
                    self._emit("PARAM", arg1=arg1)
                    self._emit("PARAM", arg1=arg2)
                    t = self._new_temp()
                    self._emit("CALL", dest=t, arg1="__pow__", arg_count=2)
                    return t

            # rand(a, b) is random.randint or random.uniform depending on types
            if self._is_token(child) and child.type == "RAND":
                exprs = [c2 for c2 in children if self._is_node(c2) and c2.name == "expression"]
                if len(exprs) >= 2:
                    arg1 = self._visit(exprs[0])
                    arg2 = self._visit(exprs[1])
                    use_float = (
                        isinstance(arg1, float) or isinstance(arg2, float) or
                        self._var_types.get(str(arg1)) == "drip" or
                        self._var_types.get(str(arg2)) == "drip" or
                        (isinstance(arg1, str) and '.' in arg1 and arg1.lstrip('-').replace('.', '', 1).isdigit()) or
                        (isinstance(arg2, str) and '.' in arg2 and arg2.lstrip('-').replace('.', '', 1).isdigit())
                    )
                    self._emit("PARAM", arg1=arg1)
                    self._emit("PARAM", arg1=arg2)
                    t = self._new_temp()
                    self._emit("CALL", dest=t, arg1="__rand__", arg_count=2, use_float=use_float)
                    return t

            # type(expr) is returns blend string of type name
            if self._is_token(child) and child.type == "TYPE":
                for c2 in children:
                    if self._is_node(c2) and c2.name == "expression":
                        arg_val = self._visit(c2)
                        self._emit("PARAM", arg1=arg_val)
                        t = self._new_temp()
                        self._emit("CALL", dest=t, arg1="__type__", arg_count=1)
                        return t

        # Fallback: visit children
        for child in children:
            if self._is_node(child) and child.name != "_empty":
                r = self._visit(child)
                if r is not None:
                    return r
        return None

    def _visit_primary_id_tail(self, var_name, tail_node):
        """Process primary ID tail: function call, array access, post-op, member access."""
        children = self._get_children(tail_node)
        if not children:
            return var_name

        first = children[0]

        # Empty tail
        if self._is_node(first) and first.name == "_empty":
            return var_name

        # Post-increment/decrement (returns old value)
        if self._is_node(first) and first.name in ("unary_op",):
            for uc in self._get_children(first):
                if self._is_token(uc) and uc.type in ("INCREMENT", "DECREMENT"):
                    old_val = self._new_temp()
                    self._emit("ASSIGN", dest=old_val, arg1=var_name)
                    t = self._new_temp()
                    inc = 1 if uc.type == "INCREMENT" else -1
                    self._emit("BINOP", dest=t, arg1=var_name, arg2=inc, binop="+")
                    self._emit("ASSIGN", dest=var_name, arg1=t)
                    return old_val
            return var_name

        # Function call: OP_PAREN args CL_PAREN
        if (self._is_node(first) and first.name == "OP_PAREN") or (self._is_token(first) and first.type == "OP_PAREN"):
            args = self._collect_function_args(tail_node)
            for a in args:
                self._emit("PARAM", arg1=a)
            t = self._new_temp()
            # sibling method call inside a class method
            if self._class_field_names and var_name in self._class_field_names \
                and self._current_class is None:

                self._emit("METHOD_CALL", dest=t, arg1="__self__",
                        arg2=var_name, arg_count=len(args))
            else:
                self._emit("CALL", dest=t, arg1=var_name, arg_count=len(args))
            return t

        print(f"[IRGEN DEBUG OP_PAREN] var={var_name} _class_field_names={self._class_field_names} _current_class={self._current_class}")

        # Array access: OP_BRACKETS index CL_BRACKETS now with 2d support! hopefully.
        if (self._is_node(first) and first.name == "OP_BRACKETS") or \
        (self._is_token(first) and first.type == "OP_BRACKETS"):
            idx = self._extract_array_index(tail_node)
            # Check for second dimension via arr_call_tail
            col_idx = None
            for c in children:
                if self._is_node(c) and c.name == "arr_call_tail":
                    for c2 in self._get_children(c):
                        if self._is_node(c2) and c2.name == "array_index":
                            col_idx = self._visit(c2)
                            break
                    break
            if col_idx is not None:
                t1 = self._new_temp()
                # 2D read, first ARR_LOAD gets is_2d=True
                self._emit("ARR_LOAD", dest=t1, arg1=var_name, arg2=idx, is_2d=True)
                t2 = self._new_temp()
                self._emit("ARR_LOAD", dest=t2, arg1=t1, arg2=col_idx)
                return t2
            t = self._new_temp()
            self._emit("ARR_LOAD", dest=t, arg1=var_name, arg2=idx)
            return t

         # Member access: .member
        if (self._is_token(first) and first.type == "DOT_ACC") or \
        (self._is_node(first) and first.name == "DOT_ACC"):
            
            # Find member name
            member_id = None
            for c in children[1:]:
                if self._is_token(c) and c.type == "ID":
                    member_id = c.value
                    break
            if member_id:
                # check if primary_dot_tail has OP_PAREN → method call
                for c in children[1:]:
                    if self._is_node(c) and c.name == "primary_dot_tail":
                        dot_children = self._get_children(c)
                        first = next((dc for dc in dot_children
                                    if not (self._is_node(dc) and dc.name == "_empty")), None)
                        if first and self._is_token(first) and first.type == "OP_PAREN":
                            args = self._collect_function_args(c)
                            for a in args:
                                self._emit("PARAM", arg1=a)
                            t = self._new_temp()
                            self._emit("METHOD_CALL", dest=t, arg1=var_name,
                                    arg2=member_id, arg_count=len(args))
                            return t
                # no call — plain field access
                t = self._new_temp()
                self._emit("MEMBER_ACC", dest=t, arg1=var_name, arg2=member_id)
                return t

        return var_name

    def _visit_primary_dot_tail(self, node):
        """
        No-op stub — primary_dot_tail is consumed inline by _visit_primary_id_tail()
        which checks for OP_PAREN inside it to detect method calls.
        If this is reached via default dispatch, pass-through.
        """
        self._visit_children_all(node)


    def _visit_primary_order_tail(self, node):
        """
        No-op stub — primary_order_tail is consumed by _visit_primary_order_tail_with_context()
        which is called directly from _visit_primary() with the field name in context.
        """
        self._visit_children_all(node)


    def _visit_primary_order_tail_with_context(self, node, var_name):
        """Handle order.field[index] array access in expressions."""
        children = self._get_children(node)
        if not children:
            return var_name
        first = children[0]
        # Empty tail
        if self._is_node(first) and first.name == "_empty":
            return var_name
        # Array access: OP_BRACKETS index CL_BRACKETS
        if (self._is_token(first) and first.type == "OP_BRACKETS") or \
           (self._is_node(first) and first.name == "OP_BRACKETS"):
            idx = self._extract_array_index_expr(node)
            t = self._new_temp()
            self._emit("ARR_LOAD", dest=t, arg1=var_name, arg2=idx)
            return t
        return var_name

    # ------------------------------------------------------------------
    # Value / Assign
    # ------------------------------------------------------------------

    def _visit_value(self, node):
        """Visit a value node - delegates to expression."""
        for child in self._get_children(node):
            if self._is_node(child):
                return self._visit(child)
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                return self._token_to_literal(child)
        return None

    def _visit_assign_val(self, node):
        """Alias for _visit_value — handles the right-hand side of an assignment."""
        return self._visit_value(node)


    def _visit_assign_value(self, node):
        """Alias for _visit_value — alternate grammar node name for assignment RHS."""
        return self._visit_value(node)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------


    def _visit_statement(self, node):
        """Top-level statement container — pass-through to the actual statement node."""
        self._visit_children_all(node)


    def _visit_stmt_tail(self, node):
        """
        Statement tail — the continuation of a block body (recursive list structure).
        In the grammar, bodies are right-recursive: stmt_tail → statement stmt_tail.
        Pass-through visits all children including the next stmt_tail.
        """
        # debug
        # for child in self._get_children(node):
        #     print(f"  [STMT_TAIL child] name={getattr(child, 'name', None)}, type={getattr(child, 'type', None)}")
        #     if self._is_node(child):
        #         for gc in self._get_children(child):
        #             print(f"    [STMT_TAIL grandchild] name={getattr(gc, 'name', None)}, type={getattr(gc, 'type', None)}")
        self._visit_children_all(node)


    def _visit_stmt_tail_until_snap(self, node):
        """
        Statement tail inside a flavour (switch) case body.
        Like stmt_tail but stops at 'snap' (break). Pass-through — snap is handled
        by _visit_intrpt_stmt which emits GOTO to the switch end label.
        """
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Output (glaze)
    # ------------------------------------------------------------------


    def _visit_output_stmt(self, node):
        """Handle glaze(args) - output statement."""
        args = self._collect_output_args(node)
        self._emit("PRINT", args=args)

    def _collect_output_args(self, node):
        """Collect all output arguments from a glaze statement."""
        args = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "output_args":
                args.extend(self._visit_output_args(child))
            elif self._is_node(child) and child.name not in ("_empty",):
                val = self._visit(child)
                if val is not None:
                    args.append(val)
        return args

    def _visit_output_args(self, node):
        """Visit output_args: BLENDLIT concat | expression concat | empty"""
        parts = []
        for child in self._get_children(node):
            if self._is_token(child) and child.type == "BLENDLIT":
                parts.append(child.value)
            elif self._is_node(child) and child.name == "concat":
                concat_parts = self._visit_concat(child)
                parts.extend(concat_parts)
            elif self._is_node(child) and child.name in ("expression",):
                val = self._visit(child)
                if val is not None:
                    parts.append(val)
            elif self._is_node(child) and child.name != "_empty":
                val = self._visit(child)
                if val is not None:
                    parts.append(val)
        return parts

    def _visit_concat(self, node):
        """Visit concat: + blend_term repeated"""
        parts = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "blend_term":
                val = self._visit_blend_term(child)
                if val is not None:
                    parts.append(val)
            elif self._is_node(child) and child.name == "concat":
                parts.extend(self._visit_concat(child))
            elif self._is_node(child) and child.name not in ("_empty", "PLUS"):
                val = self._visit(child)
                if val is not None:
                    parts.append(val)
        return parts

    # ------------------------------------------------------------------
    # Input (batter@)
    # ------------------------------------------------------------------

    def _visit_input_stmt(self, node):
        """
        Generate IR for 'batter@' (input) statements.
        Two paths based on the target:
          1. Array target (batter@arr[idx](prompt)):
             - Emits INPUT to a temp, then ARR_STORE to the array element
          2. Regular variable targets (batter@x, batter@obj.field, batter@order.x):
             - Calls _collect_input_targets() to find all target variable names
             - Emits one INPUT instruction per target

        The INPUT instruction carries:
          dest   — variable name to store into (or temp for array path)
          prompt — optional string prompt shown to user
          array_elem_type — dtype of the array element (for typed input validation)
        """
        # Extract optional prompt from input_val node
        prompt = None
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "input_val":
                for ic in self._get_children(child):
                    if self._is_token(ic) and ic.type == "BLENDLIT":
                        prompt = ic.value
                        break

        arr_name, arr_idx = self._find_array_input_target(node)
        if arr_name is not None:
            t = self._new_temp()
            dtype = self._var_types.get(arr_name)
            self._emit("INPUT", dest=t, array_elem_type=dtype, prompt=prompt)
            self._emit("ARR_STORE", dest=arr_name, arg1=arr_idx, arg2=t)
        else:
            targets = self._collect_input_targets(node)
            for target in targets:
                self._emit("INPUT", dest=target, prompt=prompt)

    def _find_array_input_target(self, node):
        """
        Detect if a batter@ statement targets an array element (e.g. batter@arr[i](prompt)).
        Recursively scans the node tree for OP_BRACKETS + array_index to determine
        if the input target is an array element rather than a plain variable.
        Returns: (arr_name, idx) if array target found, else (None, None).
        Local vars:
          ids          — list of ID token values found while walking
          has_brackets — True if OP_BRACKETS was found (indicates array access)
          idx          — the evaluated index expression
        """
        ids = []
        has_brackets = False
        idx = None

        def walk(n):
            """Recursively walk node tree collecting IDs, bracket presence, and index."""
            nonlocal has_brackets, idx
            for child in self._get_children(n):
                if self._is_token(child) and child.type == "ID":
                    ids.append(child.value)
                elif self._is_token(child) and child.type == "OP_BRACKETS":
                    has_brackets = True
                elif self._is_node(child) and child.name == "array_index":
                    # Pass the parent node (n), not the array_index child itself
                    idx = self._extract_array_index_expr(n)  # ← was: child
                elif self._is_node(child) and child.name != "_empty":
                    walk(child)

        walk(node)

        if has_brackets and len(ids) >= 1:
            return ids[0], idx if idx is not None else 0
        return None, None
    

    def _collect_input_targets(self, node):
        """ Collects where the input is going to from the batter@ statement and disambiguates between crema, order, and local."""
        targets = []
        children = self._get_children(node)
        i = 0
        while i < len(children):
            child = children[i]
            if self._is_token(child) and child.type == "ORDER":
                if i + 2 < len(children):
                    dot = children[i + 1]
                    id_tok = children[i + 2]
                    if self._is_token(dot) and dot.type == "DOT_ACC" and \
                    self._is_token(id_tok) and id_tok.type == "ID":
                        targets.append(f"order.{id_tok.value}")
                        i += 3
                        continue
            elif self._is_token(child) and child.type == "ID":
                var_name = self._shadow_map.get(child.value, child.value)
                # Check if next sibling is input_id_tail with DOT_ACC
                if i + 1 < len(children):
                    next_child = children[i + 1]
                    if self._is_node(next_child) and next_child.name == "input_id_tail":
                        tail_children = self._get_children(next_child)
                        if tail_children and self._is_token(tail_children[0]) \
                                and tail_children[0].type == "DOT_ACC":
                            if len(tail_children) > 1 and self._is_token(tail_children[1]) \
                                    and tail_children[1].type == "ID":
                                member = tail_children[1].value
                                targets.append(f"{var_name}.{member}")
                                i += 2
                                continue
                targets.append(var_name)
            elif self._is_node(child) and child.name not in ("_empty", "input_val",
                                                            "input_id_tail",
                                                            "input_order_tail"):
                targets.extend(self._collect_input_targets(child))
            i += 1
        return targets
        
    def _visit_input_args(self, node):
        """Pass-through for the argument list of a batter@ statement."""
        self._visit_children_all(node)


    def _visit_input_args_unit(self, node):
        """Pass-through for a single argument unit in batter@ (one variable target)."""
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Control Flow: If / Else If / Else
    # ------------------------------------------------------------------


    def _visit_if_cond(self, node):
        """
        Entry point for if/elifroth/elspress chains.
        Creates a shared end_label then delegates to _generate_if_chain().
        Emits: LABEL end_label after the full chain to mark where all branches converge.
        """
        end_label = self._new_label("IF_END")
        self._generate_if_chain(node, end_label)
        self._emit("LABEL", dest=end_label)


    def _generate_if_chain(self, node, end_label):
        """
        Recursively generate IR for one if/elifroth branch of a conditional chain.

        Pattern emitted:
          [condition BINOPs]
          IF_FALSE cond → else_label
          [if-body statements]
          GOTO end_label
          LABEL else_label
          [else/elifroth body via _visit_if_cond_tail]

        Parameters:
          node      — the if_cond ParseNode (or elifroth node for recursion)
          end_label — shared label where ALL branches (if/elifroth/else) jump on completion

        Local vars:
          cond_node     — the expression node for the condition (stored, not visited yet)
          body_children — list of statement nodes in the if-body
          tail_node     — the if_cond_tail node (contains elifroth/elspress chain)
          else_label    — new label where this branch jumps if condition is false

        Important: cond_node is visited AFTER prior GOTO is emitted — this avoids
        the condition BINOPs appearing before the jump in the wrong branch.
        """
        children = self._get_children(node)

        cond_node = None
        body_children = []
        tail_node = None
        in_body = False

        for child in children:
            if self._is_node(child) and child.name == "expression" and cond_node is None:
                cond_node = child          # ← store node, don't visit yet
            elif self._is_token(child) and child.type == "OP_BRACES":
                in_body = True
            elif self._is_token(child) and child.type == "CL_BRACES":
                in_body = False
            elif self._is_node(child) and child.name == "if_cond_tail":
                tail_node = child
            elif in_body or (self._is_node(child) and child.name in
                            ("statement", "stmt_tail")):
                body_children.append(child)

        else_label = self._new_label("ELSE")
        if cond_node is not None:
            cond = self._visit(cond_node)  # ← evaluate HERE, after prior GOTO is emitted
            self._emit("IF_FALSE", arg1=cond, dest=else_label)

        for bc in body_children:
            self._visit(bc)

        self._emit("GOTO", dest=end_label)
        self._emit("LABEL", dest=else_label)

        if tail_node:
            self._visit_if_cond_tail(tail_node, end_label)
            

    def _generate_if_chain(self, node, end_label):
        """
        Generate IR for one if/elifroth branch. Called by _visit_if_cond and recursively
        by _visit_if_cond_tail for each elifroth. Emits IF_FALSE → body → GOTO end_label
        → LABEL else_label, then routes the tail to _visit_if_cond_tail.
        """
        children = self._get_children(node)

        cond_node = None
        body_children = []
        tail_node = None
        in_body = False

        for child in children:
            if self._is_node(child) and child.name == "expression" and cond_node is None:
                cond_node = child          # ← store node, don't visit yet
            elif self._is_token(child) and child.type == "OP_BRACES":
                in_body = True
            elif self._is_token(child) and child.type == "CL_BRACES":
                in_body = False
            elif self._is_node(child) and child.name == "if_cond_tail":
                tail_node = child
            elif in_body or (self._is_node(child) and child.name in
                            ("statement", "stmt_tail")):
                body_children.append(child)

        else_label = self._new_label("ELSE")
        if cond_node is not None:
            cond = self._visit(cond_node)  # ← evaluate HERE, after prior GOTO is emitted
            self._emit("IF_FALSE", arg1=cond, dest=else_label)

        for bc in body_children:
            self._visit(bc)

        self._emit("GOTO", dest=end_label)
        self._emit("LABEL", dest=else_label)

        if tail_node:
            self._visit_if_cond_tail(tail_node, end_label)
            
    def _visit_if_cond_tail(self, node, end_label):
        """
        Handle the tail of an if statement — elifroth or elspress.
        Three cases:
          empty       → nothing to emit
          ELIFROTH    → recurse into _generate_if_chain() (another if branch)
          ELSPRESS    → visit the else body statements directly
        Parameters:
          node      — the if_cond_tail ParseNode
          end_label — passed through so all branches jump to the same end
        """
        children = self._get_children(node)
        if not children:
            return

        first = children[0]

        # Empty tail
        if self._is_node(first) and first.name == "_empty":
            return

        # elifroth (else-if)
        if self._is_token(first) and first.type == "ELIFROTH":
            self._generate_if_chain(node, end_label)
            return

        # elspress (else)
        if self._is_token(first) and first.type == "ELSPRESS":
            for child in children:
                if self._is_node(child) and child.name in ("statement", "stmt_tail"):
                    self._visit(child)

            # debug
            # for child in children:
            #     print(f"  [ELSPRESS child] is_node={self._is_node(child)}, name={getattr(child, 'name', None)}, type={getattr(child, 'type', None)}")
            return

        # Fallback
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Control Flow: Switch (flavour)
    # ------------------------------------------------------------------


    def _visit_flav_switch(self, node):
        """Generate IR for switch statement."""
        end_label = self._new_label("SWITCH_END")

        # push a break target for snap statements
        self._loop_stack.append((None, end_label))

        # Extract the switch expression
        switch_val = None
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "flav_lit":
                switch_val = self._visit_flav_lit(child)
            elif self._is_node(child) and child.name == "syrup_switch":
                self._visit_syrup_switch(child, switch_val, end_label)

        self._loop_stack.pop()
        self._emit("LABEL", dest=end_label)

    def _visit_flav_lit(self, node):
        """
        Extract the switch expression value from a flavour(expr) statement.
        Returns the variable name (for ID) or literal value (for literals).
        Used by _visit_flav_switch to get the value being switched on.
        """
        for child in self._get_children(node):
            if self._is_token(child):
                if child.type == "ID":
                    return child.value
                return self._token_to_literal(child)
        return None


    def _visit_syrup_switch(self, node, switch_val, end_label):
        """Generate IR for each case."""
        children = self._get_children(node)
        case_val = None
        body_children = []
        tail_node = None
        defoam_node = None

        for child in children:
            if self._is_node(child) and child.name == "case_lit":
                case_val = self._visit_case_lit(child)
            elif self._is_node(child) and child.name in ("statement", "stmt_tail",
                                                           "stmt_tail_until_snap"):
                body_children.append(child)
            elif self._is_node(child) and child.name == "syrup_switch_tail":
                tail_node = child
            elif self._is_node(child) and child.name == "defoam_stmt":
                defoam_node = child

        # Generate: if switch_val != case_val, skip
        next_case = self._new_label("CASE")
        if switch_val is not None and case_val is not None:
            t = self._new_temp()
            self._emit("BINOP", dest=t, arg1=switch_val, arg2=case_val, binop="==")
            self._emit("IF_FALSE", arg1=t, dest=next_case)

        for bc in body_children:
            self._visit(bc)

        self._emit("GOTO", dest=end_label)
        self._emit("LABEL", dest=next_case)

        # Process default
        if defoam_node:
            self._visit_defoam_stmt(defoam_node, end_label)

        # Process more cases
        if tail_node:
            for child in self._get_children(tail_node):
                if self._is_node(child) and child.name == "syrup_switch":
                    self._visit_syrup_switch(child, switch_val, end_label)

    def _visit_case_lit(self, node):
        """
        Extract the case value from a 'syrup N:' case declaration.
        Returns the literal value for this case (int, float, char, etc.).
        Used by _visit_syrup_switch to know what value triggers this branch.
        """
        for child in self._get_children(node):
            if self._is_token(child):
                return self._token_to_literal(child)
        return None


    def _visit_defoam_stmt(self, node, end_label):
        """Generate IR for default case."""
        for child in self._get_children(node):
            if self._is_node(child) and child.name in ("statement", "stmt_tail",
                                                         "stmt_tail_until_snap"):
                self._visit(child)

    # ------------------------------------------------------------------
    # Control Flow: Pour Loop (for)
    # ------------------------------------------------------------------

    def _visit_pour_loop(self, node):
        """
        Generate IR for: pour (init; cond; update) { body }
        """
        start_label = self._new_label("POUR_START")
        update_label = self._new_label("POUR_UPDATE")
        end_label = self._new_label("POUR_END")

        self._loop_stack.append((update_label, end_label))
        self._shadow_stack.append(dict(self._shadow_map))
        self._scope_depth += 1

        children = self._get_children(node)
        init_node = None
        cond_node = None
        update_node = None
        body_children = []
        in_body = False

        for child in children:
            if self._is_node(child) and child.name == "pour_init":
                init_node = child
            elif self._is_node(child) and child.name == "expression":
                if cond_node is None:
                    cond_node = child
            elif self._is_node(child) and child.name == "update":
                update_node = child
            elif self._is_token(child) and child.type == "OP_BRACES":
                in_body = True
            elif self._is_token(child) and child.type == "CL_BRACES":
                in_body = False
            elif in_body or (self._is_node(child) and child.name in
                             ("statement", "stmt_tail")):
                body_children.append(child)

        # Init
        if init_node:
            self._visit(init_node)

        # Loop start
        self._emit("LABEL", dest=start_label)

        # Condition
        if cond_node:
            cond_val = self._visit(cond_node)
            self._emit("IF_FALSE", arg1=cond_val, dest=end_label)

        # Body
        for bc in body_children:
            self._visit(bc)

        # Update
        self._emit("LABEL", dest=update_label)
        if update_node:
            self._visit(update_node)

        # Loop back
        self._emit("GOTO", dest=start_label)
        self._emit("LABEL", dest=end_label)


        self._shadow_map = self._shadow_stack.pop()
        self._scope_depth -= 1
        self._loop_stack.pop()

    def _visit_pour_init(self, node):
        """Handle pour loop initialization: data_type ID = value | ID = value"""
        dtype = self._extract_dtype(node)
        id_tok = self._find_child_token(node, "ID")
        if id_tok and dtype:
            var_name = id_tok.value
            # Shadow outer variable with scoped rename
            if var_name in self._var_types:
                print(f"[SHADOW] '{var_name}' found in _var_types, creating scoped rename")
                scoped_name = f"_s{self._scope_depth}_{var_name}"
                self._shadow_map[var_name] = scoped_name
                var_name = scoped_name
            else:
                print(f"[SHADOW] '{var_name}' NOT found in _var_types: {list(self._var_types.keys())}")
            self._var_types[var_name] = dtype
            self._emit("DECLARE", dest=var_name, type=dtype)
            # Emit initial assignment
            for child in self._get_children(node):
                if self._is_node(child) and child.name in ("value", "expression", "assign_val"):
                    val = self._visit(child)
                    if val is not None:
                        self._emit("ASSIGN", dest=var_name, arg1=val)
                    break
        elif id_tok and not dtype:
            # No type keyword, reuse existing outer variable
            var_name = self._shadow_map.get(id_tok.value, id_tok.value)
            for child in self._get_children(node):
                if self._is_node(child) and child.name in ("value", "expression", "assign_val"):
                    val = self._visit(child)
                    if val is not None:
                        self._emit("ASSIGN", dest=var_name, arg1=val)
                    break

    def _visit_update(self, node):
        """
        Process the update clause of a pour loop (the third part: i++, i+=1, etc.).
        Pass-through — routes to _visit_update_unit for each update expression.
        """
        self._visit_children_all(node)


    def _visit_update_unit(self, node):
        """Handle update unit: ID++ / ID-- / ++ID / --ID / ID op= val"""
        children = self._get_children(node)

        #debug 
        print(f"[UPDATE_UNIT] children:")
        for child in self._get_children(node):
            print(f"  is_node={self._is_node(child)}, name={getattr(child,'name',None)}, type={getattr(child,'type',None)}, value={getattr(child,'value',None)}")

        for i, child in enumerate(children):
            if self._is_token(child) and child.type == "ID":
                var_name = child.value
                var_name = self._shadow_map.get(var_name, var_name) 
                # Check for tail
                for c2 in children[i + 1:]:
                    if self._is_node(c2) and c2.name == "update_id_tail":
                        self._visit_update_id_tail(var_name, c2)
                        return
                return

            if self._is_token(child) and child.type in ("INCREMENT", "DECREMENT"):
                # Pre-increment/decrement
                for c2 in children[i + 1:]:
                    if self._is_token(c2) and c2.type == "ID":
                        var = c2.value
                        var = self._shadow_map.get(var, var)
                        t = self._new_temp()
                        inc = 1 if child.type == "INCREMENT" else -1
                        self._emit("BINOP", dest=t, arg1=var, arg2=inc, binop="+")
                        self._emit("ASSIGN", dest=var, arg1=t)
                        return
        self._visit_children_all(node)

    def _visit_update_id_tail(self, var_name, node):
        """Handle update tail: assign_op value / ++ / --"""
        children = self._get_children(node)

        # debug
        print(f"[UPDATE_ID_TAIL] children:")
        for child in self._get_children(node):
            print(f"  is_node={self._is_node(child)}, name={getattr(child,'name',None)}, type={getattr(child,'type',None)}, value={getattr(child,'value',None)}")

        for i, child in enumerate(children):
            # Post ++/--
            if self._is_node(child) and child.name in ("INCREMENT",):
                t = self._new_temp()
                self._emit("BINOP", dest=t, arg1=var_name, arg2=1, binop="+")
                self._emit("ASSIGN", dest=var_name, arg1=t)
                return
            if self._is_node(child) and child.name in ("DECREMENT",):
                t = self._new_temp()
                self._emit("BINOP", dest=t, arg1=var_name, arg2=-1, binop="+")
                self._emit("ASSIGN", dest=var_name, arg1=t)
                return
            if self._is_token(child) and child.type in ("INCREMENT", "DECREMENT"):
                t = self._new_temp()
                inc = 1 if child.type == "INCREMENT" else -1
                self._emit("BINOP", dest=t, arg1=var_name, arg2=inc, binop="+")
                self._emit("ASSIGN", dest=var_name, arg1=t)
                return

            # Assignment operators
            if self._is_node(child) and child.name == "assign_op":
                op = self._extract_assign_op(child)

                # debug
                print(f"[ASSIGN_OP] extracted op='{op}' from node children:")
                for c in self._get_children(child):
                    print(f"  is_node={self._is_node(c)}, name={getattr(c,'name',None)}, type={getattr(c,'type',None)}, value={getattr(c,'value',None)}")
                
                val = None
                for c2 in children[i + 1:]:
                    if self._is_node(c2) and c2.name == "update_val":
                        # debug
                        print(f"[UPDATE_VAL] children:")
                        for c in self._get_children(c2):
                            print(f"  is_node={self._is_node(c)}, name={getattr(c,'name',None)}, type={getattr(c,'type',None)}, value={getattr(c,'value',None)}")
                        val = self._visit(c2)

                        # debug
                        print(f"[UPDATE_VAL] visited result: {val}")
                        break
                    elif self._is_node(c2):
                        val = self._visit(c2)
                        break
                
                if val is not None:
                    if op == "=":
                        self._emit("ASSIGN", dest=var_name, arg1=val)
                    else:
                        t = self._new_temp()
                        self._emit("BINOP", dest=t, arg1=var_name, arg2=val,
                                binop=op[0])
                        self._emit("ASSIGN", dest=var_name, arg1=t)
                return
            
            if self._is_token(child) and child.type in self.ASSIGN_OP_MAP:
                op = self.ASSIGN_OP_MAP[child.type]
                val = None
                for c2 in children[i + 1:]:
                    if self._is_node(c2):
                        val = self._visit(c2)
                        break
                if val is not None:
                    if op == "=":
                        self._emit("ASSIGN", dest=var_name, arg1=val)
                    else:
                        t = self._new_temp()
                        self._emit("BINOP", dest=t, arg1=var_name, arg2=val,
                                   binop=op[0])
                        self._emit("ASSIGN", dest=var_name, arg1=t)
                return

    def _extract_assign_op(self, node):
        """
        Extract the operator string from an assign_op node using ASSIGN_OP_MAP.
        Returns '=', '+', '-', '*', or '/' for the corresponding assignment operators.
        Defaults to '=' if no known token is found.
        """
        for child in self._get_children(node):
            if self._is_token(child) and child.type in self.ASSIGN_OP_MAP:
                return self.ASSIGN_OP_MAP[child.type]
        return "="


    def _visit_update_tail(self, node):
        """Pass-through for additional update expressions after a comma in the update clause."""
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Control Flow: Whilehot Loop (while)
    # ------------------------------------------------------------------


    def _visit_whilehot_loop(self, node):
        """Generate IR for: whilehot (cond) { body }"""
        start_label = self._new_label("WHILE_START")
        end_label = self._new_label("WHILE_END")

        self._loop_stack.append((start_label, end_label))

        self._emit("LABEL", dest=start_label)

        children = self._get_children(node)
        cond_node = None
        body_children = []
        in_body = False

        for child in children:
            if self._is_node(child) and child.name == "expression":
                cond_node = child
            elif self._is_token(child) and child.type == "OP_BRACES":
                in_body = True
            elif self._is_token(child) and child.type == "CL_BRACES":
                in_body = False
            elif in_body or (self._is_node(child) and child.name in
                             ("statement", "stmt_tail")):
                body_children.append(child)

        if cond_node:
            cond_val = self._visit(cond_node)
            self._emit("IF_FALSE", arg1=cond_val, dest=end_label)

        for bc in body_children:
            self._visit(bc)

        self._emit("GOTO", dest=start_label)
        self._emit("LABEL", dest=end_label)

        self._loop_stack.pop()

    # ------------------------------------------------------------------
    # Control Flow: Taste-Till Loop (do-while)
    # ------------------------------------------------------------------

    def _visit_tastetill_loop(self, node):
        """Generate IR for: taste { body } till: (cond)"""
        start_label = self._new_label("DOWHILE_START")
        end_label = self._new_label("DOWHILE_END")

        self._loop_stack.append((start_label, end_label))

        self._emit("LABEL", dest=start_label)

        children = self._get_children(node)
        body_children = []
        cond_node = None
        in_body = False

        for child in children:
            if self._is_token(child) and child.type == "OP_BRACES":
                in_body = True
            elif self._is_token(child) and child.type == "CL_BRACES":
                in_body = False
            elif self._is_node(child) and child.name == "expression":
                cond_node = child
            elif in_body or (self._is_node(child) and child.name in
                             ("statement", "stmt_tail")):
                body_children.append(child)

        for bc in body_children:
            self._visit(bc)

        if cond_node:
            cond_val = self._visit(cond_node)
            self._emit("IF_TRUE", arg1=cond_val, dest=start_label)

        self._emit("LABEL", dest=end_label)

        self._loop_stack.pop()

    # ------------------------------------------------------------------
    # Interrupt Statements (snap / skip)
    # ------------------------------------------------------------------

    def _visit_intrpt_stmt(self, node):
        """Handle break (snap) and continue (skip)."""
        for child in self._get_children(node):
            if self._is_token(child):
                if child.type == "SNAP":
                    if self._loop_stack:
                        update_label, end_label = self._loop_stack[-1]
                        self._emit("GOTO", dest=end_label)
                if child.type == "SKIP":
                    if self._loop_stack:
                        update_label, end_label = self._loop_stack[-1]
                        if update_label:
                            self._emit("GOTO", dest=update_label) 
                        else:
                            self._emit("SKIP")
                    return

    # ------------------------------------------------------------------
    # Functions: Recipe (returning functions)
    # ------------------------------------------------------------------

    def _visit_recipe_def(self, node):
        """
        Generate IR for a named returning function (recipe returntype name(params) [...]).
        Emits: FUNC_BEGIN → params (DECLARE param=True) → body → FUNC_END.
        Sets _current_func and _current_return_type while visiting the body so
        refill? knows both the function name and the expected return type for coercion.
        Local vars:
          func_name          — function name from ID token
          dtype              — return type from recipe_ret_type child node
          prev_func          — saved _current_func to restore after
          prev_return_type   — saved _current_return_type to restore after
        """
        id_tok = self._find_child_token(node, "ID")
        func_name = id_tok.value if id_tok else "_anon"

        # Extract return type from recipe_ret_type 
        dtype = None
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "recipe_ret_type":
                dtype = self._extract_dtype(child)
                break

        self._emit("FUNC_BEGIN", dest=func_name)
        prev_func = self._current_func
        prev_return_type = self._current_return_type
        self._current_func = func_name
        self._current_return_type = dtype

        for child in self._get_children(node):
            if self._is_node(child) and child.name == "parameter":
                self._visit_parameter(child)

        for child in self._get_children(node):
            if self._is_node(child) and child.name in ("recipe_body", "empty_body"):
                self._visit(child)
            elif self._is_node(child) and child.name == "refill_final":
                self._visit_refill_final(child)

        self._current_func = prev_func
        self._current_return_type = prev_return_type
        self._emit("FUNC_END", dest=func_name)


    def _visit_recipe_body(self, node):
        """Pass-through — visits all statement children in the function body."""
        self._visit_children_all(node)


    def _visit_recipe_ret_type(self, node):
        """
        No-op — the return type node is read by _visit_recipe_def() via _extract_dtype()
        before visiting children. This stub prevents default _visit() fallback.
        """
        return None  # type info only, not executable

    # ------------------------------------------------------------------
    # Functions: Empty (void functions)
    # ------------------------------------------------------------------

    def _visit_empty_def(self, node):
        """
        Generate IR for a void function (empty returntype name(params) [...]).
        Same structure as _visit_recipe_def but always emits RETURN arg1=None at the end
        since void functions have no explicit return value.
        Emits: FUNC_BEGIN → params → body → RETURN None → FUNC_END.
        """
        id_tok = self._find_child_token(node, "ID")
        func_name = id_tok.value if id_tok else "_anon_void"

        # debug
        for child in self._get_children(node):
            print(f"[EMPTY_DEF child] is_node={self._is_node(child)}, name={getattr(child, 'name', None)}, type={getattr(child, 'type', None)}")

        self._emit("FUNC_BEGIN", dest=func_name)
        prev_func = self._current_func
        self._current_func = func_name

        for child in self._get_children(node):
            if self._is_node(child) and child.name == "parameter":
                self._visit_parameter(child)

        for child in self._get_children(node):
            if self._is_node(child) and child.name == "empty_body":
                self._visit(child)
            # FIX: handle refill_final in void functions too
            elif self._is_node(child) and child.name == "refill_final":
                self._visit_refill_final(child)

        self._emit("RETURN", arg1=None)
        self._current_func = prev_func
        self._emit("FUNC_END", dest=func_name)
        # print(f"[DEBUG] emitted FUNC_END for {func_name}, total instrs={len(self.instructions)}")  # debug, pls check if the optimizer is messing with it again


    def _visit_empty_body(self, node):
        """Pass-through — visits all statement children in the void function body."""
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------


    def _visit_parameter(self, node):
        """Process function parameters and emit DECLARE for each."""
        children = self._get_children(node)
        dtype = None

        print(f"[PARAM DEBUG] children:")
        for child in children:
            print(f"  is_node={self._is_node(child)}, name={getattr(child, 'name', None)}, type={getattr(child, 'type', None)}, value={getattr(child, 'value', None)}")
            
        for child in children:
                if self._is_node(child) and child.name == "dtype_param":
                    dtype = self._extract_dtype(child)
                    # ID is inside var_dec_init inside dtype_param
                    var_dec = self._find_child_node(child, "var_dec_init")
                    if var_dec:
                        id_tok = self._find_child_token(var_dec, "ID")
                    else:
                        id_tok = self._find_child_token(child, "ID")
                    if id_tok:
                        var_name = id_tok.value
                        if dtype:
                            self._var_types[var_name] = dtype
                        self._emit("DECLARE", dest=var_name, type=dtype, param=True)

                elif self._is_node(child) and child.name == "add_param":
                    # recurse for comma-separated additional params (skips _empty)
                    self._visit_parameter(child)

                elif self._is_node(child) and child.name in ("parameter", "param_tail", "param_list"):
                    self._visit_parameter(child)

                # fallback: flat structure (original handling)
                elif self._is_node(child) and child.name == "data_type":
                    dtype = self._extract_dtype(child)
                elif self._is_token(child) and child.type in self.DTYPE_MAP:
                    dtype = self.DTYPE_MAP[child.type]
                elif self._is_token(child) and child.type == "ID":
                    var_name = child.value
                    if dtype:
                        self._var_types[var_name] = dtype
                    self._emit("DECLARE", dest=var_name, type=dtype, param=True)

    # ------------------------------------------------------------------
    # Return (refill?)
    # ------------------------------------------------------------------

    def _visit_refill_stmt(self, node):
        """Handle refill? statement inside control flow blocks."""
        val = None
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "refill_arg":
                val = self._visit_refill_arg(child)
            elif self._is_node(child) and child.name not in ("_empty",):
                r = self._visit(child)
                if r is not None:
                    val = r
        self._emit("RETURN", arg1=val, return_type=self._current_return_type)

    def _visit_refill_final(self, node):
        """Handle refill? statement in recipe functions."""
        val = None
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "refill_arg":
                val = self._visit_refill_arg(child)
            elif self._is_node(child) and child.name not in ("_empty",):
                r = self._visit(child)
                if r is not None:
                    val = r
        self._emit("RETURN", arg1=val, return_type=self._current_return_type)

    def _visit_refill_arg(self, node):
        """
        Extract the return value from a refill? argument node.
        Tries in order: refill_content node → any non-paren node child → literal token.
        Returns 0 as fallback (refill? with no explicit value in main).
        """
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "refill_content":
                return self._visit(child)
            if self._is_node(child) and child.name not in ("_empty", "OP_PAREN", "CL_PAREN"):
                return self._visit(child)
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                return self._token_to_literal(child)
            if self._is_token(child) and child.type == "BEANLIT":
                return int(child.value)
        return 0


    def _visit_refill_content(self, node):
        """
        Evaluate the expression inside refill?(expr).
        Returns the literal value or visits the expression node to get a temp/var name.
        """
        for child in self._get_children(node):
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                return self._token_to_literal(child)
            if self._is_node(child):
                return self._visit(child)
        return None

    # ------------------------------------------------------------------
    # Classes (crema)
    # ------------------------------------------------------------------


    def _visit_crema_def(self, node):
        """
        Generate IR for a class definition (crema classname [...]).
        Sets _current_class to the class name so field/method visitors know they're
        inside a class context. Emits CLASS_DEF at the start and CLASS_END at the end.
        Also initializes _class_fields[class_name] = [] to track all fields/methods.
        The class body (fields and methods) is emitted between CLASS_DEF and CLASS_END
        via _visit_children_all → _visit_crema_body → _visit_crema_body_cont.
        """
        id_tok = self._find_child_token(node, "ID")
        class_name = id_tok.value if id_tok else "_anon_class"
        self._current_class = class_name
        self._class_fields[class_name] = []  # track fields

        self._emit("CLASS_DEF", dest=class_name)
        self._visit_children_all(node)
        self._emit("CLASS_END", dest=class_name)
        self._current_class = None


    def _visit_crema_body(self, node):
        """Pass-through — visits all crema_body_cont children (fields and methods)."""
        self._visit_children_all(node)


    def _visit_crema_body_cont(self, node):
        """
        Process one member declaration inside a class body.
        First pass: reads CAFE/BACKROOM token to set _current_field_access.
        Second pass: delegates the crema_acc_body child to _visit_crema_acc_body()
        which handles both field declarations and method definitions.
        Does NOT call _visit_children_all() — only processes crema_acc_body nodes
        to avoid re-visiting field initializers as regular statements.
        """
        for child in self._get_children(node):
            if self._is_token(child) and child.type == "CAFE":
                self._current_field_access = "public"
            elif self._is_token(child) and child.type == "BACKROOM":
                self._current_field_access = "private"
        # visit only crema_acc_body children
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "crema_acc_body":
                self._visit_crema_acc_body(child)

    def _visit_crema_acc_body(self, node):
        """Handle cafe/backroom field declaration inside a crema class."""
        
        # If this is a method (RECIPE or EMPTY), handle separately
        for child in self._get_children(node):
            if self._is_token(child) and child.type in ("RECIPE", "EMPTY"):
                self._visit_crema_method(node)
                return
            
        if self._current_class:
            access = getattr(self, '_current_field_access', 'public')
            dtype = self._extract_dtype(node)
            id_tok = self._find_child_token_deep(node, "ID")
            if dtype and id_tok:
                field_name = id_tok.value
                init_val = None
                array_size = None  # track array size

                for child in self._get_children(node):
                    if self._is_node(child) and child.name == "crema_dtype_id_tail":
                        # extract init value
                        for tc in self._get_children(child):
                            if self._is_node(tc) and tc.name == "opt_assign":
                                init_val = self._extract_literal_from_node(tc)
                                break
                        # reuse same BEANLIT-after-OP_BRACKETS pattern as regular arrays
                        toks = self._get_children(child)
                        # print(f"[DEBUG toks] {[(getattr(t,'type',None), getattr(t,'name',None)) for t in toks]}")
                        for i, tc in enumerate(toks):
                            if (self._is_token(tc) and tc.type == "OP_BRACKETS") or \
                            (self._is_node(tc) and tc.name == "OP_BRACKETS"):  # ← add node check
                                if i + 1 < len(toks):
                                    next_node = toks[i + 1]
                                    if self._is_node(next_node) and next_node.name == "arr_size_val":
                                        for sc in self._get_children(next_node):
                                            if self._is_token(sc) and sc.type == "BEANLIT":
                                                array_size = int(sc.value)
                                    elif self._is_token(next_node) and next_node.type == "BEANLIT":
                                        array_size = int(next_node.value)

                        
                self._class_fields.setdefault(self._current_class, []).append({
                    "name": field_name, "type": dtype,
                    "access": access, "init": init_val,
                    "array_size": array_size  # store for codegen
                })
                self._emit("CLASS_FIELD", dest=field_name,
                        type=dtype, access=access,
                        class_name=self._current_class,
                        init=init_val, array_size=array_size)  # pass to codegen
            return
        self._visit_children_all(node)

    def _visit_crema_dtype_id_tail(self, node):
        """Skip — field handled by _visit_crema_acc_body."""
        pass

    def _find_child_token_deep(self, node, token_type):
        """Recursively find first token with given type in any descendant."""
        for c in self._get_children(node):
            if self._is_token(c) and c.type == token_type:
                return c
            if self._is_node(c):
                result = self._find_child_token_deep(c, token_type)
                if result:
                    return result
        return None
    # ------------------------------------------------------------------
    # Objects (new)
    # ------------------------------------------------------------------

    def _visit_object_def(self, node):
        """
        Generate IR for 'new ClassName = objName' (class instantiation).
        Extracts the two ID tokens: class name and instance variable name.
        Emits:
          DECLARE dest=objName type=ClassName  (so codegen knows the type)
          CALL    dest=objName arg1=new_ClassName arg_count=0
        The CALL to 'new_ClassName' is resolved by the codegen to '_func_new_ClassName()'
        which returns a fresh Python instance of _Caramel_ClassName.
        """
        ids = self._find_all_child_tokens(node, "ID")
        if len(ids) >= 2:
            class_name = ids[0].value
            obj_name = ids[1].value
            self._emit("DECLARE", dest=obj_name, type=class_name)
            self._emit("CALL", dest=obj_name, arg1=f"new_{class_name}", arg_count=0)
        else:
            self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Arrays
    # ------------------------------------------------------------------


    def _visit_arr_dec_dim(self, node):
        """
        No-op stub — array dimension info is consumed upstream by _visit_dtype_id_tail()
        which reads arr_size_val and arr_dec_dim before they're visited by default dispatch.
        """
        # Handled by _visit_dtype_id_tail
        pass


    def _collect_arr_init_values(self, node):
        """Collect initial values from arr_dec_dim."""
        # Check if this is a 2D initializer (arr_cont_2d inside arr_dec_dim)
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "arr_cont_2d":
                return self._collect_arr_init_values_2d(child)
        # 1D path — collect flat list
        values = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "arr_cont_1d":
                values.extend(self._collect_arr_init_values_1d(child))
            elif self._is_node(child) and child.name not in (
                "_empty", "OP_BRACKETS", "CL_BRACKETS", "COMMA", "EQUALS", "arr_dec_dim"
            ):
                values.extend(self._collect_arr_init_values(child))
        return values

    def _collect_arr_init_values_1d(self, node):
        """Collect a flat list of values from arr_cont_1d."""
        values = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "arr_elem":
                val = self._visit_arr_elem(child)
                if val is not None:
                    values.append(val)
            elif self._is_node(child) and child.name == "ext_arr_elem":
                for ec in self._get_children(child):
                    if self._is_node(ec) and ec.name == "arr_elem":
                        val = self._visit_arr_elem(ec)
                        if val is not None:
                            values.append(val)
        return values

    def _collect_arr_init_values_2d(self, node):
        """Collect a list of row lists from arr_cont_2d."""
        rows = []
        # First two rows are direct OP_BRACKETS...opt_arr_elems...CL_BRACKETS
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "opt_arr_elems":
                rows.append(self._collect_arr_init_values_1d(child))
            elif self._is_node(child) and child.name == "arr_cont_2d_tail":
                for tc in self._get_children(child):
                    if self._is_node(tc) and tc.name == "opt_arr_elems":
                        rows.append(self._collect_arr_init_values_1d(tc))
        return rows

    def _visit_arr_cont_1d(self, node):
        """
        No-op stub — 1D array content is collected by _collect_arr_init_values_1d()
        which reads the arr_elem children directly. Default dispatch here would
        re-process them unnecessarily.
        """
        self._visit_children_all(node)


    def _visit_arr_cont_2d(self, node):
        """
        No-op stub — 2D array content is collected by _collect_arr_init_values_2d()
        which reads rows from opt_arr_elems children directly.
        """
        self._visit_children_all(node)


    def _visit_arr_elem(self, node):
        """Extract a single array element value."""
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "expression":
                return self._visit(child)
            if self._is_node(child) and child.name not in ("_empty",):
                return self._visit(child)
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                return self._token_to_literal(child)
        return None

    def _visit_id_bracket_tail_rhs(self, node):
        """Extract RHS value from id_bracket_tail (the = expr part after array[idx])."""
        children = self._get_children(node)
        for i, child in enumerate(children):
            if self._is_token(child) and child.type == "EQUALS":
                for c in children[i + 1:]:
                    if self._is_node(c):
                        return self._visit(c)
            # compound: +=, -=, etc. — extend here later if needed
        return None
    
    # ------------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------------

    def _extract_literal_from_node(self, node):
        """Recursively find first literal token in a node tree."""
        for child in self._get_children(node):
            if self._is_token(child) and child.type in (
                "BEANLIT", "DRIPLIT", "BLENDLIT", "CHURROLIT", "TEMPLIT"
            ):
                return child.value
            if self._is_node(child):
                result = self._extract_literal_from_node(child)
                if result is not None:
                    return result
        return None

    def _visit_crema_method(self, node):
        """
        Generate IR for a method defined inside a crema class.
        Called by _visit_crema_acc_body when it detects a RECIPE/EMPTY token.

        Key steps:
        1. Extracts method name and saves class_name before clearing _current_class
        2. Mangles the name: 'describe' in class 'point' → 'class_point__describe'
        3. Registers the method in _class_fields so sibling methods can find it
        4. Populates _class_field_names with all fields/methods of this class
           so bare references like 'increment()' inside the body emit METHOD_CALL
        5. Clears _current_class=None during body visit so local variable declarations
           don't accidentally get registered as class fields
        6. Restores _current_class and clears _class_field_names after body

        Emits: FUNC_BEGIN (with method_of=class_name) → params → body → FUNC_END

        Local vars:
          class_name  — saved _current_class (e.g. 'counter')
          mangled     — namespaced function name (e.g. 'class_counter__increment')
          prev_class  — same as class_name, used to restore _current_class
          prev_func   — saved _current_func to restore after method body
        """
        id_tok = self._find_child_token(node, "ID")
        method_name = id_tok.value if id_tok else "_anon_method"
        
        class_name = self._current_class  # save before touching anything
        mangled = f"class_{class_name}__{method_name}"

        self._emit("FUNC_BEGIN", dest=mangled, method_of=class_name)
        
        # register method name in _class_fields so siblings can find it
        if class_name not in self._class_fields:
            self._class_fields[class_name] = []
        if not any(f["name"] == method_name for f in self._class_fields[class_name]):
            self._class_fields[class_name].append({
                "name": method_name, "kind": "method"
            })

        prev_class = self._current_class
        prev_func = self._current_func
        self._current_func = mangled

        # populate field+method names so bare calls inside body resolve correctly
        self._class_field_names = set(
            f["name"] for f in self._class_fields.get(prev_class, [])
        )
        # also include method names registered in _class_fields
        for entry in self._class_fields.get(prev_class, []):
            if isinstance(entry, dict) and "name" in entry:
                self._class_field_names.add(entry["name"])

        self._current_class = None  # clear so body locals don't register as fields

        for child in self._get_children(node):
            if self._is_node(child) and child.name == "parameter":
                self._visit_parameter(child)
        for child in self._get_children(node):
            if self._is_node(child) and child.name in ("recipe_body", "empty_body"):
                self._visit(child)
            elif self._is_node(child) and child.name == "refill_final":
                self._visit_refill_final(child)

        self._current_func = prev_func
        self._current_class = prev_class  # restore class context for next method
        self._class_field_names = set()   # reset so non-method code isn't affected
        self._emit("FUNC_END", dest=mangled)


    def _collect_function_args(self, node):
        """Collect evaluated arguments from function call nodes."""
        args = []
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "function_args":
                val = self._visit_function_args_node(child)
                if val is not None:
                    args.append(val)
            elif self._is_node(child) and child.name == "function_args_tail":
                args.extend(self._collect_function_args(child))
        return args

    def _visit_function_args_node(self, node):
        """
        Evaluate a single function_args node (one argument in a call).
        Returns the value: BLENDLIT string → raw string, expression → visits and returns result.
        Called by _collect_function_args() for each argument in a function call.
        """
        for child in self._get_children(node):
            if self._is_token(child) and child.type == "BLENDLIT":
                return child.value
            if self._is_node(child) and child.name == "expression":
                return self._visit(child)
            if self._is_node(child) and child.name != "_empty":
                return self._visit(child)
        return None


    def _extract_array_index_expr(self, node):
        """Extract array index by evaluating expressions (supports variables and arithmetic)."""
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "array_index":
                for c2 in self._get_children(child):
                    if self._is_token(c2) and c2.type == "BEANLIT":
                        return int(c2.value)
                    if self._is_token(c2) and c2.type == "ID":
                        return c2.value
                    if self._is_node(c2) and c2.name == "expression":
                        return self._visit(c2)
                    if self._is_node(c2) and c2.name not in ("_empty",):
                        return self._visit(c2)
        return 0

    def _extract_array_index(self, node):
        """
        Extract a simple array index from a node containing an array_index child.
        Handles: BEANLIT (constant), ID (variable), expression (evaluated).
        Also handles bare BEANLIT tokens as direct children.
        Returns 0 if no index found.

        Difference from _extract_array_index_expr():
          This version is used in blend/string concat contexts where the parent node
          structure may be slightly different. _extract_array_index_expr() is used
          in statement contexts (assignment, id_dec_tail).
        """
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "array_index":
                for c2 in self._get_children(child):
                    if self._is_token(c2) and c2.type == "BEANLIT":
                        return int(c2.value)
                    if self._is_token(c2) and c2.type == "ID":
                        return c2.value
                    if self._is_node(c2) and c2.name == "expression":
                        return self._visit(c2)
            if self._is_token(child) and child.type == "BEANLIT":
                return int(child.value)
            if self._is_node(child) and child.name not in ("_empty", "OP_BRACKETS",
                                                             "CL_BRACKETS"):
                r = self._extract_array_index(child)
                if r is not None:
                    return r
        return 0

    def _extract_array_index_from_arr_call_tail(self, node):
        """Extract index from arr_call_tail node."""
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "array_index":
                return self._visit(child)
        return None

    # ------------------------------------------------------------------
    # Pre-unary declarations
    # ------------------------------------------------------------------

    def _visit_pre_unary_dec(self, node):
        """Handle ++ID or --ID as a statement."""
        children = self._get_children(node)
        op_type = None
        var = None

        for child in children:
            # Handle unary_op node wrapper
            if self._is_node(child) and child.name == "unary_op":
                for uc in self._get_children(child):
                    if self._is_token(uc) and uc.type in ("INCREMENT", "DECREMENT"):
                        op_type = uc.type
                        break
            # Handle direct INCREMENT/DECREMENT token
            elif self._is_token(child) and child.type in ("INCREMENT", "DECREMENT"):
                op_type = child.type
            # Get the variable name
            elif self._is_token(child) and child.type == "ID":
                var = child.value

        if op_type and var:
            t = self._new_temp()
            inc = 1 if op_type == "INCREMENT" else -1
            self._emit("BINOP", dest=t, arg1=var, arg2=inc, binop="+")
            self._emit("ASSIGN", dest=var, arg1=t)
        else:
            self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Data type node (no-op for IR)
    # ------------------------------------------------------------------

    def _visit_data_type(self, node):
        """
        No-op stub — data_type nodes are read by _extract_dtype() before visiting,
        not by dispatching. If this is reached via default _visit(), return None
        to prevent the type keyword from being interpreted as a value.
        """
        return None
