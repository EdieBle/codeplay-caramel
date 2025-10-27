from flask import Flask, request, jsonify
from flask_cors import CORS
from lexer import tokenize

app = Flask(__name__)
CORS(app)  # test

@app.route("/tokenize", methods=["POST"])
def run_lexer():
    data = request.get_json()
    code = data.get("code", "")
    tokens = tokenize(code)
    return jsonify(tokens)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
