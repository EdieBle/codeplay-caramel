from lark import Lark

def clean_expected(self, expected: list):
    temp = []
    for allowed in expected:
        token = allowed.lower()
        if token == 'batter': token = 'batter'
        elif token == 'backroom': token = 'backroom'
        elif token == 'equals': token = '='