# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from Lexer.lexer import tokenize
from Parser.parser import Parser

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

if __name__ == "__main__":
    app.run(port=5000, debug=True)
