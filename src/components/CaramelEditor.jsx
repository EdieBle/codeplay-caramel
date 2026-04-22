import React, { useState, useEffect } from "react";
import Editor, { useMonaco } from "@monaco-editor/react";

export default function CaramelEditor({ code, setCode, onChangeCursor }) {
  const [themeName, setThemeName] = useState("caramel-light");

  const handleEditorWillMount = (monaco) => {
    // Prevent re-registering if it already exists
    const languages = monaco.languages.getLanguages();
    if (!languages.find(l => l.id === "caramel")) {
      monaco.languages.register({ id: "caramel" });
    }

    // Define token rules (Monarch setup)
    monaco.languages.setMonarchTokensProvider("caramel", {
      tokenizer: {
        root: [
          // 1. Comments
          [/~~\s*.*/, "comment"], // single line
          [/~\./, { token: "comment", next: "@comment_state" }], // multi line start

          // 2. Data Types
          [/\b(?:bean|drip|churro|temp|mug|blend)\b/, "datatype"],

          // 3. Orange Keywords
          [/\b(?:recipe|empty|crema|new)\b/, "keywordOrange"],

          // 4. Green Keywords
          [/\b(?:cafe|backroom|order|brewed)\b/, "keywordGreen"],

          // 5. Pink Keywords
          [/\bsift\b/, "keywordPink"],

          // 6. Remaining Keywords
          [
            /\b(?:ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|taste\s+till|snap|skip|decaf|defoam|cup|hot|cold|glaze)\b|refill\?|batter@/,
            "keywordDefault",
          ],

          // 7. Literals
          [/".*?"/, "literal"],
          [/'.*?'/, "literal"],
          [/\b\d+(?:\.\d+)?\b/, "literal"],

          // 8. Operators
          [
            /\+\+|--|\+=|-=|\*=|\/=|\=\=|!=|&&|\|\||>=|<=|[-+*/%=<>!]/,
            "operator",
          ],

          // 9. Brackets and Punctuation
          [/[(){}\[\]]/, "@brackets"],
          [/[.,;]/, "delimiter"],

          // 10. Identifiers
          [/[a-zA-Z_]\w*/, "identifier"],
        ],
        comment_state: [
          [/[^~.]+/, "comment"],
          [/\.~/, { token: "comment", next: "@pop" }],
          [/[~.]/, "comment"],
        ],
      },
    });

    // Enable bracket matching and code folding config for Caramel
    monaco.languages.setLanguageConfiguration("caramel", {
      brackets: [
        ["[", "]"],
        ["{", "}"],
        ["(", ")"],
      ],
      autoClosingPairs: [
        { open: "[", close: "]" },
        { open: "{", close: "}" },
        { open: "(", close: ")" },
        { open: '"', close: '"', notIn: ["string"] },
        { open: "'", close: "'", notIn: ["string", "comment"] },
      ],
    });

    // Define Custom Themes mapping exactly to App.css values
    monaco.editor.defineTheme("caramel-light", {
      base: "vs",
      inherit: true,
      rules: [
        { token: "comment", foreground: "7f8c8d", fontStyle: "italic" },
        { token: "datatype", foreground: "084690", fontStyle: "bold" },
        { token: "keywordOrange", foreground: "f39c12", fontStyle: "bold" },
        { token: "keywordGreen", foreground: "27ae60", fontStyle: "bold" },
        { token: "keywordPink", foreground: "e84393", fontStyle: "bold" },
        { token: "keywordDefault", foreground: "1c9cc8", fontStyle: "bold" },
        { token: "literal", foreground: "556b2f" },
        { token: "operator", foreground: "a10702", fontStyle: "bold" },
        { token: "identifier", foreground: "c0392b" },
        { token: "delimiter", foreground: "5f5d5d", fontStyle: "bold" },
      ],
      colors: {
        "editor.background": "#fffbfb",
        "editor.foreground": "#554d40",
        "editorLineNumber.foreground": "#806341",
        "editorLineNumber.activeForeground": "#554d40",
        "editorCursor.foreground": "#dda96d",
        "editor.lineHighlightBackground": "#fff5eb",
        "editor.selectionBackground": "#dda96d40",
        "editorBracketMatch.background": "#dda96d30",
        "editorBracketMatch.border": "#dda96d"
      },
    });

    monaco.editor.defineTheme("caramel-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "a8a8a8", fontStyle: "italic" },
        { token: "datatype", foreground: "64b5f6", fontStyle: "bold" },
        { token: "keywordOrange", foreground: "ffb74d", fontStyle: "bold" },
        { token: "keywordGreen", foreground: "66bb6a", fontStyle: "bold" },
        { token: "keywordPink", foreground: "f48fb1", fontStyle: "bold" },
        { token: "keywordDefault", foreground: "4dd0e1", fontStyle: "bold" },
        { token: "literal", foreground: "a5d6a7" },
        { token: "operator", foreground: "ff6b6b", fontStyle: "bold" },
        { token: "identifier", foreground: "e57373" },
        { token: "delimiter", foreground: "b0b0b0", fontStyle: "bold" },
      ],
      colors: {
        "editor.background": "#0d0d0d", /* Matching new deep base */
        "editor.foreground": "#f5f5f5",
        "editorLineNumber.foreground": "#555555",
        "editorLineNumber.activeForeground": "#dda96d",
        "editorCursor.foreground": "#dda96d",
        "editor.lineHighlightBackground": "#161616",
        "editor.selectionBackground": "#dda96d33",
        "editorBracketMatch.background": "#dda96d44",
        "editorBracketMatch.border": "#dda96d",
        "editor.lineHighlightBorder": "#00000000", /* Remove border around active line */
        "editorIndentGuide.background": "#222222",
        "editorIndentGuide.activeBackground": "#444444"
      },
    });

    // Caramel Autocomplete / Intellisense
    const caramelKeywords = [
      "bean", "drip", "churro", "temp", "mug", "blend",
      "recipe", "empty", "crema", "new",
      "cafe", "backroom", "order", "brewed",
      "sift",
      "ifbrew", "elifroth", "elspress", "flavour", "syrup", "pour", 
      "whilehot", "taste till", "snap", "skip", "decaf", "defoam", 
      "cup", "hot", "cold", "glaze", "refill?", "batter@"
    ];

    // Wrap completion provider register so it only registers once if editor remounts
    if (!monaco.languages.hasRegisteredProvider) {
      monaco.languages.registerCompletionItemProvider("caramel", {
        provideCompletionItems: (model, position) => {
          const suggestions = caramelKeywords.map((k) => ({
            label: k,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: k,
          }));
          return { suggestions: suggestions };
        },
      });
      monaco.languages.hasRegisteredProvider = true;
    }
  };

  useEffect(() => {
    // Determine theme from documentElement dynamically
    const observer = new MutationObserver(() => {
      const mode = document.documentElement.getAttribute("data-theme");
      setThemeName(mode === "dark" ? "caramel-dark" : "caramel-light");
    });

    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    const initialMode = document.documentElement.getAttribute("data-theme");
    setThemeName(initialMode === "dark" ? "caramel-dark" : "caramel-light");

    return () => observer.disconnect();
  }, []);

  const handleEditorChange = (value) => {
    // Sanitization from original implementation
    const sanitized = (value || "")
      .replace(/[\u201C\u201D]/g, '"')
      .replace(/[\u2018\u2019]/g, "'");
    setCode(sanitized);
  };

  const handleEditorDidMount = (editor, monaco) => {
    // Track cursor changes
    editor.onDidChangeCursorPosition((e) => {
      const pos = e.position;
      if (onChangeCursor) {
        onChangeCursor(pos.lineNumber, pos.column);
      }
    });

    // Run action to configure folds if needed
    // The language config auto-provides bracket folding!
  };

  return (
    <Editor
      height="100%"
      width="100%"
      language="caramel"
      theme={themeName}
      value={code}
      onChange={handleEditorChange}
      onMount={handleEditorDidMount}
      beforeMount={handleEditorWillMount}
      options={{
        minimap: { enabled: false },
        fontFamily: '"Fira Code", monospace, "Play", sans-serif',
        fontSize: 15,
        lineHeight: 24,
        matchBrackets: "always",
        folding: true,
        showFoldingControls: "always",
        scrollBeyondLastLine: false,
        padding: { top: 15, bottom: 15 },
        cursorBlinking: "smooth",
        renderLineHighlight: "all",
        overviewRulerBorder: false,
        wordWrap: "on", // useful for folding & small screens
        scrollbar: {
          vertical: 'visible',
          horizontal: 'visible',
          useShadows: false,
          verticalHasArrows: false,
          horizontalHasArrows: false,
          verticalScrollbarSize: 10,
          horizontalScrollbarSize: 10
        }
      }}
    />
  );
}
