import { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./styles.css";
import "./App.css";
import NavBar from "./components/NavBar";
import "./components/NavBar.css";
import ErrorTabs from "./components/ErrorTabs";
import Modal from "./components/Modal";

import CaramelEditor from "./components/CaramelEditor";

// === Input Sanitization Helper ===
const sanitizeQuotes = (text) =>
  text
    .replace(/[\u201C\u201D]/g, '"')
    .replace(/[\u2018\u2019]/g, "'");


// highlightCode removed. Syntax highlighting is now handled by Monaco Editor.

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
  const [showTokenTable, setShowTokenTable] = useState(false);

  // Save Modal State
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveFilename, setSaveFilename] = useState("code");

  // Refs
  const fileInputRef = useRef(null);
  const executionSessionRef = useRef(null);
  const pollTimerRef = useRef(null);
  const [currentLine, setCurrentLine] = useState(1);
  const [currentColumn, setCurrentColumn] = useState(1);

  const [draftRestored, setDraftRestored] = useState(false);
  const [showDraftBanner, setShowDraftBanner] = useState(false);
  const autosaveTimerRef = useRef(null);
  const DRAFT_KEY = 'caramel_draft';
  const DRAFT_TIME_KEY = 'caramel_draft_time';
  const DEFAULT_CODE = `bean cup() [\n  bean x = 5, y = 7\n  drip val = 4.5\n  refill? 0\n]`;
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved' | 'unsaved' | 'saving'

  const codeRef = useRef(code);
  useEffect(() => { codeRef.current = code; }, [code]);

  useEffect(() => {
    autosaveTimerRef.current = setInterval(() => {
      if (codeRef.current && codeRef.current.trim()) {
        localStorage.setItem(DRAFT_KEY, codeRef.current);
        localStorage.setItem(DRAFT_TIME_KEY, Date.now().toString());
      }
    }, 30000);
    return () => clearInterval(autosaveTimerRef.current);
  }, []);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

    // On mount: check for saved draft
  useEffect(() => {
    const draft = localStorage.getItem(DRAFT_KEY);
    const draftTime = localStorage.getItem(DRAFT_TIME_KEY);
    if (draft && draft !== DEFAULT_CODE) {
      const time = draftTime ? new Date(parseInt(draftTime)).toLocaleTimeString() : 'unknown time';
      setShowDraftBanner(time);
    }
  }, []);

  // Autosave every 30 seconds
  useEffect(() => {
    autosaveTimerRef.current = setInterval(() => {
      if (codeRef.current && codeRef.current.trim()) {
        setSaveStatus('saving');
        localStorage.setItem(DRAFT_KEY, codeRef.current);
        localStorage.setItem(DRAFT_TIME_KEY, Date.now().toString());
        setTimeout(() => setSaveStatus('saved'), 800);
      }
    }, 30000);
  }, [code]);

  useEffect(() => {
    codeRef.current = code;
    setSaveStatus('unsaved');
  }, [code]);

  // === Handlers ===

  const handleSaveFile = () => {
    setShowSaveModal(true);
  };

  const handleRestoreDraft = () => {
    const draft = localStorage.getItem(DRAFT_KEY);
    if (draft) setCode(draft);
    setShowDraftBanner(false);
  };

  const handleDismissDraft = () => {
    setShowDraftBanner(false);
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
    localStorage.removeItem(DRAFT_KEY);
    localStorage.removeItem(DRAFT_TIME_KEY);
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
        // ADD SANITIZATION HERE
        const cleaned = content
          .replace(/^\uFEFF/, '')          
          .replace(/[\u2018\u2019]/g, "'")
          .replace(/[\u201C\u201D]/g, '"')  
          .replace(/\u00A0/g, ' ')        
          .replace(/\r\n/g, '\n')          
          .replace(/\r/g, '\n');            
        
        setCode(cleaned); 
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
    reader.readAsText(file, 'UTF-8'); 
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
    localStorage.removeItem(DRAFT_KEY);
    localStorage.removeItem(DRAFT_TIME_KEY);
  };

  // Cursor tracking is now handled directly by Monaco Editor.

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
        {showDraftBanner && (
          <div className="draft-banner">
            <span>📄 Unsaved draft found from {showDraftBanner}.</span>
            <button className="draft-btn draft-btn--restore" onClick={handleRestoreDraft}>Restore</button>
            <button className="draft-btn draft-btn--dismiss" onClick={handleDismissDraft}>Dismiss</button>
          </div>
        )}
      <div className="main-content">
        <div
          className={`layout-row-top ${
            showTokenTable ? "" : "layout-row-top--expanded"
          }`}
        >
          <div className="editor layout-flex" style={{ paddingTop: '0', background: 'transparent', border: 'none', boxShadow: 'none' }}>
                        
            <div className="editor-tabs-container">
              <div className="editor-tab-title">
                <span className="play-bold">Code Editor</span>
              </div>
              <div className="editor-tab-actions">
                <button className="tokenize-btn" onClick={handleExecute} disabled={busy}>{busy ? "Compiling..." : "Compile"}</button>
                <button className="tokenize-btn" onClick={handleTokenizeParseAndAnalyzer} disabled={busy}>{busy ? "Processing..." : "Analyze"}</button>
                <button className="tokenize-btn" onClick={handleTokenizeAndParse} disabled={busy}>{busy ? "Processing..." : "Parse"}</button>
                <button className="tokenize-btn" onClick={handleTokenize} disabled={busy}>{busy ? "Tokenizing..." : "Tokenize"}</button>
                <button className="tokenize-btn" onClick={handleClearEditor} disabled={busy}>Clear</button>
                <span className={`save-status save-status--${saveStatus}`}>
                  {saveStatus === 'saving' && <><i className="fa-solid fa-spinner fa-spin" /> Saving...</>}
                  {saveStatus === 'saved' && <><i className="fa-solid fa-cloud-check" /> Saved</>}
                  {saveStatus === 'unsaved' && <><i className="fa-solid fa-circle-dot" /> Unsaved</>}
                </span>
                <button className="tokenize-btn tokenize-btn--toggle" onClick={() => setShowTokenTable(!showTokenTable)} disabled={busy}>{showTokenTable ? "Hide Lexeme Output" : "Show Lexeme Output"}</button>
              </div>
            </div>

            <div className="editor-container" style={{ marginTop: 0, borderTopLeftRadius: 0, position: 'relative' }}>
              <CaramelEditor 
                code={code}
                setCode={setCode}
                onChangeCursor={(line, col) => {
                  setCurrentLine(line);
                  setCurrentColumn(col);
                }}
              />
              <div className="cursor-status" style={{ zIndex: 10 }}>
                Ln {currentLine}, Col {currentColumn}
              </div>
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
