export function tokenize(code) {
  const MAX_BEAN = 9_999_999_999; 
  const MAX_DRIP_INT = "9999999999";  
  const MAX_DRIP_FRAC = "9999999999";     

  const tokenSpecs = [
    ["COMMENT", /~~[^\r\n]*|~\.[\s\S]*?(?:\.~|$)/],

    ["INVALID_NUM_SEP", /\b\d[\d,_]*\.\d[\d,_]*\b|\b\d[\d,_]*\b/],
    ["INVALID_BASE", /\b0[xX][0-9A-Fa-f]+|\b0[bB][01]+|\b0[oO][0-7]+/],
    ["HYPHEN_ERROR", /[\u2010-\u2015](?=\d|\d+\.\d+)/],


    ["KEYWORD", /(?:tastetill|taste[ \t]+till)/],
    ["KEYWORD", /(refill\?|batter@)/],
    ["KEYWORD", /\b(ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|snap|skip|cup|recipe|glaze|new|defoam|empty)\b/],

    ["BOOLEAN", /\b(hot|cold)\b/],
    ["NULL", /\b(decaf)\b/],

    ["DECLARATION", /\b(cupcake|local|brewed)\b/],

    ["CLASS_KEYWORD", /\b(crema)\b/],
    ["DATA_TYPE", /\b(bean|drip|blend|temp|churro|mug)\b/],

    ["DRIP_RAW", /\b\d+\.\d+\b/],
    ["BEAN_RAW", /\b\d+\b/],
    ["STRING_LIT", /"[^"\n]*"/],
    ["CHAR_LIT", /'[^'\n]'/],

    ["IDENTIFIER", /\b[a-z][a-z0-9_]*\b/],

    ["OPERATOR", /(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])/],
    ["DELIMITER", /[{}\[\](),.;]/],

    ["WHITESPACE", /[ \t]+/],
    ["NEWLINE", /\r?\n/],
  ];

  const tokens = [];
  let line = 1, column = 1;
  let pos = 0;

  function push(tok) { tokens.push(tok); }

  function normalizeBeanDigits(digits) {
    let norm = digits.replace(/^0+(?=\d)/, "");
    if (norm === "" || /^0+$/.test(digits)) norm = "0";
    if (norm.length > 11) return String(MAX_BEAN);
    try {
      const val = BigInt(norm);
      const max = BigInt(MAX_BEAN);
      if (val > max) return String(MAX_BEAN);
      return String(val);
    } catch { return String(MAX_BEAN); }
  }

  function cmp10(a, b) {
    return a === b ? 0 : (a > b ? 1 : -1);
  }

  function clampDrip(intPart, fracPart) {
    let frac = (fracPart || "").slice(0, 10);
    frac = frac.replace(/0+$/, "");
    let intp = intPart.replace(/^0+(?=\d)/, "");
    if (intp === "") intp = "0";

    if (intp.length > 10) return [MAX_DRIP_INT, MAX_DRIP_FRAC];
    if (intp.length === 10) {
      const c = cmp10(intp, MAX_DRIP_INT);
      if (c > 0) return [MAX_DRIP_INT, MAX_DRIP_FRAC];
      if (c === 0 && frac.length > 10) return [MAX_DRIP_INT, MAX_DRIP_FRAC];
    }
    return [intp, frac];
  }

  function emitDrip(raw, l, c) {
    const [intp, fracp] = raw.split(".");
    let [ni, nf] = clampDrip(intp, fracp);
    if (ni === "0" && nf === "") {
      push({ type: "DRIP_LIT", lexeme: "0", line: l, column: c, original: raw });
    } else {
      const lex = nf ? `${ni}.${nf}` : ni;
      push({ type: "DRIP_LIT", lexeme: lex, line: l, column: c, original: raw });
    }
  }

  while (pos < code.length) {
    let matchFound = false;

    for (const [type, regex] of tokenSpecs) {
      const slice = code.slice(pos);
      const m = slice.match(regex);
      if (!m || m.index !== 0) continue;

      const raw = m[0];

      if (type === "NEWLINE") {
        push({ type: "NEWLINE", lexeme: "↵", line, column });
        pos += raw.length; line += 1; column = 1;
        matchFound = true; break;
      }

      if (type === "WHITESPACE") {
        const visible = raw.replace(/\t/g, "⇥").replace(/ /g, "␣");
        push({ type: "WHITESPACE", lexeme: visible, line, column });
        pos += raw.length; column += raw.length;
        matchFound = true; break;
      }

      if (type === "INVALID_NUM_SEP") {
        if (/[,_]/.test(raw)) {
          push({
            type: "ERROR",
            lexeme: raw,
            line, column,
            message: "Numbers cannot contain commas or underscores.",
          });
          pos += raw.length; column += raw.length;
          matchFound = true; break;
        }
      }

      if (type === "INVALID_BASE") {
        push({
          type: "ERROR",
          lexeme: raw,
          line, column,
          message: "Hex/octal/binary literals are not allowed.",
        });
        pos += raw.length; column += raw.length;
        matchFound = true; break;
      }

      if (type === "HYPHEN_ERROR") {
        push({
          type: "ERROR",
          lexeme: raw,
          line, column,
          message: "Invalid negative sign: use '-' (ASCII hyphen).",
        });
        pos += raw.length; column += raw.length;
        matchFound = true; break;
      }

      if (type === "DRIP_RAW") {
        emitDrip(raw, line, column);
        pos += raw.length; column += raw.length;
        matchFound = true; break;
      }

      if (type === "BEAN_RAW") {
        const normalized = normalizeBeanDigits(raw);
        push({ type: "BEAN_LIT", lexeme: normalized, line, column, original: raw });
        pos += raw.length; column += raw.length;
        matchFound = true; break;
      }

      push({ type, lexeme: raw, line, column });
      pos += raw.length; column += raw.length;
      matchFound = true; break;
    }

    if (!matchFound) {
      push({ type: "ERROR", lexeme: code[pos], line, column });
      pos += 1; column += 1;
    }
  }

  return tokens;
}