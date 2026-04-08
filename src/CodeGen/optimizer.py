"""
IR Optimizer for CARAMEL Language

Performs optimization passes on the three-address code IR:
  1. Constant Folding   - evaluate constant expressions at compile time
  2. Constant Propagation - replace variables with known constant values
  3. Dead Code Elimination - remove unreachable code after unconditional jumps
  4. Strength Reduction  - replace expensive ops with cheaper equivalents
  5. Redundant Label Removal - remove labels that are never jumped to
"""

import operator

# Python operator functions for constant folding
_ARITH_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": lambda a, b: a // b if isinstance(a, int) and isinstance(b, int) and b != 0
                      else (a / b if b != 0 else None),
    "%": lambda a, b: a % b if b != 0 else None,
}

_REL_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">":  operator.gt,
    "<":  operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

_LOGIC_OPS = {
    "&&": lambda a, b: bool(a) and bool(b),
    "||": lambda a, b: bool(a) or bool(b),
}


def _is_constant(val):
    """Check if a value is a compile-time constant (int, float, bool, or quoted string)."""
    if isinstance(val, (int, float, bool)):
        return True
    if isinstance(val, str):
        # Quoted string literals
        if (val.startswith('"') and val.endswith('"')) or \
           (val.startswith("'") and val.endswith("'")):
            return True
        # Numeric strings
        try:
            float(val)
            return True
        except (ValueError, TypeError):
            return False
    return False


def _to_numeric(val):
    """Convert a constant value to a numeric type for arithmetic."""
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, bool):
        return 1 if val else 0
    if isinstance(val, str):
        try:
            if "." in val:
                return float(val)
            return int(val)
        except (ValueError, TypeError):
            return None
    return None


def _to_bool(val):
    """Convert a value to boolean for logical operations."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        if val in ("True", "true", "hot"):
            return True
        if val in ("False", "false", "cold"):
            return False
        n = _to_numeric(val)
        if n is not None:
            return n != 0
    return None


class IROptimizer:
    """
    Multi-pass optimizer for CARAMEL IR instructions.

    Each pass transforms the instruction list in place and may enable
    further optimizations on subsequent passes.
    """

    def __init__(self, instructions):
        self.instructions = list(instructions)
        self._constants = {}  # var -> known constant value

    def optimize(self, passes=3):
        """
        Run all optimization passes. Repeats up to `passes` times to
        catch cascading opportunities.
        Returns the optimized instruction list.
        """
        for _ in range(passes):
            prev_len = len(self.instructions)

            self._pass_constant_folding()
            self._pass_constant_propagation()
            self._pass_strength_reduction()
            self._pass_dead_code_elimination()
            self._pass_redundant_label_removal()

            # Stop early if nothing changed
            if len(self.instructions) == prev_len:
                break

        return self.instructions

    # ------------------------------------------------------------------
    # Pass 1: Constant Folding
    # ------------------------------------------------------------------

    def _pass_constant_folding(self):
        """Evaluate binary/unary operations on constants at compile time."""
        new_instrs = []
        for instr in self.instructions:
            if instr.op == "BINOP":
                result = self._try_fold_binop(instr)
                if result is not None:
                    # Replace BINOP with a simple ASSIGN
                    instr.op = "ASSIGN"
                    instr.arg1 = result
                    instr.arg2 = None
                    instr.extra = {}
            elif instr.op == "UNARYOP":
                result = self._try_fold_unaryop(instr)
                if result is not None:
                    instr.op = "ASSIGN"
                    instr.arg1 = result
                    instr.arg2 = None
                    instr.extra = {}
            new_instrs.append(instr)
        self.instructions = new_instrs

    def _try_fold_binop(self, instr):
        a, b = instr.arg1, instr.arg2
        op = instr.extra.get("binop", "")

        if not (_is_constant(a) and _is_constant(b)):
            return None

        # Arithmetic
        if op in _ARITH_OPS:
            na, nb = _to_numeric(a), _to_numeric(b)
            if na is not None and nb is not None:
                result = _ARITH_OPS[op](na, nb)
                return result

        # Relational
        if op in _REL_OPS:
            na, nb = _to_numeric(a), _to_numeric(b)
            if na is not None and nb is not None:
                return _REL_OPS[op](na, nb)

        # Logical
        if op in _LOGIC_OPS:
            ba, bb = _to_bool(a), _to_bool(b)
            if ba is not None and bb is not None:
                return _LOGIC_OPS[op](ba, bb)

        # String concatenation with two constant strings
        if op == "+" and isinstance(a, str) and isinstance(b, str):
            if a.startswith('"') and b.startswith('"'):
                return a[:-1] + b[1:]

        return None

    def _try_fold_unaryop(self, instr):
        a = instr.arg1
        op = instr.extra.get("unaryop", "")

        if not _is_constant(a):
            return None

        if op == "-":
            n = _to_numeric(a)
            if n is not None:
                return -n

        if op == "!":
            b = _to_bool(a)
            if b is not None:
                return not b

        return None

    # ------------------------------------------------------------------
    # Pass 2: Constant Propagation
    # ------------------------------------------------------------------

    def _pass_constant_propagation(self):
        """
        Track which variables hold known constant values and substitute them
        in subsequent instructions.
        """
        self._constants = {}

        for instr in self.instructions:
            # Function boundaries reset known constants
            if instr.op in ("FUNC_BEGIN", "FUNC_END", "LABEL"):
                self._constants.clear()
                continue

            # Track assignments of constants
            if instr.op == "ASSIGN" and instr.dest:
                if _is_constant(instr.arg1):
                    self._constants[instr.dest] = instr.arg1
                else:
                    # Variable is reassigned to something non-constant
                    self._constants.pop(instr.dest, None)

            # Substitute known constants in operands
            if instr.arg1 in self._constants:
                instr.arg1 = self._constants[instr.arg1]
            if instr.arg2 in self._constants:
                instr.arg2 = self._constants[instr.arg2]

            # Also substitute in extra args
            if "args" in instr.extra:
                instr.extra["args"] = [
                    self._constants.get(a, a) if isinstance(a, str) else a
                    for a in instr.extra["args"]
                ]

            # INPUT invalidates the target's known value
            if instr.op == "INPUT" and instr.dest:
                self._constants.pop(instr.dest, None)

    # ------------------------------------------------------------------
    # Pass 3: Strength Reduction
    # ------------------------------------------------------------------

    def _pass_strength_reduction(self):
        """Replace expensive operations with cheaper equivalents."""
        for instr in self.instructions:
            if instr.op != "BINOP":
                continue

            op = instr.extra.get("binop", "")
            a, b = instr.arg1, instr.arg2

            # x * 0 = 0
            if op == "*" and (_is_zero(a) or _is_zero(b)):
                instr.op = "ASSIGN"
                instr.arg1 = 0
                instr.arg2 = None
                instr.extra = {}
                continue

            # x * 1 = x, 1 * x = x
            if op == "*":
                if _is_one(b):
                    instr.op = "ASSIGN"
                    instr.arg1 = a
                    instr.arg2 = None
                    instr.extra = {}
                    continue
                if _is_one(a):
                    instr.op = "ASSIGN"
                    instr.arg1 = b
                    instr.arg2 = None
                    instr.extra = {}
                    continue

            # x + 0 = x, 0 + x = x
            if op == "+":
                if _is_zero(b):
                    instr.op = "ASSIGN"
                    instr.arg1 = a
                    instr.arg2 = None
                    instr.extra = {}
                    continue
                if _is_zero(a):
                    instr.op = "ASSIGN"
                    instr.arg1 = b
                    instr.arg2 = None
                    instr.extra = {}
                    continue

            # x - 0 = x
            if op == "-" and _is_zero(b):
                instr.op = "ASSIGN"
                instr.arg1 = a
                instr.arg2 = None
                instr.extra = {}
                continue

            # x / 1 = x
            if op == "/" and _is_one(b):
                instr.op = "ASSIGN"
                instr.arg1 = a
                instr.arg2 = None
                instr.extra = {}
                continue

            # x * 2 = x + x (cheaper on some architectures)
            if op == "*" and _to_numeric(b) == 2:
                instr.extra["binop"] = "+"
                instr.arg2 = a
                continue

    # ------------------------------------------------------------------
    # Pass 4: Dead Code Elimination
    # ------------------------------------------------------------------

    def _pass_dead_code_elimination(self):
        new_instrs = []
        skip = False
        NEVER_SKIP = {"BINOP", "UNARYOP", "ASSIGN", "LABEL", "FUNC_BEGIN", "FUNC_END"}

        for instr in self.instructions:
            if instr.op in ("LABEL", "FUNC_BEGIN", "FUNC_END"):
                skip = False
            if not skip or instr.op in NEVER_SKIP:
                new_instrs.append(instr)
            if instr.op == "GOTO" and not skip:
                skip = True
            if instr.op == "RETURN" and not skip:
                skip = True

        self.instructions = new_instrs
    # ------------------------------------------------------------------
    # Pass 5: Redundant Label Removal
    # ------------------------------------------------------------------

    def _pass_redundant_label_removal(self):
        """Remove labels that are never referenced by any jump instruction."""
        # Collect all labels that are jump targets
        referenced = set()
        for instr in self.instructions:
            if instr.op in ("GOTO", "IF_FALSE", "IF_TRUE"):
                if instr.dest:
                    referenced.add(instr.dest)

        # Keep labels that are referenced, plus special ones
        self.instructions = [
            instr for instr in self.instructions
            if instr.op != "LABEL" or instr.dest in referenced
        ]


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _is_zero(val):
    if isinstance(val, (int, float)):
        return val == 0
    if isinstance(val, bool):
        return not val
    return False


def _is_one(val):
    if isinstance(val, (int, float)):
        return val == 1
    if isinstance(val, bool):
        return val is True
    return False


def optimize_ir(instructions, passes=3):
    """Convenience function: optimize a list of IRInstruction objects."""
    opt = IROptimizer(instructions)
    return opt.optimize(passes=passes)
