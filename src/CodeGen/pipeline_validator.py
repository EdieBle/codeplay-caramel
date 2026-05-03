"""
Compiler Pipeline Validator for CARAMEL Language
=================================================

This module provides a **centralised** compilation pipeline that all server
endpoints use.  Running the pipeline through a single function eliminates
duplicated code across ``/execute``, ``/execute/start``, and ``/build-exe``
and ensures every stage is applied consistently.

Pipeline stages
---------------
1. **Lexical analysis** (tokenise) — via ``src.Lexer.lexer.tokenize``
2. **Parsing**         (syntax)   — via ``src.Parser.parser.Parser``
3. **Semantic analysis**          — via ``src.Semantic.analyzer.SemanticAnalyzer``
4. **IR generation**              — via ``src.CodeGen.ir_generator.IRGenerator``
5. **Optimisation**               — via ``src.CodeGen.optimizer.optimize_ir``
6. **Infinite loop detection**    — via ``src.CodeGen.loop_detector.InfiniteLoopDetector``
7. **Code generation**            — via ``src.CodeGen.code_generator.StructuredCodeGenerator``

Usage
-----
    from src.CodeGen.pipeline_validator import validate_and_compile, CompilationMode

    result = validate_and_compile(source_code, mode=CompilationMode.STANDALONE)
    if not result.success:
        return jsonify({"errors": result.errors, "stage": result.stage}), 400
    exe_source = result.standalone_code

Notes
-----
- The validator is **stateless**; each call creates fresh compiler objects.
- The ``mode`` parameter controls whether ``generate()`` or
  ``generate_standalone()`` is called on the code generator.
- Lexical errors are detected as ERROR tokens in the token stream and
  converted to the same error-dict format used by the other stages so the
  frontend can render them uniformly.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import List, Optional, Any

from src.Lexer.lexer import tokenize
from src.Parser.parser import Parser
from src.Semantic.analyzer import SemanticAnalyzer
from src.CodeGen.ir_generator import IRGenerator
from src.CodeGen.optimizer import optimize_ir
from src.CodeGen.code_generator import StructuredCodeGenerator
from src.CodeGen.loop_detector import InfiniteLoopDetector


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class CompilationMode(str, Enum):
    """Controls the type of Python source code produced by the code generator."""
    INTERACTIVE = "interactive"    # Uses mock I/O — for IDE execution
    STANDALONE  = "standalone"     # Uses real I/O — for PyInstaller packaging


@dataclasses.dataclass
class CompilationResult:
    """
    Holds the outcome of a full compiler pipeline run.

    Attributes
    ----------
    success : bool
        ``True`` if every stage passed without errors.
    stage : str
        Name of the stage that failed first, or ``"complete"`` on success.
    errors : list of dict
        All accumulated error dictionaries (may span multiple stages).
    ir_instructions : list
        Raw IR instruction list (set when IR generation succeeds).
    optimized_ir : list
        Optimised IR instruction list (set when optimisation succeeds).
    generated_code : str
        Interactive-mode Python source (set when code generation succeeds).
    standalone_code : str
        Standalone-mode Python source (set when code generation succeeds and
        mode is STANDALONE).
    """
    success:          bool             = False
    stage:            str              = "unknown"
    errors:           List[dict]       = dataclasses.field(default_factory=list)
    ir_instructions:  List[Any]        = dataclasses.field(default_factory=list)
    optimized_ir:     List[Any]        = dataclasses.field(default_factory=list)
    generated_code:   str              = ""
    standalone_code:  str              = ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def validate_and_compile(
    source_code: str,
    mode: CompilationMode = CompilationMode.INTERACTIVE,
    run_loop_detection: bool = True,
) -> CompilationResult:
    """
    Run the full CARAMEL compiler pipeline and return a ``CompilationResult``.

    Parameters
    ----------
    source_code : str
        Raw Caramel source code to compile.
    mode : CompilationMode
        Whether to produce interactive or standalone Python output.
    run_loop_detection : bool
        If ``True`` (default), run the static infinite-loop detector after IR
        generation.  Disable only for internal testing of lower stages.

    Returns
    -------
    CompilationResult
        Populated with either errors or the generated code, depending on
        whether compilation succeeded.
    """
    result = CompilationResult()

    # ------------------------------------------------------------------
    # Pre-stage: Normalise the source string so the lexer never sees
    # bare \r characters (Windows CRLF → LF) or smart-quote characters
    # that the user may have accidentally typed.
    # ------------------------------------------------------------------
    source_code = (
        source_code
        .lstrip("\ufeff")                   # strip UTF-8 BOM if present
        .replace("\r\n", "\n")              # CRLF → LF
        .replace("\r",   "\n")              # lone CR → LF (old Mac)
        .replace("\u201c", '"')             # left  double curly-quote → "
        .replace("\u201d", '"')             # right double curly-quote → "
        .replace("\u2018", "'")             # left  single curly-quote → '
        .replace("\u2019", "'")             # right single curly-quote → '
        .replace("\u00a0", " ")             # non-breaking space → regular space
    )

    # ------------------------------------------------------------------
    # Stage 1 & 2: Lexical + Syntax analysis via the Parser
    # (The Parser internally tokenises; we surface its errors here.)
    # ------------------------------------------------------------------
    result.stage = "parser"
    try:
        parser = Parser(source_code)
        parser.start()
    except Exception as exc:
        result.errors = [{
            "type":    "PARSER_CRASH",
            "message": f"Parser raised an unexpected exception: {exc}",
            "line":    None,
            "stage":   "parser",
        }]
        return result

    if parser.errors:
        result.errors = _normalise_errors(parser.errors, "parser")
        return result

    # ------------------------------------------------------------------
    # Stage 3: Semantic analysis
    # ------------------------------------------------------------------
    result.stage = "semantic"
    try:
        analyzer      = SemanticAnalyzer(parser.ast)
        semantic_errs = analyzer.analyze()
    except Exception as exc:
        result.errors = [{
            "type":    "SEMANTIC_CRASH",
            "message": f"Semantic analyser raised an unexpected exception: {exc}",
            "line":    None,
            "stage":   "semantic",
        }]
        return result

    if semantic_errs:
        result.errors = _normalise_errors(semantic_errs, "semantic")
        return result

    # ------------------------------------------------------------------
    # Stage 4: IR generation
    # ------------------------------------------------------------------
    result.stage = "ir"
    try:
        ir_gen              = IRGenerator(parser.ast)
        ir_instructions     = ir_gen.generate()
        result.ir_instructions = ir_instructions
    except Exception as exc:
        result.errors = [{
            "type":    "IR_ERROR",
            "message": f"IR generation failed: {exc}",
            "line":    None,
            "stage":   "ir",
        }]
        return result

    # ------------------------------------------------------------------
    # Stage 5: Optimisation (non-fatal — fall back to unoptimised IR)
    # ------------------------------------------------------------------
    result.stage = "optimizer"
    try:
        optimized_ir = optimize_ir(ir_instructions)
    except Exception:
        # Optimiser failure is non-fatal; continue with raw IR
        optimized_ir = ir_instructions
    result.optimized_ir = optimized_ir

    # ------------------------------------------------------------------
    # Stage 6: Infinite loop detection (static analysis)
    # ------------------------------------------------------------------
    if run_loop_detection:
        result.stage = "loop_detection"
        try:
            detector   = InfiniteLoopDetector(optimized_ir)
            loop_errors = detector.analyze()
        except Exception as exc:
            # Detection failure is non-fatal — log but continue
            loop_errors = [{
                "type":    "LOOP_DETECTOR_CRASH",
                "message": f"Loop detector raised an unexpected exception: {exc}",
                "line":    None,
                "stage":   "loop_detection",
            }]

        if loop_errors:
            result.errors = loop_errors
            return result

    # ------------------------------------------------------------------
    # Stage 7: Code generation
    # ------------------------------------------------------------------
    result.stage = "codegen"
    try:
        codegen = StructuredCodeGenerator(optimized_ir)

        # Always generate interactive code (used by the IDE runner)
        result.generated_code = codegen.generate()

        # Generate standalone code when requested (for EXE building)
        if mode == CompilationMode.STANDALONE:
            result.standalone_code = codegen.generate_standalone()

    except Exception as exc:
        result.errors = [{
            "type":    "CODEGEN_ERROR",
            "message": f"Code generation failed: {exc}",
            "line":    None,
            "stage":   "codegen",
        }]
        return result

    # ------------------------------------------------------------------
    # All stages passed
    # ------------------------------------------------------------------
    result.success = True
    result.stage   = "complete"
    return result


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _normalise_errors(errors: list, stage: str) -> List[dict]:
    """
    Ensure every error in ``errors`` is a plain dict and has a ``stage``
    field.  Handles both raw dicts and objects with a ``to_dict()`` method.
    """
    normalised = []
    for err in errors:
        if hasattr(err, "to_dict"):
            d = err.to_dict()
        elif isinstance(err, dict):
            d = dict(err)
        else:
            d = {"type": "ERROR", "message": str(err)}

        d.setdefault("stage", stage)
        normalised.append(d)
    return normalised
