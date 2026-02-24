"""
Example Usage of the CARAMEL Semantic Analyzer

This file demonstrates how to use the semantic analyzer with CARAMEL code examples.
"""

from src.Semantic import run_semantic_analysis
from src.Parser.parser import ParseNode


def create_simple_ast():
    """Create a simple AST for testing."""
    return ParseNode("start", [
        ParseNode("program", [
            ParseNode("global_def", [ParseNode("_empty")]),
            ParseNode("main_def", [])
        ])
    ])


def example_1_redefinition():
    """Example: Duplicate identifier declaration (E001)"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Redefinition Error (E001)")
    print("="*60)
    
    code = """
    bean count = 5;
    bean count = 10;  // ERROR: E001 - Redefinition
    
    bean cup() {
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    # Note: In real usage, you would parse this first:
    # ast = parser.parse(code)
    # errors = run_semantic_analysis(ast)
    
    print("\nExpected Error:")
    print("  [E001] Redefinition of identifier 'count'")


def example_2_undeclared():
    """Example: Undeclared variable usage (E002)"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Undeclared Identifier (E002)")
    print("="*60)
    
    code = """
    bean cup() {
        x = 10;  // ERROR: E002 - x not declared
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Error:")
    print("  [E002] Undeclared identifier 'x'")


def example_3_missing_main():
    """Example: Missing main function (E007)"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Missing Main Function (E007)")
    print("="*60)
    
    code = """
    recipe bean add(bean a, bean b) {
        refill(a + b);
    }
    // No bean cup() function - ERROR: E007
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Error:")
    print("  [E007] Missing main function: program must have exactly one 'bean cup()' function")


def example_4_break_outside_loop():
    """Example: Break outside loop (E006)"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Control Statement Outside Loop (E006)")
    print("="*60)
    
    code = """
    bean cup() {
        snap;  // ERROR: E006 - outside loop
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Error:")
    print("  [E006] 'snap' statement outside of loop")


def example_5_valid_code():
    """Example: Valid semantic code (no errors)"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Valid Code (No Errors)")
    print("="*60)
    
    code = """
    recipe bean multiply(bean x, bean y) {
        refill(x * y);
    }
    
    bean cup() {
        bean a = 5;
        bean b = 3;
        bean product = multiply(a, b);
        glaze(product);
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Result:")
    print("  No semantic errors - code is valid!")


def example_6_function_scope():
    """Example: Variable shadowing in nested scopes"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Scope Management (Shadowing)")
    print("="*60)
    
    code = """
    bean x = 10;  // Global x
    
    recipe bean getX() {
        bean x = 20;  // Local x (shadows global)
        refill(x);    // Returns 20
    }
    
    bean cup() {
        bean y = getX();  // y = 20
        // x here refers to global x = 10
        glaze(x);
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Result:")
    print("  No semantic errors - shadowing is allowed in nested scopes")


def example_7_constant_modification():
    """Example: Attempting to modify constant (E005)"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Constant Modification (E005)")
    print("="*60)
    
    code = """
    brewed bean limit = 100;
    
    bean cup() {
        limit = 50;  // ERROR: E005 - Cannot modify constant
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Error:")
    print("  [E005] Constant modification: 'limit' is declared as constant")


def example_8_type_operations():
    """Example: Type compatibility in operations"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Type Operations")
    print("="*60)
    
    code = """
    bean cup() {
        bean a = 5;
        drip b = 3.14;
        drip result1 = a + b;      // OK - bean + drip = drip
        
        temp x = hot;
        temp result2 = x && hot;   // OK - temp && temp = temp
        
        bean wrong = a && b;       // ERROR: E010 - && requires temp operands
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Errors:")
    print("  [E010] Operator type incompatibility in binary operation")


def example_9_loop_with_break():
    """Example: Valid loop with break statement"""
    print("\n" + "="*60)
    print("EXAMPLE 9: Loop with Control Statement (Valid)")
    print("="*60)
    
    code = """
    bean cup() {
        pour(bean i = 0; i < 10; i++) {
            ifbrew (i == 5) {
                snap;  // OK - inside loop
            }
        }
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Result:")
    print("  No semantic errors - 'snap' is valid inside loop")


def example_10_class_definition():
    """Example: Class definition and instantiation"""
    print("\n" + "="*60)
    print("EXAMPLE 10: Class Definition (Valid)")
    print("="*60)
    
    code = """
    crema Calculator {
        cafe recipe bean add(bean a, bean b) {
            refill(a + b);
        }
    }
    
    bean cup() {
        new calc = Calculator;
        bean sum = calc.add(5, 3);
        glaze(sum);
        refill? 0;
    }
    """
    
    print("Code:")
    print(code)
    
    print("\nExpected Result:")
    print("  No semantic errors - class definition and usage is valid")


def run_all_examples():
    """Run all examples."""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " CARAMEL SEMANTIC ANALYZER - EXAMPLES ".center(58) + "║")
    print("╚" + "="*58 + "╝")
    
    example_1_redefinition()
    example_2_undeclared()
    example_3_missing_main()
    example_4_break_outside_loop()
    example_5_valid_code()
    example_6_function_scope()
    example_7_constant_modification()
    example_8_type_operations()
    example_9_loop_with_break()
    example_10_class_definition()
    
    print("\n" + "="*60)
    print("EXAMPLES COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_examples()
