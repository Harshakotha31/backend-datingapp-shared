class AppException(Exception):

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict | None = None,
        retry_after: int | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.retry_after = retry_after

        super().__init__(message)