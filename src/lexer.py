import re

def tokenize(code):
    MAX_BEAN = 9_999_999_999
    MAX_DRIP_INT = "9999999999"
    MAX_DRIP_FRAC = "9999999999"

    token_specs = [
        ("COMMENT", r"~~[^\r\n]*|~\.[\s\S]*?(?:\.~|$)"),

        ("INVALID_NUM_SEP", r"\b\d[\d,_.]*[,_][\d,_.]*\b"),
        ("INVALID_BASE", r"\b0[xX][0-9A-Fa-f]+|\b0[bB][01]+|\b0[oO][0-7]+"),
        ("HYPHEN_ERROR", r"[\u2010-\u2015](?=\d|\d+\.\d+)"),

        ("DRIP_LIT", r"(?<![\w.])-?\d+\.\d+\b"), # supports negative numbers now via -? and (?<![\w.]) is a look behind so it doesnt process 4-4 into 4 and -4
        ("BEAN_LIT", r"(?<![\w.])-?\d+\b"),
        ("OPERATOR", r"(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])"),
        ("DELIMITER", r"[{}\[\](),.;]"),
        ("SPACE", r"[ \t]+"),
        ("NEWLINE", r"\r?\n"),

        # Keyword Start
        ("KEYWORD", r"(?:tastetill|taste[ \t]+till)"),
        ("KEYWORD", r"(refill\?|batter@)"),
        ("KEYWORD", r"\b(ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|snap|skip|cup|crema|recipe|glaze|new|defoam|empty|order)\b"),
        ("KEYWORD", r"\b(mug)\b"),

        # Access Modifiers
        ("ACCESS_MOD", r"(cafe|backroom)"),
        ("CONSTANT", r"\b(brewed)\b"),

        # Data Types
        ("DATA_TYPE", r"\b(bean|drip|blend|churro|temp|mug)\b"),
        ("BOOLEAN", r"\b(hot|cold)\b"),
        ("NULL", r"\b(decaf)\b"),
        ("STRING_LIT", r'"[^"\n]*"'),
        ("CHAR_LIT", r"'(\\.|[^\\'\n])'"),

        ("IDENTIFIER", r"\b[a-z][a-z0-9_]*\b")
    ]

    tokens = []
    pos = 0
    line = 1
    column = 1

    # Normalize integer literals
    def normalize_beanRange(digits: str) -> str:
        norm = re.sub(r'^0+(?=\d)', '', digits)
        if norm == "" or re.fullmatch(r'0+', digits):
            norm = "0"
        if len(norm) > 10:
            return str(MAX_BEAN)
        try:
            val = int(norm)
            if val > MAX_BEAN:
                return str(MAX_BEAN)
            return str(val)
        except ValueError:
            return str(MAX_BEAN)
    
    def normalize_dripRange(whole_part, decimal_part):
        decimal = (decimal_part or "")[:10]
        decimal = decimal.rstrip("0")
        whole = whole_part.lstrip("0")
        if whole == "":
            whole = 0

        if len(whole) > 10:
            return [MAX_DRIP_INT, MAX_DRIP_FRAC]

        if len(whole) == 10:
            compare = compare(whole, MAX_DRIP_INT)
            if compare > 0:
                return [MAX_DRIP_INT, MAX_DRIP_FRAC]
            if compare == 0 and len(decimal_part) > 10:
                return [MAX_DRIP_INT, MAX_DRIP_FRAC] 
        return f"{whole}.{decimal}" if decimal else whole

    # Token push helper
    def push(tok):
        tokens.append(tok)

    while pos < len(code):
        match_found = False
        for tok_type, pattern in token_specs:
            regex = re.compile(pattern)
            m = regex.match(code, pos)
            if not m:
                continue

            raw = m.group(0)

            # --- COMMENT ---
            if tok_type == "COMMENT":
                push({"type": "COMMENT", "lexeme": raw, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- NEWLINE ---
            if tok_type == "NEWLINE":
                push({"type": "NEWLINE", "lexeme": "↵", "line": line, "column": column})
                pos += len(raw)
                line += 1
                column = 1
                match_found = True
                break

            # --- SPACE ---
            if tok_type == "SPACE":
                parts = []
                for ch in raw:
                    if ch == "\t":
                        parts.append("Tab")
                    elif ch == " ":
                        parts.append("␣")
                    else:
                        parts.append(ch)
                visible = " ".join(parts)
                push({"type": "WHITESPACE", "lexeme": visible, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- IDENTIFIER ---
            if tok_type == "IDENTIFIER":
                if len(raw) > 15:
                    push({
                        "type": "LEXICAL_ERROR",
                        "lexeme": raw,
                        "line": line,
                        "column": column,
                        "message": "Identifier exceeds 15 characters"
                    })
                else:
                    push({"type": "IDENTIFIER", "lexeme": raw, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- Invalid number sep ---
            if tok_type == "INVALID_NUM_SEP":
                push({
                "type": "LEXICAL_ERROR",
                "lexeme": code[pos],
                "line": line,
                "column": column,
                "message": "Invalid Number Separator found."
                })
                pos += 1
                column += 1
                break

            if tok_type == "HYPHEN_ERROR":
                push({
                    "type": "LEXICAL_ERROR",
                    "lexeme": raw,
                    "line": line,
                    "column": column,
                    "message": "Invalid negative sign: use '-' (ASCII hyphen)."
                })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            if tok_type == "BEAN_LIT":
                normal_bean = normalize_beanRange(raw)
                push({
                    "type": "BEAN_LIT",
                    "lexeme": normal_bean,
                    "raw": raw,
                    "line": line,
                    "column": column
                })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- DRIP_LIT normalization --- WE MIGHT NEED TO TURN THE NORMALIZED INTO THE VALUE SIGURO??
            if tok_type == "DRIP_LIT":
                parts = raw.split(".", 1)
                whole = parts[0]
                dec = parts[1] if len(parts) > 1 else ""

                normal_drip = normalize_dripRange(whole, dec)
                push({
                    "type": "DRIP_LIT",
                    "lexeme": normal_drip,
                    "raw": raw,
                    "line": line,
                    "column": column
                })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # --- Default behavior ---
            push({"type": tok_type, "lexeme": raw, "line": line, "column": column})
            pos += len(raw)
            column += len(raw)
            match_found = True
            break

        # --- Handle unmatched characters ---
        if not match_found:
            push({
                "type": "LEXICAL_ERROR",
                "lexeme": code[pos],
                "line": line,
                "column": column,
                "message": "Unmatched Character"
            })
            pos += 1
            column += 1

    return tokens
