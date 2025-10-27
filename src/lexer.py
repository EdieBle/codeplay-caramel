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

        ("KEYWORD", r"(?:tastetill|taste[ \t]+till)"),
        ("KEYWORD", r"(refill\?|batter@)"),
        ("KEYWORD", r"\b(ifbrew|elifroth|elspress|flavour|syrup|pour|whilehot|snap|skip|cup|recipe|glaze|new|defoam|empty)\b"),

        ("BOOLEAN", r"\b(hot|cold)\b"),
        ("NULL", r"\b(decaf)\b"),
        ("DECLARATION", r"\b(cupcake|local|brewed)\b"),
        ("CLASS_KEYWORD", r"\b(crema)\b"),
        ("DATA_TYPE", r"\b(bean|drip|blend|temp|churro|mug)\b"),

        ("DRIP_RAW", r"\b\d+\.\d+\b"),
        ("BEAN_RAW", r"\b\d+\b"),
        ("STRING_LIT", r'"[^"\n]*"'),
        ("CHAR_LIT", r"'[^'\n]'"),
        ("IDENTIFIER", r"\b[a-z][a-z0-9_]*\b"),
        ("OPERATOR", r"(\+{1,2}|-{1,2}|==|!=|<=|>=|&&|\|\||[+\-*/%<>=!])"),
        ("DELIMITER", r"[{}\[\](),.;]"),
        ("WHITESPACE", r"[ \t]+"),
        ("NEWLINE", r"\r?\n"),
    ]

    tokens = []
    pos = 0
    line = 1
    column = 1

    def push(tok):
        tokens.append(tok)

    while pos < len(code):
        match_found = False
        slice = code[pos:]

        for tok_type, pattern in token_specs:
            regex = re.compile(pattern)
            m = regex.match(slice)
            if not m:
                continue

            raw = m.group(0)

            # Handle newline
            if tok_type == "NEWLINE":
                push({"type": "NEWLINE", "lexeme": "↵", "line": line, "column": column})
                pos += len(raw)
                line += 1
                column = 1
                match_found = True
                break

            # Whitespace
            if tok_type == "WHITESPACE":
                visible = raw.replace("\t", "⇥").replace(" ", "␣")
                push({"type": "WHITESPACE", "lexeme": visible, "line": line, "column": column})
                pos += len(raw)
                column += len(raw)
                match_found = True
                break

            # Default token push
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
