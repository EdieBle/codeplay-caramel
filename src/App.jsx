import { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./styles.css";
import "./App.css";
import NavBar from "./components/NavBar";
import "./components/NavBar.css";
import ErrorTabs from "./components/ErrorTabs";
import Modal from "./components/Modal";

// === Syntax Highlighting Helper ===
const highlightCode = (code) => {
  if (!code) return "";

  // 1. Data Types (Use non-capturing group (?:) so we don't mess up indices)
  const dataTypesRegex = /\b(?:bean|drip|churro|temp|mug|blend)\b/;

  // 2. Literals (Strings & Numbers)
  // Updated to support decimals like 4.5 using (?:\.\d+)?
  const literalsRegex = /".*?"|'.*?'|\b\d+(?:\.\d+)?\b/;

  // 3. Keywords
  // Use non-capturing group (?:) for the OR logic
  const keywordsRegex =
    /\b(?:ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|taste\s+till|snap|skip|brewed|decaf|defoam|cup|hot|cold|recipe|empty|crema|new|cafe|backroom|order|glaze)\b|refill\?|batter@/;

  // 4. Operators
  // Removed outer parentheses.
  // Order matters: longer matches (+=) must come before single matches (+)
  const operatorsRegex =
    /\+\+|--|\+=|-=|\*=|\/=|\=\=|!=|&&|\|\||>=|<=|[-+*/%=<>!]/;

  // 5. Punctuation
  // Removed outer parentheses.
  const punctuationRegex = /[(){}[\].,]/;

  // Combine into one master regex
  // Each line here creates exactly ONE capturing group
  const masterRegex = new RegExp(
    `(${dataTypesRegex.source})|(${literalsRegex.source})|(${keywordsRegex.source})|(${operatorsRegex.source})|(${punctuationRegex.source})`,
    "g",
  );

  let lastIndex = 0;
  let match;
  const elements = [];

  while ((match = masterRegex.exec(code)) !== null) {
    // === IDENTIFIERS LOGIC ===
    // Any text *between* matches is treated as an identifier (variables like x, val)
    if (match.index > lastIndex) {
      elements.push(
        <span key={lastIndex} className="token-identifier">
          {code.slice(lastIndex, match.index)}
        </span>,
      );
    }

    let className = "token-identifier";

    // Assign class based on which Group matched
    if (match[1]) {
      className = "token-datatype"; // SeaGreen
    } else if (match[2]) {
      className = "token-literal"; // Olive
    } else if (match[3]) {
      className = "token-keyword"; // Red
    } else if (match[4]) {
      className = "token-operator"; // Blue
    } else if (match[5]) {
      className = "token-punctuation"; // Orange
    }

    elements.push(
      <span key={match.index} className={className}>
        {match[0]}
      </span>,
    );
    lastIndex = masterRegex.lastIndex;
  }

  // Push remaining text
  if (lastIndex < code.length) {
    elements.push(
      <span key={lastIndex} className="token-identifier">
        {code.slice(lastIndex)}
      </span>,
    );
  }

  return elements;
};

export default function App() {
  const [code, setCode] = useState(
    `bean cup() [
  bean x = 5, y = 7
  drip val = 4.5
  refill? 0
]`,
  );

  const [tokens, setTokens] = useState([]);
  const [errors, setErrors] = useState([]);
  const [hasRun, setHasRun] = useState(false);
  const [hasParsed, setHasParsed] = useState(false);

  // Execution state
  const [executionResult, setExecutionResult] = useState(null);
  const [hasExecuted, setHasExecuted] = useState(false);

  // Layout & UI States
  const [showTokens, setShowTokens] = useState(true);
  const [lineTokens, setLineTokens] = useState([]);
  const [showLineTokens, setShowLineTokens] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showTokenTable, setShowTokenTable] = useState(true);

  // Save Modal State
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveFilename, setSaveFilename] = useState("code");

  // Refs
  const textareaRef = useRef(null);
  const highlightRef = useRef(null);
  const lineNumbersRef = useRef(null);
  const fileInputRef = useRef(null);
  const executionSessionRef = useRef(null);
  const pollTimerRef = useRef(null);
  const [currentLine, setCurrentLine] = useState(1);
  const [currentColumn, setCurrentColumn] = useState(1);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  // === Handlers ===

  const handleSaveFile = () => {
    setShowSaveModal(true);
  };

  const handleSaveModalConfirm = () => {
    if (!saveFilename.trim()) return;
    const cleanedFilename = saveFilename.trim().replace(/\.crml$/i, "");
    const finalFilename = `${cleanedFilename}.crml`;
    const element = document.createElement("a");
    const file = new Blob([code], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = finalFilename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
    URL.revokeObjectURL(element.href);
    setShowSaveModal(false);
    setSaveFilename("code");
  };

  const handleSaveModalCancel = () => {
    setShowSaveModal(false);
    setSaveFilename("code");
  };

  const handleSaveModalKeyDown = (e) => {
    if (e.key === "Enter") {
      handleSaveModalConfirm();
    } else if (e.key === "Escape") {
      handleSaveModalCancel();
    }
  };

  const handleOpenFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith(".crml")) {
      alert("Please select a .crml file");
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === "string") {
        setCode(content);
        setTokens([]);
        setErrors([]);
        setLineTokens([]);
        setHasRun(false);
        setHasParsed(false);
        setShowLineTokens(false);
        setShowTokens(true);
        setCurrentLine(1);
        setExecutionResult(null);
        setHasExecuted(false);
      }
    };
    reader.onerror = () => alert("Error reading file");
    reader.readAsText(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleTokenize = async () => {
    setBusy(true);
    try {
      const res = await axios.post("http://127.0.0.1:5000/tokenize", { code });
      const result = res.data;
      const errors = result.filter(
        (t) => t.type === "ERROR" || t.type === "LEXICAL_ERROR",
      );
      const validTokens = result.filter(
        (t) => t.type !== "ERROR" && t.type !== "LEXICAL_ERROR",
      );
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

  const handleTokenizeAndParse = async () => {
    setBusy(true);
    try {
      const tokenRes = await axios.post("http://127.0.0.1:5000/tokenize", {
        code,
      });
      const tokenResult = tokenRes.data;
      const lexerErrors = tokenResult.filter(
        (t) => t.type === "ERROR" || t.type === "LEXICAL_ERROR",
      );
      const validTokens = tokenResult.filter(
        (t) => t.type !== "ERROR" && t.type !== "LEXICAL_ERROR",
      );
      setTokens(validTokens);
      setErrors(lexerErrors);
      setHasRun(true);
      setShowLineTokens(false);
      setShowTokens(true);

      if (lexerErrors.length === 0) {
        const parseRes = await axios.post("http://127.0.0.1:5000/parse", {
          code,
        });
        const parserErrors = parseRes.data.errors || [];
        setErrors(parserErrors);
        setHasParsed(true);
      }
    } catch (err) {
      console.error("Error contacting backend:", err);
      setErrors([{ type: "CONNECTION_ERROR", lexeme: "Backend not running" }]);
    } finally {
      setBusy(false);
    }
  };

  const handleTokenizeParseAndAnalyzer = async () => {
    setBusy(true);
    try {
      // step 1: Tokenizing
      const tokenRes = await axios.post("http://127.0.0.1:5000/tokenize", {
        code,
      });
      const tokenResult = tokenRes.data;
      const lexerErrors = tokenResult.filter(
        (t) => t.type === "ERROR" || t.type === "LEXICAL_ERROR",
      );
      const validTokens = tokenResult.filter(
        (t) => t.type !== "ERROR" && t.type !== "LEXICAL_ERROR",
      );
      setTokens(validTokens);
      setErrors(lexerErrors);
      setHasRun(true);
      setShowLineTokens(false);
      setShowTokens(true);

      if (lexerErrors.length > 0) {
        setErrors(lexerErrors);
        return;
      }

      // step 2: Parsing
      const parseRes = await axios.post("http://127.0.0.1:5000/parse", {
        code,
      });
      const parserErrors = parseRes.data.errors || [];
      setHasParsed(true);

      if (parserErrors.length > 0) {
        setErrors(parserErrors);
        return;
      }

      // step 3: Semantically Analyze
      const analyzeRes = await axios.post("http://127.0.0.1:5000/analyze", {
        code,
      });
      const semanticErrors = analyzeRes.data.errors || [];
      setErrors(semanticErrors); // empty array = no errors

      //Insert the error handler for analyzer once it's implemented in the backend
      // start with if (parserErrors.length === 0) (like hiw was lexerErrors where handled before proceeding to syntax)
    } catch (err) {
      console.error("Error contacting backend:", err);
      setErrors([{ type: "CONNECTION_ERROR", lexeme: "Backend not running" }]);
    } finally {
      setBusy(false);
    }
  };

  const handleSendInput = async (value) => {
    const sessionId = executionSessionRef.current;
    if (!sessionId) return;
    try {
      await axios.post(`http://127.0.0.1:5000/execute/input/${sessionId}`, { value });
    } catch (err) {
      console.error("Error sending input:", err);
    }
  };

  const handleExecute = async () => {
    setBusy(true);
    setHasExecuted(false);
    setExecutionResult(null);

    // Clear any previous polling
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    try {
      // Tokenize for the lexeme table
      const tokenRes = await axios.post("http://127.0.0.1:5000/tokenize", { code });
      const tokenResult = tokenRes.data;
      const validTokens = tokenResult.filter(
        (t) => t.type !== "ERROR" && t.type !== "LEXICAL_ERROR",
      );
      setTokens(validTokens);
      setErrors([]);
      setHasRun(true);
      setHasParsed(true);
      setShowLineTokens(false);
      setShowTokens(true);

      // Start interactive execution session
      const startRes = await axios.post("http://127.0.0.1:5000/execute/start", { code });
      const sessionId = startRes.data.session_id;
      executionSessionRef.current = sessionId;

      // Set initial state - show output tab immediately
      setExecutionResult({ output: "", generated_code: "", status: "running" });
      setHasExecuted(true);

      // Poll for status
      const poll = async () => {
        try {
          const statusRes = await axios.get(
            `http://127.0.0.1:5000/execute/status/${sessionId}`
          );
          const data = statusRes.data;

          setExecutionResult({
            output: data.output || "",
            generated_code: data.generated_code || "",
            runtime_error: data.runtime_error || null,
            errors: data.errors && data.errors.length > 0 ? data.errors : null,
            status: data.status,
            input_prompt: data.input_prompt || "",
          });

          if (data.errors && data.errors.length > 0) {
            setErrors(data.errors);
          }

          if (data.status === "completed") {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
            executionSessionRef.current = null;
            setBusy(false);
          }
        } catch (err) {
          console.error("Polling error:", err);
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
          setBusy(false);
        }
      };

      pollTimerRef.current = setInterval(poll, 500);
      // Also do an immediate poll
      poll();
    } catch (err) {
      console.error("Error contacting backend:", err);
      setErrors([{ type: "CONNECTION_ERROR", lexeme: "Backend not running" }]);
      setBusy(false);
    }
  };

  const handleClearEditor = () => {
    // Stop any running execution polling
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    executionSessionRef.current = null;

    setCode("");
    setTokens([]);
    setErrors([]);
    setLineTokens([]);
    setHasRun(false);
    setHasParsed(false);
    setShowLineTokens(false);
    setShowTokens(true);
    setCurrentLine(1);
    setExecutionResult(null);
    setHasExecuted(false);
  };

  const updateCursorPosition = () => {
    const ta = textareaRef.current;
    if (!ta) return;

    const pos = ta.selectionStart ?? 0;
    const before = code.slice(0, pos);

    const lines = before.split("\n");

    setCurrentLine(lines.length);

    const lastLine = lines[lines.length - 1] ?? "";
    setCurrentColumn(lastLine.length + 1);
  };

  const handleScroll = () => {
    const ta = textareaRef.current;
    const ln = lineNumbersRef.current;
    const hl = highlightRef.current;
    if (!ta) return;

    if (ln) ln.scrollTop = ta.scrollTop;
    if (hl) {
      hl.scrollTop = ta.scrollTop;
      hl.scrollLeft = ta.scrollLeft;
    }
  };

  useEffect(() => {
    updateCursorPosition();
  }, [code]);

  return (
    <div className="app-root">
      <input
        ref={fileInputRef}
        type="file"
        accept=".crml"
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />
      <NavBar onSaveFile={handleSaveFile} onOpenFile={handleOpenFile} />

      <div className="main-content">
        <div
          className={`layout-row-top ${
            showTokenTable ? "" : "layout-row-top--expanded"
          }`}
        >
          <div className="editor layout-flex">
            <h3 className="play-bold">Code Editor</h3>

            <div className="editor-container">
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

              <div className="code-wrapper">
                <pre
                  className="code-layer highlight-overlay"
                  ref={highlightRef}
                >
                  {highlightCode(code)}
                  <br />
                </pre>

                <textarea
                  ref={textareaRef}
                  className="code-layer real-textarea"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  onClick={updateCursorPosition}
                  onKeyUp={updateCursorPosition}
                  onScroll={handleScroll}
                  onKeyDown={(e) => {
                    if (e.key === "Tab") {
                      e.preventDefault();
                      const ta = textareaRef.current;
                      const start = ta.selectionStart;
                      const end = ta.selectionEnd;
                      const newValue =
                        code.slice(0, start) + "\t" + code.slice(end);
                      setCode(newValue);
                      requestAnimationFrame(() => {
                        ta.selectionStart = ta.selectionEnd = start + 1;
                        updateCursorPosition();
                      });
                    }
                  }}
                  spellCheck={false}
                />
                <div className="cursor-status">
                  Ln {currentLine}, Col {currentColumn}
                </div>
              </div>
            </div>

            <div className="tokenize-btn-container">
              <button
                className="tokenize-btn"
                onClick={handleExecute}
                disabled={busy}
              >
                {busy ? "Compiling..." : "Compile"}
              </button>

              <button
                className="tokenize-btn"
                onClick={handleTokenizeParseAndAnalyzer}
                disabled={busy}
              >
                {busy ? "Processing..." : "Analyze"}
              </button>

              <button
                className="tokenize-btn"
                onClick={handleTokenizeAndParse}
                disabled={busy}
              >
                {busy ? "Processing..." : "Parse"}
              </button>

              <button
                className="tokenize-btn"
                onClick={handleTokenize}
                disabled={busy}
              >
                {busy ? "Tokenizing..." : "Tokenize"}
              </button>

              <button
                className="tokenize-btn"
                onClick={handleClearEditor}
                disabled={busy}
              >
                Clear
              </button>

              <button
                className="tokenize-btn tokenize-btn--toggle"
                onClick={() => setShowTokenTable(!showTokenTable)}
                disabled={busy}
              >
                {showTokenTable ? "Hide Lexeme Output" : "Show Lexeme Output"}
              </button>
            </div>
          </div>

          {showTokenTable && (
            <div className="tokens layout-panel-right">
              <h3 className="play-bold">Lexeme Output</h3>

              <div className="token-table-container">
                {showLineTokens ? (
                  <TokenTable tokens={lineTokens} />
                ) : hasRun ? (
                  <TokenTable tokens={tokens} />
                ) : (
                  <p>
                    Press "Tokenize (full)" or "Tokenize line" to see results.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="layout-panel-bottom">
          <ErrorTabs
            errors={errors}
            hasParsed={hasParsed}
            hasRun={hasRun}
            executionResult={executionResult}
            hasExecuted={hasExecuted}
            sourceCode={code}
            onSendInput={handleSendInput}
          />
        </div>
      </div>

      <Modal isOpen={showSaveModal} onClose={handleSaveModalCancel}>
        <h2 className="modal-title">Save Your Code File</h2>
        <div className="modal-body">
          <p style={{ marginBottom: "1.5rem", textIndent: 0 }}>
            Enter a filename for your Caramel code. The <code>.crml</code>{" "}
            extension will be added automatically!
          </p>
          <div className="save-modal-form">
            <input
              type="text"
              className="save-modal-input"
              value={saveFilename}
              onChange={(e) => setSaveFilename(e.target.value)}
              onKeyDown={handleSaveModalKeyDown}
              placeholder="Enter filename"
              autoFocus
            />
          </div>
        </div>
        <div className="modal-actions">
          <button
            className="modal-btn modal-btn--primary"
            onClick={handleSaveModalConfirm}
          >
            <i className="fa-solid fa-save"></i> Save File
          </button>
          <button
            className="modal-btn modal-btn--secondary"
            onClick={handleSaveModalCancel}
          >
            <i className="fa-solid fa-xmark"></i> Cancel
          </button>
        </div>
      </Modal>
    </div>
  );
}

function TokenTable({ tokens }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Lexeme</th>
          <th>Tokens</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((t, i) => (
          <tr key={i}>
            <td>{t.lexeme}</td>
            <td>{t.type}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
