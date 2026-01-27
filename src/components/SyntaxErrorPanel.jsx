import React, { useState, useEffect } from "react";
import "./SyntaxErrorPanel.css";

export default function SyntaxErrorPanel({ errors, hasParsed }) {
  // --- STATE ---
  const [isCopied, setIsCopied] = useState(false);

  // --- FILTER ---
  // Only syntax errors
  const syn_errs = errors
    ? errors.filter(e => e.type === "SYNTAX_ERROR")
    : [];

  const lex_errs = errors
    ? errors.filter(e => e.type === "LEXICAL_ERROR")
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

  if (syn_errs.length === 0 && errs.length === 0 && lex_errs.length === 0 && hasParsed) {
    return (
      <div className="syntax-success" role="status" aria-live="polite">
        <div className="syntax-success__header">
          <span className="syntax-success__icon">✅</span>
          <div>
            <div className="syntax-success__title">Parsing Successful</div>
            <div className="syntax-success__summary">No lexical or syntax errors found</div>
          </div>
        </div>
      </div>
    );
  }

  if (syn_errs.length > 0 || errs.length > 0 || lex_errs.length > 0 && hasParsed) {
    return (
      <div className="syntax-error" role="status" aria-live="polite">
        <div className="syntax-success__header">
          <span className="syntax-success__icon">❌</span>
          <div>
            <div className="syntax-success__title">Parser not started, Lexer unsuccessful</div>
            <div className="syntax-success__summary">Lexical error/s found.</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="syntax-error" role="alert" aria-live="polite">
      <div className="syntax-error__header">
        <span className="syntax-error__icon">❌</span>
        <div>
          <div className="syntax-error__title">
            Syntax error{errs.length > 1 ? "s" : ""}
          </div>
          <div className="syntax-error__summary">
            {errs.length} problem{errs.length > 1 ? "s" : ""} found
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
        {errs.map((e, i) => (
          <div key={i} className="syntax-error__item">
            <div className="syntax-error__type-line">
              SYNTAX ERROR{e.message ? `: ${e.message}` : ":"}
            </div>

            <div className="syntax-error__details-row">
              {e.expected && (
                <div className="syntax-error__expected">
                  Expected: {Array.isArray(e.expected)
                    ? e.expected.join(", ")
                    : e.expected}
                </div>
              )}

              <div className="syntax-error__loc">
                at line {e.line}, col {e.column}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
