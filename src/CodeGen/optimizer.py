"""
IR Optimizer for CARAMEL Language

PIPELINE POSITION:
  IRGenerator -> [IR list] -> IROptimizer -> [optimized IR list] -> CodeGenerator

PURPOSE:
  Takes the flat three-address code (TAC) IR list from IRGenerator and runs
  multiple improvement passes over it. The goal is to reduce the size and
  improve the quality of the generated Python code before CodeGenerator runs.
  All passes mutate IRInstruction objects in place or replace the instruction
  list entirely — no new AST or IR nodes are created.

PASSES (run in order, repeated up to N times):
  1. Constant Folding       — evaluate BINOP/UNARYOP on two literal constants
                              at compile time, replacing the instruction with
                              a simple ASSIGN. E.g. _t1 = 3 + 4 -> _t1 = 7.

  2. Constant Propagation   — track variables that hold known constant values
                              (via ASSIGN to a literal) and substitute the
                              literal directly into subsequent instructions that
                              read that variable. E.g. if x = 5, then
                              _t2 = x + 1 becomes _t2 = 5 + 1 (then folded to 6).
                              Resets at every FUNC_BEGIN/FUNC_END/LABEL boundary
                              to avoid propagating across control-flow edges.

  3. Strength Reduction      — replace expensive arithmetic operations with
                              cheaper equivalents where the result is identical:
                              x*0->0, x*1->x, x+0->x, x-0->x, x/1->x, x*2->x+x.
                              Guards against applying these to string literals
                              and churro (char) variables where arithmetic
                              has different semantics.

  4. Dead Code Elimination   — remove instructions that follow an unconditional
                              GOTO or RETURN and therefore can never execute.
                              Stops skipping at the next LABEL/FUNC_BEGIN/FUNC_END
                              since those may be legitimate jump targets.

  5. Redundant Label Removal — remove LABEL instructions whose name is never
                              referenced by any GOTO, IF_FALSE, or IF_TRUE.
                              Labels that are jumped to are collected first,
                              then all unreferenced ones are filtered out.

MULTI-PASS STRATEGY:
  Each full cycle of all 5 passes may expose new opportunities for others.
  For example, constant folding a BINOP may make a variable's value constant,
  enabling propagation, which may then enable further folding. The optimizer
  runs up to `passes` cycles (default 3) and stops early if a cycle produces
  no change in instruction count.

MODULE-LEVEL HELPERS (outside the class):
  _is_constant(val)   — True if val is a compile-time constant
  _to_numeric(val)    — coerce a constant to int/float for arithmetic
  _to_bool(val)       — coerce a constant to bool for logical ops
  _is_zero(val)       — True if val numerically equals 0
  _is_one(val)        — True if val numerically equals 1
  optimize_ir(instrs) — convenience wrapper: create optimizer, run, return result

OPERATION TABLES:
  _ARITH_OPS  — maps '+', '-', '*', '/', '%' to Python operator functions
  _REL_OPS    — maps '==', '!=', '>', '<', '>=', '<=' to comparison functions
  _LOGIC_OPS  — maps '&&', '||' to boolean lambda functions
"""

import operator

# ------------------------------------------------------------------
# Operation dispatch tables
# Used by _try_fold_binop to evaluate constant binary expressions.
# Division/modulo guard against zero — return None to skip folding
# rather than raising ZeroDivisionError at compile time.
# ------------------------------------------------------------------

# Arithmetic: used when both operands are numeric constants
_ARITH_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": lambda a, b: a / b if b != 0 else None,   # None = skip fold (div-by-zero)
    "%": lambda a, b: a % b if b != 0 else None,
}

# Relational: always produce bool; enable constant condition folding
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
    """
    Return True if val is a compile-time constant the optimizer can safely
    evaluate or substitute into other instructions.

    Constant categories:
      - Python int, float, bool       — always foldable (e.g. 42, 3.14, True)
      - Quoted string literals         — e.g. '"hello"' or "'a'" — BLENDLIT/CHURROLIT
                                         IR format where quotes are part of the value
      - Numeric strings                — e.g. '42' or '3.14' — stringified numbers
                                         from some IR generator paths

    Non-constants (return False): variable names, None, unquoted non-numeric strings.
    """
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
    """
    Coerce a constant to Python int or float for arithmetic/relational evaluation.
    Called by _try_fold_binop before applying _ARITH_OPS or _REL_OPS.

    Conversion rules:
      int/float       -> returned as-is
      bool            -> 1 (True) or 0 (False)  — bool is a subclass of int
      numeric str     -> int if no '.', float if '.' present
      non-numeric str -> None  (signals: this operand cannot be folded)
      None/other      -> None

    Returns None rather than raising so callers can skip folding safely.
    """
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
    """
    Coerce a constant to Python bool for logical operation folding.
    Called by _try_fold_binop when the operator is '&&' or '||'.

    Conversion rules:
      bool                         -> returned as-is
      int/float                    -> True if != 0, False if == 0
      'True' / 'true' / 'hot'     -> True   ('hot' is Caramel's true literal)
      'False' / 'false' / 'cold'  -> False  ('cold' is Caramel's false literal)
      numeric string               -> True if != 0 (via _to_numeric)
      anything else                -> None  (signals: cannot evaluate logically)
    """
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

    Instantiate with a list of IRInstruction objects from IRGenerator,
    then call optimize() to run all passes and get the cleaned list back.
    Each pass either rebuilds self.instructions from scratch (folding,
    dead code, label removal) or mutates instructions in place (propagation,
    strength reduction). Passes are run in sequence and the whole cycle
    repeats up to N times, stopping early when nothing changes.
    """

    def __init__(self, instructions):
        """
        Initialize the optimizer.

        State variables:
          self.instructions  — working copy of the IR list; mutated in place
                               by each pass and returned by optimize()
          self._constants    — dict mapping variable name -> known constant value,
                               used by _pass_constant_propagation() to track
                               which variables currently hold literal values.
                               Reset at every FUNC_BEGIN/FUNC_END/LABEL boundary.
        """
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
        """
        Pass 1: Constant Folding.
        Scan every instruction; when a BINOP or UNARYOP has both operands as
        compile-time constants, evaluate the result immediately and replace
        the instruction with a plain ASSIGN to the folded value.

        Examples:
          BINOP  _t1 = 3 + 4     -> ASSIGN _t1 = 7
          BINOP  _t2 = 10 > 3   -> ASSIGN _t2 = True
          UNARYOP _t3 = -5      -> ASSIGN _t3 = -5
          UNARYOP _t4 = !True   -> ASSIGN _t4 = False

        Delegates to:
          _try_fold_binop(instr)   — returns folded value or None
          _try_fold_unaryop(instr) — returns folded value or None
        """
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
        """
        Attempt to constant-fold a BINOP instruction.
        Returns the folded Python value if both operands are constants
        and the operation is supported, otherwise returns None.

        Fold order:
          1. Arithmetic (+, -, *, /, %)  — both operands numeric
          2. Relational (==, !=, >, etc.) — both operands numeric, returns bool
          3. Logical (&&, ||)            — both operands bool-coercible
          4. String concat (+)           — both operands quoted blend literals

        Division/modulo by zero returns None (not an error — just skip the fold).
        """
        a, b = instr.arg1, instr.arg2
        op = instr.extra.get("binop", "")        

        if not (_is_constant(a) and _is_constant(b)):
            return None

        # Arithmetic
        if op in _ARITH_OPS:
            na, nb = _to_numeric(a), _to_numeric(b)
            if na is not None and nb is not None:
                result = _ARITH_OPS[op](na, nb)
                # print(f"[FOLD_BINOP ARITH_OPS] {instr.dest} = {a!r} {op} {b!r} -> {result!r}")
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
        """
        Attempt to constant-fold a UNARYOP instruction.
        Returns the folded value if the operand is a constant, else None.

        Supported ops:
          '-'  — numeric negation: -5 -> -5, -3.0 -> -3.0
          '!'  — boolean NOT: !True -> False, !0 -> True
        """
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
        Pass 2: Constant Propagation.
        Track which variables hold known constant values (via ASSIGN to a literal)
        and substitute those literals directly into subsequent instructions that
        read those variables as operands.

        Algorithm:
          Walk instructions linearly, maintaining self._constants dict.
          For each instruction:
            a) If ASSIGN to a constant literal -> record in self._constants
            b) If ASSIGN to a non-constant -> remove from self._constants
            c) Substitute self._constants[arg1] and self._constants[arg2]
               into the current instruction where safe
            d) For PRINT args -> substitute known constants in the args list
            e) If INPUT -> invalidate the destination (runtime value, unknowable)

        Boundary resets (self._constants.clear()):
          FUNC_BEGIN, FUNC_END, LABEL — control flow edges may bring different
          values into a variable; clearing is conservative but correct.

        Substitution guards (these are never substituted):
          - MEMBER_SET arg1 (field name): must stay as-is — it's not a variable
          - MEMBER_ACC/MEMBER_SET/CLASS_FIELD arg2: same reason
          - churro literals ('a', 'b', etc.) into non-churro BINOP destinations:
            prevents incorrect type inference downstream in codegen

        Special post-ASSIGN tracking:
          - bool constants are NOT tracked — they get coerced to 'hot'/'cold'
            for blend variables, so propagating the raw bool gives wrong types
          - float assigned to bean destination -> track as int (truncated)
          - int/float assigned to churro destination -> track as chr() char
            e.g. churro c = 96 -> stores "'`'" for downstream type()/print()
          - Everything else tracked as-is
        """
        self._constants = {}

        for instr in self.instructions:
            # Function boundaries reset known constants
            if instr.op in ("FUNC_BEGIN", "FUNC_END", "LABEL"):
                self._constants.clear()
                continue
            # if instr.op == "ASSIGN" and instr.dest:
            #     print(f"[PROP] {instr.dest} = {instr.arg1!r} -> constants[{instr.dest}] = {instr.arg1 if _is_constant(instr.arg1) else 'REMOVED'}")

            # Track assignments of constants
            if instr.op == "ASSIGN" and instr.dest:
                if _is_constant(instr.arg1):
                    self._constants[instr.dest] = instr.arg1
                else:
                    # Variable is reassigned to something non-constant
                    self._constants.pop(instr.dest, None)

            # Substitute known constants in operands
            old_arg1 = instr.arg1
            if instr.arg1 in self._constants:
                if instr.op in ("MEMBER_SET",):
                    pass 
                else:
                    val = self._constants[instr.arg1]
                # if instr.arg1 == "i":
                #     print(f"[OPT SUBST] substituting i -> {val!r} in op={instr.op} dest={instr.dest}")

                is_ir_churro = isinstance(val, str) and len(val) == 3 and val[0] == "'" and val[-1] == "'"
                # Don't substitute churro into non-churro BINOP
                if is_ir_churro and instr.op == "BINOP":
                    dest_type = None
                    for di in self.instructions:
                        if di.op == "DECLARE" and di.dest == instr.dest:
                            dest_type = di.extra.get("type")
                            break
                    if dest_type not in ("churro", None):
                        pass  # skip substitution
                    else:
                        instr.arg1 = val
                elif not is_ir_churro or instr.op == "ASSIGN":
                    instr.arg1 = val
                    
            if instr.arg2 in self._constants:
                val = self._constants[instr.arg2]
                # don't substitute field names in member access/set
                if instr.op in ("MEMBER_ACC", "MEMBER_SET", "CLASS_FIELD"):
                    pass
                elif not (isinstance(val, str) and len(val) == 3 and val[0] == "'" and val[-1] == "'") \
                or instr.op == "ASSIGN":
                    instr.arg2 = val
            
            # if old_arg1 != instr.arg1:
                # print(f"[CONST_PROP] {instr.dest}: arg1 {old_arg1!r} -> {instr.arg1!r}")

            # Also substitute in extra args
            if "args" in instr.extra:
                old_args = list(instr.extra["args"])
                instr.extra["args"] = [
                    self._constants.get(a, a) if isinstance(a, str) and not (
                        isinstance(self._constants.get(a, a), str) and
                        len(self._constants.get(a, a)) == 3 and
                        self._constants.get(a, a)[0] == "'" and
                        self._constants.get(a, a)[-1] == "'"
                    ) else a
                    for a in instr.extra["args"]
                ]
                if old_args != instr.extra["args"]:
                    print(f"[ARGS SUBST] {old_args} -> {instr.extra['args']}")
            
            if instr.op == "ASSIGN" and instr.dest:
                if _is_constant(instr.arg1):
                    if isinstance(instr.arg1, bool):
                        # Don't track bool constants — they get coerced to "hot"/"cold"
                        # for blend variables, so propagating the raw bool would give
                        # wrong type inference downstream
                        self._constants.pop(instr.dest, None)
                    elif isinstance(instr.arg1, (int, float)) and not isinstance(instr.arg1, bool):
                        # For numeric literals, check the declared type of the destination
                        # so we store the already-coerced value rather than the raw literal
                        dest_type = None
                        for di in self.instructions:
                            if di.op == "DECLARE" and di.dest == instr.dest:
                                dest_type = di.extra.get("type")
                                break
                        if dest_type == "bean" and isinstance(instr.arg1, float):
                            # drip literal assigned to bean -> truncate to int
                            # e.g. bean n = 4.0 -> propagate 4 not 4.0
                            self._constants[instr.dest] = int(instr.arg1)
                        elif dest_type == "churro":
                            # numeric literal assigned to churro -> convert to char
                            # e.g. churro c = 96 -> propagate '`' not 96
                            # so downstream type() and print() see the actual char
                            try:
                                char = chr(int(instr.arg1))
                                print(f"[CHURRO PROP] dest={instr.dest} arg1={instr.arg1!r} -> storing '{char}'")
                                self._constants[instr.dest] = f"'{char}'"
                            except (ValueError, TypeError, OverflowError):
                                self._constants.pop(instr.dest, None)
                        else:
                            self._constants[instr.dest] = instr.arg1
                    elif dest_type == "bean":
                        # If arg1 is a churro literal, store ord() value
                        val = instr.arg1
                        if isinstance(val, str) and len(val) == 3 and val[0] == "'" and val[-1] == "'":
                            self._constants[instr.dest] = ord(val[1])
                        elif isinstance(val, float):
                            self._constants[instr.dest] = int(val)
                        else:
                            self._constants[instr.dest] = val
                    else:
                        self._constants[instr.dest] = instr.arg1
                else:
                    self._constants.pop(instr.dest, None)

            # INPUT invalidates the target's known value since it comes from
            # runtime user input and cannot be known at compile time
            if instr.op == "INPUT" and instr.dest:
                self._constants.pop(instr.dest, None)

    # ------------------------------------------------------------------
    # Pass 3: Strength Reduction
    # ------------------------------------------------------------------

    def _pass_strength_reduction(self):
        """
        Pass 3: Strength Reduction.
        Replace expensive BINOP patterns with cheaper equivalents
        when one operand is a known constant identity value.

        Rules applied (in order, first match wins per instruction):
          x * 0  -> 0         (zero product)
          x * 1  -> x         (multiplicative identity)
          1 * x  -> x
          x + 0  -> x         (additive identity)
          0 + x  -> x
          x - 0  -> x
          x / 1  -> x         (division identity)
          x * 2  -> x + x     (cheaper on some CPUs; also enables further folding)

        Guards:
          - String literals are never simplified (+ is concatenation)
          - churro (char) variables are never simplified — arithmetic on
            chars has different semantics (ord/chr) and must not be elided
          - bool values are excluded from identity checks to avoid treating
            True (==1) or False (==0) as identity elements

        Inner helpers (defined once per call to avoid repeated definitions):
          _is_string_literal(v)     — True if v is a quoted string
          _is_churro_literal(v)     — True if v is a 3-char quoted churro literal
          _is_churro_var(v, instrs) — True if v is declared as churro type
          _safe_zero(v)             — _is_zero(v) excluding bools
          _safe_one(v)              — _is_one(v) excluding bools
        """
        for instr in self.instructions:
            if instr.op != "BINOP":
                continue

            op = instr.extra.get("binop", "")
            a, b = instr.arg1, instr.arg2

            def _is_string_literal(v):
                """True if v is any quoted string — blend or churro literal. Guards + from being elided on strings."""
                return isinstance(v, str) and (v.startswith("'") or v.startswith('"'))
            
            def _is_churro_literal(v):
                """True if v is a single-char churro literal like "'a'". Exactly 3 chars: quote + char + quote."""
                return isinstance(v, str) and len(v) == 3 and v[0] == "'" and v[-1] == "'"
            
            def _is_churro_var(v, instructions):
                """
                Return True if v is either a churro literal (3-char quoted string
                like "'a'") or a variable explicitly declared as churro type.
                Used to guard strength reduction from eliding char arithmetic.
                """
                if _is_churro_literal(v):
                    return True
                for instr in instructions:
                    if instr.op == "DECLARE" and instr.dest == v and instr.extra.get("type") == "churro":
                        return True
                return False
            
            def _safe_zero(v):
                """_is_zero but excludes bools — prevents treating False (==0) as numeric zero."""
                if isinstance(v, bool): return False
                return _is_zero(v)

            def _safe_one(v):
                """_is_one but excludes bools — prevents treating True (==1) as numeric one."""
                if isinstance(v, bool): return False
                return _is_one(v)

            # x * 0 = 0
            if op == "*" and (_safe_zero(a) or _safe_zero(b)):
                instr.op = "ASSIGN"
                instr.arg1 = 0
                instr.arg2 = None
                instr.extra = {}
                continue

            # x * 1 = x, 1 * x = x
            if op == "*" and _to_numeric(b) == 1 and not isinstance(b, bool) and not _is_churro_var(a, self.instructions):
                if _safe_one(b) and not _is_string_literal(a):
                    instr.op = "ASSIGN"
                    instr.arg1 = a
                    instr.arg2 = None
                    instr.extra = {}
                    continue
                if _safe_one(a) and not _is_string_literal(b):
                    instr.op = "ASSIGN"
                    instr.arg1 = b
                    instr.arg2 = None
                    instr.extra = {}
                    continue

            # x + 0 = x, 0 + x = x
            if op == "+":
                if _safe_zero(b) and not _is_string_literal(a) and not _is_churro_var(a, self.instructions):
                    instr.op = "ASSIGN"
                    instr.arg1 = a
                    instr.arg2 = None
                    instr.extra = {}
                    continue
                if _safe_zero(a) and not _is_string_literal(b) and not _is_churro_var(a, self.instructions):
                    instr.op = "ASSIGN"
                    instr.arg1 = b
                    instr.arg2 = None
                    instr.extra = {}
                    continue

            # x - 0 = x
            if op == "-" and _safe_zero(b) and not _is_string_literal(a):
                instr.op = "ASSIGN"
                instr.arg1 = a
                instr.arg2 = None
                instr.extra = {}
                continue

            # x / 1 = x
            if op == "/" and _safe_one(b) and not _is_string_literal(a):
                instr.op = "ASSIGN"
                instr.arg1 = a
                instr.arg2 = None
                instr.extra = {}
                continue

            # x * 2 = x + x
            if op == "*" and _to_numeric(b) == 2 and not isinstance(b, bool) and not _is_churro_var(a, self.instructions):
                instr.extra["binop"] = "+"
                instr.arg2 = a
                continue
    # ------------------------------------------------------------------
    # Pass 4: Dead Code Elimination
    # ------------------------------------------------------------------

    def _pass_dead_code_elimination(self):
        """
        Pass 4: Dead Code Elimination.
        Remove instructions that appear after an unconditional GOTO or RETURN
        and therefore can never be reached at runtime.

        Algorithm:
          - Walk instructions linearly, tracking a 'skip' flag
          - GOTO or RETURN sets skip=True
          - LABEL, FUNC_BEGIN, FUNC_END always resets skip=False (they may be
            jump targets or function boundaries referenced from elsewhere)
          - Instructions in NEVER_SKIP are always kept regardless of skip flag
            (BINOP, UNARYOP, ASSIGN, LABEL, FUNC_BEGIN, FUNC_END)
          - All other instructions while skip=True are dropped

        Example:
          GOTO L1        ← kept
          ASSIGN x = 5  ← DROPPED (unreachable after goto)
          LABEL L1       ← kept (resets skip, may be jumped to)
        """
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
        """
        Pass 5: Redundant Label Removal.
        Remove LABEL instructions whose name is never the target of any
        GOTO, IF_FALSE, or IF_TRUE instruction.

        Algorithm:
          1. Collect all jump targets into a 'referenced' set by scanning
             every GOTO, IF_FALSE, and IF_TRUE instruction's dest field
          2. Filter self.instructions, keeping:
             - All non-LABEL instructions
             - LABEL instructions whose dest is in 'referenced'

        This cleans up labels left behind after dead code elimination removes
        the GOTO that previously referenced them.
        """
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
    """
    Return True if val numerically equals zero.
    Used by strength reduction to detect x+0, x-0, x*0 patterns.
    Note: bool values also return True/False (False==0, True==1) since
    bool is a subclass of int — callers use _safe_zero() to exclude bools.
    """
    if isinstance(val, (int, float)):
        return val == 0
    if isinstance(val, bool):
        return not val
    return False


def _is_one(val):
    """
    Return True if val numerically equals one.
    Used by strength reduction to detect x*1, x/1 patterns.
    Note: True==1, so bool True would match — callers use _safe_one() to exclude bools.
    """
    if isinstance(val, (int, float)):
        return val == 1
    if isinstance(val, bool):
        return val is True
    return False


def optimize_ir(instructions, passes=3):
    """
    Convenience wrapper — create an IROptimizer, run all passes, return the result.
    Called by the compiler pipeline instead of instantiating IROptimizer directly.

    Parameters:
      instructions — list of IRInstruction objects from IRGenerator
      passes       — number of full optimization cycles to run (default 3)

    Returns the optimized list of IRInstruction objects.
    """
    opt = IROptimizer(instructions)
    
    return opt.optimize(passes=passes)
