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

  // Count errors by type
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

  return (
    <div className="error-tabs-container">
      {/* Tab Navigation */}
      <div className="error-tabs-nav">
        <button
          className={`error-tab-btn ${activeTab === "lexer" ? "active" : ""}`}
          onClick={() => setActiveTab("lexer")}
        >
          <span className="error-tab-label">Lexer Errors</span>
          {lexerErrorCount > 0 && (
            <span className="error-tab-badge">{lexerErrorCount}</span>
          )}
        </button>

        <button
          className={`error-tab-btn ${activeTab === "parser" ? "active" : ""}`}
          onClick={() => setActiveTab("parser")}
        >
          <span className="error-tab-label">Syntax Errors</span>
          {syntaxErrorCount > 0 && (
            <span className="error-tab-badge">{syntaxErrorCount}</span>
          )}
        </button>

        <button
          className={`error-tab-btn ${activeTab === "semantic" ? "active" : ""}`}
          onClick={() => setActiveTab("semantic")}
        >
          <span className="error-tab-label">Semantic Errors</span>
          {semanticErrorCount > 0 && (
            <span className="error-tab-badge">{semanticErrorCount}</span>
          )}
        </button>

        <button
          className={`error-tab-btn ${activeTab === "output" ? "active" : ""}`}
          onClick={() => setActiveTab("output")}
        >
          <span className="error-tab-label">Output</span>
          {hasExecuted && executionResult && !executionResult.runtime_error &&
            executionResult.output && executionResult.status === "completed" && (
            <span className="error-tab-badge error-tab-badge--success">
              &#x2713;
            </span>
          )}
          {hasExecuted && executionResult && executionResult.runtime_error && (
            <span className="error-tab-badge">!</span>
          )}
        </button>
      </div>

      {/* Tab Content */}
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
  );
}
