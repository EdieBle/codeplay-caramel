class UnexpectedError():
    def __init__(self, line: str, position: tuple[int, int]):
        self._line = line.replace('\n', '')
        self._position = position

    def __str__(self):
        error_message = f"\n{self._position[0]:<5}|{self._line}\n" \
                        f"     |{' '*(self._position[1]-1)}^\n"
        return error_message

if __name__ == '__main__':
    line = '      serve("Hello, World"); #'
    position = (6, 29)
    print(UnexpectedError(line, position))