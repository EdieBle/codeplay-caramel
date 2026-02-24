# Frontend Integration - Quick Start

## What Changed?

✅ **New**: Semantic analyzer is now integrated into the compiler pipeline
✅ **New**: Third error tab displays semantic errors  
✅ **Updated**: Backend server runs semantic analysis after parsing
✅ **No Breaking Changes**: All existing functionality preserved

## Starting the Application

### Terminal 1: Start Backend Server

```bash
cd "c:\Users\Diamo\OneDrive\Documents\GitHub\Feb 23\CodePlay_Staging"
python -m flask --app src.server run --port 5000
```

**Server starts on**: http://127.0.0.1:5000

**Endpoints**:
- POST `/tokenize` - Lexical analysis
- POST `/parse` - Parsing + Semantic analysis

### Terminal 2: Start Frontend

```bash
cd "c:\Users\Diamo\OneDrive\Documents\GitHub\Feb 23\CodePlay_Staging"
npm run dev
```

**Frontend starts on**: http://localhost:5173 (or similar)

## Using the Semantic Tab

### New Workflow

1. **Type CARAMEL code** in the editor
2. **Click "Tokenize & Parse"** button
3. **View errors in three tabs**:
   - **Lexer Errors**: Tokenization issues
   - **Parser/Syntax Errors**: Grammar violations
   - **Semantic Errors** ← NEW: Type/scope violations

### Example Code to Test

```caramel
recipe bean add(bean a, bean b) {
    refill(a + b);
}

bean count = 10;
bean count = 20;  // ERROR: E001 Redefinition

bean cup() {
    x = 5;        // ERROR: E002 Undeclared
    snap;         // ERROR: E006 Outside loop
    refill? 0;
}
```

**Expected Results**:
- ✅ No lexer errors
- ✅ No syntax errors
- ❌ 3 semantic errors in Semantic tab

## Files to Review

| File | Purpose |
|------|---------|
| `src/server.py` | Backend server with semantic integration |
| `src/components/SemanticError.jsx` | Error display component |
| `src/components/ErrorTabs.jsx` | Tab navigation |
| `src/Semantic/analyzer.py` | Core semantic analyzer |
| `src/SEMANTIC_INTEGRATION.md` | Full integration documentation |

## Common Semantic Errors

| Code | Meaning | Example |
|------|---------|---------|
| E001 | Duplicate declaration | `bean x = 1; bean x = 2;` |
| E002 | Undeclared variable | `y = 5;` (y not declared) |
| E007 | Missing main function | No `bean cup()` |
| E006 | Control outside loop | `snap;` outside loop |

See `src/Semantic/SEMANTIC_RULES.md` for complete reference.

## Troubleshooting

### Backend Error: "ModuleNotFoundError: src.Semantic"
- Ensure you're in the correct directory
- Check venv is activated
- Try: `pip install -e "C:\...\CodePlay_Staging"`

### Frontend: "Cannot reach backend"
- Verify Flask server is running on port 5000
- Check no firewall blocking localhost:5000

### No Semantic Tab Showing
- Make sure code has no syntax errors first
- Check browser console (F12) for JavaScript errors

## Next Steps

- ✅ Backend integrated
- ✅ Frontend components created  
- ✅ Error tabs updated
- ➡️ Run the application
- ➡️ Test with sample code
- ➡️ Review error messages

## Support

For detailed information:
- Semantic rules: `src/Semantic/SEMANTIC_RULES.md`
- Integration details: `src/SEMANTIC_INTEGRATION.md`
- Code examples: `src/Semantic/examples.py`
- Quick reference: `src/Semantic/QUICKSTART.md`
