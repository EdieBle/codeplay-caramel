"""
Intermediate Representation (IR) Generator for CARAMEL Language

Translates the AST (ParseNode tree) from the parser into a linear sequence of
Three-Address Code (TAC) instructions. Each instruction is a dictionary with an
'op' field and operand fields.

IR Instruction Format:
    {
        "op": <operation>,
        "dest": <destination variable or label>,
        "arg1": <first operand>,
        "arg2": <second operand>,          # optional
        "type": <CARAMEL type>,            # optional, for declarations
    }

Operations:
    DECLARE     - variable declaration          (dest=var, type=dtype)
    ASSIGN      - simple assignment             (dest=var, arg1=value)
    BINOP       - binary operation              (dest=temp, arg1, arg2, binop=op)
    UNARYOP     - unary operation               (dest=temp, arg1, unaryop=op)
    LABEL       - label marker                  (dest=label_name)
    GOTO        - unconditional jump            (dest=label)
    IF_FALSE    - conditional jump              (arg1=cond, dest=label)
    IF_TRUE     - conditional jump on true      (arg1=cond, dest=label)
    CALL        - function call                 (dest=temp, arg1=func_name, args=[...])
    PARAM       - push parameter                (arg1=value)
    RETURN      - return from function          (arg1=value)
    FUNC_BEGIN  - function entry                (dest=func_name)
    FUNC_END    - function exit                 (dest=func_name)
    PRINT       - output statement              (args=[...])
    INPUT       - input statement               (dest=var)
    ARR_DECLARE - array declaration             (dest=var, type=dtype, dims=[...])
    ARR_STORE   - array store                   (dest=arr, arg1=index, arg2=value)
    ARR_LOAD    - array load                    (dest=temp, arg1=arr, arg2=index)
    NOP         - no operation (placeholder)
    CONCAT      - string concatenation          (dest=temp, arg1, arg2)
    CAST        - type conversion               (dest=temp, arg1=source, type=target)
    MEMBER_ACC  - member access                 (dest=temp, arg1=obj, arg2=member)
"""


class IRInstruction:
    """Represents a single IR instruction."""

    __slots__ = ("op", "dest", "arg1", "arg2", "extra")

    def __init__(self, op, dest=None, arg1=None, arg2=None, **extra):
        self.op = op
        self.dest = dest
        self.arg1 = arg1
        self.arg2 = arg2
        self.extra = extra

    def to_dict(self):
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
        "TEMP": "temp", "BLEND": "blend", "MUG": "mug",
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
        "PLUS_EQUALS": "+=",
        "EQUAL_MINUS": "-=",      
        "MULTIPLY_EQUALS": "*=",
        "DIVIDE_EQUALS": "/=",
    }

    LITERAL_TYPES = {
        "BEANLIT": "bean", "DRIPLIT": "drip",
        "CHURROLIT": "churro", "HOT": "temp", "COLD": "temp",
        "BLENDLIT": "blend",
    }

    def __init__(self, ast):
        self.ast = ast
        self.instructions = []
        self._temp_count = 0
        self._label_count = 0
        self._var_types = {}          # var_name -> caramel_type
        self._current_func = None     # track current function scope
        self._loop_stack = []         # stack of (continue_label, break_label)
        self._errors = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self):
        """Generate IR from the AST. Returns list of IRInstruction objects."""
        if not self.ast:
            return []
        self._visit(self.ast)
        return self.instructions
    
    def get_ir_dicts(self):
        """Return IR as a list of plain dictionaries (for JSON serialization)."""
        return [instr.to_dict() for instr in self.instructions]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, op, **kwargs):
        instr = IRInstruction(op, **kwargs)
        self.instructions.append(instr)
        return instr

    def _new_temp(self):
        self._temp_count += 1
        return f"_t{self._temp_count}"

    def _new_label(self, hint="L"):
        self._label_count += 1
        return f"{hint}_{self._label_count}"

    def _is_node(self, obj):
        return hasattr(obj, "name") and hasattr(obj, "children")

    def _is_token(self, obj):
        return not self._is_node(obj) and hasattr(obj, "type")

    def _get_children(self, node):
        return node.children if hasattr(node, "children") else []

    def _find_child_node(self, node, name):
        """Find first child ParseNode with given name."""
        for c in self._get_children(node):
            if self._is_node(c) and c.name == name:
                return c
        return None

    def _find_child_token(self, node, token_type):
        """Find first child token with given type."""
        for c in self._get_children(node):
            if self._is_token(c) and c.type == token_type:
                return c
        return None

    def _find_all_child_tokens(self, node, token_type):
        """Find all child tokens with given type."""
        return [c for c in self._get_children(node)
                if self._is_token(c) and c.type == token_type]

    def _extract_dtype(self, node):
        """Extract CARAMEL data type string from a node tree."""
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
        """Convert a literal token to its IR value representation."""
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
        """Dispatch to a _visit_<name> method or walk children."""
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
        self._visit_children_all(node)

    def _visit_program(self, node):
        self._visit_children_all(node)

    def _visit_global_def(self, node):
        self._visit_children_all(node)

    def _visit_global_dec(self, node):
        self._visit_children_all(node)

    def _visit_children_all(self, node):
        for child in self._get_children(node):
            self._visit(child)

    # ------------------------------------------------------------------
    # Main Function
    # ------------------------------------------------------------------

    def _visit_main_def(self, node):
        self._emit("FUNC_BEGIN", dest="cup")
        self._current_func = "cup"
        self._visit_children_all(node)
        self._current_func = None
        self._emit("FUNC_END", dest="cup")

    def _visit_main_body(self, node):
        self._visit_children_all(node)

    def _visit_refill_main(self, node):
        # refill? 0  in main
        self._emit("RETURN", arg1=0)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _visit_dec(self, node):
        self._visit_children_all(node)

    def _visit_acc_mod_dec(self, node):
        self._visit_children_all(node)

    def _visit_acc_mod_dec_body(self, node):
        self._visit_children_all(node)

    def _visit_dtype_dec(self, node):
        """Handle typed declaration: data_type ID tail"""
        dtype = self._extract_dtype(node)
        id_tok = self._find_child_token(node, "ID")
        if id_tok and dtype:
            var_name = id_tok.value
            self._var_types[var_name] = dtype
            self._emit("DECLARE", dest=var_name, type=dtype)

            # process the tail (opt_assign, array, etc.)
            for child in self._get_children(node):
                if self._is_node(child) and child.name not in ("data_type",):
                    self._visit(child)
        else:
            self._visit_children_all(node)

    def _visit_dtype_brewed_body(self, node):
        """Handle constant declaration: brewed data_type ID = value"""
        dtype = self._extract_dtype(node)
        self._visit_children_all(node)

    def _visit_acc_brewed_body(self, node):
        dtype = self._extract_dtype(node)
        self._visit_children_all(node)

    def _visit_acc_dtype_tail(self, node):
        self._visit_children_all(node)

    def _visit_dtype_id_tail(self, node):
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
            if self._is_node(child) and child.name in ("value", "assign_val",
                                                        "expression", "blend_val"):
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
        """Handle constant variable initialization: ID = value"""
        id_tok = self._find_child_token(node, "ID")
        if id_tok:
            var_name = id_tok.value
            # Find dtype from context (parent should have extracted it)
            dtype = self._var_types.get(var_name)
            if not dtype:
                dtype = self._extract_dtype(node)
            if dtype:
                self._var_types[var_name] = dtype
            self._emit("DECLARE", dest=var_name, type=dtype, constant=True)

            # find and visit the value/expression child
            for child in self._get_children(node):
                if self._is_node(child) and child.name in ("value", "assign_val",
                                                             "expression", "opt_assign"):
                    val = self._visit(child)
                    if val is not None:
                        self._emit("ASSIGN", dest=var_name, arg1=val)
                    return
        self._visit_children_all(node)

    def _visit_var_dec_const_tail(self, node):
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
        for child in self._get_children(node):
            if self._is_token(child):
                if child.type == "BLENDLIT":
                    return child.value
                if child.type == "ID":
                    return child.value
            if self._is_node(child):
                return self._visit(child)
        return None

    def _visit_blend_val_tail(self, node):
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
        self._visit_children_all(node)

    def _visit_blend_const_init(self, node):
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
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # ID-Led Statements (assignments, calls, etc.)
    # ------------------------------------------------------------------

    def _visit_id_dec_stmt(self, node):
        """Handle ID-led statement: ID = value, ID++, ID.member, ID(...), etc."""
        id_tok = self._find_child_token(node, "ID")
        if not id_tok:
            self._visit_children_all(node)
            return

        var_name = id_tok.value

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

        # Compound assignment: +=, -=, *=, /=
        if self._is_token(first) and first.type in self.ASSIGN_OP_MAP:
            op = self.ASSIGN_OP_MAP[first.type]
            val = None
            for c in children[1:]:
                if self._is_node(c):
                    val = self._visit(c)
                    break
            if val is not None:
                t = self._new_temp()
                base_op = op[0]  # '+' from '+=' [seems bugged??]
                self._emit("BINOP", dest=t, arg1=var_name, arg2=val, binop=base_op)
                self._emit("ASSIGN", dest=var_name, arg1=t)
            return

        # Post-increment/decrement
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

        # Function call: (args)
        if (self._is_node(first) and first.name == "OP_PAREN") or \
           (self._is_token(first) and first.type == "OP_PAREN"):
            args = self._collect_function_args(tail_node)
            for a in args:
                self._emit("PARAM", arg1=a)
            t = self._new_temp()
            self._emit("CALL", dest=t, arg1=var_name, arg_count=len(args))
            return

        # Dot access: .member
        if (self._is_node(first) and first.name == "DOT_ACC") or \
           (self._is_token(first) and first.type == "DOT_ACC"):
            self._visit_children_all(tail_node)
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
        self._visit_children_all(node)

    def _visit_order_dec_tail(self, node):
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
        return None

    def _extract_rel_op(self, node):
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
        children = self._get_children(node)
        i = 0
        while i < len(children):
            child = children[i]
            if self._is_node(child) and child.name == "arithm_op":
                op = self._extract_arith_op(child)
                if i + 1 < len(children):
                    right = self._visit(children[i + 1])
                    t = self._new_temp()
                    self._emit("BINOP", dest=t, arg1=left, arg2=right, binop=op)
                    left = t
                    i += 2
                    continue
            i += 1
        return left

    def _visit_arith_expr_tail(self, node):
        return None

    def _extract_arith_op(self, node):
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
        for child in self._get_children(node):
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
                for c2 in children[i + 1:]:
                    if self._is_token(c2) and c2.type == "ID":
                        return f"order.{c2.value}"
                return "order"

            # Parenthesized expression
            if (self._is_node(child) and child.name == "OP_PAREN") or \
               (self._is_token(child) and child.type == "OP_PAREN"):
                for c2 in children[i + 1:]:
                    if self._is_node(c2) and c2.name in ("expression", "blend_val"):
                        return self._visit(c2)
                continue

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
        if (self._is_node(first) and first.name == "OP_PAREN") or \
           (self._is_token(first) and first.type == "OP_PAREN"):
            args = self._collect_function_args(tail_node)
            for a in args:
                self._emit("PARAM", arg1=a)
            t = self._new_temp()
            self._emit("CALL", dest=t, arg1=var_name, arg_count=len(args))
            return t

        # Array access: OP_BRACKETS index CL_BRACKETS
        if (self._is_node(first) and first.name == "OP_BRACKETS") or \
           (self._is_token(first) and first.type == "OP_BRACKETS"):
            idx = self._extract_array_index(tail_node)
            t = self._new_temp()
            self._emit("ARR_LOAD", dest=t, arg1=var_name, arg2=idx)
            return t

        # Member access: DOT_ACC ID
        if (self._is_node(first) and first.name == "DOT_ACC") or \
           (self._is_token(first) and first.type == "DOT_ACC"):
            member_id = None
            for c in children[1:]:
                if self._is_token(c) and c.type == "ID":
                    member_id = c.value
                    break
            if member_id:
                t = self._new_temp()
                self._emit("MEMBER_ACC", dest=t, arg1=var_name, arg2=member_id)
                return t

        return var_name

    def _visit_primary_dot_tail(self, node):
        self._visit_children_all(node)

    def _visit_primary_order_tail(self, node):
        self._visit_children_all(node)

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
        return self._visit_value(node)

    def _visit_assign_value(self, node):
        return self._visit_value(node)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _visit_statement(self, node):
        self._visit_children_all(node)

    def _visit_stmt_tail(self, node):
        self._visit_children_all(node)

    def _visit_stmt_tail_until_snap(self, node):
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
        """Handle batter@ input statement."""
        targets = self._collect_input_targets(node)
        for target in targets:
            self._emit("INPUT", dest=target)

    def _collect_input_targets(self, node):
        targets = []
        for child in self._get_children(node):
            if self._is_token(child) and child.type == "ID":
                targets.append(child.value)
            elif self._is_node(child) and child.name not in ("_empty",):
                targets.extend(self._collect_input_targets(child))
        return targets

    def _visit_input_args(self, node):
        self._visit_children_all(node)

    def _visit_input_args_unit(self, node):
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Control Flow: If / Else If / Else
    # ------------------------------------------------------------------

    def _visit_if_cond(self, node):
        """
        Generate IR for if/else-if/else chain.

        ifbrew (cond) { body } elifroth (cond) { body } elspress { body }
        """
        end_label = self._new_label("IF_END")
        self._generate_if_chain(node, end_label)
        self._emit("LABEL", dest=end_label)

    def _generate_if_chain(self, node, end_label):
        children = self._get_children(node)

        # Find the condition expression
        cond = None
        body_children = []
        tail_node = None

        in_body = False
        for child in children:
            if self._is_node(child) and child.name == "expression":
                cond = self._visit(child)
            elif self._is_token(child) and child.type == "OP_BRACES":
                in_body = True
            elif self._is_token(child) and child.type == "CL_BRACES":
                in_body = False
            elif self._is_node(child) and child.name == "if_cond_tail":
                tail_node = child
            elif in_body or (self._is_node(child) and child.name in
                             ("statement", "stmt_tail")):
                body_children.append(child)

        # Generate: IF_FALSE cond -> else_label
        else_label = self._new_label("ELSE")
        if cond is not None:
            self._emit("IF_FALSE", arg1=cond, dest=else_label)

        # Emit body
        for bc in body_children:
            self._visit(bc)

        # Jump to end
        self._emit("GOTO", dest=end_label)
        self._emit("LABEL", dest=else_label)

        # Process tail (elifroth / elspress / empty)
        if tail_node:
            self._visit_if_cond_tail(tail_node, end_label)

    def _visit_if_cond_tail(self, node, end_label):
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

        self._loop_stack.pop()

    def _visit_pour_init(self, node):
        """Handle pour loop initialization: data_type ID = value"""
        dtype = self._extract_dtype(node)
        id_tok = self._find_child_token(node, "ID")
        if id_tok and dtype:
            var_name = id_tok.value
            self._var_types[var_name] = dtype
            self._emit("DECLARE", dest=var_name, type=dtype)

        # Find and evaluate the initial value
        for child in self._get_children(node):
            if self._is_node(child) and child.name in ("value", "expression",
                                                         "assign_val"):
                val = self._visit(child)
                if val is not None and id_tok:
                    self._emit("ASSIGN", dest=id_tok.value, arg1=val)
            elif self._is_node(child) and child.name not in ("data_type", "_empty"):
                self._visit(child)

    def _visit_update(self, node):
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
        for child in self._get_children(node):
            if self._is_token(child) and child.type in self.ASSIGN_OP_MAP:
                return self.ASSIGN_OP_MAP[child.type]
        return "="

    def _visit_update_tail(self, node):
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
                if child.type == "SNAP" and self._loop_stack:
                    _, break_label = self._loop_stack[-1]
                    self._emit("GOTO", dest=break_label)
                    return
                if child.type == "SKIP" and self._loop_stack:
                    cont_label, _ = self._loop_stack[-1]
                    if cont_label:
                        self._emit("GOTO", dest=cont_label)
                    return

    # ------------------------------------------------------------------
    # Functions: Recipe (returning functions)
    # ------------------------------------------------------------------

    def _visit_recipe_def(self, node):
        """Generate IR for function definition."""
        id_tok = self._find_child_token(node, "ID")
        func_name = id_tok.value if id_tok else "_anon"

        self._emit("FUNC_BEGIN", dest=func_name)
        prev_func = self._current_func
        self._current_func = func_name

        # Process parameters
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "parameter":
                self._visit_parameter(child)

        # Process body
        for child in self._get_children(node):
            if self._is_node(child) and child.name in ("recipe_body", "empty_body"):
                self._visit(child)
            elif self._is_node(child) and child.name == "refill_final":
                self._visit_refill_final(child)

        self._current_func = prev_func
        self._emit("FUNC_END", dest=func_name)

    def _visit_recipe_body(self, node):
        self._visit_children_all(node)

    def _visit_recipe_ret_type(self, node):
        return None  # type info only, not executable

    # ------------------------------------------------------------------
    # Functions: Empty (void functions)
    # ------------------------------------------------------------------

    def _visit_empty_def(self, node):
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
        self._emit("RETURN", arg1=val)

    def _visit_refill_arg(self, node):
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "refill_content":
                return self._visit(child)
            if self._is_node(child) and child.name not in ("_empty",):
                return self._visit(child)
            if self._is_token(child) and child.type in self.LITERAL_TYPES:
                return self._token_to_literal(child)
            if self._is_token(child) and child.type == "BEANLIT":
                return int(child.value)
        return 0

    def _visit_refill_content(self, node):
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
        """Generate IR for class definition."""
        id_tok = self._find_child_token(node, "ID")
        class_name = id_tok.value if id_tok else "_anon_class"

        self._emit("FUNC_BEGIN", dest=f"class_{class_name}")
        self._visit_children_all(node)
        self._emit("FUNC_END", dest=f"class_{class_name}")

    def _visit_crema_body(self, node):
        self._visit_children_all(node)

    def _visit_crema_body_cont(self, node):
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Structs (mug)
    # ------------------------------------------------------------------

    def _visit_mug_dec(self, node):
        id_tok = self._find_child_token(node, "ID")
        if id_tok:
            self._emit("DECLARE", dest=id_tok.value, type="mug")
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Objects (new)
    # ------------------------------------------------------------------

    def _visit_object_def(self, node):
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
        self._visit_children_all(node)

    def _visit_arr_cont_1d(self, node):
        self._visit_children_all(node)

    def _visit_arr_cont_2d(self, node):
        self._visit_children_all(node)

    def _visit_arr_elem(self, node):
        return self._visit_value(node)

    # ------------------------------------------------------------------
    # Helpers for function args & array indices
    # ------------------------------------------------------------------

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
        for child in self._get_children(node):
            if self._is_token(child) and child.type == "BLENDLIT":
                return child.value
            if self._is_node(child) and child.name == "expression":
                return self._visit(child)
            if self._is_node(child) and child.name != "_empty":
                return self._visit(child)
        return None

    def _extract_array_index(self, node):
        for child in self._get_children(node):
            if self._is_node(child) and child.name == "array_index":
                for c2 in self._get_children(child):
                    if self._is_token(c2) and c2.type == "BEANLIT":
                        return int(c2.value)
            if self._is_token(child) and child.type == "BEANLIT":
                return int(child.value)
            if self._is_node(child) and child.name not in ("_empty", "OP_BRACKETS",
                                                             "CL_BRACKETS"):
                r = self._extract_array_index(child)
                if r is not None:
                    return r
        return 0

    # ------------------------------------------------------------------
    # Pre-unary declarations
    # ------------------------------------------------------------------

    def _visit_pre_unary_dec(self, node):
        """Handle ++ID or --ID as a statement."""
        children = self._get_children(node)
        for i, child in enumerate(children):
            if self._is_token(child) and child.type in ("INCREMENT", "DECREMENT"):
                for c2 in children[i + 1:]:
                    if self._is_token(c2) and c2.type == "ID":
                        var = c2.value
                        t = self._new_temp()
                        inc = 1 if child.type == "INCREMENT" else -1
                        self._emit("BINOP", dest=t, arg1=var, arg2=inc, binop="+")
                        self._emit("ASSIGN", dest=var, arg1=t)
                        return
        self._visit_children_all(node)

    # ------------------------------------------------------------------
    # Data type node (no-op for IR)
    # ------------------------------------------------------------------

    def _visit_data_type(self, node):
        return None
