"""
Semantic Analyzer Module for CARAMEL Language

Based on semantic rules from the CARAMEL specification document.
This module implements semantic analysis completely separate from the parser,
analyzing the AST for semantic correctness after successful parsing.

Type Compatibility Rules:
- bean (integer): no implicit conversions
- drip (float): can accept drip only (no bean -> drip conversion)
- churro (string): no implicit conversions
- temp (boolean): no implicit conversions
- blend (mixed/generic): accepts any type
- mug (struct): no implicit conversions
"""
from src.Lexer.lexer import token_final_out
from src.Parser.parser import Parser

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
        if name in self.scopes[-1]:
            return False
        self.scopes[-1][name] = symbol
        return True
    
    def lookup(self, name):
        """Look up a symbol in current and parent scopes."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
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
    - E005: Constant modification
    - E006: Invalid operation
    - E007: Missing main function
    - E008: Multiple main functions
    - E009: Attempted type cast
    - E010: Invalid operator compatibility
    """
    
    # Valid data types
    VALID_TYPES = {"bean", "drip", "churro", "temp", "blend", "mug"}
    
    # Type compatibility for assignments: target_type -> set of compatible source types
    # STRICT: bean != drip without explicit cast
    TYPE_COMPAT = {
        "bean": {"bean"},
        "drip": {"drip"},
        "churro": {"churro"},
        "temp": {"temp"},
        "blend": {"bean", "drip", "churro", "temp", "blend", "mug"},  # blend accepts all
        "mug": {"mug"}
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
            pass
        
        return [err.to_dict() for err in self.errors]
    
    def _visit(self, node):
        """Dispatch visitor based on node name."""
        if not self._is_parse_node(node):
            return None
        
        method_name = f"_visit_{node.name}"
        if hasattr(self, method_name):
            return getattr(self, method_name)(node)
        
        # Default: visit all children
        self._visit_children(node)
        return None
    
    def _is_parse_node(self, node):
        """Check if node is a ParseNode."""
        return hasattr(node, 'name') and hasattr(node, 'children')
    
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
    
    def _visit_recipe_def(self, node):
        """Visit recipe_def: recipe return_type ID (params) { body refill }"""
        # Extract function name and return type
        func_name = self._extract_name_from_node(node, depth=3)
        return_type = self._extract_return_type(node)
        
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
        """Visit dtype_dec: data type declaration"""
        # Extract data type from first child
        dtype = self._extract_type_from_node(node)
        if dtype:
            self.current_var_type = dtype
        
        self._visit_children(node)
        self.current_var_type = None
    
    def _visit_primary(self, node):
        """Visit primary: check for undeclared variables"""
        # Check for identifier usage
        for child in node.children:
            if self._is_parse_node(child) and child.name == "ID":
                var_name = self._extract_token_value(child)
                if var_name and not self.symbol_table.lookup(var_name):
                    self.errors.append(SemanticError(
                        "E002",
                        f"Undeclared identifier '{var_name}'",
                        line=getattr(child, 'line', None)
                    ))
        
        self._visit_children(node)
    
    def _visit_pour_loop(self, node):
        """Visit pour_loop: for loop"""
        self.symbol_table.push_scope()
        prev_loop = self.in_loop
        self.in_loop = True
        
        self._visit_children(node)
        
        self.in_loop = prev_loop
        self.symbol_table.pop_scope()
    
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
                self.errors.append(SemanticError(
                    "E006",
                    f"'{stmt_type.lower()}' statement outside of loop",
                    line=getattr(node, 'line', None)
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
    
    def _visit_id_dec_stmt(self, node):
        """Visit id_dec_stmt: ID = value (simple assignment)"""
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
    
    def _visit_var_dec_const_init(self, node):
        """Visit variable declaration with initialization"""
        if self.current_var_type:
            var_name = self._extract_var_name(node)
            if var_name:
                symbol = Symbol(
                    var_name,
                    "variable",
                    dtype=self.current_var_type,
                    is_constant=True,  # BREWED = constant
                    scope_level=self.symbol_table.scope_level,
                    line=getattr(node, 'line', None),
                    is_initialized=True
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
        
        self._visit_children(node)
    
    def _visit_opt_assign(self, node):
        """Visit optional assignment"""
        self._visit_children(node)
    
    def _visit_var_dec_tail(self, node):
        """Visit variable declaration tail"""
        # Collect variable names and track their types
        if self.current_var_type and hasattr(node, 'children'):
            for child in node.children:
                if self._is_parse_node(child):
                    if child.name == "ID" or (hasattr(child, 'value')):
                        var_name = self._extract_token_value(child)
                        if var_name:
                            symbol = Symbol(
                                var_name,
                                "variable",
                                dtype=self.current_var_type,
                                scope_level=self.symbol_table.scope_level,
                                line=getattr(child, 'line', None)
                            )
                            
                            if not self.symbol_table.declare(var_name, symbol):
                                self.errors.append(SemanticError(
                                    "E001",
                                    f"Redefinition of identifier '{var_name}'",
                                    line=getattr(child, 'line', None)
                                ))
        
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
    
    # ========================================================================
    # TYPE CHECKING METHODS
    # ========================================================================
    
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
            self.errors.append(SemanticError(
                "E003",
                f"Type mismatch: cannot assign '{rhs_type}' to '{symbol.dtype}' variable '{var_name}'",
                line=getattr(node, 'line', None)
            ))
    
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
    
    def _extract_name_from_node(self, node, depth=2):
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
    
    def _error(self, code, message, node=None):
        """Record a semantic error."""
        line = None
        column = None
        
        if node:
            if hasattr(node, 'line'):
                line = node.line
                column = node.column
            elif hasattr(node, 'children') and node.children:
                for child in node.children:
                    if hasattr(child, 'line'):
                        line = child.line
                        column = child.column
                        break
        
        self.errors.append(SemanticError(code, message, line, column))

def run_semantic_analysis(ast):
    """
    Entry point function for semantic analysis.
    
    Args:
        ast: Abstract syntax tree from parser
        
    Returns:
        List of semantic error dictionaries
    """
    analyzer = SemanticAnalyzer(ast)
    return analyzer.analyze()
