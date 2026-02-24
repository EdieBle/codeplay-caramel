# Quick Start Guide - CARAMEL Semantic Analyzer

## What is the Semantic Analyzer?

The semantic analyzer validates CARAMEL code for semantic correctness after parsing. It enforces language rules like:
- No duplicate declarations
- No undeclared variable usage
- Type safety and compatibility
- Proper scope management
- Loop control statements only in loops

## Installation

The semantic analyzer is already integrated into the CARAMEL compiler. No additional installation needed.

## Basic Usage

### Option 1: Using with Parser

```python
from src.Parser.parser import Parser
from src.Semantic import run_semantic_analysis

code = """
recipe bean add(bean a, bean b) {
    refill(a + b);
}

bean cup() {
    bean sum = add(5, 3);
    refill? 0;
}
"""

# Parse the code
parser = Parser(code)
parser.start()

# Check for syntax errors
if parser.errors:
    print("Syntax errors found:")
    for error in parser.errors:
        print(f"  {error['message']}")
else:
    # Run semantic analysis
    semantic_errors = run_semantic_analysis(parser.ast)
    
    if semantic_errors:
        print("Semantic errors found:")
        for error in semantic_errors:
            print(f"  [{error['code']}] {error['message']}")
    else:
        print("Code is valid!")
```

### Option 2: Standalone Usage

```python
from src.Semantic import SemanticAnalyzer

# Assuming you have an AST from parsing
analyzer = SemanticAnalyzer(ast)
errors = analyzer.analyze()

for error in errors:
    print(f"Line {error['line']}: {error['message']}")
```

## Common Errors

### E001: Redefinition Error
An identifier is declared more than once in the same scope.

```caramel
bean count = 5;
bean count = 10;  // ERROR: E001
```

**Fix**: Use unique names or declare in different scopes.

### E002: Undeclared Identifier
A variable is used before being declared.

```caramel
x = 10;  // ERROR: E002 - x not declared
bean x = 0;
```

**Fix**: Declare the variable first.

### E007: Missing Main Function
The program doesn't have a main function.

```caramel
recipe bean add(bean a, bean b) {
    refill(a + b);
}
// Missing bean cup()
```

**Fix**: Add a main function: `bean cup() { ... }`

### E006: Control Statement Outside Loop
`snap` or `skip` used outside a loop.

```caramel
snap;  // ERROR: E006

pour(bean i = 0; i < 10; i++) {
    snap;  // OK
}
```

**Fix**: Only use control statements inside loops.

## Data Types

| Type | Purpose | Default | Range |
|------|---------|---------|-------|
| bean | Integer | 0 | 0 to 9,999,999,999 |
| drip | Float | 0.0 | ±9999999999.9999999999 |
| temp | Boolean | cold | hot, cold |
| churro | Character | '' | Single ASCII char |
| blend | String | "" | Sequence of chars |
| mug | Struct | empty | Custom grouping |

## Operators

### Arithmetic: +, -, *, /, %
- Operands: bean, drip
- Result: bean or drip

### Relational: >, <, ==, !=, >=, <=
- Operands: bean, drip, blend
- Result: temp

### Logical: &&, ||
- Operands: temp
- Result: temp

### Unary: ++, --
- Operand: bean, drip
- Result: bean, drip

## Variable Scope

Variables are visible in current and nested scopes:

```caramel
bean global = 10;

recipe bean test() {
    bean local = 20;          // Accessible in recipe only
    
    pour(bean i = 0; i < 5; i++) {
        // global and local accessible here
        // i accessible here
    }
    
    // i not accessible here
}

// global accessible here
// local not accessible here
```

## Functions

### Non-void Function (recipe)

```caramel
recipe <return_type> <name>(<parameters>) {
    <body>
    refill(<value>);
}
```

Example:
```caramel
recipe bean double(bean x) {
    refill(x * 2);
}
```

### Void Function (empty)

```caramel
empty <name>(<parameters>) {
    <body>
    refill;
}
```

Example:
```caramel
empty printMessage(blend msg) {
    glaze(msg);
    refill;
}
```

### Main Function (cup)

```caramel
bean cup() {
    <declarations and statements>
    refill? 0;
}
```

## Classes

```caramel
crema <name> {
    <access_modifier> <type> <member>;
    <access_modifier> <function>;
}
```

Access Modifiers:
- `cafe` (public) - accessible from anywhere
- `backroom` (private) - accessible only within class

Example:
```caramel
crema Calculator {
    cafe recipe bean add(bean a, bean b) {
        refill(a + b);
    }
    
    backroom bean lastResult;
}
```

## Control Flow

### If Statement
```caramel
ifbrew (condition) {
    // statements
}
elifroth (condition) {
    // statements
}
elspress {
    // statements
}
```

### Switch Statement
```caramel
flavour (variable) {
    syrup 1:
        // statements
        snap;
    syrup 2:
        // statements
        snap;
    defoam:
        // statements
        snap;
}
```

### For Loop
```caramel
pour(bean i = 0; i < 10; i++) {
    // statements
}
```

### While Loop
```caramel
whilehot (condition) {
    // statements
}
```

### Do-While Loop
```caramel
taste {
    // statements
} till: (condition)
```

## Loop Control

```caramel
pour(bean i = 0; i < 10; i++) {
    ifbrew (i == 5) {
        snap;      // Break out of loop
    }
    
    ifbrew (i % 2 == 0) {
        skip;      // Continue to next iteration
    }
}
```

## Input/Output

### Input
```caramel
batter@ variable_name      // Read from user
batter@ variable_name ("prompt")  // With prompt
```

### Output
```caramel
glaze(expression)          // Print expression
glaze(expr1 + expr2)       // Concatenate
```

## Constants

```caramel
brewed bean limit = 100;   // Cannot be changed
limit = 50;                // ERROR: E005
```

## Running Semantic Tests

To see examples of semantic analysis:

```bash
cd src/Semantic
python examples.py
```

## Error Reporting Format

All semantic errors follow this format:

```python
{
    "type": "SEMANTIC_ERROR",
    "code": "E001",           # Error code
    "message": "Error description",
    "line": 5,                # Source line
    "column": 10,             # Source column
    "severity": "error"       # or "warning"
}
```

## Troubleshooting

### "Undeclared identifier" Error
- Make sure the variable is declared before use
- Check spelling of variable name
- Verify it's not a typo of a reserved word

### "Redefinition" Error
- Check for duplicate declarations in same scope
- Use different variable names
- Or declare in different scopes for shadowing

### "Missing main function" Error
- Your program must have exactly one `bean cup()` function
- Check it exists and is at global scope

### "Type mismatch" Error
- Verify operand types match operator requirements
- Check function parameter types match arguments
- Review implicit type conversion rules

## Complete Example

```caramel
// Global declarations
bean globalCount = 0;
brewed bean maxLimit = 100;

// Function definition
recipe bean fibonacci(bean n) {
    ifbrew (n <= 1) {
        refill(n);
    }
    
    bean prev = 0;
    bean curr = 1;
    pour(bean i = 2; i <= n; i++) {
        bean next = prev + curr;
        prev = curr;
        curr = next;
    }
    
    refill(curr);
}

// Main function
bean cup() {
    bean result = fibonacci(10);
    glaze(result);
    
    pour(bean i = 0; i < 5; i++) {
        globalCount = globalCount + 1;
    }
    
    glaze(globalCount);
    refill? 0;
}
```

## References

- Complete semantic rules: [SEMANTIC_RULES.md](SEMANTIC_RULES.md)
- Examples: [examples.py](examples.py)
- API Documentation: [analyzer.py](analyzer.py)
