import React, { useState, useEffect } from "react";
import "./SyntaxErrorPanel.css";

export default function SyntaxErrorPanel({ errors, hasParsed }) {
  // --- STATE ---
  const [isCopied, setIsCopied] = useState(false);

  // --- FILTER ---
  // Only syntax errors — infinite loop errors are shown in the Output tab
  const syn_errs = errors
    ? errors.filter(e => e.type === "SYNTAX_ERROR")
    : [];

  const errs = errors
    ? errors.filter(e => e.type === "ERROR")
    : [];

  // --- EFFECT ---
  // Reset copy button when errors change
  useEffect(() => {
    setIsCopied(false);
  }, [errors]);

  // --- HANDLER ---
  const handleCopyClick = () => {
    if (!navigator.clipboard) return;

    navigator.clipboard
      .writeText(JSON.stringify(errs, null, 2))
      .then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      })
      .catch(err => console.error("Copy failed:", err));
  };

  // --- RENDER ---
  if (errs.length === 0 && !hasParsed) return null;

  if (syn_errs.length === 0 && errs.length === 0 && hasParsed) {
    return (
      <div className="syntax-success" role="status" aria-live="polite">
        <div className="syntax-success__header">
          <i className="fa-solid fa-circle-check syntax-success__icon"></i>
          <div>
            <div className="syntax-success__title">Parsing Successful</div>
            <div className="syntax-success__summary">No syntax errors found</div>
          </div>
        </div>
      </div>
    );
  }

  if (errs.length > 0 && hasParsed) {
    return (
      <div className="syntax-error" role="status" aria-live="polite">
        <div className="syntax-success__header">
          <i className="fa-solid fa-circle-xmark syntax-success__icon"></i>
          <div>
            <div className="syntax-success__title">Parser not started</div>
            <div className="syntax-success__summary">Check Lexical errors.</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="syntax-error" role="alert" aria-live="polite">
      <div className="syntax-error__header">
        <i className="fa-solid fa-circle-xmark syntax-error__icon"></i>
        <div>
          <div className="syntax-error__title">
            Syntax error{syn_errs.length > 1 ? "s" : ""}
          </div>
          <div className="syntax-error__summary">
            {syn_errs.length} problem{syn_errs.length > 1 ? "s" : ""} found
          </div>
        </div>

        <button
          className="syntax-error__copy"
          onClick={handleCopyClick}
          disabled={isCopied}
          aria-label="Copy syntax error details"
        >
          {isCopied ? "Copied!" : "Copy"}
        </button>
      </div>

      <div className="syntax-error__list">
        {syn_errs.map((e, i) => (
          <div key={i} className="syntax-error__item">
            <div className="syntax-error__type-line">
              <span className="error-type-tag">SYNTAX ERROR</span>
              {e.message && <span className="error-message-text">{e.message}</span>}
            </div>

            <div className="syntax-error__details-row">
              {e.expected && (
                <div className="syntax-error__expected-box">
                  <span className="label">Expected:</span>
                  <code className="expected-code">
                    {Array.isArray(e.expected) ? e.expected.join(", ") : e.expected}
                  </code>
                </div>
              )}

              <div className="syntax-error__loc">
                <i className="fa-solid fa-location-dot"></i>
                line {e.line}, col {e.column}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
