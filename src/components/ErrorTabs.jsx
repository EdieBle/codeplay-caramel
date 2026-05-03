import React, { useState, useEffect } from "react";
import "./ErrorTabs.css";
import LexerError from "./LexerError";
import SyntaxErrorPanel from "./SyntaxErrorPanel";
import SemanticErrorPanel from "./SemanticErrorPanel";
import OutputPanel from "./OutputPanel";

export default function ErrorTabs({
  errors,
  hasParsed,
  hasRun,
  sourceCode,
  isParseStale,
  executionResult,
  hasExecuted,
  onSendInput,
  isExpanded,
  onToggleExpand,
}) {
  const [activeTab, setActiveTab] = useState("lexer");

  // When execution completes, auto-switch to output tab
  useEffect(() => {
    if (hasExecuted && executionResult) {
      setActiveTab("output");
    }
  }, [hasExecuted, executionResult]);

  // Reset to lexer tab when errors change (but not on execution)
  useEffect(() => {
    if (!hasExecuted) {
      setActiveTab("lexer");
    }
  }, [errors]);

  // Count errors by type — only parsing/analysis stage errors
  const lexerErrorCount = errors
    ? errors.filter((e) => e.type === "ERROR" || e.type === "LEXICAL_ERROR")
        .length
    : 0;

  const syntaxErrorCount = errors
    ? errors.filter((e) => e.type === "SYNTAX_ERROR").length
    : 0;

  const semanticErrorCount = errors
    ? errors.filter((e) => e.type === "SEMANTIC_ERROR" || e.type === "SEMANTIC")
        .length
    : 0;

  // Detect whether the Output tab has a loop/timeout issue to show a warning badge.
  // This is derived from executionResult (not from the errors array), because infinite
  // loop errors belong to the code-generation/runtime stage — not to parsing.
  const hasLoopWarning =
    hasExecuted &&
    executionResult &&
    (executionResult.status === "error" ||
      (executionResult.runtime_error &&
        (executionResult.runtime_error.includes("Infinite loop") ||
          executionResult.runtime_error.includes("timed out") ||
          executionResult.runtime_error.includes("infinite loop"))) ||
      // Static loop detection errors placed on executionResult.errors by App.jsx
      (executionResult.errors &&
        executionResult.errors.some(
          (e) =>
            e.type === "INFINITE_LOOP_ERROR" ||
            e.type === "LOOP_TIMEOUT" ||
            e.type === "EXECUTION_TIMEOUT"
        )));

  return (
    <div className="error-section-wrapper">
      {/* Tab Navigation matching Editor/Tokens style */}
      <div className="editor-tabs-container">
        <button
          className={`editor-tab-title ${activeTab === "lexer" ? "active" : ""} ${lexerErrorCount > 0 ? "tab--has-errors" : ""}`}
          onClick={() => setActiveTab("lexer")}
        >
          <i className="fa-solid fa-wand-magic-sparkles"></i>
          <span className="error-tab-label">Lexer</span>
          {lexerErrorCount > 0 && (
            <span className="error-tab-badge">{lexerErrorCount}</span>
          )}
        </button>

        {/* Syntax tab — only real SYNTAX_ERROR counts, no loop errors */}
        <button
          className={`editor-tab-title ${activeTab === "parser" ? "active" : ""} ${syntaxErrorCount > 0 ? "tab--has-errors" : ""}`}
          onClick={() => setActiveTab("parser")}
        >
          <i className="fa-solid fa-code"></i>
          <span className="error-tab-label">Syntax</span>
          {syntaxErrorCount > 0 && (
            <span className="error-tab-badge">{syntaxErrorCount}</span>
          )}
        </button>

        <button
          className={`editor-tab-title ${activeTab === "semantic" ? "active" : ""} ${semanticErrorCount > 0 ? "tab--has-errors" : ""}`}
          onClick={() => setActiveTab("semantic")}
        >
          <i className="fa-solid fa-brain"></i>
          <span className="error-tab-label">Semantic</span>
          {semanticErrorCount > 0 && (
            <span className="error-tab-badge">{semanticErrorCount}</span>
          )}
        </button>

        {/* Output tab — loop/timeout warnings appear here only */}
        <button
          className={`editor-tab-title ${activeTab === "output" ? "active" : ""}`}
          onClick={() => setActiveTab("output")}
        >
          <i className="fa-solid fa-terminal"></i>
          <span className="error-tab-label">Output</span>
          {hasExecuted && executionResult && !executionResult.runtime_error &&
            !hasLoopWarning &&
            executionResult.output && executionResult.status === "completed" && (
            <i className="fa-solid fa-circle-check tab-icon--success"></i>
          )}
          {hasExecuted && executionResult && executionResult.runtime_error &&
            !hasLoopWarning && (
            <i className="fa-solid fa-circle-exclamation tab-icon--error"></i>
          )}
          {/* Infinite loop / timeout indicator on the Output tab */}
          {hasLoopWarning && (
            <i
              className="fa-solid fa-infinity"
              title="Infinite loop / timeout — check Output tab"
              style={{ color: "#f59e0b", marginLeft: "0.25rem", fontSize: "0.85rem" }}
            />
          )}
        </button>

        {/* Expand / Collapse toggle */}
        <button
          className="editor-tab-title expand-toggle-btn"
          onClick={onToggleExpand}
          title={isExpanded ? "Collapse panel" : "Expand panel"}
        >
          <i className={`fa-solid ${isExpanded ? 'fa-compress' : 'fa-expand'}`}></i>
        </button>
      </div>

      {/* Tab Content matching container style */}
      <div className={`error-content-box ${isExpanded ? 'error-content-box--expanded' : ''}`}>
        <div className="error-tabs-content">
          {activeTab === "lexer" && (
            <div className="error-tab-pane">
              <LexerError errors={errors} hasRun={hasRun} />
            </div>
          )}

          {activeTab === "parser" && (
            <div className="error-tab-pane">
              <SyntaxErrorPanel
                errors={errors}
                hasParsed={hasParsed}
                sourceCode={sourceCode}
                isStale={isParseStale}
              />
            </div>
          )}

          {activeTab === "semantic" && (
            <div className="error-tab-pane">
              <SemanticErrorPanel errors={errors} hasParsed={hasParsed} />
            </div>
          )}

          {activeTab === "output" && (
            <div className="error-tab-pane">
              <OutputPanel
                executionResult={executionResult}
                hasExecuted={hasExecuted}
                onSendInput={onSendInput}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
