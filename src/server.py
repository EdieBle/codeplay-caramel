# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from src.Lexer.lexer import tokenize
from src.Parser.parser import Parser
from src.Semantic.analyzer import SemanticAnalyzer
from src.CodeGen.ir_generator import IRGenerator
from src.CodeGen.optimizer import optimize_ir
from src.CodeGen.code_generator import StructuredCodeGenerator

import threading
import queue
import uuid
import time
import io as _io

app = Flask(__name__)
CORS(app)

# -- Active execution sessions --------------------------------------------
sessions = {}          # session_id -> ExecutionSession
SESSION_TTL = 600      # seconds before a stale session is cleaned up


class ExecutionSession:
    """Holds state for one interactive execution run."""
    def __init__(self):
        self.id = uuid.uuid4().hex[:8]
        self.input_queue = queue.Queue()
        self.output_buffer = []
        self.status = "compiling"   # compiling | running | waiting_for_input | completed | error
        self.errors = None
        self.runtime_error = None
        self.generated_code = ""
        self.input_prompt = ""
        self.created_at = time.time()


def _cleanup_old_sessions():
    """Remove sessions older than SESSION_TTL."""
    now = time.time()
    stale = [sid for sid, s in sessions.items() if now - s.created_at > SESSION_TTL]
    for sid in stale:
        sessions.pop(sid, None)


def _run_session(session):
    """Run the full compiler pipeline inside a background thread."""
    code = session._source_code

    # Step 1: Parse
    parser = Parser(code)
    parser.start()
    if parser.errors:
        session.errors = parser.errors
        session.status = "completed"
        return

    # Step 2: Semantic analysis
    analyzer = SemanticAnalyzer(parser.ast)
    semantic_errors = analyzer.analyze()
    if semantic_errors:
        session.errors = semantic_errors
        session.status = "completed"
        return

    # Step 3: IR generation
    try:
        ir_gen = IRGenerator(parser.ast)
        ir_instructions = ir_gen.generate()
    except Exception as e:
        session.errors = [{"type": "IR_ERROR", "message": f"IR generation failed: {e}"}]
        session.status = "completed"
        return

    # Step 4: Optimization
    try:
        optimized_ir = optimize_ir(ir_instructions)
        print(f"[DEBUG] before optimize: {len(ir_instructions)} instrs")
        print(f"[DEBUG] after optimize:  {len(optimized_ir)} instrs")
    except Exception:
        optimized_ir = ir_instructions

    # Step 5: Code generation
    try:
        codegen = StructuredCodeGenerator(optimized_ir)
        generated_code = codegen.generate()
        session.generated_code = generated_code
    except Exception as e:
        session.errors = [{"type": "CODEGEN_ERROR", "message": f"Code generation failed: {e}"}]
        session.status = "completed"
        return
    
    # Uncomment when needed to store the generated code
    # with open(r"C:\Users\Jed\Downloads\codeplay-caramel\src\debug_generated.py", "w") as f:
    #     f.write(generated_code)

    # Step 6: Execute with interactive I.O
    session.status = "running"

    def mock_input(prompt=""):
        """Block until the frontend sends a line of input."""
        if prompt:
            session.output_buffer.append(prompt)
        session.input_prompt = prompt
        session.status = "waiting_for_input"
        try:
            value = session.input_queue.get(timeout=300)
        except queue.Empty:
            value = ""
        session.status = "running"
        session.input_prompt = ""
        return value

    def mock_print(*args, **kwargs):
        """Capture print output."""
        buf = _io.StringIO()
        kwargs.setdefault("end", "")
        print(*args, file=buf, **kwargs)
        text = buf.getvalue()
        session.output_buffer.append(text)

    env = {"__builtins__": __builtins__}
    env["input"] = mock_input
    env["print"] = mock_print
    env["_caramel_input"] = mock_input
    env["_caramel_print"] = mock_print

    try:
        exec(generated_code, env)
    except Exception as e:
        session.runtime_error = str(e)

    session.status = "completed"


# -- Existing endpoints (unchanged) -----------------------------

@app.route("/tokenize", methods=["POST"])
def run_lexer():
    data = request.get_json()
    code = data.get("code", "")
    tokens = tokenize(code)
    return jsonify(tokens)


@app.route("/parse", methods=["POST"])
def run_parser():
    data = request.get_json()
    code = data.get("code", "")
    parser = Parser(code)
    parser.start()
    return jsonify({"errors": parser.errors})


@app.route("/analyze", methods=["POST"])
def run_analyzer():
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
    """Full compiler pipeline (kept for backward compat)."""
    data = request.get_json()
    code = data.get("code", "")
    input_values = data.get("input", [])

    parser = Parser(code)
    parser.start()
    if parser.errors:
        return jsonify({"errors": parser.errors, "output": "", "generated_code": ""})

    analyzer = SemanticAnalyzer(parser.ast)
    semantic_errors = analyzer.analyze()
    if semantic_errors:
        return jsonify({"errors": semantic_errors, "output": "", "generated_code": ""})

    try:
        ir_gen = IRGenerator(parser.ast)
        ir_instructions = ir_gen.generate()
    except Exception as e:
        return jsonify({
            "errors": [{"type": "IR_ERROR", "message": f"IR generation failed: {e}"}],
            "output": "", "generated_code": "",
        })

    try:
        optimized_ir = optimize_ir(ir_instructions)
    except Exception:
        optimized_ir = ir_instructions

    try:
        codegen = StructuredCodeGenerator(optimized_ir)
        result = codegen.execute(input_values=input_values)
    except Exception as e:
        return jsonify({
            "errors": [{"type": "CODEGEN_ERROR", "message": f"Code generation failed: {e}"}],
            "output": "", "generated_code": "",
        })

    return jsonify({
        "errors": [],
        "output": result.get("output", ""),
        "generated_code": result.get("code", ""),
        "runtime_error": result.get("error"),
    })


# -- New interactive execution endpoints --------------------------

@app.route("/execute/start", methods=["POST"])
def execute_start():
    """Start an interactive execution session."""
    _cleanup_old_sessions()
    data = request.get_json()
    code = data.get("code", "")

    session = ExecutionSession()
    session._source_code = code
    sessions[session.id] = session

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
        "status": session.status,
        "output": output,
        "errors": session.errors or [],
        "runtime_error": session.runtime_error,
        "generated_code": session.generated_code,
        "input_prompt": session.input_prompt,
    })


@app.route("/execute/input/<session_id>", methods=["POST"])
def execute_input(session_id):
    """Send a line of input to a waiting execution session."""
    session = sessions.get(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404

    data = request.get_json()
    value = data.get("value", "")

    # Echo the input to the output buffer
    session.output_buffer.append(value + "\n")
    session.input_queue.put(value)

    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
