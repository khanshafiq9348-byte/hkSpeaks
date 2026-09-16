from fastapi import HTTPException, status

class ErrorCode:
    AUTH_REQUIRED = "AUTH_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    VOICE_NOT_FOUND = "VOICE_NOT_FOUND"
    VOICE_NOT_AVAILABLE = "VOICE_NOT_AVAILABLE"
    PREMIUM_REQUIRED = "PREMIUM_REQUIRED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_TEXT = "INVALID_TEXT"
    TEXT_TOO_LONG = "TEXT_TOO_LONG"
    GENERATION_FAILED = "GENERATION_FAILED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    AUDIO_PROCESSING_FAILED = "AUDIO_PROCESSING_FAILED"
    CLONE_UPLOAD_INVALID = "CLONE_UPLOAD_INVALID"
    CLONE_NOT_AUTHORIZED = "CLONE_NOT_AUTHORIZED"
    CLONE_FAILED = "CLONE_FAILED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: dict = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "code": error_code,
                "message": message,
                "details": details or {}
            }
        )
