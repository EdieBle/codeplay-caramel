import { useState, useRef } from "react";
import { tokenize } from "./lexer";
import "./styles.css";
import NavBar from "./components/NavBar";
import "./components/NavBar.css";
import LexerError from './components/LexerError';

export default function App() {
  const [code, setCode] = useState(
`local var int x = 16;
thread("Number: " + x);
thread("hello world");`
  );

  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [hasRun, setHasRun] = useState(false);

  // UI state for tokens panel
  const [showTokens, setShowTokens] = useState(false);
  const [lineTokens, setLineTokens] = useState([]);
  const [showLineTokens, setShowLineTokens] = useState(false);

  const textareaRef = useRef(null);

  const handleTokenize = () => {
    const result = tokenize(code);
    const errors = result.filter(t => t.type === "ERROR");
    const validTokens = result.filter(t => t.type !== "ERROR");
    setTokens(validTokens);
    setErrors(errors);
    setHasRun(true);
  };

  const toggleShowTokens = () => {
    setShowTokens((s) => !s);
    if (!showTokens) {
      setShowLineTokens(false);
    }
  };

  // Tokenize only the current line where the caret is
  const handleTokenizeLine = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const before = code.slice(0, pos);
    const lineIndex = before.split('\n').length - 1; // 0-based
    const lines = code.split('\n');
    const lineText = lines[lineIndex] ?? "";
    const result = tokenize(lineText);
    const normalized = result.map((t) => ({ ...t, line: lineIndex + 1 }));
    const lineErrors = normalized.filter(t => t.type === "ERROR");
    const validLineTokens = normalized.filter(t => t.type !== "ERROR");
    setLineTokens(validLineTokens);
    setErrors(lineErrors);
    setShowLineTokens(true);
    setShowTokens(true);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <NavBar />

      <div style={{ display: "flex", gap: "1rem", padding: "1rem", flex: 1 }}>
        {/* Main column: editor + error */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <div className="editor">
            <h3>Code Editor</h3>
            <textarea
              ref={textareaRef}
              className="textarea"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />

            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
              <button className="tokenize-btn" onClick={handleTokenize}>
                Tokenize (full)
              </button>
              <button className="tokenize-btn" onClick={handleTokenizeLine}>
                Tokenize line
              </button>
              <button
                className="tokenize-btn"
                onClick={toggleShowTokens}
                aria-pressed={showTokens}
              >
                {showTokens ? "Hide Tokens" : "Show Tokens"}
              </button>
            </div>
          </div>

          {/* Error area always visible under editor */}
          <div style={{ marginTop: "0.75rem" }}>
            <LexerError errors={errors} />
          </div>
        </div>

        {/* Tokens panel (hidden unless requested) */}
        {showTokens && (
          <div className="tokens" style={{ width: "45%" }}>
            <h3>Tokens</h3>
            {showLineTokens ? (
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
                  {lineTokens.map((t, i) => (
                    <tr key={i}>
                      <td>{t.type}</td>
                      <td>{t.lexeme}</td>
                      <td>{t.line}</td>
                      <td>{t.column}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : hasRun ? (
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
            ) : (
              <p>Press “Tokenize (full)” or “Tokenize line” to populate tokens.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
