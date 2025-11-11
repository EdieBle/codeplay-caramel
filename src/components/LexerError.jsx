import React, { useState, useEffect } from 'react'; // Import useState and useEffect
import './LexerError.css';

export default function LexerError({ errors }) {
  // --- STATE ---
  const [isCopied, setIsCopied] = useState(false);

  // --- FILTER ---
  const errs = errors ? errors.filter(e => e.type === "ERROR" || e.type === "LEXICAL_ERROR") : [];

  // --- EFFECT ---
  useEffect(() => {
    setIsCopied(false);
  }, [errors]);

  // --- HANDLER ---
  const handleCopyClick = () => {
    if (!navigator.clipboard) return; // Safety check for older browsers

    navigator.clipboard.writeText(JSON.stringify(errs, null, 2))
      .then(() => {
        setIsCopied(true); // Set text to "Copied!"

        setTimeout(() => {
          setIsCopied(false);
        }, 2000);
      })
      .catch(err => {
        console.error('Failed to copy errors: ', err);
      });
  };

  // --- RENDER ---
  if (errs.length === 0) return null;

  return (
    <div className="lexer-error" role="alert" aria-live="polite">
      <div className="lexer-error__header">
        <span className="lexer-error__icon">⚠️</span>
        <div>
          <div className="lexer-error__title">Lexical error{errs.length > 1 ? 's' : ''}</div>
          <div className="lexer-error__summary">{errs.length} problem{errs.length > 1 ? 's' : ''} found</div>
        </div>
        <button 
          className="lexer-error__copy" 
          onClick={handleCopyClick} 
          aria-label="Copy error details"
          disabled={isCopied}
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