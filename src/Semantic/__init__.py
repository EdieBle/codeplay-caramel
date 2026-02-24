"""
Semantic Analysis Module for CARAMEL Language

This module provides semantic analysis capabilities for CARAMEL source code.
It operates on the Abstract Syntax Tree (AST) produced by the parser to enforce
semantic rules and constraints defined in the CARAMEL specification.

Main Components:
- SemanticError: Represents individual semantic errors
- Symbol: Represents language entities (variables, functions, classes)
- SymbolTable: Manages scope and symbol management
- SemanticAnalyzer: Main analyzer implementing semantic rules
- run_semantic_analysis(): Entry point function
"""

from src.Semantic.analyzer import (
    SemanticError,
    Symbol,
    SymbolTable,
    SemanticAnalyzer,
    run_semantic_analysis
)

__all__ = [
    'SemanticError',
    'Symbol',
    'SymbolTable',
    'SemanticAnalyzer',
    'run_semantic_analysis'
]
