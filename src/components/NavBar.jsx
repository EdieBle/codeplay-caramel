import React from "react";

export default function NavBar() {
  return (
    <nav className="cp-navbar">
      <div className="cp-navbar__brand">
        <img src="/images/logo.svg" alt="CodePlay Caramel" style={{height:36}} />
      </div>
      <ul className="cp-navbar__links">
        <li><a href="#">Lexer</a></li>
        <li><a href="#">Parser</a></li>
        <li><a href="#">Syntax</a></li>
        <li><a href="#">Semantic</a></li>
      </ul>
    </nav>
  );
}
