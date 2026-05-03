import React, { useEffect, useState, useRef } from "react";
import "./OutputPanel.css";

export default function OutputPanel({
  executionResult,
  hasExecuted,
  onSendInput,
}) {
  const [isCopied, setIsCopied] = useState(false);
  const [showCode, setShowCode] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const outputRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setIsCopied(false);
  }, [executionResult]);

  // Auto-scroll output to bottom when new content appears
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [executionResult?.output]);

  // Auto-focus input when waiting for input
  useEffect(() => {
    if (executionResult?.status === "waiting_for_input" && inputRef.current) {
      inputRef.current.focus();
    }
  }, [executionResult?.status]);

  const handleCopyOutput = () => {
    if (!navigator.clipboard || !executionResult) return;
    const text = executionResult.output || "(no output)";
    navigator.clipboard
      .writeText(text)
      .then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      })
      .catch((err) => console.error("Copy failed:", err));
  };

  const handleSubmitInput = () => {
    if (onSendInput) {
      onSendInput(inputValue);
    }
    setInputValue("");
  };

  const handleInputKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmitInput();
    }
  };

  if (!hasExecuted) {
    return null;
  }

  // ---------------------------------------------------------------------------
  // Extract loop detection errors from the errors array.
  // These come from the pipeline validator's static loop detector and are
  // placed on executionResult.errors by App.jsx.  They are NOT parser/syntax
  // errors — they belong here in the Output tab.
  // ---------------------------------------------------------------------------
  const loopDetectionErrors =
    executionResult?.errors?.filter(
      (e) =>
        e.type === "INFINITE_LOOP_ERROR" ||
        e.type === "LOOP_TIMEOUT" ||
        e.type === "EXECUTION_TIMEOUT"
    ) || [];

  // Non-loop compilation errors (parser / semantic / generic) — these show
  // the "Compilation Failed" banner.
  const compilerErrors =
    executionResult?.errors?.filter(
      (e) =>
        e.type !== "INFINITE_LOOP_ERROR" &&
        e.type !== "LOOP_TIMEOUT" &&
        e.type !== "EXECUTION_TIMEOUT"
    ) || [];

  const hasLoopDetectionErrors = loopDetectionErrors.length > 0;

  // ---------------------------------------------------------------------------
  // If there were ONLY non-loop compilation errors → show the old
  // "Compilation Failed" banner.
  // ---------------------------------------------------------------------------
  if (compilerErrors.length > 0 && !hasLoopDetectionErrors) {
    return (
      <div className="output-panel" role="alert">
        <div className="output-panel__header">
          <div className="output-panel__header-left">
            <span className="output-panel__icon">&#x26A0;&#xFE0F;</span>
            <div>
              <div className="output-panel__title">Compilation Failed</div>
              <div className="output-panel__summary">
                Fix errors before executing
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // If the pipeline was blocked by the loop detector (static analysis),
  // show an amber warning card — not the normal execution output.
  // ---------------------------------------------------------------------------
  if (hasLoopDetectionErrors) {
    return (
      <div className="output-panel" role="alert" aria-live="polite">
        <div className="output-panel__header">
          <div className="output-panel__header-left">
            <i className="fa-solid fa-infinity output-panel__icon--loop"></i>
            <div>
              <div className="output-panel__title">
                Infinite Loop Warning
              </div>
              <div className="output-panel__summary">
                Possible non-terminating execution detected during code
                generation. Process automatically stopped to prevent freezing.
              </div>
            </div>
          </div>
        </div>

        {/* Render each loop error as an amber card */}
        <div className="output-panel__loop-errors">
          {loopDetectionErrors.map((e, i) => (
            <div key={`loop-${i}`} className="output-panel__error output-panel__error--loop">
              <div className="output-panel__error-header">
                <i className="fa-solid fa-infinity" style={{ marginRight: "0.5rem" }} />
                <strong>Infinite Loop Detected</strong>
              </div>
              <div className="output-panel__error-body">
                {e.message}
              </div>
              {e.line && (
                <div className="output-panel__error-location">
                  <i className="fa-solid fa-location-dot" style={{ marginRight: "0.4rem" }} />
                  Near line {e.line}
                </div>
              )}
              <div className="output-panel__error-hint">
                <i className="fa-solid fa-lightbulb" style={{ marginRight: "0.4rem" }} />
                Tip: Check your loop conditions and ensure loop variables are modified. Use{" "}
                <code>snap</code> (break) to exit loops when needed.
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Normal execution output (running / completed / waiting / error)
  // ---------------------------------------------------------------------------
  const output = executionResult?.output || "";
  const runtimeError = executionResult?.runtime_error;
  const generatedCode = executionResult?.generated_code || "";
  const status = executionResult?.status || "completed";
  const isWaiting = status === "waiting_for_input";
  const isRunning = status === "running" || status === "compiling";
  const isCompleted = status === "completed";
  const isErrored = status === "error";

  // Detect runtime infinite loop / timeout errors (from the iteration counter
  // or the 30-second watchdog timer) for specialised display.
  const isLoopTimeout =
    runtimeError &&
    (runtimeError.includes("Infinite loop") ||
      runtimeError.includes("infinite loop") ||
      runtimeError.includes("timed out") ||
      runtimeError.includes("CARAMEL_MAX_ITERATIONS"));

  const isExecutionTimeout =
    runtimeError &&
    (runtimeError.includes("Execution timed out") ||
      runtimeError.includes("possible infinite loop"));

  const isAnyLoopError = isLoopTimeout || isExecutionTimeout;

  return (
    <div className="output-panel" role="status" aria-live="polite">
      <div className="output-panel__header">
        <div className="output-panel__header-left">
          {isCompleted || isErrored ? (
            runtimeError ? (
              isAnyLoopError ? (
                <i className="fa-solid fa-infinity output-panel__icon--loop"></i>
              ) : (
                <i className="fa-solid fa-circle-xmark output-panel__icon--error"></i>
              )
            ) : (
              <i className="fa-solid fa-circle-check output-panel__icon--success"></i>
            )
          ) : isWaiting ? (
            <i className="fa-solid fa-keyboard output-panel__icon--waiting"></i>
          ) : (
            <i className="fa-solid fa-spinner fa-spin output-panel__icon--running"></i>
          )}
          <div>
            <div className="output-panel__title">
              {isCompleted || isErrored
                ? runtimeError
                  ? isAnyLoopError
                    ? "Infinite Loop / Timeout Detected"
                    : "Runtime Error"
                  : "Program Output"
                : isWaiting
                  ? "Input Required"
                  : "Executing..."}
            </div>
            <div className="output-panel__summary">
              {isCompleted || isErrored
                ? runtimeError
                  ? isAnyLoopError
                    ? "Program stopped — possible infinite loop"
                    : "Execution stopped due to a runtime error"
                  : output
                    ? "Program finished successfully"
                    : "Execution finished (no output)"
                : isWaiting
                  ? "The program is waiting for your input"
                  : "Compiling and running your code..."}
            </div>
          </div>
        </div>

        <div className="output-panel__actions">
          {generatedCode && isCompleted && (
            <button
              className="output-panel__toggle"
              onClick={() => setShowCode(!showCode)}
            >
              <i className={`fa-solid ${showCode ? "fa-eye-slash" : "fa-eye"}`}></i>
              {showCode ? "Hide Code" : "Show Code"}
            </button>
          )}
          {isCompleted && (
            <button
              className="output-panel__copy"
              onClick={handleCopyOutput}
              disabled={isCopied || !output}
              aria-label="Copy output"
            >
              <i className={`fa-solid ${isCopied ? "fa-check" : "fa-copy"}`}></i>
              {isCopied ? "Copied!" : "Copy"}
            </button>
          )}
        </div>
      </div>

      {/* Program Output */}
      <div
        ref={outputRef}
        className={`output-panel__output ${!output && !runtimeError && isCompleted ? "output-panel__output--empty" : ""}`}
      >
        {output || (isCompleted ? "(no output)" : "")}
        {isRunning && !output && (
          <span className="output-panel__cursor">_</span>
        )}
      </div>

      {/* Input Row */}
      {isWaiting && (
        <div className="output-panel__input-row">
          <span className="output-panel__input-prompt">&gt;</span>
          <input
            ref={inputRef}
            type="text"
            className="output-panel__input-field"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleInputKeyDown}
            placeholder="Type input and press Enter..."
            autoFocus
          />
          <button
            className="output-panel__input-submit"
            onClick={handleSubmitInput}
          >
            Send
          </button>
        </div>
      )}

      {/* Runtime Error — generic or loop/timeout */}
      {runtimeError && (
        <div
          className={`output-panel__error ${
            isAnyLoopError ? "output-panel__error--loop" : ""
          }`}
        >
          {isAnyLoopError && (
            <div className="output-panel__error-header">
              <i className="fa-solid fa-infinity" style={{ marginRight: "0.5rem" }} />
              <strong>Infinite Loop / Timeout</strong>
            </div>
          )}
          {runtimeError}
          {isAnyLoopError && (
            <div className="output-panel__error-hint">
              <i className="fa-solid fa-lightbulb" style={{ marginRight: "0.4rem" }} />
              Tip: Check your loop conditions and ensure loop variables are modified. Use{" "}
              <code>snap</code> (break) to exit loops when needed.
            </div>
          )}
        </div>
      )}

      {/* Generated Code (collapsible) */}
      {showCode && generatedCode && (
        <div className="output-panel__code-section">
          <div className="output-panel__code-header">
            <span className="output-panel__code-title">
              Generated Python Code
            </span>
            <button
              className="output-panel__toggle"
              onClick={() => setShowCode(false)}
            >
              Hide
            </button>
          </div>
          <pre className="output-panel__code">{generatedCode}</pre>
        </div>
      )}
    </div>
  );
}
