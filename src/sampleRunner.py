from src.Parser import parser      
from src.Semantic.analyzer import SemanticAnalyzer

source_code = """
bean cup() [
    bean x = 5
    drip val = 4.5
    refill? 0
]
"""

p = parser(source_code)
p.start()

if p.errors:
    print("Parse errors found:")
    for err in p.errors:
        print(err)
else:
    analyzer = SemanticAnalyzer(p.ast)
    errors = analyzer.analyze()

    if errors:
        print("Semantic errors found:")
        for err in errors:
            print(err)
    else:
        print("No semantic errors.")