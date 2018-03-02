class CompileError(BaseException):

    def __init__(self, error_message):
        self.error = error_message


class RuntimeError(BaseException):
    pass
