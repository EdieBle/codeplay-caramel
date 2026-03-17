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

  // Execution had compiler errors (pre-execution)
  if (
    executionResult &&
    executionResult.errors &&
    executionResult.errors.length > 0
  ) {
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

  const output = executionResult?.output || "";
  const runtimeError = executionResult?.runtime_error;
  const generatedCode = executionResult?.generated_code || "";
  const status = executionResult?.status || "completed";
  const isWaiting = status === "waiting_for_input";
  const isRunning = status === "running" || status === "compiling";
  const isCompleted = status === "completed";

  return (
    <div className="output-panel" role="status" aria-live="polite">
      <div className="output-panel__header">
        <div className="output-panel__header-left">
          <span className="output-panel__icon">
            {isCompleted
              ? runtimeError
                ? "\u274C"
                : "\u2705"
              : isWaiting
                ? "\u270F\uFE0F"
                : "\u23F3"}
          </span>
          <div>
            <div className="output-panel__title">
              {isCompleted
                ? runtimeError
                  ? "Runtime Error"
                  : "Program Output"
                : isWaiting
                  ? "Waiting for Input"
                  : "Running..."}
            </div>
            <div className="output-panel__summary">
              {isCompleted
                ? runtimeError
                  ? "Program encountered an error during execution"
                  : output
                    ? "Execution completed successfully"
                    : "Program ran with no output"
                : isWaiting
                  ? "Type your input below and press Enter"
                  : "Program is executing..."}
            </div>
          </div>
        </div>

        <div className="output-panel__actions">
          {generatedCode && isCompleted && (
            <button
              className="output-panel__toggle"
              onClick={() => setShowCode(!showCode)}
            >
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

      {/* Runtime Error */}
      {runtimeError && (
        <div className="output-panel__error">{runtimeError}</div>
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
