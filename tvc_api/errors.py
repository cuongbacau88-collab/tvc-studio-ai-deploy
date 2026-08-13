"""Stable API errors shared by validation, registry, and workers."""


class APIError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status

    def as_dict(self) -> dict[str, object]:
        return {"error": {"code": self.code, "message": self.message}}


UNAVAILABLE_GPU = "unavailable_insufficient_gpu"

