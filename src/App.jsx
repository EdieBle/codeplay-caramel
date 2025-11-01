import { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./styles.css";
import NavBar from "./components/NavBar";
import "./components/NavBar.css";
import LexerError from "./components/LexerError";

export default function App() {
  const [code, setCode] = useState(
`~~this is supposed to be an unclosed multi-line comment, but thats the problem of the parser afaik
bean x = -4
~. 
    should flag the 2 statements below
    test multi  @$%^&*()[]~\`"{}|<>?/\\
.~
Drip draaaaaaaaaaaaaaaaaaaaaaa = 5.0 ~~more than 15 chars
bean% bener = 3  

mug [  ~~sample program lol bean x = 4 sample :D @$%^&*()[]~\`"{}|<>?/\ <-- tester ignore
    bean x_bean = 40
    drip y_bean = 20
    blend b_blend = "Test string literal"
    churro c_churro = 'a',k = '\\n'
    temp t_temp = hot, t_ = cold
]  

recipe bean calc_test (bean x, bean y) [
    bean sum = x + y
    glaze(sum)
    refill? sum
]

crema class_uno [
    backroom bean not_pub = 7
    bean not_pub_implic = 120
    cafe bean pub = 5

    cafe recipe drip cube_func (drip x) [
      drip square = x * x * x
      refill? square
    ]
    cafe recipe drip cube_func (drip x) [
      drip square = x * x * x
      refill? square
    ]
]

bean cup() [
    bean x = 5, y = 7
    bean sum = glob_x + calc_test(order.x, y)
    glaze("Function sum and glob_x = " + sum)
    refill? 0
]
`
  );

  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [hasRun, setHasRun] = useState(false);

  const [showTokens, setShowTokens] = useState(false);
  const [lineTokens, setLineTokens] = useState([]);
  const [showLineTokens, setShowLineTokens] = useState(false);
  const [busy, setBusy] = useState(false);

  const textareaRef = useRef(null);
  const lineNumbersRef = useRef(null);
  const [currentLine, setCurrentLine] = useState(1);

  // Tokenize all lines
  const handleTokenize = async () => {
    setBusy(true);
    try {
      const res = await axios.post("http://127.0.0.1:5000/tokenize", { code });
      const result = res.data;

      // error handler for the entirety
      const errors = result.filter((t) => t.type === "ERROR" || t.type === "LEXICAL_ERROR");
      const validTokens = result.filter((t) => t.type !== "ERROR" ||t.type !== "LEXICAL_ERROR");

      setTokens(validTokens);
      setErrors(errors);
      setHasRun(true);
      setShowLineTokens(false);
      setShowTokens(true);
    } catch (err) {
      console.error("Error contacting backend:", err);
      setErrors([{ type: "CONNECTION_ERROR", lexeme: "Backend not running" }]);
    } finally {
      setBusy(false);
    }
  };

  // Tokenize only current line
  const handleTokenizeLine = async () => {
    setBusy(true);
    try {
      const ta = textareaRef.current;
      if (!ta) return;
      const pos = ta.selectionStart;
      const before = code.slice(0, pos);
      const lineIndex = before.split("\n").length - 1;
      const lines = code.split("\n");
      const lineText = lines[lineIndex] ?? "";

      const res = await axios.post("http://127.0.0.1:5000/tokenize", { code: lineText });
      const result = res.data;

      const normalized = result.map((t) => ({ ...t, line: lineIndex + 1 }));

      // Error handler for the single line
      const lineErrors = normalized.filter((t) => t.type === "ERROR" || t.type ===  "LEXICAL_ERROR");
      const validLineTokens = normalized.filter((t) => t.type !== "ERROR" || t.type !== "LEXICAL_ERROR");

      setLineTokens(validLineTokens);
      setErrors(lineErrors);
      setShowLineTokens(true);
      setShowTokens(true);
    } catch (err) {
      console.error("Error contacting backend:", err);
      setErrors([{ type: "CONNECTION_ERROR", lexeme: "Backend not running" }]);
    } finally {
      setBusy(false);
    }
  };

  const toggleShowTokens = () => {
    setShowTokens((s) => !s);
    if (!showTokens) setShowLineTokens(false);
  };

  // Detect active line
  const updateCurrentLine = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    const pos = ta.selectionStart;
    const before = code.slice(0, pos);
    const lineIndex = before.split("\n").length - 1;
    setCurrentLine(lineIndex + 1);
  };

const handleScroll = () => {
  const ta = textareaRef.current;
  const ln = lineNumbersRef.current;
  if (!ta || !ln) return;
  ln.scrollTop = ta.scrollTop; // keeps numbers aligned while scrolling
};


  useEffect(() => {
    updateCurrentLine();
  }, [code]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <NavBar />

      <div style={{ display: "flex", gap: "1rem", padding: "1rem", flex: 1 }}>
        {/* CODE EDITOR */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <div className="editor">
            <h3 className="play-bold">Code Editor</h3>

            <div className="editor-container">
  {/* Line numbers */}
  <div className="line-numbers" ref={lineNumbersRef}>
    {code.split("\n").map((_, i) => (
      <div
        key={i}
        className={`line-number ${i + 1 === currentLine ? "active" : ""}`}
      >
        {i + 1}
      </div>
    ))}
  </div>

  {/* Text area */}
  <textarea
    ref={textareaRef}
    className="textarea"
    value={code}
    onChange={(e) => setCode(e.target.value)}
    onClick={updateCurrentLine}
    onKeyUp={updateCurrentLine}
    onScroll={handleScroll}
    onKeyDown={(e) => {
      if (e.key === "Tab") {
        e.preventDefault();
        const ta = textareaRef.current;
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        const newValue = code.slice(0, start) + "\t" + code.slice(end);
        setCode(newValue);
        requestAnimationFrame(() => {
          ta.selectionStart = ta.selectionEnd = start + 1;
          updateCurrentLine();
        });
      }
    }}
    spellCheck={false}
  />
</div>


<div className="tokenize-btn-container">
  <button className="tokenize-btn" onClick={handleTokenize} disabled={busy}>
    {busy ? "Tokenizing..." : "Tokenize (full)"}
  </button>

  <button className="tokenize-btn" onClick={handleTokenizeLine} disabled={busy}>
    Tokenize line
  </button>

  <button
    className="tokenize-btn"
    onClick={toggleShowTokens}
    aria-pressed={showTokens}
    disabled={busy}
  >
    {showTokens ? "Hide Tokens" : "Show Tokens"}
  </button>
</div>

          </div>

          {/* ERROR AREA */}
          <div style={{ marginTop: "0.75rem" }}>
            <LexerError errors={errors} />
          </div>
        </div>

        {/* TOKENS PANEL */}
        {showTokens && (
          <div className="tokens">
            <h3 className="play-bold">Tokens</h3>
            {showLineTokens ? (
              <TokenTable tokens={lineTokens} />
            ) : hasRun ? (
              <TokenTable tokens={tokens} />
            ) : (
              <p>Press “Tokenize (full)” or “Tokenize line” to see results.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TokenTable({ tokens }) {
  return (
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
  );
}