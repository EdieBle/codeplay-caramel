export function tokenize(code) {
  const MAX_BEAN = 9_999_999_999;
  const tokenSpecs = [

    ["COMMENT", /~~[^\r\n]*|~\.[\s\S]*?(?:\.~|$)/],

    ["KEYWORD", /(?:tastetill|taste[ \t]+till)/],

    ["KEYWORD", /(refill\?|batter@)/],

    ["KEYWORD", /\b(ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|snap|skip|cup|recipe|glaze|new|defoam|empty)\b/],

    ["BOOLEAN", /\b(hot|cold)\b/],
    ["NULL", /\b(decaf)\b/],

    ["DECLARATION", /\b(cupcake|local|brewed)\b/],

    ["CLASS_KEYWORD", /\b(crema)\b/],
    ["DATA_TYPE", /\b(bean|drip|blend|temp|churro|mug)\b/],

    ["FLOAT_LIT", /\b\d+\.\d+\b/],

    ["BEAN_RAW", /\b\d+\b/],

    ["STRING_LIT", /"[^"\n]*"/],
    ["CHAR_LIT", /'[^'\n]'/],

    ["IDENTIFIER", /\b[a-z][a-z0-9_]*\b/],

    ["HYPHEN_ERROR", /[\u2010-\u2015](?=\d)/],

    ["OPERATOR", /(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])/],
    ["DELIMITER", /[{}\[\](),.;]/],

    ["WHITESPACE", /[ \t]+/],
    ["NEWLINE", /\r?\n/],
  ];

  const tokens = [];
  let line = 1, column = 1;
  let pos = 0;

  function normalizeBeanDigits(digits) {
    let norm = digits.replace(/^0+(?=\d)/, "");
    if (norm === "" || /^0+$/.test(digits)) {
      norm = "0";
    }
    if (norm.length > 11) {
      return String(MAX_BEAN);
    }
    try {
      const val = BigInt(norm);
      const max = BigInt(MAX_BEAN);
      if (val > max) return String(MAX_BEAN);
      return String(val);
    } catch {
      return String(MAX_BEAN);
    }
  }

  while (pos < code.length) {
    let matchFound = false;

    for (const [type, regex] of tokenSpecs) {
      const slice = code.slice(pos);
      const match = slice.match(regex);

      if (match && match.index === 0) {
        const raw = match[0];

        if (type === "NEWLINE") {
          tokens.push({ type: "NEWLINE", lexeme: "↵", line, column });
          pos += raw.length;
          line += 1;
          column = 1;
          matchFound = true;
          break;
        }

        if (type === "WHITESPACE") {
          const visible = raw.replace(/\t/g, "⇥").replace(/ /g, "␣");
          tokens.push({ type: "WHITESPACE", lexeme: visible, line, column });
          pos += raw.length;
          column += raw.length;
          matchFound = true;
          break;
        }

        if (type === "HYPHEN_ERROR") {
          tokens.push({
            type: "ERROR",
            lexeme: raw,
            line,
            column,
            message: "Invalid negative sign: use '-' (ASCII) not a hyphen/dash",
          });
          pos += raw.length;
          column += raw.length;
          matchFound = true;
          break;
        }

        if (type === "BEAN_RAW") {
          const normalized = normalizeBeanDigits(raw);
          tokens.push({
            type: "BEAN_LIT",
            lexeme: normalized,
            line,
            column,
            original: raw,
          });
          pos += raw.length;
          column += raw.length;
          matchFound = true;
          break;
        }

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
