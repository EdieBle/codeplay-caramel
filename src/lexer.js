// lexer.js — Caramel (PDF-aligned) reserved words + '_' rule in identifiers
export function tokenize(code) {
  const tokenSpecs = [
    // === Comments (from comment spec) ===
    // ~~ ... EOL   |   ~. ... .~   |   ~. ... (to EOF if no .~)
    ["COMMENT", /~~[^\r\n]*|~\.[\s\S]*?(?:\.~|$)/],

    // === Multi-token keywords (e.g. "taste till") ===
    ["KEYWORD", /(?:tastetill|taste[ \t]+till)/],

    // Symbolic keywords (contain non-alphanumeric characters)
    ["KEYWORD", /(refill\?|batter@)/],

    // === Control-flow & other reserved words ===
    ["KEYWORD", /\b(ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|snap|skip|cup|recipe|glaze|new|defoam|empty)\b/],

    // === Booleans & null literal ===
    ["BOOLEAN", /\b(hot|cold)\b/],
    ["NULL", /\b(decaf)\b/],

    // === Declarations ===
    ["DECLARATION", /\b(cupcake|local|brewed)\b/],

    // === Types ===
    ["CLASS_KEYWORD", /\b(crema)\b/], // class
    ["DATA_TYPE", /\b(bean|drip|blend|temp|churro|mug)\b/], // primitives + struct

    // === Literals (float BEFORE int) ===
    ["FLOAT_LIT", /\b\d+\.\d+\b/],
    ["INT_LIT", /\b\d+\b/],
    ["STRING_LIT", /"[^"\n]*"/],
    ["CHAR_LIT", /'[^'\n]'/],

    // === Identifiers (allow underscore but not as first char) ===
    // ✅ starts with lowercase letter, followed by letters, digits, or underscores
    ["IDENTIFIER", /\b[a-z][a-z0-9_]*\b/],

    // === Operators & delimiters ===
    ["OPERATOR", /(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])/],
    ["DELIMITER", /[{}\[\](),.;]/],

    // === Whitespace & newlines ===
    ["WHITESPACE", /[ \t]+/],
    ["NEWLINE", /\r?\n/], // handle CRLF or LF
  ];

  const tokens = [];
  let line = 1, column = 1;
  let pos = 0;

  while (pos < code.length) {
    let matchFound = false;

    for (const [type, regex] of tokenSpecs) {
      const slice = code.slice(pos);
      const match = slice.match(regex);

      if (match && match.index === 0) {
        const raw = match[0];

        if (type === "NEWLINE") {
          tokens.push({ type, lexeme: "↵", line, column });
          pos += raw.length;     // consumes \n or \r\n
          line += 1;
          column = 1;
          matchFound = true;
          break;
        }

        if (type === "WHITESPACE") {
          const visible = raw.replace(/\t/g, "⇥").replace(/ /g, "␣");
          tokens.push({ type, lexeme: visible, line, column });
          pos += raw.length;
          column += raw.length;
          matchFound = true;
          break;
        }

        // Normal tokens (including COMMENT, KEYWORD, BOOLEAN, NULL, etc.)
        tokens.push({ type, lexeme: raw, line, column });
        pos += raw.length;
        column += raw.length;
        matchFound = true;
        break;
      }
    }

    if (!matchFound) {
      tokens.push({ type: "ERROR", lexeme: code[pos], line, column });
      pos += 1;
      column += 1;
    }
  }

  return tokens;
}