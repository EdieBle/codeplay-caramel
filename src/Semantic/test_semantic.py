#!/usr/bin/env python3
"""
Quick test script to verify semantic analyzer type checking.
Tests the bean -> drip type mismatch detection.
"""

import sys
from src.Parser.parser import Parser
from src.Semantic import run_semantic_analysis

# Test case 1: bean value assigned to drip variable (should error)
# Based on actual parser rules for CARAMEL
test_code_1 = """
bean cup() {
    drip x;
    x=5;
    refill?(0);
}
"""

# Test case 2: drip variable assigned drip value (should pass)
test_code_2 = """
bean cup() {
    drip x;
    x=3.14;
    refill?(0);
}
"""

# Test case 3: bean variable assigned drip value (should error)
test_code_3 = """
bean cup() {
    bean y;
    y=15.5;
    refill?(0);
}
"""

def test_code(name, code):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    print("Code:")
    print(code)
    print("-" * 60)
    
    try:
        # Create parser with suppressed debug output
        import io
        import contextlib
        
        # Capture stdout to suppress lexer debug output
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            with contextlib.redirect_stderr(io.StringIO()):
                parser = Parser(code)
                parser.start()
        
        if parser.errors:
            print(f"Parser errors: {len(parser.errors)}")
            for err in parser.errors:
                if isinstance(err, dict):
                    print(f"  - {err.get('message', str(err))}")
                else:
                    print(f"  - {err}")
            return
        
        if not parser.ast:
            print("Parser failed: No AST generated")
            return
        
        semantic_errors = run_semantic_analysis(parser.ast)
        
        if semantic_errors:
            print(f"[+] Semantic errors found: {len(semantic_errors)}")
            for err in semantic_errors:
                print(f"  [{err['code']}] {err['message']}")
                if err.get('line'):
                    print(f"         @ line {err.get('line')}, col {err.get('column')}")
        else:
            print("[+] No semantic errors found")
    
    except Exception as e:
        print(f"[ERROR] Test failed with exception: {e}")

# Run tests
if __name__ == "__main__":
    test_code("Bean (5) assigned to Drip var (should ERROR)", test_code_1)
    test_code("Drip (3.14) assigned to Drip var (should PASS)", test_code_2)
    test_code("Drip (15.5) assigned to Bean var (should ERROR)", test_code_3)
