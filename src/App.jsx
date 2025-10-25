import { useState } from "react";
import { tokenize } from "./lexer";
import "./styles.css";

export default function App() {
  const [code, setCode] = useState(
`local var int x = 16;
thread("Number: " + x);
thread("hello world");`
  );

  const [tokens, setTokens] = useState([]);
  const [hasRun, setHasRun] = useState(false);

  const handleTokenize = () => {
    const result = tokenize(code);
    setTokens(result);
    setHasRun(true);
  };

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* Left: code editor */}
      <div className="editor">
        <h3>Code Editor</h3>
        <textarea
          className="textarea"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <button className="tokenize-btn" onClick={handleTokenize}>
          Tokenize
        </button>
      </div>

      {/* Right: tokens */}
      <div className="tokens">
        <h3>Tokens</h3>
        {hasRun ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Lexeme</th>
                  <th>Line</th>
                  <th>Column</th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((t, i) => (
                  <tr key={i}>
                    <td>{t.type}</td>
                    <td>{t.lexeme}</td>
                    <td>{t.line}</td>
                    <td>{t.column}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="error-box">
              {tokens.some((t) => t.type === "ERROR")
                ? "Lexical error found!"
                : "No errors"}
            </div>
          </>
        ) : (
          <p>Press “Tokenize” to start.</p>
        )}
      </div>
    </div>
  );
}
