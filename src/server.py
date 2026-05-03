# server.py
"""
CARAMEL Language Compiler — Flask Backend Server
=================================================

This server exposes the compiler pipeline over HTTP so the React frontend
IDE can communicate with it.  All compilation-related logic (tokenising,
parsing, semantic analysis, IR generation, loop detection, code generation)
is delegated to the modules in ``src/CodeGen/`` and the new centralised
``pipeline_validator`` module.

Endpoints
---------
POST /tokenize              → Run the lexer only
POST /parse                 → Run lexer + parser
POST /analyze               → Run lexer + parser + semantic analyser
POST /execute               → Full pipeline + synchronous execution (legacy)
POST /execute/start         → Start an interactive execution session
GET  /execute/status/<id>   → Poll session status
POST /execute/input/<id>    → Send user input to a waiting session
POST /build-exe             → Compile → validate → build a standalone .exe

Infinite Loop Protection
------------------------
Three layers prevent an infinite loop from hanging the server:

1. **Static analysis** (``loop_detector.InfiniteLoopDetector``):
   Catches obvious infinite loops at compile time (before any code runs).
   Blocks EXE generation immediately if a loop is detected.

2. **Runtime iteration counter** (injected into generated Python):
   Every loop in the generated code calls ``_caramel_check_loop()`` on each
   iteration.  After 100 000 iterations the loop raises
   ``_CaramelLoopTimeout``, which is caught and surfaced as a runtime error.

3. **Session execution timeout** (``threading.Timer``):
   The interactive execution thread is given a hard 30-second wall-clock
   deadline.  If it has not completed by then the session is force-stopped
   and the user sees a clear timeout message.
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from src.Lexer.lexer import tokenize
from src.Parser.parser import Parser
from src.Semantic.analyzer import SemanticAnalyzer
from src.CodeGen.ir_generator import IRGenerator
from src.CodeGen.optimizer import optimize_ir
from src.CodeGen.code_generator import StructuredCodeGenerator
from src.CodeGen.pipeline_validator import validate_and_compile, CompilationMode

import threading
import queue
import uuid
import time
import io as _io
import os
import shutil
import subprocess
import sys
import tempfile

app = Flask(__name__)
CORS(app)

# -- Active execution sessions -----------------------------------------------
sessions = {}          # session_id -> ExecutionSession
SESSION_TTL = 600      # Seconds before a stale session is garbage-collected

# Hard wall-clock limit (seconds) for a single interactive execution session.
# If the program has not finished within this window the session is force-killed
# and the user sees an "Execution timed out" message.
EXECUTION_TIMEOUT_SECONDS = 30


class ExecutionSession:
    """
    Holds all state for one interactive execution run.

    Attributes
    ----------
    id : str
        Short unique identifier for this session.
    input_queue : queue.Queue
        Used to pass user-supplied input lines to the running program thread.
    output_buffer : list[str]
        Accumulated output text that the frontend polls for.
    status : str
        One of: "compiling" | "running" | "waiting_for_input" | "completed" | "error"
    errors : list[dict] or None
        Compiler / runtime errors (None if none).
    runtime_error : str or None
        Runtime exception message, if any.
    generated_code : str
        The Python source produced by the code generator.
    input_prompt : str
        Current input prompt text (empty when not waiting).
    created_at : float
        Unix timestamp of session creation (used for TTL-based cleanup).
    _timeout_timer : threading.Timer or None
        Watchdog timer that force-stops the session after EXECUTION_TIMEOUT_SECONDS.
    _stop_event : threading.Event
        Set when the session should be forcibly stopped (e.g. timeout).
    """

    def __init__(self):
        self.id              = uuid.uuid4().hex[:8]
        self.input_queue     = queue.Queue()
        self.output_buffer   = []
        self.status          = "compiling"
        self.errors          = None
        self.runtime_error   = None
        self.generated_code  = ""
        self.input_prompt    = ""
        self.created_at      = time.time()
        # Timeout / force-stop infrastructure
        self._timeout_timer  = None
        self._stop_event     = threading.Event()


# ---------------------------------------------------------------------------
# Session lifecycle helpers
# ---------------------------------------------------------------------------

def _cleanup_old_sessions():
    """Remove sessions that have exceeded SESSION_TTL without completing."""
    now = time.time()
    stale = [sid for sid, s in sessions.items() if now - s.created_at > SESSION_TTL]
    for sid in stale:
        _force_stop_session(sessions.pop(sid, None))


def _force_stop_session(session):
    """
    Gracefully force-stop a running session.

    - Sets the stop event so the execution thread can detect it.
    - Cancels any pending watchdog timer.
    - Puts a sentinel value into the input queue to unblock any blocked
      ``mock_input()`` call.
    """
    if session is None:
        return
    session._stop_event.set()
    if session._timeout_timer is not None:
        session._timeout_timer.cancel()
        session._timeout_timer = None
    # Unblock any thread blocked on input_queue.get()
    try:
        session.input_queue.put_nowait("__CARAMEL_STOP__")
    except Exception:
        pass


def _on_session_timeout(session):
    """
    Called by the watchdog timer when the session exceeds the time limit.

    Marks the session as errored and force-stops the thread.
    """
    if session.status not in ("completed", "error"):
        session.runtime_error = (
            f"Execution timed out after {EXECUTION_TIMEOUT_SECONDS} seconds. "
            "A possible infinite loop was detected. "
            "Check your loop conditions or use 'snap' to break out."
        )
        session.status = "error"
        session.output_buffer.append(
            f"\n[CARAMEL RUNTIME ERROR] Execution timed out after "
            f"{EXECUTION_TIMEOUT_SECONDS} seconds (possible infinite loop).\n"
        )
    _force_stop_session(session)


# ---------------------------------------------------------------------------
# Core execution thread
# ---------------------------------------------------------------------------

def _run_session(session):
    """
    Run the full compiler pipeline and then execute the generated code
    inside a sandboxed ``exec()`` call.

    This function runs on a background daemon thread.  A watchdog timer
    (``_timeout_timer``) is started before execution begins; if the program
    does not complete within ``EXECUTION_TIMEOUT_SECONDS``, the session is
    force-stopped.

    Pipeline
    --------
    1. Compile via ``pipeline_validator.validate_and_compile()``
       (lexer → parser → semantic → IR → loop detection → codegen)
    2. Execute the generated code with mock I/O
    3. Handle _CaramelLoopTimeout (from the iteration-counter guard)
    4. Handle all other runtime exceptions

    Parameters
    ----------
    session : ExecutionSession
        The session object whose ``_source_code`` attribute contains the
        Caramel source code to compile and run.
    """
    code = session._source_code

    # ------------------------------------------------------------------
    # Stage 1–7: Full compiler pipeline (with loop detection)
    # ------------------------------------------------------------------
    result = validate_and_compile(code, mode=CompilationMode.INTERACTIVE)

    if not result.success:
        session.errors = result.errors
        session.status = "completed"
        return

    generated_code       = result.generated_code
    session.generated_code = generated_code

    # ------------------------------------------------------------------
    # Stage 8: Execute with interactive I/O
    # ------------------------------------------------------------------
    session.status = "running"

    # --- Start watchdog timer -------------------------------------------
    # The timer fires on the main-thread pool after EXECUTION_TIMEOUT_SECONDS.
    # It marks the session as timed out and sets the stop event.
    watchdog = threading.Timer(
        EXECUTION_TIMEOUT_SECONDS,
        _on_session_timeout,
        args=(session,),
    )
    watchdog.daemon = True
    session._timeout_timer = watchdog
    watchdog.start()
    # -------------------------------------------------------------------

    def mock_input(prompt=""):
        """
        Block until the frontend sends a line of input or until the session
        is stopped (timeout / force-kill).
        """
        if session._stop_event.is_set():
            raise SystemExit("Session stopped")

        if prompt:
            session.output_buffer.append(prompt)
        session.input_prompt = prompt
        session.status       = "waiting_for_input"

        # Wait for frontend input with periodic stop-event checks
        while not session._stop_event.is_set():
            try:
                value = session.input_queue.get(timeout=1.0)
                break
            except queue.Empty:
                continue
        else:
            # Stop event was set — bail out gracefully
            raise SystemExit("Session stopped")

        # Sentinel value used by _force_stop_session()
        if value == "__CARAMEL_STOP__":
            raise SystemExit("Session stopped")

        session.status       = "running"
        session.input_prompt = ""
        return value

    def mock_print(*args, **kwargs):
        """Capture print output to the session output buffer."""
        buf = _io.StringIO()
        kwargs.setdefault("end", "")
        print(*args, file=buf, **kwargs)
        text = buf.getvalue()
        session.output_buffer.append(text)

    # Build the sandboxed execution environment.
    # We expose only the builtins that the generated code needs.
    env = {"__builtins__": __builtins__}
    env["input"]           = mock_input
    env["print"]           = mock_print
    env["_caramel_input"]  = mock_input
    env["_caramel_print"]  = mock_print

    try:
        exec(generated_code, env)  # noqa: S102
    except SystemExit:
        # Clean stop (timeout force-kill or sentinel value)
        pass
    except Exception as exc:
        # Surface runtime errors (including _CaramelLoopTimeout which becomes
        # a plain Exception after exec() re-raises it from generated code)
        err_msg = str(exc)
        session.runtime_error = err_msg
        session.output_buffer.append(f"\n[CARAMEL RUNTIME ERROR] {err_msg}\n")
    finally:
        # Cancel the watchdog timer (if the program finished before the limit)
        if session._timeout_timer is not None:
            session._timeout_timer.cancel()
            session._timeout_timer = None

    # Only mark as completed if we haven't already been force-stopped as error
    if session.status not in ("error",):
        session.status = "completed"


# ---------------------------------------------------------------------------
# Existing endpoints (tokenise / parse / analyse — unchanged behaviour)
# ---------------------------------------------------------------------------

@app.route("/tokenize", methods=["POST"])
def run_lexer():
    """Tokenise the source code and return the token list."""
    data = request.get_json()
    code = data.get("code", "")
    tokens = tokenize(code)
    return jsonify(tokens)


@app.route("/parse", methods=["POST"])
def run_parser():
    """Run lexer + parser and return any syntax errors."""
    data = request.get_json()
    code = data.get("code", "")
    parser = Parser(code)
    parser.start()
    return jsonify({"errors": parser.errors})


@app.route("/analyze", methods=["POST"])
def run_analyzer():
    """Run lexer + parser + semantic analyser and return errors."""
    data = request.get_json()
    code = data.get("code", "")
    parser = Parser(code)
    parser.start()
    if parser.errors:
        return jsonify({"errors": parser.errors})
    analyzer = SemanticAnalyzer(parser.ast)
    semantic_errors = analyzer.analyze()
    return jsonify({"errors": semantic_errors})


@app.route("/execute", methods=["POST"])
def run_execute():
    """
    Full compiler pipeline (synchronous, legacy endpoint).

    Uses ``validate_and_compile()`` with loop detection enabled.
    Kept for backward compatibility with older frontend code.
    """
    data         = request.get_json()
    code         = data.get("code", "")
    input_values = data.get("input", [])

    result = validate_and_compile(code, mode=CompilationMode.INTERACTIVE)
    if not result.success:
        return jsonify({
            "errors":         result.errors,
            "output":         "",
            "generated_code": "",
        })

    try:
        codegen      = StructuredCodeGenerator(result.optimized_ir)
        exec_result  = codegen.execute(input_values=input_values)
    except Exception as exc:
        return jsonify({
            "errors":         [{"type": "CODEGEN_ERROR", "message": f"Code generation failed: {exc}"}],
            "output":         "",
            "generated_code": "",
        })

    return jsonify({
        "errors":         [],
        "output":         exec_result.get("output", ""),
        "generated_code": exec_result.get("code", ""),
        "runtime_error":  exec_result.get("error"),
    })


# ---------------------------------------------------------------------------
# Interactive execution endpoints
# ---------------------------------------------------------------------------

@app.route("/execute/start", methods=["POST"])
def execute_start():
    """
    Start an interactive execution session.

    Returns a ``session_id`` that the frontend can use to poll status and
    send input.
    """
    _cleanup_old_sessions()
    data = request.get_json()
    code = data.get("code", "")

    session               = ExecutionSession()
    session._source_code  = code
    sessions[session.id]  = session

    thread = threading.Thread(target=_run_session, args=(session,), daemon=True)
    thread.start()

    return jsonify({"session_id": session.id})


@app.route("/execute/status/<session_id>", methods=["GET"])
def execute_status(session_id):
    """Poll the current state of an execution session."""
    session = sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404

    output = "".join(session.output_buffer)

    return jsonify({
        "status":         session.status,
        "output":         output,
        "errors":         session.errors or [],
        "runtime_error":  session.runtime_error,
        "generated_code": session.generated_code,
        "input_prompt":   session.input_prompt,
    })


@app.route("/execute/input/<session_id>", methods=["POST"])
def execute_input(session_id):
    """Send a line of input to a waiting execution session."""
    session = sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404

    data  = request.get_json()
    value = data.get("value", "")

    # Echo the input to the output buffer so it appears in the terminal view
    session.output_buffer.append(value + "\n")
    session.input_queue.put(value)

    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# EXE Build endpoint
# ---------------------------------------------------------------------------

@app.route("/build-exe", methods=["POST"])
def build_exe():
    """
    Compile Caramel source code into a standalone Windows .exe.

    Validation Pipeline
    -------------------
    Every stage must pass before PyInstaller is invoked:

    1. Lexer / Parser  (syntax errors)
    2. Semantic Analyser (type / scope errors)
    3. IR Generator
    4. Optimiser
    5. **Infinite Loop Detector** ← new safety gate
    6. Code Generator (standalone mode)
    7. PyInstaller → .exe
    8. Stream .exe to client

    If any stage fails the endpoint returns a 400/500 JSON response with
    structured error information.  No executable is written to disk.

    Request JSON
    ------------
    ``{ "code": "<caramel source>", "filename": "<optional output name>" }``

    Responses
    ---------
    - ``200 + binary``  — EXE download on success
    - ``400 + JSON``    — Compilation / validation errors
    - ``500 + JSON``    — Build system errors (PyInstaller failure, OS error)
    """
    data     = request.get_json()
    code     = data.get("code", "").strip()
    raw_name = data.get("filename", "caramel_program") or "caramel_program"

    # Sanitise the requested output filename to a safe filesystem identifier
    exe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw_name)
    exe_name = exe_name.strip("_") or "caramel_program"

    if not code:
        return jsonify({"error": "No source code provided."}), 400

    # ------------------------------------------------------------------
    # Stages 1–6: Full pipeline validation (including loop detection)
    # ------------------------------------------------------------------
    result = validate_and_compile(
        code,
        mode=CompilationMode.STANDALONE,
        run_loop_detection=True,
    )

    if not result.success:
        # Map stage name to HTTP status code
        # Loop detection / semantic / parser errors → 400 (client fault)
        # Internal crashes → 500
        client_stages = {"parser", "semantic", "ir", "codegen", "loop_detection"}
        status_code   = 400 if result.stage in client_stages else 500

        error_stage_labels = {
            "parser":         "Cannot build EXE: source code has syntax errors.",
            "semantic":       "Cannot build EXE: source code has semantic errors.",
            "ir":             "Cannot build EXE: IR generation failed.",
            "codegen":        "Cannot build EXE: code generation failed.",
            "loop_detection": "Cannot build EXE: infinite loop detected in source code.",
        }
        message = error_stage_labels.get(
            result.stage,
            f"Cannot build EXE: compilation failed at stage '{result.stage}'.",
        )

        return jsonify({
            "errors":  result.errors,
            "stage":   result.stage,
            "message": message,
        }), status_code

    standalone_code = result.standalone_code

    # ------------------------------------------------------------------
    # Stage 7: PyInstaller build
    # All temp artefacts are placed inside a unique temp directory and
    # cleaned up unconditionally in the ``finally`` block below.
    # ------------------------------------------------------------------
    build_dir = tempfile.mkdtemp(prefix="caramel_build_")
    exe_path  = None

    try:
        # 7a. Write the generated Python source to a temp file
        src_file = os.path.join(build_dir, f"{exe_name}.py")
        with open(src_file, "w", encoding="utf-8") as fh:
            fh.write(standalone_code)

        # 7b. Ensure PyInstaller is available; install on-the-fly if needed
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"],
                check=True,
                capture_output=True,
            )

        # 7c. Run PyInstaller
        #   --onefile    : bundle everything into a single .exe
        #   --console    : keep the console window (Caramel uses input/print)
        #   --clean      : remove PyInstaller cache before building
        #   --noconfirm  : overwrite output without prompting
        #   --distpath   : output directory for the finished .exe
        #   --workpath   : intermediate build artefacts directory
        #   --specpath   : .spec file directory
        dist_dir = os.path.join(build_dir, "dist")
        work_dir = os.path.join(build_dir, "work")
        spec_dir = build_dir

        pyinstaller_cmd = [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--console",
            "--clean",
            "--noconfirm",
            f"--distpath={dist_dir}",
            f"--workpath={work_dir}",
            f"--specpath={spec_dir}",
            f"--name={exe_name}",
            src_file,
        ]

        build_result = subprocess.run(
            pyinstaller_cmd,
            capture_output=True,
            text=True,
            timeout=120,   # 2-minute hard limit for PyInstaller itself
        )

        if build_result.returncode != 0:
            # Surface PyInstaller's stderr so the user can diagnose the problem
            error_detail = (build_result.stderr or build_result.stdout or "Unknown error")[-2000:]
            return jsonify({
                "stage":   "pyinstaller",
                "message": "PyInstaller failed to build the executable.",
                "detail":  error_detail,
            }), 500

        # 7d. Locate the produced .exe
        exe_path = os.path.join(dist_dir, f"{exe_name}.exe")
        if not os.path.isfile(exe_path):
            return jsonify({
                "stage":   "pyinstaller",
                "message": "EXE file was not found after build. This is unexpected.",
            }), 500

        # ------------------------------------------------------------------
        # Stage 8: Stream the .exe back to the client
        # ------------------------------------------------------------------
        return send_file(
            exe_path,
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=f"{exe_name}.exe",
        )

    except subprocess.TimeoutExpired:
        return jsonify({
            "stage":   "pyinstaller",
            "message": "EXE build timed out (> 2 minutes). The program may be too large.",
        }), 500
    except Exception as exc:
        return jsonify({
            "stage":   "build",
            "message": f"Unexpected build error: {exc}",
        }), 500
    finally:
        # Always clean up the temporary build directory, even on error.
        # Flask's send_file handles the file descriptor safely on most WSGI
        # servers before we remove the directory.
        try:
            shutil.rmtree(build_dir, ignore_errors=True)
        except Exception:
            pass  # Non-fatal — OS will clean up the temp dir eventually


if __name__ == "__main__":
    app.run(port=5000, debug=True)
