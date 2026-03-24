"""
Semantic Analyzer Module for CARAMEL Language

Based on semantic rules from the CARAMEL specification document.
This module implements semantic analysis completely separate from the parser,
analyzing the AST for semantic correctness after successful parsing.

Type Compatibility Rules: refer to rule 11 tinatamad pa aq
"""
from src.Lexer.lexer import token_final_out
from src.Parser.parser import Parser
# import traceback

class SemanticError:
    """Represents a semantic error in the code."""
    
    def __init__(self, code, message, line=None, column=None, severity="error"):
        self.code = code  # Error code (e.g., "E001" for redefinition)
        self.message = message
        self.line = line
        self.column = column
        self.severity = severity  # "error" or "warning"
    
    def to_dict(self):
        """Convert to dictionary format for reporting."""
        return {
            "type": "SEMANTIC_ERROR",
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "severity": self.severity
        }

class Symbol:
    """Represents a symbol (variable, function, class) in the program."""
    
    def __init__(self, name, kind, dtype=None, is_constant=False, scope_level=0, 
                 line=None, column=None, parameters=None, return_type=None, is_array=False):
        self.name = name
        self.kind = kind  # "variable", "function", "class", "struct"
        self.dtype = dtype  # "bean", "drip", "churro", "temp", "blend", "mug", None
        self.is_constant = is_constant
        self.is_array = is_array  # True if this is an array type
        self.scope_level = scope_level
        self.line = line
        self.column = column
        self.parameters = parameters or []  # List of (name, type) tuples for functions
        self.return_type = return_type  # For functions
        self.is_initialized = False

class SymbolTable:
    """Manages symbol scopes and symbol tracking."""
    
    def __init__(self):
        self.scopes = [{}]  # Stack of scope dictionaries
        self.scope_level = 0
        self.errors = []
    
    def push_scope(self):
        """Enter a new scope."""
        self.scopes.append({})
        self.scope_level += 1
    
    def pop_scope(self):
        """Exit current scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
            self.scope_level -= 1
    
    def declare(self, name, symbol):
        """
        Declare a symbol in current scope.
        Returns True if successful, False if already declared in this scope.
        """
        # for debugging purposes only.
        print(f"[DECLARE] '{name}' at scope depth {len(self.scopes)}")
        print(f"[DECLARE] Current scopes: {[list(s.keys()) for s in self.scopes]}")
        if name in self.scopes[-1]:
            return False
        self.scopes[-1][name] = symbol
        return True
    
    def lookup(self, name):
        """Look up a symbol in current and parent scopes."""

        # for debugging purposes only.
        print(f"[LOOKUP] '{name}' - Searching {len(self.scopes)} scopes")
        for i, scope in enumerate(reversed(self.scopes)):
            print(f"  Scope {len(self.scopes)-i-1}: {list(scope.keys())}")
            if name in scope:
                print(f"  → FOUND in scope {len(self.scopes)-i-1}")
                return scope[name]
        print(f"  → NOT FOUND!")
        return None
    
    def lookup_current(self, name):
        """Look up a symbol in current scope only."""
        return self.scopes[-1].get(name)
    
    def update_symbol(self, name, symbol):
        """Update an existing symbol."""
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = symbol
                return True
        return False

class SemanticAnalyzer:
    """
    Analyzes CARAMEL AST for semantic correctness.
    
    Checks based on specification:
    - E001: Redefinition of identifier
    - E002: Undeclared identifier
    - E003: Type mismatch
    - E004: Invalid type conversion
    - E005: Constant value being modified
    - E006: Invalid operation
    - E007: Missing main function
    - E008: Multiple main functions
    - E009: Attempted type cast (REJECTED)
    - E010: Invalid operator compatibility
    - E011: Parameter unfulfilled by the arguments passed
    - E012: Array Overloaded
    - E013: Array 
    - E014: 
    """
    
    # Valid data types
    VALID_TYPES = {"bean", "drip", "churro", "temp", "blend", "mug"}
    
    # Type compatibility for assignments: target_type to set of compatible source types
    # STRICT: bean != drip without explicit cast
    TYPE_COMPAT = {
        "bean":   {"bean", "drip", "temp", "churro"},  # bean can go into drip, temp, churro
        "drip":   {"drip", "bean", "temp"},             # drip can go into bean, temp
        "churro": {"churro", "bean", "drip", "temp"},   # churro can go into bean, drip, temp
        "temp":   {"temp", "bean", "drip"},             # temp can go into bean, drip
        "blend":  {"blend"},                            # blend only into blend
    }

    # (source_type, target_type) -> True if allowed, False if invalid (REDUNDANT NA SIYA)
    # TYPE_CAST_COMPAT = {
    #     ("bean",   "bean"):   True,
    #     ("bean",   "drip"):   True,   # .0 added
    #     ("bean",   "blend"):  False,  # syntax error toh
    #     ("bean",   "temp"):   True,   # non-zero=hot, zero=cold
    #     ("bean",   "churro"): True,   # ASCII value

    #     ("drip",   "bean"):   True,   # decimal truncated
    #     ("drip",   "drip"):   True,
    #     ("drip",   "blend"):  False,
    #     ("drip",   "temp"):   True,   # non-zero=hot, zero=cold
    #     ("drip",   "churro"): False,

    #     ("blend",  "bean"):   False,
    #     ("blend",  "drip"):   False,
    #     ("blend",  "blend"):  True,
    #     ("blend",  "temp"):   False,
    #     ("blend",  "churro"): False,

    #     ("temp",   "bean"):   True,   # hot=1, cold=0
    #     ("temp",   "drip"):   True,   # hot=1.0, cold=0.0
    #     ("temp",   "blend"):  False,
    #     ("temp",   "temp"):   True,
    #     ("temp",   "churro"): False,

    #     ("churro", "bean"):   True,   # ASCII value
    #     ("churro", "drip"):   True,   # ASCII + .0
    #     ("churro", "blend"):  False,
    #     ("churro", "temp"):   True,   # non-zero=hot, zero=cold
    #     ("churro", "churro"): True,   # blend (ASCII addition)
    # }
    
    # Binary operator result types: (left_type, right_type) -> result_type
    BINARY_RESULT_TYPES = {
        # Arithmetic operators (bean and drip only, but must match)
        ("bean", "bean"): "bean",
        ("drip", "drip"): "drip",
        
        # Relational operators
        ("bean", "bean"): "temp",
        ("drip", "drip"): "temp",
        
        # For operations that mix types, result is most general
        ("bean", "blend"): "bean",
        ("blend", "bean"): "bean",
        ("drip", "blend"): "drip",
        ("blend", "drip"): "drip",
    }
    
    def __init__(self, ast):
        self.ast = ast
        self.symbol_table = SymbolTable()
        self.errors = []
        self.current_function = None
        self.current_class = None
        self.in_loop = False
        self.main_function_count = 0
        self.has_main = False
        self.current_var_type = None  # Track type of variable being declared
    
    def analyze(self, ast=None):
        """
        Main entry point for semantic analysis.
        
        Args:
            ast: The abstract syntax tree from the parser
            
        Returns:
            List of SemanticError objects converted to dictionaries
        """
        if ast:
            self.ast = ast
        
        if not self.ast:
            return []
        
        try:
            self._visit(self.ast)
            
            # Final checks
            if not self.has_main:
                self.errors.append(SemanticError(
                    "E007",
                    "Missing main function: program must have exactly one 'bean cup()' function",
                    severity="error"
                ))
            
            if self.main_function_count > 1:
                self.errors.append(SemanticError(
                    "E008",
                    f"Multiple main functions found: {self.main_function_count}. Only one 'bean cup()' is allowed",
                    severity="error"
                ))
        
        except Exception as e:
            # Silently skip analysis errors
            # print(f"[ANALYSIS CRASH] {e}")
            # traceback.print_exc()
            pass
        
        return [err.to_dict() for err in self.errors]
    
    def _visit(self, node):
        """Dispatch visitor based on node name."""
        if not self._is_parse_node(node):
            return None
        
        # for debugging purposes only.
        # print(f"[VISIT] {node.name} at scope depth {self.symbol_table.scope_level}") 


        method_name = f"_visit_{node.name}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(node)
        
        # Default: visit all children
        # print(f"[NO HANDLER] {node.name} has no visitor — falling through to children")
        self._visit_children(node)
        return None
    
    def _is_parse_node(self, node):
        """Check if node is a ParseNode."""
        return hasattr(node, 'name') and hasattr(node, 'children')
    
    # redundant
    # def _is_cast_compatible(self, source_type, target_type):
    #     """Check if source can be explicitly cast to target per Table 11."""
    #     print("[IS CAST COMPATIBLE DEBUG] f{self}")
    #     print("[IS CAST COMPATIBLE DEBUG] f{source_type}")
    #     print("[IS CAST COMPATIBLE DEBUG] f{target_type}")
    #     if not source_type or not target_type:
    #         return True  # unknown type, let it pass (wala pa masyadong strict dito haha)
    #     return self.TYPE_CAST_COMPAT.get((source_type, target_type), False)

    # def _visit_cast_expr(self, node):
    #     # Step 1: extract target type (the outer type, e.g. bean)
    #     target_type = self._extract_type_from_node(node)
    #     print("[VISIT CAST COMPATIBLE DEBUG] f{self}")
    #     print("[VISIT CAST COMPATIBLE DEBUG] f{node}")
    #     # Step 2: extract the expression being cast and infer its type
    #     source_type = self._infer_value_type(node)  # walk children to find type
    #     print("[VISIT CAST COMPATIBLE DEBUG] f{source_type}")
    #     # Step 3: check validity
    #     if source_type and target_type:
    #         if not self._is_cast_compatible(source_type, target_type):
    #             self._error(
    #                 "E004",
    #                 f"Invalid type cast: cannot cast '{source_type}' to '{target_type}'",
    #                 node
    #             )
    #     self._visit_children(node)

    def _visit_children(self, node):
        """Visit all children of a node."""
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                if self._is_parse_node(child):
                    self._visit(child)
    
    def _visit_start(self, node):
        """Visit start -> program"""
        self._visit_children(node)
    
    def _visit_program(self, node):
        """Visit program -> global_def main_def"""
        self._visit_children(node)
    
    def _visit_global_def(self, node):
        """Visit global_def for global declarations"""
        self._visit_children(node)
    
    def _visit_global_dec(self, node):
        """Visit global_dec"""
        self._visit_children(node)
    

    # Main function
    def _visit_main_def(self, node):
        """Visit main_def: bean cup() { body }"""
        self.main_function_count += 1
        self.has_main = True
        
        self.symbol_table.push_scope()
        prev_function = self.current_function
        self.current_function = "cup"
        
        self._visit_children(node)
        
        self.current_function = prev_function
        self.symbol_table.pop_scope()

    def _visit_main_body(self, node):
        print(f"[MAIN BODY DEBUG] children: {[c.name if hasattr(c, 'name') else f'{c.type}={c.value}' for c in node.children]}")
        self._visit_children(node)
    
    # Functions
    def _visit_recipe_def(self, node):
        """Visit recipe_def: recipe return_type ID (params) { body refill }"""
        # Extract function name and return type
        func_name = None

        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                func_name = child.value
                break 
        
        # func_name = self._extract_name_from_node(node, depth=3)
        return_type = self._extract_return_type(node)
        
            # DEBUG
        print(f"[RECIPE DEBUG] recipe_def: func_name='{func_name}' return_type='{return_type}'")
        print(f"[RECIPE DEBUG] recipe_def: scope_level before push = {self.symbol_table.scope_level}")
        print(f"[RECIPE DEBUG] recipe_def: \node children = \{[c.name if hasattr(c, 'name') else f'{c.type}={c.value}' for c in node.children]}")
        print(f"{return_type}")

        if func_name:
            symbol = Symbol(
                func_name,
                "function",
                dtype=return_type,
                scope_level=self.symbol_table.scope_level,
                return_type=return_type
            )
            
            if not self.symbol_table.declare(func_name, symbol):
                self.errors.append(SemanticError(
                    "E001",
                    f"Redefinition of function '{func_name}'",
                    line=getattr(node, 'line', None)
                ))
            
            # Enter function scope
            self.symbol_table.push_scope()
            prev_function = self.current_function
            self.current_function = func_name
            
            self._visit_children(node)
            
            self.current_function = prev_function
            self.symbol_table.pop_scope()
        else:
            self._visit_children(node)
    
    def _visit_empty_def(self, node):
        """Visit empty_def: empty ID (params) { body refill }"""
        func_name = self._extract_name_from_node(node, depth=2)
        
        if func_name:
            symbol = Symbol(
                func_name,
                "function",
                dtype=None,
                scope_level=self.symbol_table.scope_level,
                return_type="void"
            )
            
            if not self.symbol_table.declare(func_name, symbol):
                self.errors.append(SemanticError(
                    "E001",
                    f"Redefinition of function '{func_name}'",
                    line=getattr(node, 'line', None)
                ))
            
            self.symbol_table.push_scope()
            prev_function = self.current_function
            self.current_function = func_name
            
            self._visit_children(node)
            
            self.current_function = prev_function
            self.symbol_table.pop_scope()
        else:
            self._visit_children(node)
    
    # Classes
    def _visit_crema_def(self, node):
        """Visit crema_def: crema ID { body }"""
        class_name = self._extract_name_from_node(node, depth=2)
        
        if class_name:
            symbol = Symbol(
                class_name,
                "class",
                scope_level=self.symbol_table.scope_level
            )
            
            if not self.symbol_table.declare(class_name, symbol):
                self.errors.append(SemanticError(
                    "E001",
                    f"Redefinition of class '{class_name}'",
                    line=getattr(node, 'line', None)
                ))
            
            self.symbol_table.push_scope()
            prev_class = self.current_class
            self.current_class = class_name
            
            self._visit_children(node)
            
            self.current_class = prev_class
            self.symbol_table.pop_scope()
        else:
            self._visit_children(node) 

    # Mug/Datatype/Undeclared checks
    def _visit_mug_dec(self, node):
        """Visit mug_dec: mug ID [var_list]"""
        struct_name = self._extract_name_from_node(node, depth=2)
        
        if struct_name:
            symbol = Symbol(
                struct_name,
                "struct",
                scope_level=self.symbol_table.scope_level
            )
            
            if not self.symbol_table.declare(struct_name, symbol):
                self.errors.append(SemanticError(
                    "E001",
                    f"Redefinition of struct '{struct_name}'",
                    line=getattr(node, 'line', None)
                ))
        
        self._visit_children(node)
    
    def _visit_dtype_dec(self, node):
        dtype = self._extract_type_from_node(node)

        print(f"[_visit_dtype_dec] dtype={dtype}, node={node.name}") 
        if not dtype:
            self._visit_children(node)
            return

        self.current_var_type = dtype

        # Pass 1: check if brewed appears anywhere in children BEFORE finding the ID
        is_constant = False
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "BREWED":
                print(f"[DEBUG] brewed spotted")
                is_constant = True
                break
            if self._is_parse_node(child) and child.name in ("dtype_brewed_body", "acc_brewed_body"):
                is_constant = True
                break

        # Pass 2: find the ID and declare it with the correct is_constant value
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                print(f"[DEBUG] Declaring '{child.value}' dtype='{dtype}' is_constant={is_constant} at scope_level={self.symbol_table.scope_level}")
                
                sym = Symbol(
                    child.value, "variable",
                    dtype=dtype,
                    is_constant=is_constant,
                    scope_level=self.symbol_table.scope_level,
                    line=getattr(child, 'line', None)
                )
                if not self.symbol_table.declare(child.value, sym):
                    self._error("E001", f"Redefinition of identifier '{child.value}'", child)
                break

        self._visit_children(node)
        self.current_var_type = None

    def _visit_primary(self, node):
        """Visit primary: check for undeclared variables.
        FIX: Check token leaves with type=='ID' directly instead of checking
        for parse nodes named 'ID'. The old approach caused _extract_token_value
        to grab the first child of a parse node (e.g. '=') instead of the
        actual identifier, producing false 'Undeclared identifier' errors.
        """
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                var_name = child.value
                if var_name and not self.symbol_table.lookup(var_name):
                    self._error("E002", f"Undeclared identifier '{var_name}'", child)
        self._visit_children(node)
    
    # Statements
    def _visit_pour_loop(self, node):
        """Visit pour_loop: for loop"""
        self.symbol_table.push_scope()
        prev_loop = self.in_loop
        self.in_loop = True
        
        # self._visit_children(node) 

        if hasattr(node, 'children'): 
            for child in node.children: 
                if self._is_parse_node(child): 
                    self._visit(child)

        self.in_loop = prev_loop
        self.symbol_table.pop_scope()

    def _visit_pour_init(self, node):
        """Visit pour_init: bean m = 1"""
        # Extract the data type
        dtype = None
        var_name = None
        
        for child in node.children:
            if self._is_parse_node(child) and child.name == "data_type":
                dtype = self._extract_type_from_node(child)
            elif not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                var_name = child.value
        
        if dtype and var_name:
            print(f"[_visit_pour_init] DECLARING '{var_name}' as {dtype}")
            sym = Symbol(
                var_name, "variable",
                dtype=dtype,
                scope_level=self.symbol_table.scope_level
            )
            if not self.symbol_table.declare(var_name, sym):
                self._error("E001", f"Redefinition of identifier '{var_name}'", node)
        
        self._visit_children(node)
    
    def _visit_whilehot_loop(self, node):
        """Visit whilehot_loop: while loop"""
        self.symbol_table.push_scope()
        prev_loop = self.in_loop
        self.in_loop = True
        
        self._visit_children(node)
        
        self.in_loop = prev_loop
        self.symbol_table.pop_scope()
    
    def _visit_tastetill_loop(self, node):
        """Visit tastetill_loop: do-while loop"""
        self.symbol_table.push_scope()
        prev_loop = self.in_loop
        self.in_loop = True
        
        self._visit_children(node)
        
        self.in_loop = prev_loop
        self.symbol_table.pop_scope()
    
    def _visit_intrpt_stmt(self, node):
        """Visit interrupt statement: snap/skip"""
        if not self.in_loop:
            stmt_type = None
            if node.children:
                first_child = node.children[0]
                if self._is_parse_node(first_child):
                    stmt_type = first_child.name
                elif hasattr(first_child, 'type'):
                    stmt_type = first_child.type
            

        if stmt_type in ("SNAP", "SKIP"):
            err_line = getattr(node, 'line', None) or getattr(first_child, 'line', None)
            err_col = getattr(node, 'column', None) or getattr(first_child, 'column', None)
            self.errors.append(SemanticError(
                "E006",
                f"'{stmt_type.lower()}' statement outside of loop",
                line=err_line,
                column=err_col
            ))

    def _visit_if_cond(self, node):
        """Visit if condition: create block scope"""
        self.symbol_table.push_scope()
        self._visit_children(node)
        self.symbol_table.pop_scope()
    
    def _visit_flav_switch(self, node):
        """Visit switch statement: create block scope"""
        self.symbol_table.push_scope()
        self._visit_children(node)
        self.symbol_table.pop_scope()
    
    # ID stuff
    def _visit_id_dec_stmt(self, node):
        """Visit id_dec_stmt: ID = value
        
        FIX: Scan for the ID token leaf directly so we get real line/col.
        """
        var_name = None
        id_token = None
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                var_name = child.value
                id_token = child
                break

        if var_name:
            symbol = self.symbol_table.lookup(var_name)
            # print(f"[ID_DEC_STMT DEBUG] var={var_name} symbol={symbol} is_constant={getattr(symbol, 'is_constant', None)}")
            if not symbol:
                self._error("E002", f"Undeclared identifier '{var_name}'", id_token)
            elif symbol.is_constant:
                self._error("E005", f"Cannot modify constant identifier '{var_name}'", id_token)
        self._visit_children(node)
    
    def _visit_update_id(self, node):
        """Visit update_id: ID assignment"""
        var_name = self._extract_name_from_node(node, depth=0)
        
        if var_name:
            symbol = self.symbol_table.lookup(var_name)
            if not symbol:
                self.errors.append(SemanticError(
                    "E002",
                    f"Undeclared identifier '{var_name}'",
                    line=getattr(node, 'line', None)
                ))
            elif symbol.is_constant:
                self.errors.append(SemanticError(
                    "E005",
                    f"Cannot modify constant identifier '{var_name}'",
                    line=getattr(node, 'line', None)
                ))
            else:
                # Check type compatibility of assignment
                self._check_assignment_type(var_name, symbol, node)
        
        self._visit_children(node)
    
    # Variables declarations
    def _visit_var_dec_init(self, node):
        """Visit var_dec_init: ID opt_assign in a comma-separated list"""
        # Extract the ID from this node
        var_name = None
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                var_name = child.value
                break
        
        if var_name and self.current_var_type:
            print(f"[_visit_var_dec_init] DECLARING '{var_name}' as {self.current_var_type}")
            sym = Symbol(
                var_name, "variable",
                dtype=self.current_var_type,
                scope_level=self.symbol_table.scope_level,
                line=getattr(child, 'line', None) if child else None
            )
            if not self.symbol_table.declare(var_name, sym):
                self._error("E001", f"Redefinition of identifier '{var_name}'", child)
        
        self._visit_children(node)

    def _visit_var_dec_const_init(self, node):
        """Visit variable declaration with initialization"""
        if self.current_var_type:
            var_name = self._extract_var_name(node)
            print(f"[CONST INIT DEBUG] var={var_name} dtype={self.current_var_type} is_constant=True")

            if var_name:
                symbol = Symbol(
                    var_name,
                    "variable",
                    dtype=self.current_var_type,
                    is_constant=True,  # BREWED = constant
                    scope_level=self.symbol_table.scope_level,
                    line=getattr(node, 'line', None),
                    # is_initialized=True
                )
                
                if not self.symbol_table.declare(var_name, symbol):
                    self.errors.append(SemanticError(
                        "E001",
                        f"Redefinition of identifier '{var_name}'",
                        line=getattr(node, 'line', None)
                    ))
                else:
                    # Check initialization type
                    self._check_assignment_type(var_name, symbol, node)
        
        print(f"[CONST INIT DEBUG] children: {[c.name if hasattr(c, 'name') else f'{c.type}={c.value}' for c in node.children]}")
        self._visit_children(node)
        print(f"[CONST INIT DEBUG] done visiting children")
    
    def _visit_opt_assign(self, node):
        # Only check if we're inside a declaration (current_var_type is set)
        if self.current_var_type:
            # Infer the type of the RHS value
            rhs_type = self._infer_value_type(node)
            print(f"[OPT ASSIGN DEBUG] opt_assign: declared={self.current_var_type}, rhs={rhs_type}")

            if rhs_type and rhs_type != self.current_var_type:
                # Check if it's a valid implicit cast per TYPE_COMPAT
                if not self._is_type_compatible(self.current_var_type, rhs_type):
                    self._error(
                        "E003",
                        f"Type mismatch: cannot assign '{rhs_type}' value to "
                        f"'{self.current_var_type}' variable",
                        node
                    )

        self._visit_children(node)

    def _visit_var_dec_tail(self, node):
        """Visit variable declaration tail.
        FIX: Only match actual ID token leaves, not parse nodes.
        """
        if self.current_var_type and hasattr(node, 'children'):
            for child in node.children:
                if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                    var_name = child.value
                    if var_name:
                        symbol = Symbol(var_name, "variable", dtype=self.current_var_type,
                                        scope_level=self.symbol_table.scope_level,
                                        line=getattr(child, 'line', None))
                        if not self.symbol_table.declare(var_name, symbol):
                            self._error("E001", f"Redefinition of identifier '{var_name}'", child)
        self._visit_children(node)
    
    def _visit_acc_mod_dec_body(self, node):
        """Visit access modifier declaration body"""
        dtype = self._extract_type_from_node(node)
        if dtype:
            self.current_var_type = dtype
        
        self._visit_children(node)
        self.current_var_type = None
    
    def _visit_dtype_brewed_body(self, node):
        """Visit data type brewed (constant) body"""
        dtype = self._extract_type_from_node(node)
        if dtype:
            self.current_var_type = dtype
        
        self._visit_children(node)
        self.current_var_type = None
    
    def _visit_blend_id_tail(self, node):
        """Visit blend variable declaration"""
        var_name = self._extract_name_from_node(node, depth=0)
        if var_name:
            symbol = Symbol(
                var_name,
                "variable",
                dtype="blend",
                scope_level=self.symbol_table.scope_level,
                line=getattr(node, 'line', None)
            )
            
            if not self.symbol_table.declare(var_name, symbol):
                self.errors.append(SemanticError(
                    "E001",
                    f"Redefinition of identifier '{var_name}'",
                    line=getattr(node, 'line', None)
                ))
        
        self._visit_children(node)
    
    def _visit_order_dec_stmt(self, node):
        """Visit array declaration"""
        self._visit_children(node)
    
    # TYPE CHECKING METHODS
    def _infer_type_from_literal(self, token_type):
        """Infer CARAMEL type from token type."""
        if token_type == "BEANLIT":
            return "bean"
        elif token_type == "DRIPLIT":
            return "drip"
        elif token_type == "CHURROLIT":
            return "churro"
        elif token_type in ("HOT", "COLD"):
            return "temp"
        elif token_type == "BLENDLIT":
            return "blend"
        return None
    
    def _infer_value_type(self, node):
        """Infer the type of a value/expression."""
        if not self._is_parse_node(node):
            # Token node - check token type
            if hasattr(node, 'type'):
                return self._infer_type_from_literal(node.type)
            return None
        
        # Check node type
        if node.name == "primary":
            return self._infer_primary_type(node)
        elif node.name == "expression":
            print("expression hit")
            return self._infer_expression_type(node)
        elif node.name == "assign_val":
            return self._infer_expression_type(node)
        elif node.name == "value":
            return self._infer_value_type_from_children(node)
        
        # Try to infer from children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                inferred = self._infer_value_type(child)
                if inferred:
                    return inferred
        
        return None
    
    def _infer_primary_type(self, node):
        """Infer type of primary expression."""
        if not hasattr(node, 'children') or not node.children:
            return None
        
        for child in node.children:
            if not self._is_parse_node(child):
                if hasattr(child, 'type'):
                    return self._infer_type_from_literal(child.type)
            elif child.name == "ID":
                var_name = self._extract_token_value(child)
                if var_name:
                    symbol = self.symbol_table.lookup(var_name)
                    if symbol:
                        return symbol.dtype
        
        return None
    
    def _infer_expression_type(self, node):
        """Infer type of expression (may have binary operators)."""
        if not hasattr(node, 'children') or not node.children:
            return None
        
        # Simplified: just check first operand type for now
        for child in node.children:
            inferred = self._infer_value_type(child)
            if inferred:
                return inferred
        
        return None
    
    def _infer_value_type_from_children(self, node):
        """Infer value type from children."""
        if not hasattr(node, 'children') or not node.children:
            return None
        
        for child in node.children:
            inferred = self._infer_value_type(child)
            if inferred:
                return inferred
        
        return None
    
    def _check_assignment_type(self, var_name, symbol, node):
        """Check type compatibility of assignment to a variable."""
        if not symbol or not symbol.dtype:
            return
        
        # Find the RHS value in the node
        rhs_type = self._extract_rhs_type(node)
        if not rhs_type:
            return
        
        # Check compatibility
        if not self._is_type_compatible(symbol.dtype, rhs_type):
            self._error("E003", f"Type mismatch: cannot assign '{rhs_type}' to '{symbol.dtype}' variable '{var_name}'", node)
    
    def _extract_rhs_type(self, node):
        """Extract RHS type from assignment node."""
        if not hasattr(node, 'children'):
            return None
        
        # Look for value/assign_val/expression nodes
        for i, child in enumerate(node.children):
            if self._is_parse_node(child):
                if child.name in ("value", "assign_val", "expression", "assign_value"):
                    return self._infer_value_type(child)
            else:
                # Token - check for literal
                if hasattr(child, 'type'):
                    inferred = self._infer_type_from_literal(child.type)
                    if inferred:
                        return inferred
        
        return None
    
    def _is_type_compatible(self, target_type, source_type):
        """Check if source_type can be assigned to target_type."""
        if target_type not in self.TYPE_COMPAT:
            return True  # Unknown type, allow it
        
        return source_type in self.TYPE_COMPAT[target_type]
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_type_from_node(self, node):
        """Extract data type (bean, drip, etc.) from a node."""
        if not hasattr(node, 'children'):
            return None
        
        for child in node.children:
            if self._is_parse_node(child):
                if child.name == "data_type":
                    return self._extract_data_type_value(child)
                inferred = self._extract_type_from_node(child)
                if inferred:
                    return inferred
            elif hasattr(child, 'type'):
                dtype_map = {
                    "BEAN": "bean",
                    "DRIP": "drip",
                    "CHURRO": "churro",
                    "TEMP": "temp",
                    "BLEND": "blend",
                    "MUG": "mug"
                }
                if child.type in dtype_map:
                    return dtype_map[child.type]
        
        return None
    
    def _extract_data_type_value(self, node):
        """Extract type from data_type node."""
        if not hasattr(node, 'children'):
            return None
        
        for child in node.children:
            if not self._is_parse_node(child):
                if hasattr(child, 'type'):
                    dtype_map = {
                        "BEAN": "bean",
                        "DRIP": "drip",
                        "CHURRO": "churro",
                        "TEMP": "temp",
                        "BLEND": "blend"
                    }
                    return dtype_map.get(child.type)
        
        return None
    
    def _extract_var_name(self, node):
        """Extract variable name from declaration node."""
        if not hasattr(node, 'children'):
            return None
        
        for child in node.children:
            if self._is_parse_node(child) and child.name == "ID":
                return self._extract_token_value(child)
            token_val = self._extract_token_value(child)
            if token_val and hasattr(child, 'type') and child.type == "ID":
                return token_val
        
        return None
    
    def _extract_name_from_node(self, node, depth=3):
        """Extract identifier name from a node at given depth."""
        if not hasattr(node, 'children') or not node.children:
            return None
        
        idx = 0
        for child in node.children:
            if self._is_parse_node(child):
                if idx == depth:
                    return self._extract_token_value(child)
                idx += 1
        
        return None
    
    def _extract_token_value(self, node):
        """Extract token value from a node."""
        if not self._is_parse_node(node):
            if hasattr(node, 'value'):
                return node.value
            return None
        
        if node.children:
            for child in node.children:
                if hasattr(child, 'value'):
                    return child.value
        
        return None
    
    def _extract_return_type(self, node):
        """Extract return type from a recipe node."""
        if not hasattr(node, 'children'):
            return None
        
        for child in node.children:
            if self._is_parse_node(child) and child.name == "recipe_ret_type":
                if child.children:
                    first = child.children[0]
                    if self._is_parse_node(first):
                        name = first.name.lower()
                        if name in self.VALID_TYPES:
                            return name
                    elif hasattr(first, 'type') and first.type == "BLEND":
                        return "blend"
        
        return None
    
    def _find_token_location(self, node, _depth=0):
        """
        Recursively walk the node tree to find the first token leaf
        that carries line/column information.
        Only token (leaf) nodes have .line/.column — parse nodes never do.
        Depth-limited to 10 to avoid runaway recursion on malformed trees.
        """
        if _depth > 10:
            return None, None
        # Leaf token — check directly
        if not self._is_parse_node(node):
            line = getattr(node, 'line', None)
            col  = getattr(node, 'column', None)
            if line is not None:
                return line, col
            return None, None
        # Parse node — recurse into children
        if hasattr(node, 'children'):
            for child in node.children:
                line, col = self._find_token_location(child, _depth + 1)
                if line is not None:
                    return line, col
        return None, None

    def _error(self, code, message, node=None):
        """
        Record a semantic error.
        Always routes through _find_token_location so line/column are resolved
        by walking down to the first token leaf. Parse nodes never carry
        location info directly — only token leaves do.
        """
        line, column = None, None
        if node is not None:
            line, column = self._find_token_location(node)
        self.errors.append(SemanticError(code, message, line, column))

def run_semantic_analysis(ast):
    """
    Entry point function for semantic analysis.
    Args: Abstract syntax tree from parser (ast)    
    Returns: List of semantic error dictionaries
    """
    analyzer = SemanticAnalyzer(ast)
    return analyzer.analyze()
