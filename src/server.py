# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from src.Lexer.lexer import tokenize
from src.Parser.parser import Parser
from src.Semantic.analyzer import SemanticAnalyzer

app = Flask(__name__)
CORS(app)

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

    return jsonify({
        "errors": parser.errors
    })

@app.route("/analyze", methods=["POST"])
def run_analyzer():                          # was duplicate of run_parser — fixed
    data = request.get_json()
    code = data.get("code", "")

    parser = Parser(code)
    parser.start()

    if parser.errors:                        # stop if parse failed
        return jsonify({ "errors": parser.errors })

    analyzer = SemanticAnalyzer(parser.ast)
    semantic_errors = analyzer.analyze()

    return jsonify({ "errors": semantic_errors })

if __name__ == "__main__":
    app.run(port=5000, debug=True)
