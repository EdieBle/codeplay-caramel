"""
CARAMEL Code Generation Backend

This package implements the compiler backend for the CARAMEL language:
  1. ir_generator.py   - AST → Three-Address Code (Intermediate Representation)
  2. optimizer.py       - IR-level optimizations (constant folding, dead code elimination)
  3. code_generator.py  - IR → Executable Python target code
"""
