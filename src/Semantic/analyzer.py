"""
Semantic Analyzer Module for CARAMEL Language

Based on semantic rules from the CARAMEL specification document.
This module implements semantic analysis completely separate from the parser,
analyzing the AST for semantic correctness after successful parsing.

"""
from src.Lexer.lexer import token_final_out
from src.Parser.parser import Parser
# import traceback

class SemanticError:
    """ Represents a semantic error in the code.
        Given the __init__ where it throws errors
        The to_dict converts it so that it can send to the frontend
    """
    
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
    """ Represents a symbol (an entry) in the symbol table.
        kind = represents a symbol whether it a variable, function, or class in the program
        is_constant = if it is true, then it is brewed (constant)
        is_array = if it is true, then it is an array type
        is_initialized = only set true for function parameters
        """
    
    def __init__(self, name, kind, dtype=None, is_constant=False, scope_level=0, 
                 line=None, column=None, parameters=None, return_type=None, is_array=False):
        self.name = name
        self.kind = kind  # "variable", "function", "class"
        self.dtype = dtype  # "bean", "drip", "churro", "temp", "blend", None
        self.is_constant = is_constant # True if declared with brewed
        self.is_array = is_array  # True if this is an array type
        self.scope_level = scope_level # determines whether it is within the global or local body scope
        self.line = line
        self.column = column
        self.parameters = parameters or []  # List of (name, type) tuples for functions
        self.return_type = return_type  # For functions
        self.is_initialized = False

class SymbolTable:
    """ Manages symbol scopes and symbol tracking. This can be implemented via: 
        Each scope level has its own dictionary. Everytime we enter a statement block (e.g., conditionals and looping statements),
        it creates a new dictionary. When it is left, it will be popped and all variables declared inside go out of scope.
        
        Example:
        scopes[0] = {global variables, functions, classes}
        scopes[1] = {cup(), local variables}
        scopes[2] = {looping initialization variables i and j}
        scopes[3] = {nested ifbrew block variables}
    """
    
    def __init__(self):
        self.scopes = [{}]      # Stack of scope dictionaries where the scope level is stored
        self.scope_level = 0    # Start at scope level 0
        self.errors = []        # Capture for any errors if there are any
    
    def push_scope(self):
        """Called on entering a new scope."""
        self.scopes.append({})  # Appends the scopes level array 
        self.scope_level += 1   # Scopes array size + 1
    
    def pop_scope(self):
        """Called on exiting the current scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
            self.scope_level -= 1
    
    def declare(self, name, symbol):
        """
        Declare a symbol in current scope.
        Returns True if successful, False if already declared in this scope.
        """
        if name in self.scopes[-1]:
            return False
        self.scopes[-1][name] = symbol
        return True

    def lookup(self, name):
        """ Look up a symbol in current and parent scopes.
            Walks from innermost to global, enables variable shadowing. """
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None
    
    def lookup_current(self, name):
        """Look up a symbol in current scope only. This is used to detect for any redeclaration of a variable."""
        return self.scopes[-1].get(name)
    
    def update_symbol(self, name, symbol):
        """Walks all scopes to find and update an existing symbol."""
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
    VALID_TYPES = {"bean", "drip", "churro", "temp", "blend"}
    # Built-in functions
    RESERVED_BUILTINS = {"sift", "ceil", "floor", "pow", "rand", "sqrt", "type"}

    # Type compatibility for assignments: target_type to set of compatible source types
    # STRICT: bean != drip without explicit cast
    TYPE_COMPAT = {
        "bean":   {"bean", "drip", "temp", "churro"},           # bean can go into drip, temp, churro
        "drip":   {"drip", "bean", "temp"},                     # drip can go into bean, temp
        "churro": {"churro", "bean", "drip", "temp", "blend"},  # churro accepts string literals (blend) / can go into bean, drip, temp, blend
        "temp":   {"temp", "bean", "drip"},                     # temp can go into bean, drip
        "blend":  {"blend", "churro"},                          # blend only into blend, also churro maybe?
    }
    
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
    
    """ __init__ state:
        symbol_table = scope stack, starts with the global scope 
        current_function = name of the function being analyzed (None at global level)
        current_class = name of the class being analyzed (None if not in class)
        in_loop = true if it is inside pour/whiltehot/taste-till, validation for snap/skip
        main_function_count = counts bean cup() declarations, strictly only one main function must exist
        current_var_type = set during dtype_dec to know what type to assign to each ID they find
    """
    
    
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
        def analyze() - Main entry point for semantic analysis.
        
        Args:
            ast: The abstract syntax tree from the parser
        
        _visit(ast):
            recursively walks every ParseNode, After walking the ast, it will check E007 (no cup) and E008 (multiple cups)

        Returns:
            List of SemanticError objects converted to dictionaries
        """
        if ast:
            self.ast = ast
        
        if not self.ast:
            return []
        
        try:
            self._visit(self.ast)
            
            # Final checks - This is where E007 is being checked
            if not self.has_main:
                self.errors.append(SemanticError(
                    "E007",
                    "Missing main function: program must have exactly one 'bean cup()' function",
                    severity="error"
                ))
            
            # Final checks - This is where E008 is being checked
            if self.main_function_count > 1:
                self.errors.append(SemanticError(
                    "E008",
                    f"Multiple main functions found: {self.main_function_count}. Only one 'bean cup()' is allowed",
                    severity="error"
                ))
        
        # This is where it prevents the semantic analyzer from crashing out. It blocks the compilation entirely as errors are printed.
        except Exception as e:
            # Silently skip analysis errors
            print(f"[SEMANTIC ANALYSIS CRASH] {e}")
            import traceback
            traceback.print_exc()
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
        self.has_main = True    # Checks if a cup() is found
        
        self.symbol_table.push_scope() # local scope within cup() is established
        prev_function = self.current_function
        self.current_function = "cup"   # current function is "cup"
        
        self._visit_children(node)
        
        self.current_function = prev_function
        self.symbol_table.pop_scope()

    def _visit_main_body(self, node):
        # print(f"[SEMANTIC MAIN BODY DEBUG] children: {[c.name if hasattr(c, 'name') else f'{c.type}={c.value}' for c in node.children]}")
        self._visit_children(node)
    
    """"Functions: _visit_recipe_def
        How does it work?
        1. Extract function name from ID token 
        2. Check name if it isn't a reserved built-in or throw E_RES_FUNC error
        3. Extract return type from recipe_ret_type
        4. Declare symbol(kind = "function", return_Type = "...") in CURRENT scope
        5. push_scope will enter the function's own scope
        6. Register each parameter as a symbol with is_intialized = True
        7. visit body (Recursive walk)
        8. pop_scope() -> all locals and params go out of scope
    """
    def _visit_recipe_def(self, node):
        """Visit recipe_def: recipe return_type ID (params) { body refill }"""
        # debug
        # print(f"[RECIPE DEBUG] node children: {[(c.name if hasattr(c, 'name') else f'TOKEN type={c.type} val={c.value}') for c in node.children]}")
        func_name = None
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                func_name = child.value
                break

        return_type = self._extract_return_type(node)

        if func_name:
            if func_name in self.RESERVED_BUILTINS:
                self._error("E_RES_FUNC", f"{func_name} is a reserved built-in and cannot be used as a function name", f"{func_name}")  # Throws an error if it is a built-in and is a function name
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

            # Enter function scope and register parameters before visiting body
            self.symbol_table.push_scope()
            prev_function = self.current_function
            self.current_function = func_name
            
            # debug
            # print(f"[RECIPE '{func_name}'] all children: {[c.name if hasattr(c, 'name') else f'TOKEN:{c.type}' for c in node.children]}")
            for child in node.children:
                if self._is_parse_node(child) and child.name == "parameter":
                    print(f"[RECIPE '{func_name}'] parameter node children: {[c.name if hasattr(c, 'name') else f'{c.type}={c.value}' for c in child.children]}")
                    for param_name, param_type in self._extract_parameters(child):
                        param_symbol = Symbol(
                            param_name,
                            "variable",
                            dtype=param_type,
                            scope_level=self.symbol_table.scope_level,
                        )
                        param_symbol.is_initialized = True
                        self.symbol_table.declare(param_name, param_symbol)
                    break
            
            #debug
            # print(f"[RECIPE '{func_name}'] scope before visit_children: {list(self.symbol_table.scopes[-1].keys())}")
            self._visit_children(node)

            self.current_function = prev_function
            self.symbol_table.pop_scope()
        else:
            # debug
            # print(f"[RECIPE '{func_name}'] scope before visit_children: {list(self.symbol_table.scopes[-1].keys())}")
            self._visit_children(node)

    # pre-defined functions   
    def _visit_sift_arg(self, node):
        """sift argument must be blend type or a recipe returning blend."""
        for child in node.children:
            if not self._is_parse_node(child):
                continue
            inferred = self._infer_value_type(child)
            if inferred is not None and inferred != "blend":
                self._error(
                    "E_SIFT",
                    f"'sift' requires a blend argument but got '{inferred}'",
                    child
                )

    def _visit_sqrt_arg(self, node):
        """sqrt(expr) — arg must be bean or drip, returns drip."""
        for child in node.children:
            if not self._is_parse_node(child): continue
            inferred = self._infer_value_type(child)
            if inferred is not None and inferred not in ("bean", "drip"):
                self._error("E_BUILTIN", f"'sqrt' requires a numeric argument but got '{inferred}'", child)

    def _visit_ceil_arg(self, node):
        """ceil(expr) — arg must be bean or drip, returns bean."""
        for child in node.children:
            if not self._is_parse_node(child): continue
            inferred = self._infer_value_type(child)
            if inferred is not None and inferred not in ("bean", "drip"):
                self._error("E_BUILTIN", f"'ceil' requires a numeric argument but got '{inferred}'", child)

    def _visit_floor_arg(self, node):
        """floor(expr) — arg must be bean or drip, returns bean."""
        for child in node.children:
            if not self._is_parse_node(child): continue
            inferred = self._infer_value_type(child)
            if inferred is not None and inferred not in ("bean", "drip"):
                self._error("E_BUILTIN", f"'floor' requires a numeric argument but got '{inferred}'", child)

    def _visit_pow_arg(self, node):
        """pow(base, exp) — both must be bean or drip, returns drip."""
        exprs = [c for c in node.children if self._is_parse_node(c) and c.name == "expression"]
        for expr in exprs:
            inferred = self._infer_value_type(expr)
            if inferred is not None and inferred not in ("bean", "drip"):
                self._error("E_BUILTIN", f"'pow' requires numeric arguments but got '{inferred}'", expr)

    def _visit_rand_arg(self, node):
        """rand(a, b) — both must be bean or drip, returns bean or drip."""
        exprs = [c for c in node.children if self._is_parse_node(c) and c.name == "expression"]
        for expr in exprs:
            inferred = self._infer_value_type(expr)
            if inferred is not None and inferred not in ("bean", "drip"):
                self._error("E_BUILTIN", f"'rand' requires numeric arguments but got '{inferred}'", expr)

    def _visit_type_arg(self, node):
        """type(expr) — accepts any type, returns blend."""
        pass  # no type restriction — accepts anything
        
    def _extract_parameters(self, param_node):
        """Extract list of (name, type) tuples from a parameter AST node."""
        params = []
        # debug
        # print(f"[EXTRACT_PARAMS] children: {[c.name if hasattr(c, 'name') else f'TOKEN:{c.type}' for c in (param_node.children or [])]}")
        for child in (param_node.children or []):
            if not self._is_parse_node(child):
                continue
            if child.name == "dtype_param":
                p = self._extract_one_param(child)
                if p:
                    params.append(p)
            elif child.name == "add_param":
                for c in (child.children or []):
                    if self._is_parse_node(c) and c.name == "dtype_param":
                        p = self._extract_one_param(c)
                        if p:
                            params.append(p)
        return params

    def _extract_one_param(self, dtype_param_node):
        """Extract (name, type) from a single dtype_param node."""
        # debug
        # print(f"[EXTRACT_ONE_PARAM] children: {[c.name if hasattr(c, 'name') else f'TOKEN:{c.type}={c.value}' for c in (dtype_param_node.children or [])]}")
        param_type = None
        param_name = None
        for child in (dtype_param_node.children or []):
            if self._is_parse_node(child) and child.name == "data_type":
                for tc in (child.children or []):
                    if not self._is_parse_node(tc) and hasattr(tc, 'type'):
                        param_type = tc.type.lower()
                        break
            elif self._is_parse_node(child) and child.name == "var_dec_init":
                for tc in (child.children or []):
                    if not self._is_parse_node(tc) and hasattr(tc, 'type') and tc.type == "ID":
                        param_name = tc.value
                        break
        if param_name and param_type:
            return (param_name, param_type)
        return None
    
    def _visit_empty_def(self, node):
        """ Visit empty_def: empty ID (params) { body refill }
            Similarly how it is to functions.
            dtype = None, return_type = "void", kind = "function" is_initialized = true
            """
        func_name = None
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                func_name = child.value
                break

        if func_name:
            if func_name in self.RESERVED_BUILTINS:
                self._error("E_RES_FUNC", f"{func_name} is a reserved built-in and cannot be used as a function name", f"{func_name}")

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

            # Register parameters before visiting body
            for child in node.children:
                if self._is_parse_node(child) and child.name == "parameter":
                    for param_name, param_type in self._extract_parameters(child):
                        param_symbol = Symbol(
                            param_name, "variable",
                            dtype=param_type,
                            scope_level=self.symbol_table.scope_level,
                        )
                        param_symbol.is_initialized = True
                        self.symbol_table.declare(param_name, param_symbol)
                    break

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
    
    """ _visit_dtype_dec -> handles all typed variable declarations. This has the following passes:
    Pass 1: If brewed appears anywhere in children before finding the ID -> set is_constant = True
    Pass 2: If ID is found, declare symbol in symbol table. It also does the following for arrays:
        - also detects array size [size] or [***] and it will proceed to go to bounds checking
        - array size = [***] -> no bounds chcecking
        - array size = N -> initializer must not exceed [size]
        
    Pass 3: Shadowing check - checks if it has the same name in the local scope. 
    """
    
    
    def _visit_dtype_dec(self, node):
        dtype = self._extract_type_from_node(node)

        # print(f"[SEMANTIC _visit_dtype_dec] dtype={dtype}, node={node.name}") 
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

        # Pass 2: find the ID and declare it; also detect arrays and check bounds.
        id_token = None
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                id_token = child
                break

        if id_token:
            # Detect array declaration and collect size + initializer count
            is_array = False
            is_2d = False
            arr_size = None
            arr_init_count = None
            arr_size_token = None
            for child in node.children:
                if not (self._is_parse_node(child) and child.name == "dtype_id_tail"):
                    continue
                for tc in child.children:
                    if self._is_parse_node(tc) and tc.name == "arr_size_val":
                        for sc in tc.children:
                            if not self._is_parse_node(sc) and hasattr(sc, 'type'):
                                if sc.type == "BEANLIT":
                                    arr_size = int(sc.value)
                                    arr_size_token = sc
                                elif sc.type == "FLEX_ASTERISK":
                                    arr_size = "***"
                                elif sc.type == "ID":
                                    sym = self.symbol_table.lookup(sc.value) # lookup if the id is in the symbol table
                                    if sym is None:
                                        self._error(
                                            "E_ARR_SIZE",
                                            f"Undeclared identifier '{sc.value}' used as array size", # Throws an error if the variable used inside the array size is undeclared
                                            sc
                                        )
                                    elif sym.dtype not in ("bean",):
                                        self._error(
                                            "E_ARR_SIZE",
                                            f"Array size must be a whole number (bean), got '{sym.dtype}' for '{sc.value}'", # If the array size is non-beanlit (driplit), it will throw an error.
                                            sc
                                        )
                                    else:
                                        arr_size = sc.value  # valid bean variable
                    
                    if (self._is_parse_node(tc) and tc.name == "OP_BRACKETS") or \
                       (not self._is_parse_node(tc) and hasattr(tc, 'type') and tc.type == "OP_BRACKETS"):
                        is_array = True
                    if self._is_parse_node(tc) and tc.name == "arr_size_val":
                        for sc in tc.children:
                            if not self._is_parse_node(sc) and hasattr(sc, 'type') and sc.type == "BEANLIT":
                                arr_size = int(sc.value)
                                arr_size_token = sc
                    if self._is_parse_node(tc) and tc.name == "arr_dec_dim":
                        
                        # Detect 2D: arr_dec_dim starts with OP_BRACKETS + arr_size_val
                        col_size = None
                        is_2d = False
                        for i, dc in enumerate(tc.children):
                            if i == 0 and (
                                (self._is_parse_node(dc) and dc.name == "OP_BRACKETS") or
                                (not self._is_parse_node(dc) and hasattr(dc, 'type') and dc.type == "OP_BRACKETS")
                            ):
                                if len(tc.children) > 1 and self._is_parse_node(tc.children[1]) and tc.children[1].name == "arr_size_val":
                                    is_2d = True
                            if self._is_parse_node(dc) and dc.name == "arr_size_val":
                                for sc in dc.children:
                                    if not self._is_parse_node(sc) and hasattr(sc, 'type') and sc.type == "BEANLIT":
                                        col_size = int(sc.value)
                            if self._is_parse_node(dc) and dc.name == "arr_cont_1d":
                                arr_init_count = self._count_arr_elements_1d(dc)
                                self._check_arr_element_types(dc, dtype, id_token)

                            elif self._is_parse_node(dc) and dc.name == "arr_cont_2d":
                                if is_2d and col_size is not None and arr_size is not None:
                                    # Check row count and each row's element count separately
                                    arr_init_count = self._check_arr_2d_bounds(
                                        dc, arr_size, col_size, id_token, dtype
                                    )
                                else:
                                    arr_init_count = self._count_arr_elements_2d(dc)

            # print(f"[SEMANTIC ID STATE DEBUG] Declaring '{id_token.value}' dtype='{dtype}' is_constant={is_constant} is_array={is_array} at scope_level={self.symbol_table.scope_level}")

            sym = Symbol(
                id_token.value, "variable",
                dtype=dtype,
                is_constant=is_constant,
                is_array=is_array,
                scope_level=self.symbol_table.scope_level,
                line=getattr(id_token, 'line', None)
            )
            if not self.symbol_table.declare(id_token.value, sym):
                self._error("E001", f"Redefinition of identifier '{id_token.value}'", id_token)

            # print(f"[SEMANTIC ARR_DEBUG] arr_size={arr_size} arr_init_count={arr_init_count} is_array={is_array} is_2d={is_2d}")
            # Bounds check: initializer count must not exceed declared size
            if is_array and arr_size is not None and arr_init_count is not None:
                if is_array and arr_size is not None and arr_init_count is not None:
                    if arr_size != "***" and not is_2d and arr_init_count > arr_size:
                        print(not is_2d and arr_init_count > arr_size)
                        if not is_2d and arr_init_count > arr_size: 
                            # print(f"[SEMANTIC ARR_DEBUG] arr_size={arr_size} arr_init_count={arr_init_count} is_array={is_array} is_2d={is_2d}")
                            self._error(        # Throws an error if it has array size of 2 then array elements has 3, semantic error
                                "E_ARR",
                                f"Array '{id_token.value}' declared with size {arr_size} "
                                f"but initialized with {arr_init_count} element(s)",
                                arr_size_token or id_token
                            )

        # Pass 3 - shadowing check where it checks if the same name exists in the local scope, emit E001 error message: variable shadowing not allowed in blocks
        if id_token:
            # Only block shadowing within the same function, global scope which is in scope[0] will is always be allowed to be shadowed
            outer = None
            # Search all scopes EXCEPT global (scopes[0]) when inside a function
            search_scopes = self.symbol_table.scopes[1:-1] if self.current_function else self.symbol_table.scopes[:-1]
            for scope in reversed(search_scopes):
                if id_token.value in scope:
                    outer = scope[id_token.value]
                    break
            if outer is not None:
                self._error(
                    "E001",
                    f"'{id_token.value}' is already declared in an outer scope — "
                    f"variable shadowing is not allowed in blocks",
                    id_token
                )
        self._visit_children(node)
        self.current_var_type = None

    def _check_arr_2d_bounds(self, arr_cont_2d_node, row_size, col_size, id_token, dtype=None):
        """Check 2D array bounds: row count vs row_size, each row's count vs col_size.
        Returns total element count (for consistency), emits errors directly."""
        rows = []
        # Collect all opt_arr_elems nodes (each is one row)
        for child in arr_cont_2d_node.children:
            if self._is_parse_node(child) and child.name == "opt_arr_elems":
                rows.append(child)
            elif self._is_parse_node(child) and child.name == "arr_cont_2d_tail":
                for tc in child.children:
                    if self._is_parse_node(tc) and tc.name == "opt_arr_elems":
                        rows.append(tc)

        if len(rows) > row_size:
            self._error(
                "E_ARR",
                f"Array '{id_token.value}' declared with {row_size} row(s) "
                f"but initialized with {len(rows)} row(s)",
                id_token
            )

        for i, row in enumerate(rows):
            count = self._count_arr_elements_1d(row)
            if count > col_size:
                self._error(
                    "E_ARR",
                    f"Array '{id_token.value}' row {i} declared with size {col_size} "
                    f"but initialized with {count} element(s)",
                    id_token
                )
            # Check element types for this row
            self._check_arr_element_types(row, dtype, id_token)


    def _visit_primary(self, node):
        """Visit primary: check for undeclared variables and built-in calls."""
        for child in node.children:
            if self._is_parse_node(child):
                continue
            if not hasattr(child, 'type'):
                continue
            if child.type == "ID":
                var_name = child.value
                if var_name and not self.symbol_table.lookup(var_name):
                    self._error("E002", f"Undeclared identifier '{var_name}'", child)
            
            # walang sift dito kc yung SIFT may sariling AST node na ginawa siya called sift_call, ctrl+f mo nalang - J
            elif child.type == "SQRT":
                self._visit_sqrt_arg(node)
                return
            elif child.type == "CEIL":
                self._visit_ceil_arg(node)
                return
            elif child.type == "FLOOR":
                self._visit_floor_arg(node)
                return
            elif child.type == "POW":
                self._visit_pow_arg(node)
                return
            elif child.type == "RAND":
                self._visit_rand_arg(node)
                return
            elif child.type == "TYPE":
                self._visit_type_arg(node)
                return
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

    def _visit_input_stmt(self, node):
        """Visit batter@ statement — check all target variables are declared."""
        for child in node.children:
            if not self._is_parse_node(child):
                continue
            if child.name == "input_args":
                self._check_input_args(child)

    def _check_input_args(self, node):
        """Recursively check all input target IDs are declared."""
        for child in node.children:
            if not self._is_parse_node(child):
                if hasattr(child, 'type') and child.type == "ID":
                    if not self.symbol_table.lookup(child.value):
                        self._error("E002", f"Undeclared identifier '{child.value}'", child)
            else:
                if child.name not in ("_empty", "input_val"):
                    self._check_input_args(child)

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
        """Visit id_dec_stmt: ID = value"""
        var_name = None
        id_token = None
        for child in node.children:
            if not self._is_parse_node(child) and hasattr(child, 'type') and child.type == "ID":
                var_name = child.value
                id_token = child
                break

        if var_name:
            symbol = self.symbol_table.lookup(var_name)
            print(f"[ID_DEC] dtype repr: {repr(symbol.dtype)} type: {type(symbol.dtype)}")
            print(f"[ID_DEC_STMT] var={var_name} symbol={symbol} dtype={getattr(symbol,'dtype',None)} is_array={getattr(symbol,'is_array',None)}")
            if not symbol:
                self._error("E002", f"Undeclared identifier '{var_name}'", id_token)
                self._visit_children(node)
                return

            if symbol.is_constant:
                self._error("E005", f"Cannot modify constant identifier '{var_name}'", id_token)

            # Check ++/-- on non-numeric types
            if symbol.dtype in ("blend", "churro", "temp"):
                for child in node.children:
                    if self._is_parse_node(child) and child.name == "id_dec_tail":
                        for tc in child.children:
                            if not self._is_parse_node(tc) and hasattr(tc, 'type') and tc.type in ("INCREMENT", "DECREMENT"):
                                self._error("E_TYPE", f"Cannot apply '++/--' to '{symbol.dtype}' variable '{var_name}'", id_token)
                            elif self._is_parse_node(tc) and tc.name == "unary_op":
                                for uc in tc.children:
                                    if not self._is_parse_node(uc) and hasattr(uc, 'type') and uc.type in ("INCREMENT", "DECREMENT"):
                                        self._error("E_TYPE", f"Cannot apply '++/--' to '{symbol.dtype}' variable '{var_name}'", id_token)

            # Check array element assignment type
            if symbol.is_array and symbol.dtype:
                for child in node.children:
                    if self._is_parse_node(child) and child.name == "id_dec_tail":
                        for tc in child.children:
                            if self._is_parse_node(tc) and tc.name == "id_bracket_tail":
                                for bc in tc.children:
                                    if self._is_parse_node(bc) and bc.name in ("arr_elem", "expression", "assign_val", "value"):
                                        inferred = self._infer_value_type(bc)
                                        if inferred and inferred != symbol.dtype:
                                            self._error(
                                                "E_ARR_TYPE",
                                                f"Cannot assign '{inferred}' value to '{symbol.dtype}' array '{var_name}'",
                                                id_token
                                            )

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
    
    """ Variables declarations: _visit_var_dec_init
        Declares one variable in a list
        Relies on self.current_var_type set by the parent _visit_dtype_dec()
    """
    
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
                self._error("E001", f"Redefinition of identifier '{var_name}'", child) # Emits E001 if identifier is already declared in the same scope
        
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
                    self.errors.append(SemanticError(           # Emits E001 if identifier is already declared in the same scope
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
        """ _visit_opt_assign -> checks type of initialization value if it is valid to the implicit conversions
            Example: bean x = 3.14 -> RHS is "drip", target is "bean"
            TYPE_COMPAT["bean"] has "drip" = implicit type casting of drip to bean is allowed.
        """
        
        # Only check if we're inside a declaration (current_var_type is set)
        if self.current_var_type:
            # Infer the type of the RHS value
            rhs_type = self._infer_value_type(node)

            if rhs_type and rhs_type != self.current_var_type:
                # Check if it's a valid implicit cast per TYPE_COMPAT
                if not self._is_type_compatible(self.current_var_type, rhs_type):
                    self._error(        # Throws an error if it is not within the implicit type casting scope.
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
    
    def _count_arr_elements_1d(self, arr_cont_1d_node):
        """Count elements in a 1D array initializer (arr_cont_1d node)."""
        count = 0
        for child in arr_cont_1d_node.children:
            if self._is_parse_node(child) and child.name == "arr_elem":
                count += 1
            elif self._is_parse_node(child) and child.name == "ext_arr_elem":
                for ec in child.children:
                    if self._is_parse_node(ec) and ec.name == "arr_elem":
                        count += 1
        return count

    def _count_arr_elements_2d(self, arr_cont_2d_node):
        """Count total elements across all rows in a 2D array initializer (arr_cont_2d node)."""
        count = 0
        for child in arr_cont_2d_node.children:
            if self._is_parse_node(child) and child.name == "arr_cont_1d":
                count += self._count_arr_elements_1d(child)
            elif self._is_parse_node(child) and child.name == "opt_arr_elems":
                count += self._count_arr_elements_1d(child)
            elif self._is_parse_node(child) and child.name == "arr_cont_2d_tail":
                for tc in child.children:
                    if self._is_parse_node(tc) and tc.name == "opt_arr_elems":
                        count += self._count_arr_elements_1d(tc)
        return count

    def _visit_order_dec_stmt(self, node):
        """Visit order declaration"""
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
            # print("[SEMANTIC DEBUG EXPRESSION HIT INFER VAL]expression hit")
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
                    if child.type == "ID":
                        # Look up variable type
                        symbol = self.symbol_table.lookup(child.value)
                        if symbol:
                            return symbol.dtype
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
        
        collected = []
        for child in node.children:
            inferred = self._infer_value_type(child)
            if inferred:
                collected.append(inferred)

        if not collected:
            return None

        # churro + churro → blend
        if len(collected) >= 2 and all(t == "churro" for t in collected):
            return "blend"
        if "blend" in collected:
            return "blend"
        return collected[0]
    
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
                    "BLEND": "blend"
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
    
    def _check_arr_element_types(self, arr_cont_node, expected_dtype, id_token):
        """Check each element in a 1D array initializer matches the declared type."""
        for child in arr_cont_node.children:
            if self._is_parse_node(child) and child.name == "arr_elem":
                inferred = self._infer_value_type(child)
                if inferred and inferred != expected_dtype:
                    self._error(
                        "E_ARR_TYPE",
                        f"Array of type '{expected_dtype}' cannot contain '{inferred}' value",
                        child
                    )
            elif self._is_parse_node(child) and child.name == "ext_arr_elem":
                for ec in child.children:
                    if self._is_parse_node(ec) and ec.name == "arr_elem":
                        inferred = self._infer_value_type(ec)
                        if inferred and inferred != expected_dtype:
                            self._error(
                                "E_ARR_TYPE",
                                f"Array of type '{expected_dtype}' cannot contain '{inferred}' value",
                                ec
                            )

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
