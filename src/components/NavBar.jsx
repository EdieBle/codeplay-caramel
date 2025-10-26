import React from "react";

export default function NavBar() {
  return (
    <nav className="cp-navbar">
      <div className="cp-navbar__brand">
        <img src="/images/logo.svg" alt="CodePlay Caramel" style={{height:36}} />
      </div>
      <ul className="cp-navbar__links">
        <li><a href="#">Analyser</a></li>
        <li><a href="#">About</a></li>
      </ul>
    </nav>
  );
}
