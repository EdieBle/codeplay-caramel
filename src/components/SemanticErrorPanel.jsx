import React, { useEffect, useState } from "react";
import "./SemanticErrorPanel.css";

export default function SemanticErrorPanel({ errors, hasParsed }) {
  const [isCopied, setIsCopied] = useState(false);

  const semanticErrors = errors
    ? errors.filter((e) => e.type === "SEMANTIC_ERROR" || e.type === "SEMANTIC")
    : [];

  useEffect(() => {
    setIsCopied(false);
  }, [errors]);

  const handleCopyClick = () => {
    if (!navigator.clipboard) return;

    navigator.clipboard
      .writeText(JSON.stringify(semanticErrors, null, 2))
      .then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      })
      .catch((err) => console.error("Copy failed:", err));
  };

  if (semanticErrors.length === 0 && !hasParsed) {
    return null;
  }

  if (semanticErrors.length === 0) {
    return (
      <div className="semantic-success" role="status" aria-live="polite">
        <div className="semantic-success__header">
          <i className="fa-solid fa-circle-check semantic-success__icon"></i>
          <div>
            <div className="semantic-success__title">Semantic Check Complete</div>
            <div className="semantic-success__summary">
              No semantic errors to display
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="semantic-error" role="alert" aria-live="polite">
      <div className="semantic-error__header">
        <i className="fa-solid fa-circle-xmark semantic-error__icon"></i>
        <div>
          <div className="semantic-error__title">
            Semantic error{semanticErrors.length > 1 ? "s" : ""}
          </div>
          <div className="semantic-error__summary">
            {semanticErrors.length} problem
            {semanticErrors.length > 1 ? "s" : ""} found
          </div>
        </div>

        <button
          className="semantic-error__copy"
          onClick={handleCopyClick}
          disabled={isCopied}
          aria-label="Copy semantic error details"
        >
          {isCopied ? "Copied!" : "Copy"}
        </button>
      </div>

      <div className="semantic-error__list">
        {semanticErrors.map((e, i) => (
          <div key={i} className="semantic-error__item">
            <div className="semantic-error__type-line">
              <span className="error-type-tag">SEMANTIC ERROR</span>
              {e.message && <span className="error-message-text">{e.message}</span>}
            </div>

            <div className="semantic-error__details-row">
              {e.lexeme && (
                <div className="semantic-error__lexeme-box">
                  <span className="label">Context:</span>
                  <code className="lexeme-code">{e.lexeme}</code>
                </div>
              )}
              <div className="semantic-error__loc">
                <i className="fa-solid fa-location-dot"></i>
                {Number.isFinite(Number(e.line)) &&
                Number.isFinite(Number(e.column))
                  ? `line ${e.line}, col ${e.column}`
                  : "Location unavailable"}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
