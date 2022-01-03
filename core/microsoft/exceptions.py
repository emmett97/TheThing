class MicrosoftError(Exception):
    def __init__(self,
        code: int,
        data: dict = None,
        context: dict = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.code = code
        self.data = data
        self.context = context