import React, { useState, useEffect } from "react";
import "./ErrorTabs.css";
import LexerError from "./LexerError";
import SyntaxErrorPanel from "./SyntaxErrorPanel";

export default function ErrorTabs({ errors, hasParsed, hasRun }) {
  const [activeTab, setActiveTab] = useState("lexer");

  // Reset to lexer tab when errors change
  useEffect(() => {
    setActiveTab("lexer");
  }, [errors]);

  // Count errors by type
  const lexerErrorCount = errors
    ? errors.filter((e) => e.type === "ERROR" || e.type === "LEXICAL_ERROR")
        .length
    : 0;

  const syntaxErrorCount = errors
    ? errors.filter((e) => e.type === "SYNTAX_ERROR").length
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
          <span className="error-tab-label">Parser/Syntax Errors</span>
          {syntaxErrorCount > 0 && (
            <span className="error-tab-badge">{syntaxErrorCount}</span>
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
            <SyntaxErrorPanel errors={errors} hasParsed={hasParsed} />
          </div>
        )}
      </div>
    </div>
  );
}