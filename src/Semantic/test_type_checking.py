#!/usr/bin/env python3
"""
Direct semantic analyzer test without going through the parser.
Creates test ASTs directly to verify type checking logic.
"""

from src.Semantic.analyzer import SemanticAnalyzer, Symbol, SymbolTable
from src.Parser.parser import ParseNode
import sys

def test_type_checking():
    """Test type compatibility checking directly"""
    
    print("="*60)
    print("DIRECT TYPE CHECKING TEST")
    print("="*60)
    
    # Create analyzer
    analyzer = SemanticAnalyzer()
    
    # Test 1: bean -> drip should ERROR
    print("\n[TEST 1] Bean value -> Drip variable (should ERROR)")
    print("-" * 60)
    
    # Create a symbol for drip variable
    drip_var = Symbol("x", "variable", dtype="drip", scope_level=0)
    
    # Check if bean can be assigned to drip
    is_compatible = analyzer._is_type_compatible("drip", "bean")
    print(f"Can assign 'bean' to 'drip'? {is_compatible}")
    if not is_compatible:
        print(f"[+] CORRECT: Type mismatch detected (E003)")
    else:
        print(f"[-] ERROR: Should not allow bean -> drip")
    
    # Test 2: drip -> drip should PASS
    print("\n[TEST 2] Drip value -> Drip variable (should PASS)")
    print("-" * 60)
    
    is_compatible = analyzer._is_type_compatible("drip", "drip")
    print(f"Can assign 'drip' to 'drip'? {is_compatible}")
    if is_compatible:
        print(f"[+] CORRECT: Types match")
    else:
        print(f"[-] ERROR: Should allow drip -> drip")
    
    # Test 3: drip -> bean should ERROR
    print("\n[TEST 3] Drip value (15.5) -> Bean variable (should ERROR)")
    print("-" * 60)
    
    is_compatible = analyzer._is_type_compatible("bean", "drip")
    print(f"Can assign 'drip' to 'bean'? {is_compatible}")
    if not is_compatible:
        print(f"[+] CORRECT: Type mismatch detected (E003)")
    else:
        print(f"[-] ERROR: Should not allow drip -> bean")
    
    # Test 4: blend accepts all
    print("\n[TEST 4] Any type -> Blend variable (should PASS)")
    print("-" * 60)
    
    test_types = ["bean", "drip", "churro", "temp", "blend", "mug"]
    all_compatible = True
    for source_type in test_types:
        is_compat = analyzer._is_type_compatible("blend", source_type)
        print(f"  Can assign '{source_type}' to 'blend'? {is_compat}")
        all_compatible &= is_compat
    
    if all_compatible:
        print(f"[+] CORRECT: Blend accepts all types")
    else:
        print(f"[-] ERROR: Blend should accept all types")
    
    # Test 5: Type inference from literals
    print("\n[TEST 5] Type inference from literals")
    print("-" * 60)
    
    tests = [
        ("BEANLIT", "bean"),
        ("DRIPLIT", "drip"),
        ("CHURROLIT", "churro"),
        ("HOT", "temp"),
        ("COLD", "temp"),
    ]
    
    for token_type, expected_type in tests:
        inferred = analyzer._infer_type_from_literal(token_type)
        status = "[+]" if inferred == expected_type else "[-]"
        print(f"  {status} {token_type} -> {inferred} (expected: {expected_type})")
    
    print("\n" + "="*60)
    print("TYPE CHECKING TESTS COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_type_checking()
