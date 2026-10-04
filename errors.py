class HubError(Exception):
    def __init__(self, code, message, source="local", status=503, retryable=False, retry_after=None):
        super().__init__(message)
        self.code, self.message, self.source = code, message, source
        self.status, self.retryable = status, retryable
        self.retry_after = retry_after

    def payload(self):
        return {"error": {"code": self.code, "message": self.message,
                          "source": self.source, "retryable": self.retryable,
                          "retry_after_seconds": self.retry_after}}
