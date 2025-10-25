export function tokenize(code) {
   const tokenSpecs = [
    // Comments
    ["COMMENT", /\/\/[^\n]*|\/\*[\s\S]*?\*\//],

    // Keywords (control, function, etc.)
    ["KEYWORD", /\b(ifbrew|elseiflatte|elsepress|pour|whilehot|tastetill|flavour|syrup|defaultbean|snap|glaze)\b/],

    // Declarations and function-related
    ["DECLARATION", /\b(cupcake|local|brewed)\b/],
    ["FUNCTION_KEYWORD", /\b(emptycup|recipe|refill)\b/],

    // Class and struct
    ["CLASS_KEYWORD", /\b(crema|mug)\b/],

    // Data types
    ["DATA_TYPE", /\b(bean|drip|blend|temp|mug|churro|decaf)\b/],

    // Literals
    ["INT_LIT", /\b\d+\b/],
    ["FLOAT_LIT", /\b\d+\.\d+\b/],
    ["STRING_LIT", /"[^"\n]*"/],
    ["CHAR_LIT", /'[^'\n]'/],

    // Identifiers
    ["IDENTIFIER", /\b[a-z][a-z0-9]*\b/],

    // Operators
    ["OPERATOR", /(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])/],

    // Delimiters
    ["DELIMITER", /[{}\[\](),]/],

    // Whitespace and newlines
    ["WHITESPACE", /[ \t]+/],
    ["NEWLINE", /\n/],
  ];


  const tokens = [];
  let line = 1, column = 1;
  let pos = 0;

  while (pos < code.length) {
    let matchFound = false;

    for (const [type, regex] of tokenSpecs) {
      // Match from the start of the remaining code only
      const substring = code.slice(pos);
      const match = substring.match(regex);

      if (match && match.index === 0) {
        const lexeme = match[0];
        if (type === "NEWLINE") {
          line++;
          column = 1;
        } else if (type !== "WHITESPACE") {
          tokens.push({ type, lexeme, line, column });
          column += lexeme.length;
        } else {
          column += lexeme.length;
        }

        pos += lexeme.length;
        matchFound = true;
        break;
      }
    }

    // No regex matched so treat as an error token and advance
    if (!matchFound) {
      tokens.push({ type: "ERROR", lexeme: code[pos], line, column });
      pos++;
      column++;
    }
  }

  return tokens;
}
