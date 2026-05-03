"""
Infinite Loop Detector for CARAMEL Language Compiler
=====================================================

This module performs **static analysis** on the IR instruction list produced
by the IRGenerator to identify potential infinite loops BEFORE the program is
executed or packaged into an executable.

Detection Strategies
--------------------
1. Unconditional loop detection:
   - ``whilehot(hot)`` / ``whilehot(cold)`` — loops with a constant-TRUE or
     always-FALSE condition and no reachable ``snap`` (break) inside the body.
   - A loop whose condition variable is assigned a constant boolean ``True``
     (hot) at every definition point before the loop header.

2. Unmodified loop variable detection (for ``pour`` loops):
   - A ``pour`` loop whose iteration variable is never written inside the
     loop body. Since the condition depends on that variable, the loop
     cannot terminate.

3. Constant-condition ``whilehot`` loops:
   - A ``whilehot`` loop where the condition evaluates to a compile-time
     constant ``True`` (e.g. ``whilehot(hot)`` or ``whilehot(1)``) with no
     reachable break inside.

Limitations
-----------
- The halting problem is undecidable in general; this detector is
  **best-effort** and will catch obvious patterns only.
- Complex conditions involving function calls or pointer arithmetic are
  conservatively treated as unknown (no error reported).
- Dynamic loop detection is handled at **runtime** via iteration counters
  injected into the generated Python code (see ``code_generator.py``).

Usage
-----
    from src.CodeGen.loop_detector import InfiniteLoopDetector

    detector = InfiniteLoopDetector(ir_instructions)
    errors = detector.analyze()
    # errors is a list of dicts, each describing a detected loop issue.
"""

from __future__ import annotations
from typing import List, Dict, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class InfiniteLoopDetector:
    """
    Analyses a flat IR instruction list for statically-detectable infinite
    loop patterns and returns structured error dictionaries.

    Parameters
    ----------
    ir_instructions : list of IRInstruction
        The instruction list produced by ``IRGenerator.generate()``.
    """

    # IR operations that write to a destination variable
    _WRITE_OPS = frozenset({
        "ASSIGN", "BINOP", "UNARYOP", "CALL", "INPUT",
        "ARR_LOAD", "CAST", "CONCAT",
    })

    def __init__(self, ir_instructions: list) -> None:
        self.ir = list(ir_instructions)  # defensive copy
        self._errors: List[Dict] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(self) -> List[Dict]:
        """
        Run all static analysis passes and return a list of error dicts.

        Each dict has the form::

            {
                "type":    "INFINITE_LOOP_ERROR",
                "message": "<human-readable description>",
                "line":    <source line number or None>,
                "stage":   "loop_detection",
            }

        Returns an empty list if no issues are found.
        """
        self._errors = []
        self._analyze_loops()
        return list(self._errors)

    # ------------------------------------------------------------------
    # Internal helpers — loop region discovery
    # ------------------------------------------------------------------

    def _find_loop_regions(self) -> List[Dict]:
        """
        Identify every loop region in the IR.

        A loop region is defined by the pattern::

            LABEL <WHILE_START_N | POUR_START_N | DOWHILE_START_N>
            ...
            GOTO  <start_label>          ← back-edge
            LABEL <...END_N>             ← optional exit label

        Returns a list of region descriptors, each a dict with keys:
            - ``kind``        : "while" | "pour" | "dowhile"
            - ``start_idx``   : index of the opening LABEL
            - ``back_idx``    : index of the back-edge GOTO
            - ``end_idx``     : index of the exit LABEL (or ``back_idx``)
            - ``start_label`` : label name string
            - ``end_label``   : exit label name string (or None)
            - ``cond_idx``    : index of the IF_FALSE condition check, or None
            - ``cond_var``    : the condition variable name, or None
            - ``line_hint``   : approximate source line (from extra metadata)
        """
        regions = []
        label_index: Dict[str, int] = {}  # label_name -> ir index

        # First pass: build a label → index map
        for idx, instr in enumerate(self.ir):
            if instr.op == "LABEL" and instr.dest:
                label_index[instr.dest] = idx

        # Second pass: identify each loop start label
        for idx, instr in enumerate(self.ir):
            if instr.op != "LABEL" or not instr.dest:
                continue
            label = instr.dest
            if not any(p in label for p in ("WHILE_START", "POUR_START", "DOWHILE_START")):
                continue

            # Determine kind
            if "WHILE_START" in label:
                kind = "while"
            elif "POUR_START" in label:
                kind = "pour"
            else:
                kind = "dowhile"

            # Find the back-edge GOTO and exit label
            back_idx: Optional[int] = None
            end_label: Optional[str] = None
            end_idx: Optional[int] = None

            for j in range(idx + 1, len(self.ir)):
                cur = self.ir[j]
                # Stop at function boundaries
                if cur.op in ("FUNC_BEGIN", "FUNC_END"):
                    break
                if cur.op == "GOTO" and cur.dest == label:
                    back_idx = j
                    # The exit label should be the very next LABEL
                    if j + 1 < len(self.ir) and self.ir[j + 1].op == "LABEL":
                        end_label = self.ir[j + 1].dest
                        end_idx = j + 1
                    break

            if back_idx is None:
                # do-while: no back-edge GOTO for taste-till (it uses IF_TRUE)
                # Find the end label by convention
                pass

            # Find the IF_FALSE condition instruction
            cond_idx: Optional[int] = None
            cond_var: Optional[str] = None
            for j in range(idx + 1, back_idx or (idx + 200)):
                if j >= len(self.ir):
                    break
                cur = self.ir[j]
                if cur.op in ("FUNC_BEGIN", "FUNC_END"):
                    break
                if cur.op == "IF_FALSE":
                    cond_idx = j
                    cond_var = cur.arg1 if isinstance(cur.arg1, str) else None
                    break

            # Approximate source line from IR metadata
            line_hint = instr.extra.get("line_hint") if hasattr(instr, "extra") else None

            regions.append({
                "kind":        kind,
                "start_idx":   idx,
                "back_idx":    back_idx,
                "end_idx":     end_idx,
                "start_label": label,
                "end_label":   end_label,
                "cond_idx":    cond_idx,
                "cond_var":    cond_var,
                "line_hint":   line_hint,
            })

        return regions

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------

    def _analyze_loops(self) -> None:
        """Run all loop-specific analysis passes."""
        regions = self._find_loop_regions()

        for region in regions:
            # 1. Check for unconditional loops (no IF_FALSE condition)
            self._check_unconditional_loop(region)

            # 2. Check for constant-true condition
            if region["cond_idx"] is not None:
                self._check_constant_condition(region)

            # 3. For pour loops, check the iteration variable is modified
            if region["kind"] == "pour":
                self._check_pour_variable_modified(region)

    # ------------------------------------------------------------------
    # Pass 1: Unconditional loops
    # ------------------------------------------------------------------

    def _check_unconditional_loop(self, region: Dict) -> None:
        """
        Report an error if a loop has no condition (no IF_FALSE) and no
        reachable snap (break → GOTO to end label) inside its body.

        Such a loop is structurally infinite at compile time.
        """
        if region["cond_idx"] is not None:
            return  # has a condition — skip

        if region["back_idx"] is None:
            return  # can't determine bounds

        body_start = region["start_idx"] + 1
        body_end   = region["back_idx"]
        end_label  = region["end_label"]

        # Check for any GOTO that jumps to the end label (snap/break)
        has_break = self._body_has_break(body_start, body_end, end_label)
        # Also check for RETURN inside the body
        has_return = self._body_has_return(body_start, body_end)

        if not has_break and not has_return:
            line = region["line_hint"]
            kind_name = {"while": "whilehot", "pour": "pour", "dowhile": "taste-till"}.get(
                region["kind"], "loop"
            )
            self._errors.append({
                "type":    "INFINITE_LOOP_ERROR",
                "message": (
                    f"Possible non-terminating {kind_name} loop detected"
                    + (f" near line {line}" if line else "")
                    + ". The loop has no exit condition and no 'snap' (break) statement. "
                    + "Executable generation stopped."
                ),
                "line":    line,
                "stage":   "loop_detection",
            })

    # ------------------------------------------------------------------
    # Pass 2: Constant-true conditions
    # ------------------------------------------------------------------

    def _check_constant_condition(self, region: Dict) -> None:
        """
        Report an error if the loop condition variable is always ``True``
        (hot) at the loop entry and there is no break inside.

        Detection cases:
        - The condition arg is literally ``True`` (Python bool).
        - The condition variable is assigned only ``True`` / 1 before the
          loop and never modified inside the loop body.
        """
        cond_idx = region["cond_idx"]
        if cond_idx is None:
            return

        instr = self.ir[cond_idx]
        cond_arg = instr.arg1

        # Direct literal True (IR stores Python True for 'hot')
        if cond_arg is True:
            # Only report if there is no break
            if not self._body_has_break(
                region["start_idx"] + 1, region["back_idx"] or (region["start_idx"] + 5000),
                region["end_label"]
            ) and not self._body_has_return(
                region["start_idx"] + 1, region["back_idx"] or (region["start_idx"] + 5000)
            ):
                line = region["line_hint"]
                kind_name = {"while": "whilehot", "pour": "pour", "dowhile": "taste-till"}.get(
                    region["kind"], "loop"
                )
                self._errors.append({
                    "type":    "INFINITE_LOOP_ERROR",
                    "message": (
                        f"Possible non-terminating {kind_name} loop detected"
                        + (f" near line {line}" if line else "")
                        + ". The loop condition is always 'hot' (true) with no 'snap' (break). "
                        + "Executable generation stopped."
                    ),
                    "line":    line,
                    "stage":   "loop_detection",
                })
            return

        # Condition is a temp variable — trace its definitions
        if not isinstance(cond_arg, str) or not cond_arg.startswith("_t"):
            return

        # Find the most recent ASSIGN/BINOP before the loop that defines cond_arg
        const_val = self._trace_constant_value(cond_arg, 0, region["start_idx"])
        if const_val is not True:
            return  # Not provably True

        # Check for break
        back = region["back_idx"] or (region["start_idx"] + 5000)
        if not self._body_has_break(region["start_idx"] + 1, back, region["end_label"]) \
                and not self._body_has_return(region["start_idx"] + 1, back):
            line = region["line_hint"]
            kind_name = {"while": "whilehot", "pour": "pour", "dowhile": "taste-till"}.get(
                region["kind"], "loop"
            )
            self._errors.append({
                "type":    "INFINITE_LOOP_ERROR",
                "message": (
                    f"Possible non-terminating {kind_name} loop detected"
                    + (f" near line {line}" if line else "")
                    + ". The loop condition evaluates to a constant 'hot' (true) value. "
                    + "Executable generation stopped."
                ),
                "line":    line,
                "stage":   "loop_detection",
            })

    # ------------------------------------------------------------------
    # Pass 3: Pour loop — iteration variable not modified
    # ------------------------------------------------------------------

    def _check_pour_variable_modified(self, region: Dict) -> None:
        """
        For a ``pour`` loop, find the iteration variable (declared in the
        init section, just before the POUR_START label) and verify it is
        written somewhere in the loop body.

        If the iteration variable is never written inside the loop body,
        the loop condition cannot change, making the loop infinite.
        """
        if region["back_idx"] is None:
            return

        # The iteration variable is typically DECLARE'd just before POUR_START
        iter_var = self._find_pour_iter_var(region["start_idx"])
        if iter_var is None:
            return  # Cannot determine — skip

        # Check if iter_var is written anywhere in the body
        body_start = region["start_idx"] + 1
        body_end   = region["back_idx"]

        written = False
        for j in range(body_start, min(body_end + 1, len(self.ir))):
            instr = self.ir[j]
            if instr.op in self._WRITE_OPS and instr.dest == iter_var:
                written = True
                break
            # Also catch ARR_STORE targeting the var
            if instr.op == "ARR_STORE" and instr.dest == iter_var:
                written = True
                break

        if not written:
            line = region["line_hint"]
            self._errors.append({
                "type":    "INFINITE_LOOP_ERROR",
                "message": (
                    f"Possible non-terminating pour loop detected"
                    + (f" near line {line}" if line else "")
                    + f". The loop variable '{iter_var}' is never modified in the loop body. "
                    + "Executable generation stopped."
                ),
                "line":    line,
                "stage":   "loop_detection",
            })

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def _body_has_break(
        self, body_start: int, body_end: int, end_label: Optional[str]
    ) -> bool:
        """
        Return True if any instruction in [body_start, body_end) is a GOTO
        that jumps to ``end_label`` (representing a snap/break statement) or
        if any GOTO destination contains "END" (conservative match).
        """
        if body_end is None:
            return False
        for j in range(body_start, min(body_end, len(self.ir))):
            instr = self.ir[j]
            if instr.op == "GOTO":
                dest = instr.dest or ""
                # Exact match with end label
                if end_label and dest == end_label:
                    return True
                # Conservative: any GOTO to a label containing END
                if "END" in dest:
                    return True
        return False

    def _body_has_return(self, body_start: int, body_end: int) -> bool:
        """Return True if any RETURN instruction appears in the loop body."""
        if body_end is None:
            return False
        for j in range(body_start, min(body_end, len(self.ir))):
            if self.ir[j].op == "RETURN":
                return True
        return False

    def _trace_constant_value(
        self, var_name: str, search_start: int, search_end: int
    ):
        """
        Walk backwards through IR[search_start:search_end] and return the
        Python value if ``var_name`` is provably assigned a constant
        (True / False / int literal) at its last definition. Returns
        ``None`` if undetermined.
        """
        # Walk backwards from search_end - 1
        for j in range(min(search_end - 1, len(self.ir) - 1), search_start - 1, -1):
            instr = self.ir[j]
            if instr.dest != var_name:
                continue
            if instr.op == "ASSIGN":
                val = instr.arg1
                if isinstance(val, bool):
                    return val
                if isinstance(val, int):
                    return bool(val)
                # Recurse on another temp variable
                if isinstance(val, str) and val.startswith("_t"):
                    return self._trace_constant_value(val, search_start, j)
                return None  # Non-constant
            if instr.op == "BINOP":
                # Simple case: && True True → True, || False False → False
                # Too complex to analyse generically — return None
                return None
        return None

    def _find_pour_iter_var(self, start_idx: int) -> Optional[str]:
        """
        Look backwards from ``start_idx`` for the DECLARE instruction
        belonging to the pour loop's iteration variable.

        Convention: The last DECLARE before the POUR_START label that is
        immediately followed by an ASSIGN is the iteration variable.
        """
        # Scan up to 20 instructions before the loop start
        for j in range(start_idx - 1, max(-1, start_idx - 20), -1):
            instr = self.ir[j]
            if instr.op in ("FUNC_BEGIN", "LABEL"):
                break
            if instr.op == "DECLARE":
                # Verify it has an ASSIGN following it (initial value)
                for k in range(j + 1, min(j + 5, start_idx)):
                    if self.ir[k].op == "ASSIGN" and self.ir[k].dest == instr.dest:
                        return instr.dest
        return None
