import re

def tokenize(code):
    MAX_BEAN = 9_999_999_999
    MAX_DRIP_INT = "9999999999"
    MAX_DRIP_FRAC = "9999999999"

    token_specs = [
        ("COMMENT", r"~~[^\r\n]*|~\.[\s\S]*?(?:\.~|$)"),
        
        ("INVALID_NUM_SEP", r"\b\d[\d,_]*\.\d[\d,_]*\b|\b\d[\d,_]*\b"),
        ("INVALID_BASE", r"\b0[xX][0-9A-Fa-f]+|\b0[bB][01]+|\b0[oO][0-7]+"),
        ("HYPHEN_ERROR", r"[\u2010-\u2015](?=\d|\d+\.\d+)"),
        
        ("IDENTIFIER", r"\b[a-z][a-z0-9_]*\b"),
        ("OPERATOR", r"(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])"),
        ("DELIMITER", r"[{}\[\](),.;]"),
        ("WHITESPACE", r"[ \t]+"),
        ("NEWLINE", r"\r?\n"),
        
        # Access Modifiers
        ("ACCESS_MOD", r"(cafe|backroom)"),
        ("CONSTANT", r"\b(brewed)\b"),
        
        # Data Types
        ("DATA_TYPE", r"\b(bean|drip|blend|churro|temp|mug)\b"),
        ("BOOLEAN", r"\b(hot|cold)\b"),
        ("NULL", r"\b(decaf)\b"),
        ("DRIP_LIT", r"\b\d+\.\d+\b"),
        ("BEAN_LIT", r"\b\d+\b"),
        ("STRING_LIT", r'"[^"\n]*"'),
        ("CHAR_LIT", r"'[^'\n]'"),
        
        # Keyword Start
        ("KEYWORD", r"(?:tastetill|taste[ \t]+till)"),
        ("KEYWORD", r"(refill\?|batter@)"),
        ("KEYWORD", r"\b(ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|snap|skip|cup|crema|recipe|glaze|new|defoam|empty)\b")
    ]

    tokens = []
    pos = 0 
    line = 1 
    column = 1
    
    ''' 
    # Bean (int) Digits - remove trailing zeroes
    def normalizeBeanDigits(digits: str) -> str:
        norm = re.sub(r'^0+(?=\d)', '', digits)
        if norm == "" or re.fullmatch(r'0+',digits):
            norm = "0"
        if len(norm) > 11:
            return str(MAX_BEAN)
        
        try:
            val = int(norm)
            max = int(MAX_BEAN)
            if val > MAX_BEAN:
                return str(MAX_BEAN)
            return str(val)
        except ValueError:
            return str(MAX_BEAN)
    '''
    
    # Tokenizer Function
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

            if tok_type == "COMMENT":
                push({"type": "COMMENT", "lexeme": raw, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            if tok_type == "NEWLINE":
                push({"type": "NEWLINE", "lexeme": "↵", "line": line, "column": column})
                pos += len(raw)
                line += 1
                column = 1
                match_found = True
                break

            if tok_type == "WHITESPACE":
                if raw == "\t":
                    push({
                        "type": "TAB",
                        "lexeme": "Tab",
                        "line": line,
                        "column": column
                    })
                else:
                    parts = []
                    for ch in raw:
                        if ch == "\t":
                            parts.append("Tab")
                        elif ch == " ":
                            parts.append("␣")
                        else:
                            parts.append(ch)
                    visible = " ".join(parts)
                    push({
                        "type": "WHITESPACE",
                        "lexeme": visible,
                        "line": line,
                        "column": column
                    })
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            push({"type": tok_type, "lexeme": raw, "line": line, "column": column})
            pos += len(raw)
            column += len(raw)
            match_found = True
            break

        if not match_found:
            push({"type": "ERROR", "lexeme": code[pos], "line": line, "column": column})
            pos += 1
            column += 1

    return tokens