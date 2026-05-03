"""
Final Code Generator for CARAMEL Language

Translates optimized IR (three-address code) into executable Python source code.
The generated Python code can be executed directly to run the CARAMEL program.

Architecture:
  1. Walk the IR instruction list linearly
  2. Maintain an indentation stack for function/control-flow scoping
  3. Generate idiomatic Python for each IR operation
  4. Execute the generated code in a sandboxed environment with captured I/O
"""

import sys
import io
import traceback

# ------------------------------------------------------------------
# Structured Code Generator (higher quality output)
# ------------------------------------------------------------------

class StructuredCodeGenerator:
    """
    A higher-level code generator that produces cleaner Python output by
    reconstructing control flow structures (if/while/for) from the IR
    rather than emitting flat goto-style code.

    This walks the IR and builds Python directly, recognizing patterns:
      - FUNC_BEGIN...FUNC_END → def blocks
      - IF_FALSE + LABEL + GOTO + LABEL → if/else blocks
      - LABEL + IF_FALSE + GOTO + LABEL → while loops
      - DECLARE + ASSIGN + LABEL + IF_FALSE...GOTO + LABEL → for loops
    """

        # CARAMEL type → Python default value
    DEFAULT_VALUES = {
        "bean": "0",
        "drip": "0.0",
        "churro": "''",
        "temp": "False",
        "blend": '""',
        "mug": "{}",
    }

    # CARAMEL type → Python type coercion
    TYPE_COERCE = {
        "bean": "int",
        "drip": "float",
        "churro": "str",
        "temp": "bool",
        "blend": "str",
    }

    def __init__(self, ir_instructions):
        self.ir = list(ir_instructions)
        self._lines = []
        self._indent = 0
        self._declared = set()
        self._in_func = False

        
        # for i, instr in enumerate(ir_instructions):
        #     print(f"[{i:03}] {instr}")

    def generate(self):
        self._emit_header()
        self._translate(0, len(self.ir))
        self._emit_footer()
        return "\n".join(self._lines)

    def execute(self, input_values=None):
        code = self.generate()
        captured_out = io.StringIO()
        input_list = list(input_values) if input_values else []
        input_idx = [0]

        def mock_input(prompt=""):
            if prompt:
                captured_out.write(str(prompt))
            if input_idx[0] < len(input_list):
                val = input_list[input_idx[0]]
                input_idx[0] += 1
                return val
            return ""

        exec_globals = {
            "__builtins__": {
                "print": lambda *a, **kw: print(*a, file=captured_out, **kw),
                "input": mock_input,
                "int": int, "float": float, "str": str, "bool": bool,
                "len": len, "range": range, "abs": abs, "max": max, "min": min,
                "True": True, "False": False, "None": None,
                "isinstance": isinstance, "chr": chr, "ord": ord,
            },
        }

        error = None
        try:
            exec(code, exec_globals)
        except Exception as e:
            print(f"[ANALYSIS CRASH] {e}")
            traceback.print_exc()
            error = f"{type(e).__name__}: {e}"

        return {
            "output": captured_out.getvalue(),
            "error": error,
            "code": code,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, line):
        self._lines.append("    " * self._indent + line)

    def _emit_raw(self, line):
        self._lines.append(line)

    def _push(self):
        self._indent += 1

    def _pop(self):
        if self._indent > 0:
            self._indent -= 1

    def _py_func_name(self, name):
        if not name:
            return "_anon"
        if name == "cup":
            return "_main_cup"
        if name == "__sift__":
            return "len"
        if name == "__sqrt__":  
            return "math.sqrt"
        if name == "__ceil__":  
            return "math.ceil"
        if name == "__floor__": 
            return "math.floor"
        if name == "__pow__":   
            return "math.pow"
        if name == "__type__":  
            return "_caramel_type"
        if name.startswith("class_"):
            return f"_class_{name[6:]}"
        safe = str(name).replace(".", "_").replace("?", "_q").replace("@", "_at")
        
        return f"_func_{safe}"

    def _py_var(self, name):
        if not name:
            return "_unknown"
        if isinstance(name, (int, float, bool)):
            return str(name)
        s = str(name)
        if s.startswith("_t"):
            return s
        if s.startswith("order."):
            field = s[6:]
            return f'_order["{field}"]'
        # Check if this is a global variable stored in _order
        if not s.startswith('"') and not s.startswith("'"):
            if self._is_global_var(s):
                return f'_order["{s}"]'

        safe = s.replace(".", "_").replace("?", "_q").replace("@", "_at")
        if safe in ("class", "def", "return", "if", "else", "elif", "for",
                     "while", "break", "continue", "pass", "import", "from",
                     "True", "False", "None", "and", "or", "not", "in", "is"):
            safe = f"_{safe}"
        return safe

    def _py_val(self, val):
        """Convert an IR value to a Python expression string."""
        if val is None:
            return "None"
        if isinstance(val, bool):
            return "True" if val else "False"
        if isinstance(val, int):
            return str(val)
        if isinstance(val, float):
            return repr(val)
        s = str(val)
        eb = getattr(self, '_elif_binops', {})
        if s.startswith('_t') and s in eb:
            print(f"[STRUCT CODEGEN PY_VAL] resolving {s!r} -> {eb[s]!r} from _elif_binops")
            return eb[s]
        # String literals
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
            return s
        # Temp vars
        if s.startswith("_t"):
            return s
        # Order access
        if s.startswith("order."):
            field = s[6:]
            return f'_order["{field}"]'
        if not s.startswith("_t") and not s.startswith('"') and not s.startswith("'"):
            if self._is_global_var(s):
                return f'_order["{s}"]'
        # Regular variable reference
        return self._py_var(s)

    # RELATED TO BINOP
    def _get_var_type(self, var_name):
        if not isinstance(var_name, str):
            return None
        if len(var_name) == 3 and var_name[0] == "'" and var_name[-1] == "'":
            return "churro"
        if len(var_name) >= 2 and var_name[0] == '"' and var_name[-1] == '"':
            return "blend"
        for instr in self.ir:
            if instr.op == "DECLARE" and instr.dest == var_name:
                return instr.extra.get("type")
        for instr in self.ir:
            if instr.dest != var_name:
                continue
            if instr.op == "ASSIGN":
                return self._get_var_type(instr.arg1)
            if instr.op in ("BINOP", "CONCAT"):
                t1 = self._get_var_type(instr.arg1)
                t2 = self._get_var_type(instr.arg2)
                binop = instr.extra.get("binop", "")
                if binop in (">", "<", ">=", "<=", "==", "!=", "&&", "||"):
                    return "temp"
                if binop in ("+", "-", "*", "/", "%"):
                    if "churro" in (t1, t2) and "blend" not in (t1, t2):
                        return "bean"
                if "blend" in (t1, t2):
                    return "blend"
                if "churro" in (t1, t2):
                    return "churro"
                return t1 or t2
            if instr.op == "ARR_LOAD":
                return self._get_var_type(instr.arg1)
            if instr.op == "CALL":
                fn = instr.arg1
                if fn == "__sift__":  return "bean"
                if fn == "__sqrt__":  return "drip"
                if fn == "__ceil__":  return "bean"
                if fn == "__floor__": return "bean"
                if fn == "__pow__":   return "drip"
                if fn == "__type__":  return "blend"
                if fn == "__rand__":
                    return "drip" if instr.extra.get("use_float") else "bean"
        return None
    
    def _emit_pour_continue(self, goto_dest):
        """Emit pour loop update instructions before continue for skip support."""
        # Find the POUR_UPDATE label and emit its instructions
        update_label = goto_dest
        for j in range(len(self.ir)):
            if self.ir[j].op == "LABEL" and self.ir[j].dest == update_label:
                k = j + 1
                while k < len(self.ir) and self.ir[k].op not in ("GOTO", "LABEL", "IF_FALSE"):
                    self._gen_simple(self.ir[k], k)
                    k += 1
                break
        self._emit("continue")
    
    # ------------------------------------------------------------------
    # Header / Footer
    # ------------------------------------------------------------------

    def _emit_header(self):
        self._emit_raw("# === Generated CARAMEL Program ===")
        self._emit_raw("")
        self._emit_raw("import math")
        self._emit_raw("import random")
        self._emit_raw("def _caramel_to_bool(val):")
        self._emit_raw("    if isinstance(val, bool): return val")
        self._emit_raw("    if isinstance(val, (int, float)): return val != 0")
        self._emit_raw("    if isinstance(val, str): return len(val) > 0")
        self._emit_raw("    return bool(val)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input(prompt=''):")
        self._emit_raw("    return input(prompt)")
        self._emit_raw("")
        self._emit_raw("def _caramel_type(val):")
        self._emit_raw("    if isinstance(val, bool): return 'temp'")
        self._emit_raw("    if isinstance(val, int): return 'bean'")
        self._emit_raw("    if isinstance(val, float): return 'drip'")
        self._emit_raw("    if isinstance(val, str) and len(val) == 1: return 'churro'")
        self._emit_raw("    if isinstance(val, str): return 'blend'")
        self._emit_raw("    if isinstance(val, list): return 'array'")
        self._emit_raw("    return 'unknown'")
        
        self._emit_raw("class _CaramelEarlyExit(Exception):")
        self._emit_raw("    pass")
        self._emit_raw("")
        self._emit_raw("class _CaramelLoopTimeout(Exception):")
        self._emit_raw("    pass")
        self._emit_raw("")
        # --- Runtime loop guard -------------------------------------------------
        # Each while/pour/taste-till loop is assigned a unique ID string.
        # _caramel_check_loop() increments the iteration counter for that loop
        # and raises _CaramelLoopTimeout when the hard limit is exceeded.
        # This prevents infinite loops from freezing the IDE or the executable.
        self._emit_raw("_CARAMEL_MAX_ITERATIONS = 100_000  # Hard iteration limit per loop")
        self._emit_raw("_caramel_loop_counters = {}        # loop_id -> iteration count")
        self._emit_raw("")
        self._emit_raw("def _caramel_check_loop(loop_id):")
        self._emit_raw("    _caramel_loop_counters[loop_id] = _caramel_loop_counters.get(loop_id, 0) + 1")
        self._emit_raw("    if _caramel_loop_counters[loop_id] > _CARAMEL_MAX_ITERATIONS:")
        self._emit_raw("        del _caramel_loop_counters[loop_id]  # reset for safety")
        self._emit_raw("        raise _CaramelLoopTimeout(")
        self._emit_raw("            f'Infinite loop detected: loop {loop_id!r} exceeded '")
        self._emit_raw("            f'{_CARAMEL_MAX_ITERATIONS:,} iterations.'")
        self._emit_raw("        )")
        self._emit_raw("")
        self._emit_raw("def _caramel_reset_loop(loop_id):")
        self._emit_raw("    _caramel_loop_counters.pop(loop_id, None)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input_bean(prompt=''):")
        self._emit_raw("    raw = input(prompt).strip()")
        self._emit_raw("    neg = raw.startswith('-')")
        self._emit_raw("    digits = raw[1:] if neg else raw")
        self._emit_raw("    if not digits.isdigit() or len(digits) > 10:")
        self._emit_raw("        print('INVALID INPUT: Number too large.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    if neg and digits == '0':")  
        self._emit_raw("        print('INVALID INPUT: Negative symbol and a zero are not allowed.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    return int(raw)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input_drip(prompt=''):")
        self._emit_raw("    raw = input(prompt).strip()")
        self._emit_raw("    neg = raw.startswith('-')")
        self._emit_raw("    body = raw[1:] if neg else raw")
        self._emit_raw("    if '.' in body:")
        self._emit_raw("        parts = body.split('.')")
        self._emit_raw("        if len(parts) != 2:")
        self._emit_raw("            print('INVALID INPUT')")
        self._emit_raw("            raise _CaramelEarlyExit()")
        self._emit_raw("        whole, frac = parts[0], parts[1]")
        self._emit_raw("    else:")
        self._emit_raw("        whole, frac = body, ''")
        self._emit_raw("    if not whole.isdigit() or (frac and not frac.isdigit()):")
        self._emit_raw("        print('INVALID INPUT')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    if len(whole) > 10 or len(frac) > 10:")
        self._emit_raw("        print('INVALID INPUT: Number too large.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    if neg and float(body) == 0.0:")
        self._emit_raw("        print('INVALID INPUT: Negative symbol and a zero are not allowed.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    return float(raw)")
        self._emit_raw("")

        self._emit_raw("def _caramel_input_temp(prompt=''):")
        self._emit_raw("    raw = input(prompt).strip().lower()")
        self._emit_raw("    if raw in ('hot', 'true'):")
        self._emit_raw("        return True")
        self._emit_raw("    if raw in ('cold', 'false'):")
        self._emit_raw("        return False")
        self._emit_raw("    try:")
        self._emit_raw("        n = float(raw)")
        self._emit_raw("        return n != 0")
        self._emit_raw("    except ValueError:")
        self._emit_raw("        print('INVALID INPUT: Expected hot/cold, true/false, or a number.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("")
        
        self._emit_raw("def _caramel_print(*args, end='\\n'):")
        self._emit_raw("    parts = []")
        self._emit_raw("    for a in args:")
        self._emit_raw("        if isinstance(a, bool):")
        self._emit_raw('            parts.append("hot" if a else "cold")')
        self._emit_raw("        elif isinstance(a, str) and len(a) >= 2 and a[0] == '\"' and a[-1] == '\"':")
        self._emit_raw("            parts.append(a[1:-1])")
        self._emit_raw("        elif isinstance(a, str) and len(a) >= 2 and a[0] == \"'\" and a[-1] == \"'\":")
        self._emit_raw("            parts.append(a[1:-1])")
        self._emit_raw("        else:")
        self._emit_raw("            parts.append(str(a))")
        self._emit_raw('    print("".join(parts), end="")')
        self._emit_raw("")
        self._emit_raw("_order = {}")
        self._emit_raw("_functions = {}")
        self._emit_raw("")

    def _emit_footer(self):
        self._emit_raw("")
        self._emit_raw("# --- Entry point ---")
        self._emit_raw("try:")
        self._emit_raw("    _main_cup()")
        self._emit_raw("except _CaramelEarlyExit:")
        self._emit_raw("    pass")

    # ------------------------------------------------------------------
    # Structured Translation
    # ------------------------------------------------------------------

    def _translate(self, start, end):
        """Translate IR instructions from start to end index."""
        i = start
        while i < end and i < len(self.ir):
            instr = self.ir[i]

            if instr.op == "FUNC_BEGIN":
                i = self._gen_function(i)
                continue

            if instr.op == "LABEL":
                # Check if this is a loop header
                loop_end = self._detect_while_loop(i)
                if loop_end is not None:
                    i = self._gen_while_loop(i, loop_end)
                    continue
                # Skip labels in structured mode
                i += 1
                continue

            if instr.op == "IF_FALSE":
                i = self._gen_if_block(i, end)
                continue

            if instr.op == "IF_TRUE":
                # do-while continuation
                cond = self._py_val(instr.arg1)
                # This is part of a do-while - it should be handled by the loop
                i += 1
                continue

            if instr.op in ("GOTO",):
                i += 1  # Skip gotos in structured code
                continue

            
            # Regular instructions
            i = self._gen_simple(instr, i)

    def _gen_function(self, start):
        """Generate a function definition block."""
        try:
            instr = self.ir[start]
            func_name = instr.dest
            py_name = self._py_func_name(func_name)

            # Find FUNC_END
            func_end = start + 1
            depth = 1
            while func_end < len(self.ir):
                if self.ir[func_end].op == "FUNC_BEGIN":
                    depth += 1
                elif self.ir[func_end].op == "FUNC_END":
                    depth -= 1
                    if depth == 0:
                        break
                func_end += 1

            # Collect parameters
            params = []
            for j in range(start + 1, func_end):
                if self.ir[j].op == "DECLARE" and self.ir[j].extra.get("param"):
                    params.append(self.ir[j].dest)

            param_str = ", ".join(params)
            self._emit(f"def {py_name}({param_str}):")
            self._push()

            # Track declared
            old_declared = self._declared.copy()
            old_in_func = self._in_func  
            self._in_func = True    
            self._declared = set(params)

            # Emit body (skip param declarations)
            body_start = start + 1
            has_body = False
            bi = body_start
            while bi < func_end:
                instr_i = self.ir[bi]
                if instr_i.op == "DECLARE" and instr_i.extra.get("param"):
                    bi += 1
                    continue
                has_body = True
                # Use structured translation for the body
                if instr_i.op == "LABEL":
                    loop_end = self._detect_while_loop(bi)
                    if loop_end is not None and loop_end <= func_end:
                        bi = self._gen_while_loop(bi, loop_end)
                        continue
                    bi += 1
                    continue
                if instr_i.op == "IF_FALSE":
                    bi = self._gen_if_block(bi, func_end)
                    continue
                if instr_i.op in ("GOTO",):
                    bi += 1
                    continue
                # print(f"[FUNC_WALK CODEGEN BEFORE GEN_SIMPLE] bi={bi} op={instr_i.op} dest={instr_i.dest} arg1={instr_i.arg1!r} arg2={getattr(instr_i, 'arg2', None)!r}")
                bi = self._gen_simple(instr_i, bi)

            if not has_body:
                self._emit("pass")

            self._pop()
            self._emit("")
            self._declared = old_declared
            self._in_func = old_in_func
            return func_end + 1
        except Exception as e:
            print(f"[GEN_FUNCTION FATAL] start={start}: {e}")
            traceback.print_exc()
            return start + 1

    def _detect_while_loop(self, label_idx):
        """
        Check if a LABEL at label_idx starts a while-loop pattern:
          LABEL L_start
          ... (condition)
          IF_FALSE cond -> L_end
          ... (body)
          GOTO L_start
          LABEL L_end
        Returns L_end index if pattern found, else None.
        """
        if label_idx >= len(self.ir):
            return None
        label = self.ir[label_idx]
        if label.op != "LABEL":
            return None

        start_label = label.dest
        if not start_label:
            return None

        # Only detect loop patterns (WHILE_START, POUR_START, DOWHILE_START)
        is_loop_label = any(prefix in start_label for prefix in
                           ("WHILE_START", "POUR_START",
                            "DOWHILE_START"))
        if not is_loop_label:
            return None

        # Find the LAST GOTO back to this label (the actual back-edge)
        back_edge = None
        for j in range(label_idx + 1, min(label_idx + 2000, len(self.ir))):
            if self.ir[j].op == "GOTO" and self.ir[j].dest == start_label:
                back_edge = j
            # Stop at FUNC boundaries
            if self.ir[j].op in ("FUNC_BEGIN", "FUNC_END"):
                break

        if back_edge is not None:
            if back_edge + 1 < len(self.ir) and self.ir[back_edge + 1].op == "LABEL":
                return back_edge + 1
            return back_edge
        return None

    def _gen_while_loop(self, start, end):
        # Find the IF_FALSE condition
        cond_idx = None
        cond_val = None
        for j in range(start + 1, end):
            if self.ir[j].op == "IF_FALSE":
                cond_idx = j
                cond_val = self._py_val(self.ir[j].arg1)
                break

        # Find the back-GOTO (GOTO that points back to our start label)
        start_label_name = self.ir[start].dest
        back_goto_idx = None
        for j in range(start + 1, end + 1):
            if j < len(self.ir) and self.ir[j].op == "GOTO" and self.ir[j].dest == start_label_name:
                back_goto_idx = j 

        # Emit condition computation before the while header
        if cond_idx:
            for j in range(start + 1, cond_idx):
                if self.ir[j].op not in ("LABEL", "GOTO", "IF_FALSE", "IF_TRUE"):
                    self._gen_simple(self.ir[j], j)

        if cond_val:
            self._emit(f"while _caramel_to_bool({cond_val}):")
        else:
            self._emit("while True:")

        self._push()

        # --- Runtime infinite-loop guard ----------------------------------------
        # Emit a unique loop-ID string derived from the IR position so that
        # nested loops each get their own independent counter.  The guard
        # raises _CaramelLoopTimeout after _CARAMEL_MAX_ITERATIONS iterations.
        loop_guard_id = f"loop_{start}"
        self._emit(f"_caramel_check_loop({loop_guard_id!r})")
        # -----------------------------------------------------------------------

        # Body runs from after IF_FALSE up to (but not including) the back-GOTO
        body_start = (cond_idx + 1) if cond_idx else start + 1
        body_end = back_goto_idx if back_goto_idx is not None else end

        has_body = False
        bi = body_start
        while bi < body_end and bi < len(self.ir):
            instr_i = self.ir[bi]

            if instr_i.op == "LABEL":
                inner_loop = self._detect_while_loop(bi)
                if inner_loop is not None:
                    bi = self._gen_while_loop(bi, inner_loop)
                    has_body = True
                    continue
                bi += 1
                continue
            if instr_i.op == "IF_FALSE":
                bi = self._gen_if_block(bi, body_end)
                has_body = True
                continue
            if instr_i.op == "IF_TRUE":
                cond = self._py_val(instr_i.arg1)
                self._emit(f"if not _caramel_to_bool({cond}):")
                self._push()
                self._emit("break")
                self._pop()
                has_body = True
                bi += 1
                continue
            if instr_i.op == "GOTO":
                if instr_i.dest and ("END" in instr_i.dest or instr_i.dest == start_label_name):
                    if "END" in instr_i.dest:
                        self._emit("break")
                    else:
                        self._emit("continue")
                    has_body = True
                bi += 1
                continue

            self._gen_simple(instr_i, bi)
            has_body = True
            bi += 1

        if not has_body:
            self._emit("pass")

        # Re-emit condition computation at end of body so while sees fresh _t
        if cond_idx:
            for j in range(start + 1, cond_idx):
                if self.ir[j].op not in ("LABEL", "GOTO", "IF_FALSE", "IF_TRUE"):
                    self._gen_simple(self.ir[j], j)

        self._pop()
        # Reset the loop counter once the loop exits normally (not via exception)
        self._emit(f"_caramel_reset_loop({loop_guard_id!r})")
        return end + 1
    
    def _gen_if_block(self, start, boundary, is_elif=False):
        print(f"[GEN_IF] called start={start} boundary={boundary} is_elif={is_elif}")
        """Generate an if/else block from IR pattern."""
        instr = self.ir[start]
        cond = self._py_val(instr.arg1)
        else_label = instr.dest

        keyword = "elif" if is_elif else "if"
        # Check if condition was pre-computed by a BINOP that we can inline
        elif_binops = getattr(self, '_elif_binops', {})
        if is_elif and cond in elif_binops:
            self._emit(f"{keyword} _caramel_to_bool({elif_binops.pop(cond)}):")
        else:
            self._emit(f"{keyword} _caramel_to_bool({cond}):")
        self._push()

        # Find the LABEL else_label first, then find the GOTO just before it
        goto_end_idx = None
        else_label_idx = None
        end_label = None

        for j in range(start + 1, boundary):
            if self.ir[j].op == "LABEL" and self.ir[j].dest == else_label:
                else_label_idx = j
                break

        # Find the GOTO immediately preceding the else label (skip nested if GOTOs)
        if else_label_idx is not None:
            for j in range(else_label_idx - 1, start, -1):
                if self.ir[j].op == "GOTO":
                    dest = self.ir[j].dest or ""
                    if "WHILE_END" in dest or "POUR_END" in dest or \
                    "WHILE_START" in dest or "POUR_START" in dest or \
                    "POUR_UPDATE" in dest or "DOWHILE_END" in dest:
                        continue
                    goto_end_idx = j
                    end_label = dest
                    break

        # Emit if-body (between IF_FALSE and GOTO/else_label)
        body_end = goto_end_idx if goto_end_idx else (else_label_idx or boundary)
        print(f"[GEN_IF] cond={cond} body_end={body_end} else_label_idx={else_label_idx} goto_end_idx={goto_end_idx}")
        has_body = False
        bi = start + 1
        while bi < body_end and bi < len(self.ir):
            instr_i = self.ir[bi]
            if instr_i.op == "LABEL":
                inner_loop = self._detect_while_loop(bi)
                if inner_loop is not None:
                    bi = self._gen_while_loop(bi, inner_loop)
                    has_body = True
                    continue
                bi += 1
                continue
            if instr_i.op == "GOTO":
                dest = instr_i.dest or ""
                if "WHILE_END" in dest or "POUR_END" in dest or "DOWHILE_END" in dest:
                    self._emit("break")
                    has_body = True
                elif "WHILE_START" in dest or "POUR_START" in dest:
                    self._emit("continue")
                    has_body = True
                elif "POUR_UPDATE" in dest:
                    self._emit_pour_continue(dest)
                    has_body = True
                bi += 1
                continue
            if instr_i.op == "IF_FALSE":
                bi = self._gen_if_block(bi, body_end)
                has_body = True
                continue
            self._gen_simple(instr_i, bi)
            has_body = True
            bi += 1

        if not has_body:
            self._emit("pass")

        self._pop()

        # Check for else block
        if else_label_idx is not None and end_label:
            # Find end label
            end_label_idx = None
            for j in range(else_label_idx, boundary+1):
                if self.ir[j].op == "LABEL" and self.ir[j].dest == end_label:
                    end_label_idx = j
                    break

            if end_label_idx and end_label_idx > else_label_idx + 1:
                # Check if else block is an elif chain (elifroth)
                # Pattern: [BINOPs...] IF_FALSE → elif
                elif_if_false = None
                for j in range(else_label_idx + 1, end_label_idx):
                    op_j = self.ir[j].op
                    if op_j in ("LABEL", "GOTO", "NOP", "ARR_LOAD"):
                        continue
                    if op_j == "BINOP":
                        continue  # condition computation before elif
                    if op_j == "IF_FALSE":
                        elif_if_false = j
                    break

                if elif_if_false is not None:
                    self._elif_binops = getattr(self, '_elif_binops', {})
                    # Find which temp the IF_FALSE condition uses
                    final_cond = self.ir[elif_if_false].arg1
                    for j in range(else_label_idx + 1, elif_if_false):
                        if self.ir[j].op == "BINOP":
                            b_instr = self.ir[j]
                            raw_a = self._py_var(b_instr.arg1) if isinstance(b_instr.arg1, str) else self._py_val(b_instr.arg1)
                            raw_b = self._py_var(b_instr.arg2) if isinstance(b_instr.arg2, str) else self._py_val(b_instr.arg2)
                            a = self._elif_binops.get(raw_a, raw_a)
                            b = self._elif_binops.get(raw_b, raw_b)
                            binop = b_instr.extra.get("binop", "+")
                            dest = self._py_var(b_instr.dest)
                            if binop == "&&":
                                expr = f"_caramel_to_bool({a}) and _caramel_to_bool({b})"
                            elif binop == "||":
                                expr = f"_caramel_to_bool({a}) or _caramel_to_bool({b})"
                            else:
                                expr = f"{a} {binop} {b}"
                            self._elif_binops[dest] = expr
                        elif self.ir[j].op == "ARR_LOAD":
                            arr = self._py_var(self.ir[j].arg1)
                            raw_idx = self._py_val(self.ir[j].arg2)
                            idx = self._elif_binops.get(raw_idx, raw_idx)
                            dest = self._py_var(self.ir[j].dest)
                            self._elif_binops[dest] = f"{arr}[{idx}]"

                    # Generate elif chain
                    bi = elif_if_false
                    while bi < end_label_idx:
                        instr_i = self.ir[bi]
                        if instr_i.op == "IF_FALSE":
                            bi = self._gen_if_block(bi, end_label_idx, is_elif=True)
                            continue
                        if instr_i.op in ("LABEL", "GOTO"):
                            bi += 1
                            continue
                        if instr_i.op == "BINOP":
                            b_instr = instr_i
                            raw_a = self._py_var(b_instr.arg1) if isinstance(b_instr.arg1, str) else self._py_val(b_instr.arg1)
                            raw_b = self._py_var(b_instr.arg2) if isinstance(b_instr.arg2, str) else self._py_val(b_instr.arg2)
                            a = self._elif_binops.get(raw_a, raw_a)  # ← substitute if known
                            b = self._elif_binops.get(raw_b, raw_b)  # ← substitute if known
                            binop = b_instr.extra.get("binop", "+")
                            dest = self._py_var(b_instr.dest)
                            if binop == "&&":
                                expr = f"_caramel_to_bool({a}) and _caramel_to_bool({b})"
                            elif binop == "||":
                                expr = f"_caramel_to_bool({a}) or _caramel_to_bool({b})"
                            else:
                                expr = f"{a} {binop} {b}"
                            self._elif_binops[dest] = expr
                            bi += 1
                            continue

                        if instr_i.op == "ARR_LOAD":
                            arr = self._py_var(instr_i.arg1)
                            raw_idx = self._py_val(instr_i.arg2)
                            idx = self._elif_binops.get(raw_idx, raw_idx)  
                            dest = self._py_var(instr_i.dest)
                            self._elif_binops[dest] = f"{arr}[{idx}]"
                            bi += 1
                            continue

                        # Non-elif content after last elif → else block
                        self._emit("else:")
                        self._push()
                        while bi < end_label_idx:
                            instr_k = self.ir[bi]
                            if instr_k.op == "LABEL":
                                inner_loop = self._detect_while_loop(bi)
                                if inner_loop is not None:
                                    bi = self._gen_while_loop(bi, inner_loop)
                                    continue
                                bi += 1
                                continue
                            if instr_k.op == "GOTO":
                                bi += 1
                                continue
                            if instr_k.op in ("BINOP", "ARR_LOAD"):
                                dest = self._py_var(instr_k.dest)
                                eb = getattr(self, '_elif_binops', {})
                                if dest in eb:
                                    self._emit(f"{dest} = {eb[dest]}")
                                    bi += 1
                                    continue
                            self._gen_simple(instr_k, bi)
                            bi += 1
                        self._pop()
                        break
                else:
                    self._emit("else:")
                    self._push()
                    has_else = False
                    bi = else_label_idx + 1
                    while bi < end_label_idx:
                        instr_i = self.ir[bi]
                        if instr_i.op == "LABEL":
                            inner_loop = self._detect_while_loop(bi)
                            if inner_loop is not None:
                                bi = self._gen_while_loop(bi, inner_loop)
                                has_else = True
                                continue
                            bi += 1
                            continue
                        if instr_i.op == "GOTO":
                            dest = instr_i.dest or ""
                            if "WHILE_END" in dest or "POUR_END" in dest or "DOWHILE_END" in dest:
                                self._emit("break")
                                has_else = True
                            elif "WHILE_START" in dest or "POUR_START" in dest:
                                self._emit("continue")
                                has_body = True
                            elif "POUR_UPDATE" in dest:
                                self._emit_pour_continue(dest)
                                has_body = True
                            bi += 1
                            continue
                        if instr_i.op == "IF_FALSE":
                            bi = self._gen_if_block(bi, end_label_idx)
                            has_else = True
                            continue
                        if instr_i.op in ("BINOP", "ARR_LOAD"):
                            dest = self._py_var(instr_i.dest)
                            eb = getattr(self, '_elif_binops', {})
                            if dest in eb:
                                self._emit(f"{dest} = {eb[dest]}")
                                has_else = True
                                bi += 1
                                continue
                        self._gen_simple(instr_i, bi)
                        has_else = True
                        bi += 1
                    if not has_else:
                        self._emit("pass")
                    self._pop()

                return end_label_idx + 1

        # No else block
        if else_label_idx:
            return else_label_idx + 1
        

        if not is_elif:
            # Look ahead for elif blocks and pre-emit their intermediate BINOPs
            for j in range(else_label_idx + 1, end_label_idx):
                if self.ir[j].op == "BINOP":
                    b_instr = self.ir[j]
                    # Check if this feeds into an IF_FALSE (final condition) or is intermediate
                    if self.ir[elif_if_false].arg1 != b_instr.dest:
                        dest = self._py_var(b_instr.dest)
                        a = self._py_val(b_instr.arg1)
                        b = self._py_val(b_instr.arg2)
                        binop = b_instr.extra.get("binop", "+")
                        if binop == "&&":
                            self._emit(f"{dest} = _caramel_to_bool({a}) and _caramel_to_bool({b})")
                        elif binop == "||":
                            self._emit(f"{dest} = _caramel_to_bool({a}) or _caramel_to_bool({b})")
                        else:
                            self._emit(f"{dest} = {a} {binop} {b}")
                elif self.ir[j].op == "IF_FALSE":
                    break
            # Now emit the if/elif line
            self._emit(f"{keyword} _caramel_to_bool({cond}):")

        return body_end + 1

    def _gen_simple(self, instr, idx):
        """Generate a simple (non-control-flow) instruction."""
        try:
            op = instr.op

            if op == "DECLARE":
                if instr.extra.get("param"):
                    return idx + 1
                var_name = instr.dest
                dtype = instr.extra.get("type", "bean")
                default = self.DEFAULT_VALUES.get(dtype, "None")
                if not self._in_func:
                    self._emit(f'_order["{var_name}"] = {default}')
                else:
                    var = self._py_var(var_name)
                    if var not in self._declared:
                        self._emit(f"{var} = {default}")
                        self._declared.add(var)
                                
            elif op == "ASSIGN":
                var_name = instr.dest
                val = self._py_val(instr.arg1)
                var_type = self._get_var_type(instr.dest)
                src_type = self._get_var_type(instr.arg1) if isinstance(instr.arg1, str) else None
                is_churro_src = (
                    src_type == "churro" or
                    (isinstance(instr.arg1, str) and len(instr.arg1) == 3
                    and instr.arg1[0] == "'" and instr.arg1[-1] == "'")
                )
                if not self._in_func:
                    self._emit(f'_order["{var_name}"] = {val}')
                elif var_type == "bean" and is_churro_src:
                    self._emit(f"{self._py_var(var_name)} = ord({val})")
                elif var_type == "bean" and src_type != "blend":
                    self._emit(f"{self._py_var(var_name)} = int({val})")
                elif var_type == "blend" and src_type == "temp":
                    self._emit(f"{self._py_var(var_name)} = ('hot' if {val} else 'cold')")
                elif var_type == "drip" and src_type == "temp":
                    self._emit(f"{self._py_var(var_name)} = float({val})")
                else:
                    self._emit(f"{self._py_var(var_name)} = {val}")

            elif op == "BINOP":
                dest = self._py_var(instr.dest)
                a = self._py_val(instr.arg1)
                b = self._py_val(instr.arg2)
                binop = instr.extra.get("binop", "+")
                t1 = self._get_var_type(instr.arg1)
                t2 = self._get_var_type(instr.arg2)

                def is_churro(val_raw, inferred_type):
                    if inferred_type == "churro":
                        return True
                    if isinstance(val_raw, str) and len(val_raw) == 3 \
                            and val_raw[0] == "'" and val_raw[-1] == "'":
                        return True
                    return False

                other_is_blend = (
                    (isinstance(instr.arg2, str) and instr.arg2.startswith('"')) or t2 == "blend"
                )
                other_is_blend_left = (
                    (isinstance(instr.arg1, str) and instr.arg1.startswith('"')) or t1 == "blend"
                )

                if is_churro(instr.arg1, t1) and is_churro(instr.arg2, t2) and binop == "+":
                    self._emit(f"{dest} = {a} + {b}")
                elif binop == "&&":
                    self._emit(f"{dest} = _caramel_to_bool({a}) and _caramel_to_bool({b})")
                elif binop == "||":
                    self._emit(f"{dest} = _caramel_to_bool({a}) or _caramel_to_bool({b})")
                elif is_churro(instr.arg1, t1) or is_churro(instr.arg2, t2):
                    a = f"ord({a})" if is_churro(instr.arg1, t1) and not other_is_blend else a
                    b = f"ord({b})" if is_churro(instr.arg2, t2) and not other_is_blend_left else b
                    self._emit(f"{dest} = {a} {binop} {b}")
                elif binop == "+" and "blend" in (t1, t2):
                    if t1 == "temp":
                        a = f"('hot' if {a} else 'cold')"
                    elif t1 != "blend":
                        a = f"str({a})"
                    if t2 == "temp":
                        b = f"('hot' if {b} else 'cold')"
                    elif t2 != "blend":
                        b = f"str({b})"
                    self._emit(f"{dest} = {a} + {b}")
                else:
                    self._emit(f"{dest} = {a} {binop} {b}")

            elif op == "UNARYOP":
                dest = self._py_var(instr.dest)
                a = self._py_val(instr.arg1)
                uop = instr.extra.get("unaryop", "-")
                if uop == "!":
                    print(f"[uop = ! PRINT] raw args={instr.extra.get('args')} → py_args={[self._py_val(a) for a in instr.extra.get('args', [])]}")
                    self._emit(f"{dest} = not _caramel_to_bool({a})")
                else:
                    print(f"[else not uop = ! PRINT] raw args={instr.extra.get('args')} → py_args={[self._py_val(a) for a in instr.extra.get('args', [])]}")
                    self._emit(f"{dest} = {uop}({a})")

            elif op == "PRINT":
                args = instr.extra.get("args", [])
                # print(f"[PRINT CODEGEN] raw args = {args!r}")
                if args:
                    py_args = ", ".join(self._py_val(a) for a in args)
                    self._emit(f"_caramel_print({py_args})")
                else:
                    self._emit("_caramel_print()")

            elif op == "INPUT": # WALA PALA YUNG TEMP PAKI TEST IF VALID, also check if it does indeed print kase sa parser oks naman and child siya ni batter@
                dest = self._py_var(instr.dest)
                dtype = self._get_var_type(instr.dest) or instr.extra.get("array_elem_type")
                prompt = instr.extra.get("prompt") or ""
                prompt_arg = f"{prompt}" if prompt else "''"
                if dtype == "bean":
                    self._emit(f"{dest} = _caramel_input_bean({prompt_arg})")
                elif dtype == "drip":
                    self._emit(f"{dest} = _caramel_input_drip({prompt_arg})")
                elif dtype == "temp":
                    self._emit(f"{dest} = _caramel_input_temp({prompt_arg})")
                else:
                    self._emit(f"{dest} = _caramel_input({prompt_arg})")
            
            elif op == "RETURN":
                if instr.arg1 is not None:
                    val = self._py_val(instr.arg1)
                    rtype = instr.extra.get("return_type")
                    if rtype == "drip":
                        self._emit(f"return float({val})")
                    elif rtype == "bean":
                        self._emit(f"return int({val})")
                    elif rtype == "temp":
                        self._emit(f"return bool({val})")
                    else:
                        self._emit(f"return {val}")
                else:
                    self._emit("return")

            elif op == "CALL":
                dest = self._py_var(instr.dest)
                func = self._py_func_name(instr.arg1)
                arg_count = instr.extra.get("arg_count", 0)
                params = []
                for j in range(max(0, idx - arg_count), idx):
                    if j < len(self.ir) and self.ir[j].op == "PARAM":
                        params.append(self._py_val(self.ir[j].arg1))
                
                if instr.arg1 == "__rand__":
                    use_float = instr.extra.get("use_float", False)
                    fn = "random.uniform" if use_float else "random.randint"
                    self._emit(f"{dest} = {fn}({', '.join(params)})")
                    return idx + 1
                self._emit(f"{dest} = {func}({', '.join(params)})")

            elif op == "PARAM":
                pass  # handled by CALL

            elif op == "CONCAT":
                dest = self._py_var(instr.dest)
                a = self._py_val(instr.arg1)
                b = self._py_val(instr.arg2)
                self._emit(f"{dest} = str({a}) + str({b})")

            elif op == "ARR_DECLARE":
                name = instr.dest
                dims = instr.extra.get("dims", [])
                init_vals = instr.extra.get("init", [])
                dtype = instr.extra.get("type", "bean")
                default = {"churro": "''", "blend": '""', "temp": "False", "drip": "0.0"}.get(dtype, "0")
                if not self._in_func:
                    var = f'_order["{name}"]'
                elif name.startswith("order."):
                    var = f'_order["{name[6:]}"]'
                else:
                    var = name


                if len(dims) == 2:
                    r, c = dims[0], dims[1]
                    if r == "***" or c == "***":
                        self._emit(f"{var} = []")
                    elif init_vals and isinstance(init_vals[0], list):
                        padded = []
                        for row in init_vals:
                            padded_row = list(row) + [default] * (c - len(row)) if isinstance(c, int) else list(row)
                            padded.append(padded_row)
                        while isinstance(r, int) and len(padded) < r:
                            padded.append([default] * (c if isinstance(c, int) else 0))
                        self._emit(f"{var} = {padded}")
                    else:
                        self._emit(f"{var} = [[{default}] * {c} for _ in range({r})]")
                elif len(dims) == 1:
                    d = dims[0]
                    if d == "***":
                        if init_vals:
                            self._emit(f"{var} = {[self._clean_init_val(v) for v in init_vals]}")
                        else:
                            self._emit(f"{var} = []")
                    elif init_vals:
                        if isinstance(d, int) and len(init_vals) < d:
                            padded = [self._clean_init_val(v) for v in init_vals] + [default] * (d - len(init_vals))
                            self._emit(f"{var} = {padded}")
                        elif not isinstance(d, int):
                            self._emit(f"{var} = {[self._clean_init_val(v) for v in init_vals]}")
                            self._emit(f"while len({var}) < {d}: {var}.append({default})")
                        else:
                            self._emit(f"{var} = {[self._clean_init_val(v) for v in init_vals]}")
                    else:
                        self._emit(f"{var} = [{default}] * {d}")
                else:
                    self._emit(f"{var} = []")

            elif op == "ARR_LOAD":
                dest = self._py_var(instr.dest)
                arr = self._py_var(instr.arg1)
                idx_val = self._py_val(instr.arg2)
                idx_val = getattr(self, '_elif_binops', {}).get(idx_val, idx_val)
                is_2d = instr.extra.get("is_2d", False)
                # Find if source array is dynamic
                arr_decl = next((ins for ins in self.ir if ins.op == "ARR_DECLARE" and ins.dest == instr.arg1), None)
                is_dynamic = arr_decl and (arr_decl.extra.get("dims") in (["***"], ["***", "***"]) or 
                                        arr_decl.extra.get("dims", [None])[0] == "***")
                if is_dynamic or is_2d:
                    expand_with = "[]" if is_2d else self._get_default_for(instr.arg1)
                    self._emit(f"while len({arr}) <= {idx_val}: {arr}.append({expand_with})")
                self._emit(f"{dest} = {arr}[{idx_val}]")

            elif op == "ARR_STORE":
                arr = self._py_var(instr.dest)
                idx_val = self._py_val(instr.arg1)
                idx_val = getattr(self, '_elif_binops', {}).get(idx_val, idx_val)
                val = self._py_val(instr.arg2)
                if instr.dest and str(instr.dest).startswith("_t"):
                    # Temp subarray from 2D load — auto-expand with default
                    # Find original array type by tracing back through ARR_LOAD
                    orig_type = None
                    for ins in self.ir:
                        if ins.op == "ARR_LOAD" and ins.dest == instr.dest:
                            orig_type = self._get_var_type(ins.arg1)
                            break
                    default = {"churro": "''", "blend": '""', "temp": "False", "drip": "0.0"}.get(orig_type, "0")
                    self._emit(f"while len({arr}) <= {idx_val}: {arr}.append({default})")
                    self._emit(f"{arr}[{idx_val}] = {val}")
                else:
                    arr_decl = next((ins for ins in self.ir if ins.op == "ARR_DECLARE" and ins.dest == instr.dest), None)
                    is_dynamic = arr_decl and arr_decl.extra.get("dims", [None])[0] == "***"
                    if is_dynamic:
                        self._emit(f"while len({arr}) <= {idx_val}: {arr}.append({self._get_default_for(instr.dest)})")
                    self._emit(f"{arr}[{idx_val}] = {val}")

            elif op == "MEMBER_ACC":
                dest = self._py_var(instr.dest)
                obj = self._py_var(instr.arg1)
                member = instr.arg2
                self._emit(f"{dest} = {obj}.get('{member}', None) if isinstance({obj}, dict) else getattr({obj}, '{member}', None)")

            elif op == "SNAP":
                self._emit("break")

            elif op == "SKIP":
                self._emit("continue")

                
            elif op in ("FUNC_BEGIN", "FUNC_END", "LABEL", "GOTO",
                        "IF_FALSE", "IF_TRUE", "NOP", "PARAM"):
                pass  # handled elsewhere

            return idx + 1
        except Exception as e:
            print(f"[GEN_SIMPLE FATAL] bi={idx} op={instr.op} dest={instr.dest} arg1={instr.arg1!r}: {e}")
            traceback.print_exc()
            return idx + 1

    def _get_var_type(self, var_name):
        if not isinstance(var_name, str):
            return None
        if len(var_name) == 3 and var_name[0] == "'" and var_name[-1] == "'":
            return "churro"
        if len(var_name) >= 2 and var_name[0] == '"' and var_name[-1] == '"':
            return "blend"
        for instr in self.ir:
            if instr.op == "DECLARE" and instr.dest == var_name:
                return instr.extra.get("type")
        for instr in self.ir:
            if instr.dest != var_name:
                continue
            if instr.op == "ASSIGN":
                return self._get_var_type(instr.arg1)
            if instr.op in ("BINOP", "CONCAT"):
                t1 = self._get_var_type(instr.arg1)
                t2 = self._get_var_type(instr.arg2)
                binop = instr.extra.get("binop", "")
                if binop in (">", "<", ">=", "<=", "==", "!=", "&&", "||"):
                    return "temp"
                if binop in ("+", "-", "*", "/", "%"):
                    if "churro" in (t1, t2) and "blend" not in (t1, t2):
                        return "bean"
                if "blend" in (t1, t2):
                    return "blend"
                if "churro" in (t1, t2):
                    return "churro"
                return t1 or t2
            if instr.op == "ARR_LOAD":
                return self._get_var_type(instr.arg1)
            if instr.op == "CALL":
                fn = instr.arg1
                if fn == "__sift__":  return "bean"
                if fn == "__sqrt__":  return "drip"
                if fn == "__ceil__":  return "bean"
                if fn == "__floor__": return "bean"
                if fn == "__pow__":   return "drip"
                if fn == "__type__":  return "blend"
                if fn == "__rand__":
                    return "drip" if instr.extra.get("use_float") else "bean"
        return None

    # ==========================
    # HELPER FUNCTIONS
    # ==========================


    def _clean_init_val(self, v):
        """Strip surrounding IR quotes from string literals for array init."""
        if isinstance(v, str):
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                return v[1:-1]  # blend literal → raw string content
            if len(v) == 3 and v[0] == "'" and v[-1] == "'":
                return v[1]     # churro literal → single char
        return v

    def _get_default_for(self, var_name):
        dtype = self._get_var_type(var_name)
        return {"churro": "''", "blend": '""', "temp": "False", "drip": "0.0"}.get(dtype, "0")

    def _is_global_var(self, name):
        """Check if variable was declared outside any function in IR."""
        in_func = False
        for instr in self.ir:
            if instr.op == "FUNC_BEGIN":
                in_func = True
            elif instr.op == "FUNC_END":
                in_func = False
            elif not in_func and instr.op in ("DECLARE", "ARR_DECLARE") and instr.dest == name:
                return True
        return False


    # ------------------------------------------------------------------
    # Standalone / EXE Generation
    # ------------------------------------------------------------------

    def generate_standalone(self):
        """
        Generate a self-contained Python script suitable for packaging into
        a Windows executable via PyInstaller.

        Key differences from generate():
          - Uses real sys.stdin / sys.stdout (no mock I/O patching).
          - Wraps the entry point in `if __name__ == '__main__':` so that
            PyInstaller's multiprocessing bootstrap does not re-run the
            program body on every worker spawn.
          - The _CaramelEarlyExit exception is used for controlled exits
            (e.g. invalid input) and results in sys.exit(0) so the console
            window closes cleanly.

        Returns the generated Python source code as a string.
        """
        # Reset generator state for a fresh pass
        self._lines = []
        self._indent = 0
        self._declared = set()
        self._in_func = False

        # Emit header (same helpers, but _caramel_input/print use real I/O)
        self._emit_standalone_header()
        # Translate the IR instructions exactly as in the regular path
        self._translate(0, len(self.ir))
        # Emit a standalone-safe footer
        self._emit_standalone_footer()

        return "\n".join(self._lines)

    def _emit_standalone_header(self):
        """
        Emit the Python file header for standalone / PyInstaller mode.

        This is identical to _emit_header() except:
          - _caramel_input delegates to the real built-in input().
          - _caramel_print delegates to the real built-in print().
        Both are already the case in the existing header because the mocking
        only happens inside execute() at runtime; the generated source itself
        always calls `input` / `print`. We re-use _emit_header() unchanged.
        """
        self._emit_raw("# === Generated CARAMEL Program (Standalone) ===")
        self._emit_raw("# This file was produced by the Caramel compiler.")
        self._emit_raw("# It is intended to be packaged with PyInstaller.")
        self._emit_raw("")
        self._emit_raw("import sys")
        self._emit_raw("import math")
        self._emit_raw("import random")
        self._emit_raw("")
        # ------------------------------------------------------------------
        # Runtime helpers (identical to the interactive-mode header)
        # ------------------------------------------------------------------
        self._emit_raw("def _caramel_to_bool(val):")
        self._emit_raw("    if isinstance(val, bool): return val")
        self._emit_raw("    if isinstance(val, (int, float)): return val != 0")
        self._emit_raw("    if isinstance(val, str): return len(val) > 0")
        self._emit_raw("    return bool(val)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input(prompt=''):")
        self._emit_raw("    return input(prompt)")
        self._emit_raw("")
        self._emit_raw("def _caramel_type(val):")
        self._emit_raw("    if isinstance(val, bool): return 'temp'")
        self._emit_raw("    if isinstance(val, int): return 'bean'")
        self._emit_raw("    if isinstance(val, float): return 'drip'")
        self._emit_raw("    if isinstance(val, str) and len(val) == 1: return 'churro'")
        self._emit_raw("    if isinstance(val, str): return 'blend'")
        self._emit_raw("    if isinstance(val, list): return 'array'")
        self._emit_raw("    return 'unknown'")
        self._emit_raw("")
        self._emit_raw("class _CaramelEarlyExit(Exception):")
        self._emit_raw("    pass")
        self._emit_raw("")
        self._emit_raw("class _CaramelLoopTimeout(Exception):")
        self._emit_raw("    pass")
        self._emit_raw("")
        # --- Runtime loop guard (standalone / EXE mode) -------------------------
        # Identical to the interactive-mode guard; included here so the packaged
        # .exe is fully self-contained without importing server-side modules.
        self._emit_raw("_CARAMEL_MAX_ITERATIONS = 100_000  # Hard iteration limit per loop")
        self._emit_raw("_caramel_loop_counters = {}        # loop_id -> iteration count")
        self._emit_raw("")
        self._emit_raw("def _caramel_check_loop(loop_id):")
        self._emit_raw("    _caramel_loop_counters[loop_id] = _caramel_loop_counters.get(loop_id, 0) + 1")
        self._emit_raw("    if _caramel_loop_counters[loop_id] > _CARAMEL_MAX_ITERATIONS:")
        self._emit_raw("        del _caramel_loop_counters[loop_id]")
        self._emit_raw("        raise _CaramelLoopTimeout(")
        self._emit_raw("            f'Infinite loop detected: loop {loop_id!r} exceeded '")
        self._emit_raw("            f'{_CARAMEL_MAX_ITERATIONS:,} iterations.'")
        self._emit_raw("        )")
        self._emit_raw("")
        self._emit_raw("def _caramel_reset_loop(loop_id):")
        self._emit_raw("    _caramel_loop_counters.pop(loop_id, None)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input_bean(prompt=''):")
        self._emit_raw("    raw = input(prompt).strip()")
        self._emit_raw("    neg = raw.startswith('-')")
        self._emit_raw("    digits = raw[1:] if neg else raw")
        self._emit_raw("    if not digits.isdigit() or len(digits) > 10:")
        self._emit_raw("        print('INVALID INPUT: Number too large.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    if neg and digits == '0':")
        self._emit_raw("        print('INVALID INPUT: Negative symbol and a zero are not allowed.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    return int(raw)")
        self._emit_raw("")

        self._emit_raw("def _caramel_input_drip(prompt=''):")
        self._emit_raw("    raw = input(prompt).strip()")
        self._emit_raw("    neg = raw.startswith('-')")
        self._emit_raw("    body = raw[1:] if neg else raw")
        self._emit_raw("    if '.' in body:")
        self._emit_raw("        parts = body.split('.')")
        self._emit_raw("        if len(parts) != 2:")
        self._emit_raw("            print('INVALID INPUT')")
        self._emit_raw("            raise _CaramelEarlyExit()")
        self._emit_raw("        whole, frac = parts[0], parts[1]")
        self._emit_raw("    else:")
        self._emit_raw("        whole, frac = body, ''")
        self._emit_raw("    if not whole.isdigit() or (frac and not frac.isdigit()):")
        self._emit_raw("        print('INVALID INPUT')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    if len(whole) > 10 or len(frac) > 10:")
        self._emit_raw("        print('INVALID INPUT: Number too large.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    if neg and float(body) == 0.0:")
        self._emit_raw("        print('INVALID INPUT: Negative symbol and a zero are not allowed.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("    return float(raw)")
        self._emit_raw("")

        self._emit_raw("def _caramel_input_temp(prompt=''):")
        self._emit_raw("    raw = input(prompt).strip().lower()")
        self._emit_raw("    if raw in ('hot', 'true'):")
        self._emit_raw("        return True")
        self._emit_raw("    if raw in ('cold', 'false'):")
        self._emit_raw("        return False")
        self._emit_raw("    try:")
        self._emit_raw("        n = float(raw)")
        self._emit_raw("        return n != 0")
        self._emit_raw("    except ValueError:")
        self._emit_raw("        print('INVALID INPUT: Expected hot/cold, true/false, or a number.')")
        self._emit_raw("        raise _CaramelEarlyExit()")
        self._emit_raw("")

        self._emit_raw("def _caramel_print(*args, end='\\n'):")
        self._emit_raw("    parts = []")
        self._emit_raw("    for a in args:")
        self._emit_raw("        if isinstance(a, bool):")
        self._emit_raw('            parts.append("hot" if a else "cold")')
        self._emit_raw("        elif isinstance(a, str) and len(a) >= 2 and a[0] == '\"' and a[-1] == '\"':")
        self._emit_raw("            parts.append(a[1:-1])")
        self._emit_raw("        elif isinstance(a, str) and len(a) >= 2 and a[0] == \"'\" and a[-1] == \"'\":")
        self._emit_raw("            parts.append(a[1:-1])")
        self._emit_raw("        else:")
        self._emit_raw("            parts.append(str(a))")
        self._emit_raw('    print("".join(parts), end="")')
        self._emit_raw("")
        self._emit_raw("_order = {}")
        self._emit_raw("_functions = {}")
        self._emit_raw("")

    def _emit_standalone_footer(self):
        """
        Emit the program entry point for standalone / PyInstaller mode.

        Uses `if __name__ == '__main__':` to prevent double-execution when
        PyInstaller spawns worker processes (required on Windows with the
        'spawn' multiprocessing start method).

        On _CaramelEarlyExit (e.g. invalid user input) the process exits
        cleanly with code 0 so the console window disappears without an
        unhandled-exception traceback.
        """
        self._emit_raw("")
        self._emit_raw("# --- Standalone entry point ---")
        self._emit_raw("if __name__ == '__main__':")
        self._emit_raw("    import time as _time")
        self._emit_raw("    try:")
        self._emit_raw("        _main_cup()")
        self._emit_raw("    except _CaramelEarlyExit:")
        self._emit_raw("        # Controlled exit (e.g. invalid input) — show a short pause")
        self._emit_raw("        pass")
        self._emit_raw("    except _CaramelLoopTimeout as _lte:")
        self._emit_raw("        # Infinite loop detected at runtime")
        self._emit_raw("        print(f'\\n[CARAMEL RUNTIME ERROR] {_lte}')")
        self._emit_raw("    except KeyboardInterrupt:")
        self._emit_raw("        print('\\n[Execution interrupted by user.]')")
        self._emit_raw("    except Exception as _exc:")
        self._emit_raw("        print(f'\\n[CARAMEL RUNTIME ERROR] {type(_exc).__name__}: {_exc}')")
        self._emit_raw("    # --- 10-second auto-close window ----------------------------")
        self._emit_raw("    # Keeps the console open so the user can read the output")
        self._emit_raw("    # before the window closes automatically.")
        self._emit_raw("    print('\\n\\nProgram finished. This window will close in 10 seconds...')")
        self._emit_raw("    _time.sleep(10)")
        self._emit_raw("    sys.exit(0)")