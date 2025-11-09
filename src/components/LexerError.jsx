import React, { useState, useEffect } from 'react'; // Import useState and useEffect
import './LexerError.css';

export default function LexerError({ errors }) {
  // --- STATE ---
  // State to track if the "Copy" button has been clicked
  const [isCopied, setIsCopied] = useState(false);

  // --- FILTER ---
  // Filter for relevant errors
  // We do this early so we can return null if there are no errors to show.
  const errs = errors ? errors.filter(e => e.type === "ERROR" || e.type === "LEXICAL_ERROR") : [];

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

    navigator.clipboard.writeText(JSON.stringify(errs, null, 2))
      .then(() => {
        setIsCopied(true); // Set text to "Copied!"

        // Set a timer to change it back to "Copy" after 2 seconds
        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      })
      .catch(err => {
        console.error('Failed to copy errors: ', err);
        // You could add an error state here if you wanted
      });
  };

  // --- RENDER ---
  // If there are no *filtered* errors, don't render the component
  if (errs.length === 0) return null;

  return (
    <div className="lexer-error" role="alert" aria-live="polite">
      <div className="lexer-error__header">
        <span className="lexer-error__icon">⚠️</span>
        <div>
          <div className="lexer-error__title">Lexical error{errs.length > 1 ? 's' : ''}</div>
          <div className="lexer-error__summary">{errs.length} problem{errs.length > 1 ? 's' : ''} found</div>
        </div>
        
        {/* --- UPDATED BUTTON --- */}
        <button 
          className="lexer-error__copy" 
          onClick={handleCopyClick} 
          aria-label="Copy error details"
          disabled={isCopied} /* Optional: prevent re-clicking while "Copied!" */
        >
          {isCopied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <div className="lexer-error__list">
        {errs.map((e, i) => (
          <div key={i} className="lexer-error__item">
            <div className="lexer-error__type-line">
              {e.type.replace("_", " ").toUpperCase()}
              {e.message ? `: ${e.message}` : ":"}
            </div>

            <div className="lexer-error__details-row">
              <div className="lexer-error__lexeme">"{e.lexeme}"</div>
              <div className="lexer-error__loc">
                at line {e.line}, col {e.column}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}