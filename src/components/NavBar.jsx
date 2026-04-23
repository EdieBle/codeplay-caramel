import React, { useState, useEffect } from "react";
import "./NavBar.css";
import Modal from "./Modal";

export default function NavBar({ onSaveFile, onOpenFile }) {
  const [showAbout, setShowAbout] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== "undefined" && window.localStorage) {
      try {
        return localStorage.getItem("darkMode") === "true";
      } catch (e) {
        console.error("Failed to read localStorage:", e);
        return false;
      }
    }
    return false;
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        if (darkMode) {
          document.documentElement.setAttribute("data-theme", "dark");
          if (window.localStorage) {
            localStorage.setItem("darkMode", "true");
          }
        } else {
          document.documentElement.removeAttribute("data-theme");
          if (window.localStorage) {
            localStorage.setItem("darkMode", "false");
          }
        }
      } catch (e) {
        console.error("Failed to update theme:", e);
      }
    }
  }, [darkMode]);

  const handleModeToggle = (e) => {
    e.preventDefault();
    setDarkMode(!darkMode);
  };

  return (
    <>
      <nav className="cp-navbar">
        <div className="cp-navbar__brand">
          <img
            src="/images/logo.svg"
            alt="CodePlay Caramel"
            style={{ height: 36 }}
          />
        </div>
        <ul className="cp-navbar__links">
          <li>
            <a
              href="#"
              onClick={(e) => {
                // e.preventDefault();
                // onSaveFile?.();
              }}
            >
              <i className="fa-solid fa-save"></i>
              <span>Save File</span>
            </a>
          </li>

          <li>
            <a
              href="#"
              onClick={(e) => {
                // e.preventDefault();
                 //onOpenFile?.();
              }}
            >
              <i className="fa-solid fa-folder-open"></i>
              <span>Open File</span>
            </a>
          </li>

          <li>
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                setShowAbout(true);
              }}
            >
              <i className="fa-solid fa-info"></i>
              <span>About</span>
            </a>
          </li>
          <li>
            <a href="#" onClick={handleModeToggle} className="mode-toggle">
              <i className={`fa-solid ${darkMode ? "fa-sun" : "fa-moon"}`}></i>
              <span>Mode</span>
            </a>
          </li>
        </ul>
      </nav>

      <Modal isOpen={showAbout} onClose={() => setShowAbout(false)}>
        <h2 className="modal-title">About Caramel Programming Language</h2>
        <div className="modal-body">
          <img
            src="/images/logo.png"
            alt="Caramel Logo"
            className="modal-logo"
          />
          <p>
            Caramel is a strongly typed and explicitly declared programming
            language, inspired heavily by C++ and with a touch of Kotlin,
            designed to simplify and modernize syntax. The name Caramel was
            chosen to represent its developers—coffeeholics who love the sweet,
            toasted flavor of caramel. Its theme is reflected throughout the
            programming language, primarily using coffee and sweets-themed
            reserved words. Students and other developers using this language
            should be familiar with or have experience coding using C++ to
            understand Caramel's syntax.
          </p>
          <p>
            The two principles that guide the design of the programming language
            are simplicity and modernized syntax. Key features of the
            programming language include basic syntax, handling data types, and
            modular programming using global and constant values—concepts
            referenced from C++. Caramel also supports functions, arrays, access
            modifiers, classes, and a variety of statements and expressions. On
            the other hand, the structure of the programming language is modeled
            after Kotlin. The features of Caramel are traditional and common
            among existing programming languages, but made unique through its
            theme. These features will all be discussed in more detail.
          </p>
        </div>
      </Modal>
    </>
  );
}