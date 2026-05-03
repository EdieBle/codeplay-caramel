import { useState, useRef, useEffect, useCallback } from "react";
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

  // EXE Build state
  const [buildingExe, setBuildingExe] = useState(false);
  // exeToast: null | { type: 'success'|'error', message: string }
  const [exeToast, setExeToast] = useState(null);

  // Save Modal State
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveFilename, setSaveFilename] = useState("code");
  const [openedFilename, setOpenedFilename] = useState("main.crml");

  // Refs
  const fileInputRef = useRef(null);
  const executionSessionRef = useRef(null);
  const pollTimerRef = useRef(null);
  const [currentLine, setCurrentLine] = useState(1);

  // Resizable panel state
  const [panelSplit, setPanelSplit] = useState(65); // top panel takes 65% by default
  const [isBottomExpanded, setIsBottomExpanded] = useState(false);
  const isDraggingRef = useRef(false);
  const mainContentRef = useRef(null);
  const [currentColumn, setCurrentColumn] = useState(1);
  const [sidePanelSplit, setSidePanelSplit] = useState(70); // Editor takes 70% by default
  const isDraggingSideRef = useRef(false);
  const ideBodyRef = useRef(null);

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
        setOpenedFilename(file.name);
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
            // Only push non-loop errors to the shared errors array.
            // Loop detection errors stay on executionResult.errors so they
            // render exclusively in the Output tab, not the Syntax panel.
            const nonLoopErrors = data.errors.filter(
              (e) =>
                e.type !== "INFINITE_LOOP_ERROR" &&
                e.type !== "LOOP_TIMEOUT" &&
                e.type !== "EXECUTION_TIMEOUT"
            );
            if (nonLoopErrors.length > 0) {
              setErrors(nonLoopErrors);
            }
          }

          // Stop polling when the session has finished or errored out
          if (data.status === "completed" || data.status === "error") {
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
    setOpenedFilename("main.crml");
    localStorage.removeItem(DRAFT_KEY);
    localStorage.removeItem(DRAFT_TIME_KEY);
  };

  // === Build EXE Handler ===
  const handleBuildExe = async () => {
    // Guard: do not build while another operation is running
    if (busy || buildingExe) return;

    // Guard: require non-empty code
    if (!code || !code.trim()) {
      setExeToast({ type: "error", message: "Cannot build EXE: the editor is empty." });
      setTimeout(() => setExeToast(null), 5000);
      return;
    }

    setBuildingExe(true);
    setExeToast({ type: "building", message: "Building executable — this may take 20-30 seconds…" });

    try {
      // Derive a safe filename from the currently opened .crml file
      const baseName = openedFilename.replace(/\.crml$/i, "") || "caramel_program";

      // POST to the backend build-exe endpoint.
      // We ask for a binary (blob) response so we can trigger a browser download.
      const response = await fetch("http://127.0.0.1:5000/build-exe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, filename: baseName }),
      });

      if (!response.ok) {
        // The server returned an error; parse the JSON body for a user-facing message
        let errMsg = `Build failed (HTTP ${response.status}).`;
        try {
          const errData = await response.json();
          errMsg = errData.message || errMsg;
          // If compilation errors were returned, check whether they are
          // loop detection errors.  Loop errors should appear in the
          // Output tab (via executionResult), NOT in the Syntax panel.
          if (errData.errors && errData.errors.length > 0) {
            const loopErrors = errData.errors.filter(
              (e) =>
                e.type === "INFINITE_LOOP_ERROR" ||
                e.type === "LOOP_TIMEOUT" ||
                e.type === "EXECUTION_TIMEOUT"
            );
            const otherErrors = errData.errors.filter(
              (e) =>
                e.type !== "INFINITE_LOOP_ERROR" &&
                e.type !== "LOOP_TIMEOUT" &&
                e.type !== "EXECUTION_TIMEOUT"
            );

            // Regular errors → shared errors state (Syntax/Semantic tabs)
            if (otherErrors.length > 0) {
              setErrors(otherErrors);
            }

            // Loop errors → executionResult so they show in the Output tab
            if (loopErrors.length > 0) {
              setExecutionResult({
                output: "",
                generated_code: "",
                runtime_error: null,
                errors: loopErrors,
                status: "completed",
                input_prompt: "",
              });
              setHasExecuted(true);
            }
          }
        } catch (_) { /* ignore JSON parse failures */ }
        setExeToast({ type: "error", message: errMsg });
        setTimeout(() => setExeToast(null), 8000);
        return;
      }

      // Build succeeded — download the binary blob
      const blob = await response.blob();
      const url  = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href     = url;
      link.download = `${baseName}.exe`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExeToast({ type: "success", message: `✓ ${baseName}.exe downloaded successfully!` });
      setTimeout(() => setExeToast(null), 6000);

    } catch (err) {
      // Network or unexpected JS error
      const msg = err?.message?.includes("Failed to fetch")
        ? "Cannot reach the backend. Is the Flask server running?"
        : `Unexpected error: ${err?.message || err}`;
      setExeToast({ type: "error", message: msg });
      setTimeout(() => setExeToast(null), 8000);
    } finally {
      setBuildingExe(false);
    }
  };

  // Cursor tracking is now handled directly by Monaco Editor.

  // === Resize Handle Drag Logic ===
  const handleResizeMouseDown = useCallback((e) => {
    e.preventDefault();
    isDraggingRef.current = true;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const handleSideResizeMouseDown = useCallback((e) => {
    e.preventDefault();
    isDraggingSideRef.current = true;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  useEffect(() => {
    const handleMouseMove = (e) => {
      // Bottom Panel Resize
      if (isDraggingRef.current && mainContentRef.current) {
        const rect = mainContentRef.current.getBoundingClientRect();
        const offsetY = e.clientY - rect.top;
        const totalHeight = rect.height;
        let newSplit = (offsetY / totalHeight) * 100;
        newSplit = Math.max(15, Math.min(90, newSplit));
        setPanelSplit(newSplit);
      }

      // Side Panel Resize
      if (isDraggingSideRef.current && ideBodyRef.current) {
        const rect = ideBodyRef.current.getBoundingClientRect();
        const offsetX = e.clientX - rect.left;
        const totalWidth = rect.width;
        let newSplit = (offsetX / totalWidth) * 100;
        // Clamp between 20% and 80%
        newSplit = Math.max(20, Math.min(80, newSplit));
        setSidePanelSplit(newSplit);
      }
    };

    const handleMouseUp = () => {
      if (isDraggingRef.current || isDraggingSideRef.current) {
        isDraggingRef.current = false;
        isDraggingSideRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  return (
    <div className="app-root">
      {/* === EXE Build Toast Notification === */}
      {exeToast && (
        <div className={`exe-toast exe-toast--${exeToast.type}`} role="status" aria-live="polite">
          <span className="exe-toast__icon">
            {exeToast.type === "building" && <i className="fa-solid fa-spinner fa-spin" />}
            {exeToast.type === "success"  && <i className="fa-solid fa-circle-check" />}
            {exeToast.type === "error"    && <i className="fa-solid fa-circle-xmark" />}
          </span>
          <span className="exe-toast__msg">{exeToast.message}</span>
          <button
            className="exe-toast__close"
            onClick={() => setExeToast(null)}
            aria-label="Dismiss notification"
          >
            <i className="fa-solid fa-xmark" />
          </button>
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept=".crml"
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />
      <NavBar onSaveFile={handleSaveFile} onOpenFile={handleOpenFile} />
      <div className="main-content" ref={mainContentRef}>
        {showDraftBanner && (
          <div className="draft-banner">
            <span className="draft-msg">
              <i className="fa-solid fa-file-pen"></i>
              <span>Unsaved draft found from {showDraftBanner}</span>
            </span>
            <div className="draft-actions">
              <button className="draft-btn draft-btn--restore" onClick={handleRestoreDraft}>Restore</button>
              <button className="draft-btn draft-btn--dismiss" onClick={handleDismissDraft}>Dismiss</button>
            </div>
          </div>
        )}

        <div className="workspace-container">
          {/* === TOP PANEL: VS Code-style IDE Box === */}
          {!isBottomExpanded && (
            <div
              className="ide-box"
              style={{ height: `${panelSplit}%`, minHeight: 0 }}
            >
              {/* === ACTIVITY BAR === */}
              <div className="activity-bar">
                <button
                  className={`activity-btn ${showTokenTable ? "activity-btn--active" : ""}`}
                  onClick={() => setShowTokenTable(!showTokenTable)}
                  title={showTokenTable ? "Hide Lexeme Output" : "Show Lexeme Output"}
                >
                  <i className="fa-solid fa-table-list"></i>
                </button>
                <button
                  className="activity-btn"
                  onClick={handleExecute}
                  disabled={busy || buildingExe}
                  title="Compile and Run"
                >
                  <i className={`fa-solid ${busy ? "fa-spinner fa-spin" : "fa-play"}`}></i>
                </button>
                {/* Build EXE button */}
                <button
                  id="btn-build-exe"
                  className={`activity-btn activity-btn--exe ${buildingExe ? "activity-btn--building" : ""}`}
                  onClick={handleBuildExe}
                  disabled={busy || buildingExe}
                  title={buildingExe ? "Building EXE…" : "Build Executable (.exe)"}
                  aria-label="Build Executable"
                >
                  <i className={`fa-solid ${buildingExe ? "fa-spinner fa-spin" : "fa-hammer"}`}></i>
                </button>
              </div>

              {/* === MAIN IDE AREA === */}
              <div className="ide-main">
                {/* Unified Header */}
                <div className="ide-header">
                  <div className="ide-header-tab">
                    <i className="fa-solid fa-code" style={{ color: "var(--color-primary)", fontSize: "1rem" }}></i>
                    <span>{openedFilename}</span>
                    <span className={`save-status save-status--${saveStatus}`} style={{ marginLeft: "0.5rem" }}>
                      {saveStatus === "saving" && <i className="fa-solid fa-spinner fa-spin" />}
                      {saveStatus === "saved" && <i className="fa-solid fa-check-circle" />}
                      {saveStatus === "unsaved" && <i className="fa-solid fa-circle-dot" />}
                    </span>
                  </div>

                  <div className="ide-header-actions">
                    <button className="tokenize-btn" onClick={handleTokenizeParseAndAnalyzer} disabled={busy}>Analyze</button>
                    <button className="tokenize-btn" onClick={handleTokenizeAndParse} disabled={busy}>Parse</button>
                    <button className="tokenize-btn" onClick={handleTokenize} disabled={busy}>Tokenize</button>
                    <button className="tokenize-btn" onClick={handleClearEditor} disabled={busy}>Clear</button>
                  </div>
                </div>

                {/* IDE Body */}
                <div className="ide-body" ref={ideBodyRef}>
                  <div className="ide-section editor" style={{ width: showTokenTable ? `${sidePanelSplit}%` : "100%", flex: "none" }}>
                    <div className="editor-container" style={{ position: "relative" }}>
                      <CaramelEditor
                        code={code}
                        setCode={setCode}
                        onChangeCursor={(line, col) => {
                          setCurrentLine(line);
                          setCurrentColumn(col);
                        }}
                      />
                    </div>
                  </div>

                  {showTokenTable && (
                    <>
                      <div className="resize-handle--vertical" onMouseDown={handleSideResizeMouseDown} title="Drag to resize panels">
                        <div className="resize-handle--vertical__grip">
                          <i className="fa-solid fa-grip-vertical"></i>
                        </div>
                      </div>
                      <div className="ide-section ide-section--tokens" style={{ width: `${100 - sidePanelSplit}%`, flex: "none" }}>
                        <div className="ide-section-title">
                          <i className="fa-solid fa-table-list"></i>
                          Lexeme Output
                        </div>
                        <div className="tokens-container">
                          <div className="token-table-container">
                            {showLineTokens ? (
                              <TokenTable tokens={lineTokens} />
                            ) : hasRun ? (
                              <TokenTable tokens={tokens} />
                            ) : (
                              <p style={{ padding: "1rem", color: "var(--color-text-muted-light)", fontSize: "0.85rem" }}>
                                Press "Tokenize" or "Compile" to see results.
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* VS Code Style Status Bar - Moved outside ide-box to prevent clipping */}
          {!isBottomExpanded && (
            <div className="ide-status-bar">
              <div className="ide-status-left">
                <span className="ide-status-item">
                  <i className="fa-solid fa-code-branch"></i> main*
                </span>
              </div>
              <div className="ide-status-right">
                <span className="ide-status-item">
                  Ln {currentLine}, Col {currentColumn}
                </span>
                <span className="ide-status-item">Spaces: 2</span>
                <span className="ide-status-item">UTF-8</span>
                <span className="ide-status-item">Caramel</span>
              </div>
            </div>
          )}

          {/* === RESIZE HANDLE === */}
          {!isBottomExpanded && (
          <div
            className="resize-handle"
            onMouseDown={handleResizeMouseDown}
            title="Drag to resize panels"
          >
            <div className="resize-handle__grip">
              <i className="fa-solid fa-grip-lines"></i>
            </div>
          </div>
        )}

        {/* === BOTTOM PANEL: Errors + Output === */}
        <div
          className={`layout-panel-bottom ${isBottomExpanded ? 'layout-panel-bottom--expanded' : ''}`}
          style={isBottomExpanded ? { height: '100%' } : { height: `${100 - panelSplit}%`, minHeight: 0 }}
        >
          <ErrorTabs
            errors={errors}
            hasParsed={hasParsed}
            hasRun={hasRun}
            executionResult={executionResult}
            hasExecuted={hasExecuted}
            sourceCode={code}
            onSendInput={handleSendInput}
            isExpanded={isBottomExpanded}
            onToggleExpand={() => setIsBottomExpanded(!isBottomExpanded)}
          />
        </div>
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
          <th>Line</th>
          <th>Col</th>
          <th>Lexeme</th>
          <th>Tokens</th>
        </tr>
      </thead>
      <tbody>
        {tokens.map((t, i) => (
          <tr key={i}>
            <td>{t.line}</td>
            <td>{t.column}</td>
            <td>{t.lexeme}</td>
            <td>{t.type}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
