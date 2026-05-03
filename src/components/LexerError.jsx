import React, { useState, useEffect } from "react"; // Import useState and useEffect
import "./LexerError.css";

export default function LexerError({ errors, hasRun }) {
  // --- STATE ---
  // State to track if the "Copy" button has been clicked
  const [isCopied, setIsCopied] = useState(false);

  // --- FILTER ---
  // Filter for relevant errors
  // We do this early so we can return null if there are no errors to show.
  const errs = errors
    ? errors.filter((e) => e.type === "ERROR" || e.type === "LEXICAL_ERROR")
    : [];

  // --- EFFECT ---
  // This effect runs every time the 'errors' prop changes.
  // This satisfies your requirement: "restarts to copy if the user tokenized again"
  useEffect(() => {
    setIsCopied(false); // Reset the button text to "Copy"
  }, [errors]); // The dependency array: this code runs when 'errors' changes

  // --- HANDLER ---
  // Handle the copy button click
  const handleCopyClick = () => {
    if (!navigator.clipboard) return; // Safety check for older browsers

    navigator.clipboard
      .writeText(JSON.stringify(errs, null, 2))
      .then(() => {
        setIsCopied(true); // Set text to "Copied!"

        // Set a timer to change it back to "Copy" after 2 seconds
        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      })
      .catch((err) => {
        console.error("Failed to copy errors: ", err);
        // You could add an error state here if you wanted
      });
  };

  // --- RENDER ---
  if (errs.length === 0) {
    if (hasRun) {
      return (
        <div className="lexer-success" role="status" aria-live="polite">
          <div className="lexer-success__header">
            <i className="fa-solid fa-circle-check lexer-success__icon"></i>
            <div>
              <div className="lexer-success__title">Lexing Successful</div>
              <div className="lexer-success__summary">
                No lexical errors found
              </div>
            </div>
          </div>
        </div>
      );
    }

    return null;
  }

  return (
    <div className="lexer-error" role="alert" aria-live="polite">
      <div className="lexer-error__header">
        <i className="fa-solid fa-circle-xmark lexer-error__icon"></i>
        <div>
          <div className="lexer-error__title">
            Lexical error{errs.length > 1 ? "s" : ""}
          </div>
          <div className="lexer-error__summary">
            {errs.length} problem{errs.length > 1 ? "s" : ""} found
          </div>
        </div>

        <button
          className="lexer-error__copy"
          onClick={handleCopyClick}
          aria-label="Copy error details"
          disabled={isCopied}
        >
          {isCopied ? "Copied!" : "Copy"}
        </button>
      </div>

      <div className="lexer-error__list">
        {errs.map((e, i) => (
          <div key={i} className="lexer-error__item">
            <div className="lexer-error__type-line">
              <span className="error-type-tag">LEXICAL ERROR</span>
              {e.message && <span className="error-message-text">{e.message}</span>}
            </div>

            <div className="lexer-error__details-row">
              {e.lexeme && (
                <div className="lexer-error__lexeme-box">
                  <span className="label">Invalid:</span>
                  <code className="lexeme-code">{e.lexeme}</code>
                </div>
              )}
              <div className="lexer-error__loc">
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