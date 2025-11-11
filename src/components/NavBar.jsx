import React, { useState } from "react";
import "./NavBar.css";
import Modal from "./Modal";

// 1. Accept props: 'theme' and 'onToggleTheme'
export default function NavBar({ theme, onToggleTheme }) {
  const [showAbout, setShowAbout] = useState(false);

  return (
    <>
      <nav className="cp-navbar">
        <div className="cp-navbar__brand">
          <img src="/images/logo.svg" alt="CodePlay Caramel" style={{height:36}} />
        </div>
        <ul className="cp-navbar__links">
          <li>
            <a href="#">
              <i className="fa-solid fa-code"></i>
              <span>Analyser</span>
            </a>
          </li>
          
          <li><a href="#" onClick={(e) => {
            e.preventDefault();
            setShowAbout(true);
          }}>
            {/* Fixed: class -> className */}
            <i className="fa-solid fa-info"></i>
            <span>About</span>
            </a>
          </li>

          {/* 2. THIS IS THE UPDATED TOGGLE BUTTON */}
          <li>
            <a href="#" onClick={(e) => {
              e.preventDefault();
              onToggleTheme(); // Call the function from App.jsx
            }}>
              {/* 3. Icon changes based on the theme prop */}
              <i className={theme === 'dark' ? "fa-solid fa-moon" : "fa-solid fa-sun"}></i>
              <span>Mode</span>
            </a>
          </li>
        </ul>
      </nav>

      <Modal isOpen={showAbout} onClose={() => setShowAbout(false)}>
        <h2 className="modal-title">About Caramel Programming Language</h2>
        <div className="modal-body">
          <img src="/images/logo.png" alt="Caramel Logo" className="modal-logo" />
          <p>
            Caramel is a strongly typed and explicitly declared programming language, inspired heavily by C++ and with a touch of Kotlin, designed to simplify and modernize syntax. The name Caramel was chosen to represent its developers—coffeeholics who love the sweet, toasted flavor of caramel. Its theme is reflected throughout the programming language, primarily using coffee and sweets-themed reserved words. Students and other developers using this language should be familiar with or have experience coding using C++ to understand Caramel's syntax.
          </p>
          <p>
            The two principles that guide the design of the programming language are simplicity and modernized syntax. Key features of the programming language include basic syntax, handling data types, and modular programming using global and constant values—concepts referenced from C++. Caramel also supports functions, arrays, access modifiers, classes, and a variety of statements and expressions. On the other hand, the structure of the programming language is modeled after Kotlin. The features of Caramel are traditional and common among existing programming languages, but made unique through its theme. These features will all be discussed in more detail.
          </p>
        </div>
      </Modal>
    </>
  );
}