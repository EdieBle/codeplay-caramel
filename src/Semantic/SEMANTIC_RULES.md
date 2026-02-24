# CARAMEL Semantic Analyzer

Comprehensive semantic analysis for the CARAMEL programming language, based on the official language specification.

## Overview

The semantic analyzer validates CARAMEL source code after lexical and syntactic analysis. It enforces the semantic rules defined in the CARAMEL specification to ensure type safety, proper scope management, and correct language usage.

## Architecture

### Core Components

#### 1. **SemanticError**
Represents a semantic error in the source code.

```python
class SemanticError:
    code: str                # Error code (E001, E002, etc.)
    message: str             # Human-readable error message
    line: int               # Source code line number
    column: int             # Source code column number
    severity: str           # "error" or "warning"
```

#### 2. **Symbol**
Represents a declaration in the source (variable, function, class, struct).

```python
class Symbol:
    name: str                    # Identifier name
    kind: str                    # "variable", "function", "class", "struct"
    dtype: str                   # Data type: "bean", "drip", "churro", "temp", "blend", "mug"
    is_constant: bool            # True if declared with 'brewed'
    scope_level: int             # Scope nesting depth
    line: int                    # Declaration line
    parameters: List             # Function parameters: [(name, type), ...]
    return_type: str             # Function return type
    is_initialized: bool         # True if value assigned
```

#### 3. **SymbolTable**
Manages scopes and symbol lookup.

Key methods:
- `push_scope()`: Enter new scope (function, class, loop, block)
- `pop_scope()`: Exit current scope
- `declare(name, symbol)`: Declare symbol in current scope
- `lookup(name)`: Find symbol in current or parent scopes
- `lookup_current(name)`: Find symbol in current scope only

#### 4. **SemanticAnalyzer**
Main analyzer implementing the AST visitor pattern. Checks semantic rules and collects errors.

## Semantic Rules

Based on CARAMEL Specification (General Rules, pages 6-9):

### Rule 1: Reserved Words & Identifiers
- Reserved words must be lowercase and cannot be used as identifiers
- Identifiers must start with lowercase letter
- Identifiers: 1-15 characters, alphanumeric + underscore only
- Cannot be reserved words

**Error Code: E001 (for reserved word violations)**

### Rule 2: Duplicate Declarations (General Rule 2)
**Error Code: E001 - Redefinition of identifier**

A redefinition error occurs when an identifier is declared more than once in the same scope.

```caramel
bean count = 5;
bean count = 10;  // ERROR: E001 - Redefinition
```

**Analyzer Behavior:**
- Tracks all declared symbols per scope
- Rejects duplicate declarations in same scope
- Allows symbol shadowing in nested scopes

### Rule 3: Single Main Function (General Rule 4)
**Error Codes:**
- **E007** - Missing main function
- **E008** - Multiple main functions

A CARAMEL program must have exactly ONE main function: `bean cup() { ... }`

```caramel
bean cup() {
    // Body must exist
    refill? 0;
}
```

**Analyzer Behavior:**
- Tracks main function count
- Reports error if no main function
- Reports error if multiple main functions

### Rule 4: Type Safety (General Rule 5)
**Error Code: E003 - Type mismatch**
**Error Code: E002 - Undeclared identifier**

Variables must be declared with a data type before use.

```caramel
bean total;          // OK - declared
total = 5;           // OK
result = 10;         // ERROR: E002 - Undeclared identifier
```

### Rule 5: Constant Immutability (General Rule 8)
**Error Code: E005 - Constant modification**

Constants declared with `brewed` cannot be changed after initialization.

```caramel
brewed bean limit = 100;
limit = 50;  // ERROR: E005 - Cannot modify constant
```

### Rule 6: Global Declarations (General Rule 7)
**Error Code: E001 - Redefinition**

Global declarations must appear before the main function. Multiple globals are allowed.

```caramel
bean global_var = 10;  // OK - must be before cup()

bean cup() {
    // global_var is accessible here
}
```

### Rule 7: Function Definition (General Rule 12)
**Error Code: E001 - Redefinition**

Functions must be defined before main and cannot be defined inside other functions.

```caramel
recipe bean double(bean x) {
    refill(x * 2);
}

bean cup() {
    bean result = double(5);
    refill? 0;
}
```

### Rule 8: Function Parameters & Arguments (General Rule 13)
**Error Code: E003 - Parameter count mismatch**
**Error Code: E010 - Type incompatibility**

Function calls must provide arguments matching parameter count and types.

```caramel
recipe bean add(bean a, bean b) {
    refill(a + b);
}

bean cup() {
    bean sum = add(5, 3);     // OK
    bean err = add(5);         // ERROR: argument count mismatch
    refill? 0;
}
```

### Rule 9: Class Definitions (General Rule 14)
**Error Code: E001 - Redefinition**

Classes can contain access modifiers, functions, and members. Cannot be nested.

```caramel
crema MyClass {
    cafe bean publicMember;
    backroom bean privateMember;
}

bean cup() {
    new obj = MyClass;
    refill? 0;
}
```

### Rule 10: Operator Type Compatibility (General Rule 21)
**Error Code: E010 - Type incompatibility**

Operators require compatible operand types.

```caramel
bean a = 5;
drip b = 3.14;
temp result1 = a + b;      // OK - bean + drip
temp result2 = a && b;     // ERROR: E010 - && requires temp operands
```

Supported operations:
- **Arithmetic** (+, -, *, /, %): bean/drip operands → bean/drip result
- **Relational** (>, <, ==, !=, >=, <=): numeric operands → temp result
- **Logical** (&&, ||): temp operands → temp result

### Rule 11: Implicit Type Conversion (Variables Rule 5)
**Error Code: E004 - Invalid type conversion**

Type conversions follow the implicit conversion table (from specification):
- bean → drip, temp (allowed)
- drip → bean (with potential loss), drip (allowed)
- temp, churro, blend → only compatible types
- mug → mug only

```caramel
bean x = 5;
drip y = x;      // OK - bean to drip allowed
bean z = y;      // WARNING - drip to bean (loss of precision)
```

### Rule 12: Loop Control Statements (General Rule 23-24)
**Error Code: E006 - Control statement outside loop**

`snap` (break) and `skip` (continue) can only appear inside loops.

```caramel
pour(bean i = 0; i < 10; i++) {
    if (i == 5) {
        snap;  // OK - inside loop
    }
}

snap;  // ERROR: E006 - outside loop
```

### Rule 13: Array Type Consistency (General Rule 16)
**Error Code: E003 - Type mismatch**

Array elements must follow the declared data type.

```caramel
bean nums[5] = [1, 2, 3, 4, 5];  // OK
bean vals[3] = [1, 2.5, 3];       // ERROR: E003 - drip in bean array
```

### Rule 14: Expression Statements (General Rule 19)
**Error Code: E006 - Invalid statement**

Standalone expressions must be unary or valid statements (not binary operations).

```caramel
5 + 3;           // ERROR - standalone expression not allowed
x++;             // OK - unary expression
count = count + 1;  // OK - assignment statement
```

### Rule 15: Scope Management
Scopes are created for:
- Global scope (top level)
- Function bodies (recipe, empty)
- Class bodies (crema)
- Loop bodies (pour, whilehot, tastetill)
- Conditional blocks (ifbrew, elspress)

Variables in nested scopes can shadow parent scope variables.

```caramel
bean x = 10;     // Global x

bean cup() {
    bean x = 20;  // Local x (shadows global)
    // Local x = 20 inside cup()
    refill? 0;
}
```

## Data Type Rules (from specification pages 15-18)

### Bean (Integer)
- Range: 0 to 9999999999
- Can contain: bean, drip (with conversion), temp
- Cannot contain: floats, hex/octal/binary, commas, quotes
- Default: 0

### Drip (Float)
- Range: ±9999999999.9999999999 (10-digit decimal accuracy)
- Can contain: bean, drip
- Cannot contain: commas, incomplete values (.5, 0.), hex/octal/binary
- Default: 0.0

### Temp (Boolean)
- Values: hot (true), cold (false)
- Default: cold (false)
- Can hold: temp values only

### Churro (Character)
- Single ASCII character or escape sequence
- Must be in single quotes: 'a'
- Can hold: churro values only
- Default: ''

### Blend (String)
- Sequence of characters
- Must be in double quotes: "hello"
- Can hold: blend values only
- Default: ""

### Mug (Struct)
- Groups variables of different types
- Members accessed with dot (.)
- Cannot contain other mug types
- Default: empty mug

## Error Codes Reference

| Code | Error | Rule | Severity |
|------|-------|------|----------|
| E001 | Redefinition of identifier | 2, 7, 12, 14 | Error |
| E002 | Undeclared identifier | 4, 5 | Error |
| E003 | Type mismatch | 4, 13 | Error |
| E004 | Invalid type conversion | 11 | Error |
| E005 | Constant modification | 5 | Error |
| E006 | Invalid operation/statement | 12, 14 | Error |
| E007 | Missing main function | 3 | Error |
| E008 | Multiple main functions | 3 | Error |
| E009 | Type cast not allowed | - | Error |
| E010 | Operator type incompatibility | 10 | Error |

## Usage

### Basic Usage

```python
from src.Semantic import run_semantic_analysis

# After successful parsing
ast = parser.parse()

# Run semantic analysis
errors = run_semantic_analysis(ast)

# Print errors
for error in errors:
    print(f"[{error['code']}] Line {error['line']}: {error['message']}")
```

### Advanced Usage

```python
from src.Semantic import SemanticAnalyzer

analyzer = SemanticAnalyzer(ast)
errors = analyzer.analyze()

# Analyzer tracks:
# - Current function context
# - Current class context
# - Loop nesting level
# - Symbol table with scope stack
```

## Examples

### Example 1: Duplicate Declaration
```caramel
bean count = 5;
bean count = 10;  // ERROR: E001 - Redefinition
```
**Error**: E001 - Redefinition of identifier 'count'

### Example 2: Undeclared Variable
```caramel
bean cup() {
    x = 10;       // ERROR: E002 - x not declared
    refill? 0;
}
```
**Error**: E002 - Undeclared identifier 'x'

### Example 3: Missing Main
```caramel
recipe bean add(bean a, bean b) {
    refill(a + b);
}
// No bean cup() function
```
**Error**: E007 - Missing main function

### Example 4: Control Statement Outside Loop
```caramel
bean cup() {
    snap;         // ERROR: E006 - outside loop
    refill? 0;
}
```
**Error**: E006 - 'snap' statement outside of loop

### Example 5: Valid Code
```caramel
recipe bean multiply(bean x, bean y) {
    refill(x * y);
}

bean cup() {
    bean a = 5;
    bean b = 3;
    bean product = multiply(a, b);
    glaze(product);
    refill? 0;
}
```
**No errors** - All semantic rules satisfied

## Integration with Parser

The semantic analyzer can be independently used without modifying the parser:

```python
from src.Parser.parser import Parser
from src.Semantic import run_semantic_analysis

code = "... caramel source ..."

# Parse
parser = Parser(code)
parser.start()

if parser.errors:
    print("Syntax errors found")
else:
    # Run semantic analysis
    semantic_errors = run_semantic_analysis(parser.ast)
    
    if semantic_errors:
        print("Semantic errors found")
    else:
        print("Code is valid!")
```

## Future Enhancements

1. **Type Checking for Binary Operations** - Full validation of operator compatibility
2. **Return Statement Validation** - Ensure all code paths return correct types
3. **Array Dimension Tracking** - Validate multi-dimensional array access
4. **Member Access Validation** - Check class member existence and access modifiers
5. **Unreachable Code Detection** - Warn about dead code
6. **Constant Initialization Tracking** - Ensure constants are initialized before use
7. **Function Call Validation** - Verify function arguments match parameters
