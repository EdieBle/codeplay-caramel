import React, { useState, useEffect } from "react";
import Editor, { useMonaco } from "@monaco-editor/react";

export default function CaramelEditor({ code, setCode, onChangeCursor }) {
  const [themeName, setThemeName] = useState("caramel-dark");

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
          [/\b(?:bean|drip|churro|temp|blend)\b/, "datatype"],

          // 3. Orange Keywords
          [/\b(?:recipe|empty|crema|new)\b/, "keywordOrange"],

          // 4. Green Keywords
          [/\b(?:cafe|backroom|order|brewed)\b/, "keywordGreen"],

          // 5. Pink Keywords
          [/\b(?:sift|ceil|floor|pow|rand|sqrt|type)\b/, "keywordPink"],

          // 6. Remaining Keywords
          [
            /\b(?:ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|taste\s+till|snap|skip|decaf|defoam|cup|hot|cold|glaze)\b|refill\?|batter@/,
            "keywordDefault",
          ],

          // 7. Literals - Separates the \ from the other literals to highlight
          [/"/, { token: "string.quote", next: "@string_double" }],
          [/'/, { token: "string.quote", next: "@string_single" }],
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

        string_double: [
          [/\\[nt"\\']/, "escape"],
          [/\\./,        "literal"],
          [/[()[\]{}]/, "literal"],
          [/[^"\\]+/,    "literal"],
          [/"/,  { token: "string.quote", next: "@pop" }],
        ],
        string_single: [
          [/\\[nt"\\']/, "escape"],
          [/\\./,        "literal"],
          [/[()[\]{}]/, "literal"], // remove if not applicable in character
          [/[^'\\]+/,    "literal"],
          [/'/,  { token: "string.quote", next: "@pop" }],
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
        { token: "escape", foreground: "e67e22", fontStyle: "bold" },
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
        // "editorBracketMatch.background": "#dda96d30",
        // "editorBracketMatch.border": "#dda96d"
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
        { token: "escape", foreground: "e67e22", fontStyle: "bold" },
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
        // "editorBracketMatch.background": "#dda96d44",
        // "editorBracketMatch.border": "#dda96d",
        "editor.lineHighlightBorder": "#00000000", /* Remove border around active line */
        "editorIndentGuide.background": "#222222",
        "editorIndentGuide.activeBackground": "#444444"
      },
    });

    // Caramel Autocomplete / Intellisense
    const caramelKeywords = [
      "bean", "drip", "churro", "temp", "blend",
      "recipe", "empty", "crema", "new",
      "cafe", "backroom", "order", "brewed",
      "sift", "ceil", "floor", "pow", "rand", "sqrt", "type",
      "ifbrew", "elifroth", "elspress", "flavour", "syrup", "pour", 
      "whilehot", "taste till", "snap", "skip", "decaf", "defoam", 
      "cup", "hot", "cold", "glaze", "refill?", "batter@"
    ];

    // Wrap completion provider register so it only registers once if editor remounts
    if (!monaco.languages.hasRegisteredProvider) {
      monaco.languages.registerCompletionItemProvider("caramel", {
        provideCompletionItems: (model, position) => {
          const code = model.getValue();
          
          // For the variables to appear in the suggestion
          const lineContent = model.getLineContent(position.lineNumber);
          const textBeforeCursor = lineContent.substring(0, position.column - 1).trimStart();

          // Check if user is writing a new declaration
          const isDeclaration = /^(?:bean|drip|churro|blend|temp|crema|empty)\s+\w*$/.test(textBeforeCursor);

          // Get the declared variable
          const varRegex = /\b(?:bean|blend|churro|drip|temp|crema|empty)\s+([a-zA-Z_]\w*)/g
          const declaredVars = new Set();
          let match;
          while ((match = varRegex.exec(code)) !== null) {
            const name = match[1];
            if (name !== "cup") {
              declaredVars.add(name);
            }
          }

          // Static keyword suggestions
          const keywordSuggestions = caramelKeywords.map((k) => ({
            label: k,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: k,
          }));
          
          if (isDeclaration) {
            return { suggestions: keywordSuggestions };
          }

          // Dynamic variable suggestions
          const varSuggestions = [...declaredVars].map((v) => ({
            label: v,
            kind: monaco.languages.CompletionItemKind.Variable,
            insertText: v,
            detail: "declared variable",
          }));

          return { suggestions: [...keywordSuggestions, ...varSuggestions] };
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

  // Check if the \ is inside a string or not
  const isInsideString = (line, col) => {
    let inDouble = false;
    let inSingle = false;
    for (let i = 0; i < col; i++) {
      const ch = line[i];
      const prev = line[i - 1];
      if (ch === '"' && prev !== '\\' && !inSingle) inDouble = !inDouble;
      else if (ch === "'" && prev !== '\\' && !inDouble) inSingle = !inSingle;
    }
    return inDouble || inSingle;
  };

  const handleEditorDidMount = (editor, monaco) => {
    const decorations = editor.createDecorationsCollection([]);
    const stringBracketDecorations = editor.createDecorationsCollection([]);

    // If it is inside the string, then apply the colors same to the string literals
    const updateStringBrackets = () => {
      const model = editor.getModel();
      const totalLines = model.getLineCount();
      const newDecorations = [];
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      const className = isDark ? "caramel-string-bracket-dark" : "caramel-string-bracket-light";

      for (let l = 1; l <= totalLines; l++) {
        const lc = model.getLineContent(l);
        for (let c = 0; c < lc.length; c++) {
          if (isInsideString(lc, c) && "()[]{}".includes(lc[c])) {
            newDecorations.push({
              range: new monaco.Range(l, c + 1, l, c + 2),
              options: { inlineClassName: className }
            });
          }
        }
      }
      stringBracketDecorations.set(newDecorations);
    };

    editor.onDidChangeModelContent(updateStringBrackets);

    const themeObserver = new MutationObserver(updateStringBrackets);
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    updateStringBrackets();
    editor.onDidChangeCursorPosition((e) => {
      const pos = e.position;
      if (onChangeCursor) onChangeCursor(pos.lineNumber, pos.column);

      const model = editor.getModel();
      const lineContent = model.getLineContent(pos.lineNumber);
      const col = pos.column - 1;

      // Skip bracket highlighting if inside a string
      if (isInsideString(lineContent, col)) {
        decorations.set([]);
        return;
      }

      const ch = lineContent[col];
      const pairs = { '(': ')', '[': ']', '{': '}', ')': '(', ']': '[', '}': '{' };
      const openers = new Set(['(', '[', '{']);
      const closers = new Set([')', ']', '}']);

      if (!pairs[ch]) {
        decorations.set([]);
        return;
      }

      const target = pairs[ch];
      let depth = 0;
      let matchLine = pos.lineNumber;
      let matchCol = -1;
      const totalLines = model.getLineCount();

      if (openers.has(ch)) {
        // Search forward
        outer: for (let l = pos.lineNumber; l <= totalLines; l++) {
          const lc = model.getLineContent(l);
          const start = l === pos.lineNumber ? col : 0;
          for (let c = start; c < lc.length; c++) {
            if (isInsideString(lc, c)) continue;
            if (lc[c] === ch) depth++;
            else if (lc[c] === target) {
              depth--;
              if (depth === 0) { matchLine = l; matchCol = c; break outer; }
            }
          }
        }
      } else if (closers.has(ch)) {
        // Search backward
        outer: for (let l = pos.lineNumber; l >= 1; l--) {
          const lc = model.getLineContent(l);
          const start = l === pos.lineNumber ? col : lc.length - 1;
          for (let c = start; c >= 0; c--) {
            if (isInsideString(lc, c)) continue;
            if (lc[c] === ch) depth++;
            else if (lc[c] === target) {
              depth--;
              if (depth === 0) { matchLine = l; matchCol = c; break outer; }
            }
          }
        }
      }

      // Apply highlight decorations to both brackets
      if (matchCol === -1) { decorations.set([]); return; }
      const isDark = document.documentElement.getAttribute("data-theme") === "dark";
      const className = isDark ? "caramel-bracket-match-dark" : "caramel-bracket-match-light";

      decorations.set([
        {
          range: new monaco.Range(pos.lineNumber, col + 1, pos.lineNumber, col + 2),
          options: { inlineClassName: className }
        },
        {
          range: new monaco.Range(matchLine, matchCol + 1, matchLine, matchCol + 2),
          options: { inlineClassName: className }
        }
      ]);
    });
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
        fontSize: 16,
        lineHeight: 24,
        matchBrackets: "always",
        folding: true,
        showFoldingControls: "always",
        scrollBeyondLastLine: false,
        padding: { top: 5, bottom: 5 },
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
