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


class CodeGenerator:
    """
    Converts CARAMEL IR instructions into executable Python source code.
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
        self.ir = ir_instructions
        self._lines = []
        self._indent = 0
        self._in_func = False
        self._func_stack = []
        self._declared = set()      # track declared variables
        self._labels = {}           # label -> line index for goto simulation
        self._label_uses = set()    # labels referenced by gotos

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self):
        """
        Generate Python source code from IR instructions.
        Returns the generated code as a string.
        """
        self._preprocess()
        self._emit_header()
        self._translate_instructions()
        self._emit_footer()
        return "\n".join(self._lines)

    def execute(self, input_values=None):
        """
        Generate and execute the Python code.
        Returns dict with 'output' (stdout), 'error' (if any), and 'code' (generated).

        input_values: list of strings to feed as stdin lines, or None for empty input
        """
        code = self.generate()

        # print("=== GENERATED CODE ===") On server na siya
        # with open("debug_generated.py", "w") as f:
        #     f.write(code)
        # print("=== END GENERATED CODE ===")
    

        # Prepare sandboxed execution
        captured_out = io.StringIO()
        captured_err = io.StringIO()

        # Mock input
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

        # Execute in isolated namespace
        exec_globals = {
            "__builtins__": {
                "print": lambda *a, **kw: print(*a, file=captured_out, **kw),
                "input": mock_input,
                "int": int,
                "float": float,
                "str": str,
                "bool": bool,
                "len": len,
                "range": range,
                "abs": abs,
                "max": max,
                "min": min,
                "True": True,
                "False": False,
                "None": None,
                "isinstance": isinstance,
                "chr": chr,
                "ord": ord,
            },
        }

        error = None
        try:
            exec(code, exec_globals)
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            tb = traceback.format_exc()
            captured_err.write(tb)

        return {
            "output": captured_out.getvalue(),
            "error": error,
            "code": code,
        }

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def _preprocess(self):
        """Scan IR for labels used by jumps (needed for goto emulation)."""
        for instr in self.ir:
            if instr.op in ("GOTO", "IF_FALSE", "IF_TRUE"):
                if instr.dest:
                    self._label_uses.add(instr.dest)

    # ------------------------------------------------------------------
    # Code Emission Helpers
    # ------------------------------------------------------------------

    def _emit(self, line):
        """Emit a line of Python code at the current indentation level."""
        self._lines.append("    " * self._indent + line)

    def _emit_raw(self, line):
        """Emit a line without indentation adjustment."""
        self._lines.append(line)

    def _push_indent(self):
        self._indent += 1

    def _pop_indent(self):
        if self._indent > 0:
            self._indent -= 1

    # ------------------------------------------------------------------
    # Header / Footer
    # ------------------------------------------------------------------

    def _emit_header(self):
        """Emit the Python file header with runtime helpers."""
        self._emit_raw("# === Generated CARAMEL Program ===")
        self._emit_raw("# Target: Python 3")
        self._emit_raw("")
        self._emit_raw("# --- Runtime helpers ---")
        self._emit_raw("def _caramel_to_bool(val):")
        self._emit_raw("    if isinstance(val, bool): return val")
        self._emit_raw("    if isinstance(val, (int, float)): return val != 0")
        self._emit_raw("    if isinstance(val, str): return len(val) > 0")
        self._emit_raw("    return bool(val)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input(prompt=''):")
        self._emit_raw("    return input(prompt)")
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
        # Global variable storage for order. access
        self._emit_raw("_order = {}")
        self._emit_raw("")
        # Function definitions dict
        self._emit_raw("_functions = {}")
        self._emit_raw("")

    def _emit_footer(self):
        """Emit the program entry point call."""
        self._emit_raw("")
        self._emit_raw("# --- Entry point ---")
        self._emit_raw("if __name__ == '__main__' or True:")
        self._emit_raw("    _main_cup()")

    # ------------------------------------------------------------------
    # Main Translation Loop
    # ------------------------------------------------------------------

    def _translate_instructions(self):
        """Walk through all IR instructions and emit Python code."""
        i = 0
        while i < len(self.ir):
            instr = self.ir[i]
            handler = getattr(self, f"_gen_{instr.op}", None)
            if handler:
                handler(instr)
            i += 1

    # ------------------------------------------------------------------
    # Instruction Generators
    # ------------------------------------------------------------------

    def _gen_FUNC_BEGIN(self, instr):
        func_name = instr.dest or "_anon"
        py_name = self._py_func_name(func_name)

        self._func_stack.append(func_name)
        self._in_func = True

        # FIX: find our index first, then scan FORWARD only
        start_idx = self.ir.index(instr)
        params = []
        for j in range(start_idx + 1, len(self.ir)):
            fi = self.ir[j]
            if fi.op == "FUNC_END" and fi.dest == func_name:
                break
            if fi.op == "FUNC_BEGIN":  # don't steal params from nested/sibling funcs
                break
            if fi.op == "DECLARE" and fi.extra.get("param"):
                params.append(fi.dest)

        param_str = ", ".join(params) if params else ""
        self._emit(f"def {py_name}({param_str}):")
        self._push_indent()
        self._declared = set(params)

    def _gen_FUNC_END(self, instr):
        # Ensure function body is not empty
        if self._lines and self._lines[-1].strip().startswith("def "):
            self._emit("pass")
        self._pop_indent()
        self._emit("")
        self._in_func = False
        if self._func_stack:
            self._func_stack.pop()
        self._declared = set()

    def _gen_DECLARE(self, instr):
        if instr.extra.get("param"):
            return  # handled in FUNC_BEGIN

        var_name = self._py_var(instr.dest)
        dtype = instr.extra.get("type", "bean")
        default = self.DEFAULT_VALUES.get(dtype, "None")

        if var_name not in self._declared:
            self._emit(f"{var_name} = {default}")
            self._declared.add(var_name)

    def _gen_ASSIGN(self, instr):
        dest = self._py_var(instr.dest)
        val = self._py_val(instr.arg1)
        self._emit(f"{dest} = {val}")

    def _gen_BINOP(self, instr):
        dest = self._py_var(instr.dest)
        a = self._py_val(instr.arg1)
        b = self._py_val(instr.arg2)
        op = instr.extra.get("binop", "+")

        # Translate CARAMEL logical operators to Python
        if op == "&&":
            self._emit(f"{dest} = _caramel_to_bool({a}) and _caramel_to_bool({b})")
        elif op == "||":
            self._emit(f"{dest} = _caramel_to_bool({a}) or _caramel_to_bool({b})")
        else:
            self._emit(f"{dest} = {a} {op} {b}")

    def _gen_UNARYOP(self, instr):
        dest = self._py_var(instr.dest)
        a = self._py_val(instr.arg1)
        op = instr.extra.get("unaryop", "-")

        if op == "!":
            self._emit(f"{dest} = not _caramel_to_bool({a})")
        elif op == "-":
            self._emit(f"{dest} = -({a})")
        else:
            self._emit(f"{dest} = {op}({a})")

    def _gen_LABEL(self, instr):
        # Labels are emitted as comments (Python doesn't have gotos)
        # We use a while/break pattern for control flow
        label = instr.dest
        if label in self._label_uses:
            self._emit(f"# LABEL: {label}")

    def _gen_GOTO(self, instr):
        # Python doesn't support goto; control flow is handled structurally
        # We emit a pass comment for now - the structured code generation
        # from if/while/for handles the actual flow
        self._emit(f"pass  # goto {instr.dest}")

    def _gen_IF_FALSE(self, instr):
        cond = self._py_val(instr.arg1)
        # Emit Python if-not with a pass placeholder
        # The actual control flow is reconstructed from the label structure
        self._emit(f"if not _caramel_to_bool({cond}):")
        self._push_indent()
        self._emit("pass  # branch target")
        self._pop_indent()

    def _gen_IF_TRUE(self, instr):
        cond = self._py_val(instr.arg1)
        self._emit(f"if _caramel_to_bool({cond}):")
        self._push_indent()
        self._emit("pass  # branch target")
        self._pop_indent()

    def _gen_CALL(self, instr):
        dest = self._py_var(instr.dest)
        func = self._py_func_name(instr.arg1)
        arg_count = instr.extra.get("arg_count", 0)

        # Collect the preceding PARAM instructions
        params = []
        idx = self.ir.index(instr)
        for j in range(max(0, idx - arg_count), idx):
            if self.ir[j].op == "PARAM":
                params.append(self._py_val(self.ir[j].arg1))

        args_str = ", ".join(params)
        self._emit(f"{dest} = {func}({args_str})")

    def _gen_PARAM(self, instr):
        # Handled by CALL - skip standalone emission
        pass

    def _gen_RETURN(self, instr):
        if instr.arg1 is not None:
            val = self._py_val(instr.arg1)
            self._emit(f"return {val}")
        else:
            self._emit("return")

    def _gen_PRINT(self, instr):
        args = instr.extra.get("args", [])
        if not args:
            self._emit("_caramel_print()")
            return

        py_args = ", ".join(self._py_val(a) for a in args)
        self._emit(f"_caramel_print({py_args})")

    def _gen_INPUT(self, instr):
        dest = self._py_var(instr.dest)
        dtype = self._get_var_type(instr.dest)
        if dtype == "bean":
            self._emit(f"{dest} = int(_caramel_input())")
        elif dtype == "drip":
            self._emit(f"{dest} = float(_caramel_input())")
        elif dtype == "temp":
            self._emit(f'_inp = _caramel_input()')
            self._emit(f'{dest} = _inp.lower() in ("hot", "true", "1")')
        else:
            self._emit(f"{dest} = _caramel_input()")

    def _gen_CONCAT(self, instr):
        dest = self._py_var(instr.dest)
        a = self._py_val(instr.arg1)
        b = self._py_val(instr.arg2)
        self._emit(f"{dest} = str({a}) + str({b})")

    def _gen_CAST(self, instr):
        dest = self._py_var(instr.dest)
        src = self._py_val(instr.arg1)
        target_type = instr.extra.get("type", "bean")
        coerce_fn = self.TYPE_COERCE.get(target_type, "str")
        self._emit(f"{dest} = {coerce_fn}({src})")

    def _gen_ARR_DECLARE(self, instr):
        dest = self._py_var(instr.dest)
        dims = instr.extra.get("dims", [])
        if len(dims) == 1:
            self._emit(f"{dest} = [None] * {dims[0]}")
        elif len(dims) == 2:
            self._emit(f"{dest} = [[None] * {dims[1]} for _ in range({dims[0]})]")
        else:
            self._emit(f"{dest} = []")
        self._declared.add(dest)

    def _gen_ARR_STORE(self, instr):
        arr = self._py_var(instr.dest)
        idx = self._py_val(instr.arg1)
        val = self._py_val(instr.arg2)
        self._emit(f"{arr}[{idx}] = {val}")

    def _gen_ARR_LOAD(self, instr):
        dest = self._py_var(instr.dest)
        arr = self._py_var(instr.arg1)
        idx = self._py_val(instr.arg2)
        self._emit(f"{dest} = {arr}[{idx}]")

    def _gen_MEMBER_ACC(self, instr):
        dest = self._py_var(instr.dest)
        obj = self._py_var(instr.arg1)
        member = instr.arg2
        self._emit(f"{dest} = {obj}.get('{member}', None) if isinstance({obj}, dict) else getattr({obj}, '{member}', None)")

    def _gen_NOP(self, instr):
        pass

    # ------------------------------------------------------------------
    # Name Mapping Helpers
    # ------------------------------------------------------------------

    def _py_func_name(self, name):
        """Convert CARAMEL function name to Python-safe name."""
        if not name:
            return "_anon"
        if name == "cup":
            return "_main_cup"
        if name.startswith("class_"):
            return f"_class_{name[6:]}"
        if name.startswith("new_"):
            return name
        # Sanitize identifier
        safe = name.replace(".", "_").replace("?", "_q").replace("@", "_at")
        return f"_func_{safe}"

    def _py_var(self, name):
        """Convert CARAMEL variable name to Python-safe name."""
        if not name:
            return "_unknown"
        if isinstance(name, (int, float, bool)):
            return str(name)
        s = str(name)
        if s.startswith("_t"):
            return s  # temp vars are already safe
        if s.startswith("order."):
            field = s[6:]
            return f'_order["{field}"]'
        # Sanitize
        safe = s.replace(".", "_").replace("?", "_q").replace("@", "_at")
        # Avoid Python keywords
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
        # Regular variable reference
        return self._py_var(s)

    def _get_var_type(self, var_name):
        """Try to find the declared type of a variable from the IR."""
        for instr in self.ir:
            if instr.op == "DECLARE" and instr.dest == var_name:
                return instr.extra.get("type")
        return None


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

    DEFAULT_VALUES = CodeGenerator.DEFAULT_VALUES
    TYPE_COERCE = CodeGenerator.TYPE_COERCE

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
            return f'_order["{s[6:]}"]'
        safe = s.replace(".", "_").replace("?", "_q").replace("@", "_at")
        if safe in ("class", "def", "return", "if", "else", "elif", "for",
                     "while", "break", "continue", "pass", "import", "from",
                     "True", "False", "None", "and", "or", "not", "in", "is"):
            safe = f"_{safe}"
        return safe

    def _py_val(self, val):
        if val is None:
            return "None"
        if isinstance(val, bool):
            return "True" if val else "False"
        if isinstance(val, int):
            return str(val)
        if isinstance(val, float):
            return repr(val)
        s = str(val)
        if (s.startswith('"') and s.endswith('"')) or \
           (s.startswith("'") and s.endswith("'")):
            return s
        if s.startswith("_t"):
            return s
        if s.startswith("order."):
            return f'_order["{s[6:]}"]'
        return self._py_var(s)

    def _get_var_type(self, var_name):
        for instr in self.ir:
            if instr.op == "DECLARE" and instr.dest == var_name:
                return instr.extra.get("type")
        return None

    # ------------------------------------------------------------------
    # Header / Footer
    # ------------------------------------------------------------------

    def _emit_header(self):
        self._emit_raw("# === Generated CARAMEL Program ===")
        self._emit_raw("")
        self._emit_raw("def _caramel_to_bool(val):")
        self._emit_raw("    if isinstance(val, bool): return val")
        self._emit_raw("    if isinstance(val, (int, float)): return val != 0")
        self._emit_raw("    if isinstance(val, str): return len(val) > 0")
        self._emit_raw("    return bool(val)")
        self._emit_raw("")
        self._emit_raw("def _caramel_input(prompt=''):")
        self._emit_raw("    return input(prompt)")
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
        self._emit_raw("_main_cup()")

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
            bi = self._gen_simple(instr_i, bi)

        if not has_body:
            self._emit("pass")

        self._pop()
        self._emit("")
        self._declared = old_declared
        return func_end + 1

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

        # Find a GOTO back to this label
        for j in range(label_idx + 1, min(label_idx + 200, len(self.ir))):
            if self.ir[j].op == "GOTO" and self.ir[j].dest == start_label:
                # The LABEL after the GOTO is the end
                if j + 1 < len(self.ir) and self.ir[j + 1].op == "LABEL":
                    return j + 1  # ← returns the END label index
                return j
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
                break

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
                if instr_i.dest and "END" in instr_i.dest:
                    self._emit("break")
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
        return end + 1
    
    def _gen_if_block(self, start, boundary):
        """Generate an if/else block from IR pattern."""
        instr = self.ir[start]
        cond = self._py_val(instr.arg1)
        else_label = instr.dest

        self._emit(f"if _caramel_to_bool({cond}):")
        self._push()

        # Find the GOTO end_label and LABEL else_label
        goto_end_idx = None
        else_label_idx = None
        end_label = None

        for j in range(start + 1, boundary):
            if self.ir[j].op == "GOTO" and goto_end_idx is None:
                goto_end_idx = j
                end_label = self.ir[j].dest
            if self.ir[j].op == "LABEL" and self.ir[j].dest == else_label:
                else_label_idx = j
                break

        # Emit if-body (between IF_FALSE and GOTO/else_label)
        body_end = goto_end_idx if goto_end_idx else (else_label_idx or boundary)
        has_body = False
        bi = start + 1
        while bi < body_end and bi < len(self.ir):
            instr_i = self.ir[bi]
            if instr_i.op == "LABEL":
                bi += 1
                continue
            if instr_i.op in ("GOTO",):
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
            for j in range(else_label_idx, boundary):
                if self.ir[j].op == "LABEL" and self.ir[j].dest == end_label:
                    end_label_idx = j
                    break

            if end_label_idx and end_label_idx > else_label_idx + 1:
                # Check if else block is another if (elifroth)
                first_else_instr = None
                for j in range(else_label_idx + 1, end_label_idx):
                    if self.ir[j].op not in ("LABEL", "GOTO", "NOP"):
                        first_else_instr = j
                        break

                if first_else_instr and self.ir[first_else_instr].op == "IF_FALSE":
                    self._emit("else:")
                    self._push()
                    # Recurse for elif chain
                    bi = first_else_instr
                    while bi < end_label_idx:
                        instr_i = self.ir[bi]
                        if instr_i.op == "IF_FALSE":
                            bi = self._gen_if_block(bi, end_label_idx)
                            continue
                        if instr_i.op in ("LABEL", "GOTO"):
                            bi += 1
                            continue
                        self._gen_simple(instr_i, bi)
                        bi += 1
                    self._pop()
                else:
                    self._emit("else:")
                    self._push()
                    has_else = False
                    bi = else_label_idx + 1
                    while bi < end_label_idx:
                        instr_i = self.ir[bi]
                        if instr_i.op in ("LABEL", "GOTO"):
                            bi += 1
                            continue
                        if instr_i.op == "IF_FALSE":
                            bi = self._gen_if_block(bi, end_label_idx)
                            has_else = True
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
        return body_end + 1

    def _gen_simple(self, instr, idx):
        """Generate a simple (non-control-flow) instruction."""
        op = instr.op

        if op == "DECLARE":
            if instr.extra.get("param"):
                return idx + 1
            var = self._py_var(instr.dest)
            dtype = instr.extra.get("type", "bean")
            default = self.DEFAULT_VALUES.get(dtype, "None")
            if var not in self._declared:
                self._emit(f"{var} = {default}")
                self._declared.add(var)

        elif op == "ASSIGN":
            dest = self._py_var(instr.dest)
            val = self._py_val(instr.arg1)
            self._emit(f"{dest} = {val}")

        elif op == "BINOP":
            dest = self._py_var(instr.dest)
            a = self._py_val(instr.arg1)
            b = self._py_val(instr.arg2)
            binop = instr.extra.get("binop", "+")
            if binop == "&&":
                self._emit(f"{dest} = _caramel_to_bool({a}) and _caramel_to_bool({b})")
            elif binop == "||":
                self._emit(f"{dest} = _caramel_to_bool({a}) or _caramel_to_bool({b})")
            else:
                self._emit(f"{dest} = {a} {binop} {b}")

        elif op == "UNARYOP":
            dest = self._py_var(instr.dest)
            a = self._py_val(instr.arg1)
            uop = instr.extra.get("unaryop", "-")
            if uop == "!":
                self._emit(f"{dest} = not _caramel_to_bool({a})")
            else:
                self._emit(f"{dest} = {uop}({a})")

        elif op == "PRINT":
            args = instr.extra.get("args", [])
            if args:
                py_args = ", ".join(self._py_val(a) for a in args)
                self._emit(f"_caramel_print({py_args})")
            else:
                self._emit("_caramel_print()")

        elif op == "INPUT":
            dest = self._py_var(instr.dest)
            dtype = self._get_var_type(instr.dest)
            if dtype == "bean":
                self._emit(f"{dest} = int(_caramel_input())")
            elif dtype == "drip":
                self._emit(f"{dest} = float(_caramel_input())")
            else:
                self._emit(f"{dest} = _caramel_input()")

        elif op == "RETURN":
            if instr.arg1 is not None:
                self._emit(f"return {self._py_val(instr.arg1)}")
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
            self._emit(f"{dest} = {func}({', '.join(params)})")

        elif op == "PARAM":
            pass  # handled by CALL

        elif op == "CONCAT":
            dest = self._py_var(instr.dest)
            a = self._py_val(instr.arg1)
            b = self._py_val(instr.arg2)
            self._emit(f"{dest} = str({a}) + str({b})")

        elif op == "ARR_LOAD":
            dest = self._py_var(instr.dest)
            arr = self._py_var(instr.arg1)
            idx_val = self._py_val(instr.arg2)
            self._emit(f"{dest} = {arr}[{idx_val}]")

        elif op == "ARR_STORE":
            arr = self._py_var(instr.dest)
            idx_val = self._py_val(instr.arg1)
            val = self._py_val(instr.arg2)
            self._emit(f"{arr}[{idx_val}] = {val}")

        elif op == "MEMBER_ACC":
            dest = self._py_var(instr.dest)
            obj = self._py_var(instr.arg1)
            member = instr.arg2
            self._emit(f"{dest} = {obj}.get('{member}', None) if isinstance({obj}, dict) else getattr({obj}, '{member}', None)")

        elif op in ("FUNC_BEGIN", "FUNC_END", "LABEL", "GOTO",
                     "IF_FALSE", "IF_TRUE", "NOP"):
            pass  # handled elsewhere

        return idx + 1

    def _get_var_type(self, var_name):
        for instr in self.ir:
            if instr.op == "DECLARE" and instr.dest == var_name:
                return instr.extra.get("type")
        return None
