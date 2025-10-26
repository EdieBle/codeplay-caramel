import React from 'react';
import './LexerError.css';

export default function LexerError({ errors }) {
  // errors: array of { type, lexeme, line, column } or empty
  if (!errors || errors.length === 0) return null;

  const errs = errors.filter(e => e.type === 'ERROR');

  return (
    <div className="lexer-error" role="alert" aria-live="polite">
      <div className="lexer-error__header">
        <span className="lexer-error__icon">⚠️</span>
        <div>
          <div className="lexer-error__title">Lexical error{errs.length > 1 ? 's' : ''}</div>
          <div className="lexer-error__summary">{errs.length} problem{errs.length>1?'s':''} found</div>
        </div>
        <button className="lexer-error__copy" onClick={() => {
          navigator.clipboard?.writeText(JSON.stringify(errs, null, 2));
        }} aria-label="Copy error details">Copy</button>
      </div>

      <div className="lexer-error__list">
        {errs.map((e, i) => (
          <div key={i} className="lexer-error__item">
            <div className="lexer-error__item-left">
              <span className="lexer-error__lexeme">{e.lexeme}</span>
              <span className="lexer-error__type">{e.type}</span>
            </div>
            <div className="lexer-error__loc">line {e.line}, col {e.column}</div>
          </div>
        ))}
      </div>
    </div>
  );
}