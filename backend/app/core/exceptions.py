class PatternGenesisError(Exception):
    def __init__(self, code: str, message: str, suggestion: str | None = None):
        self.code = code
        self.message = message
        self.suggestion = suggestion or "Please review the input and try again."
        super().__init__(message)


class InvalidImageError(PatternGenesisError):
    def __init__(self, message: str = "Invalid image upload."):
        super().__init__("INVALID_IMAGE", message, "Upload a valid PNG, JPG, or WEBP image.")


class DotDetectionError(PatternGenesisError):
    def __init__(self, message: str = "Unable to confidently detect a dot grid."):
        super().__init__("DOT_DETECTION_FAILED", message, "Try a clearer image with higher contrast and cleaner dots.")


class GeometryError(PatternGenesisError):
    def __init__(self, message: str = "No valid geometry could be extracted."):
        super().__init__("GEOMETRY_EXTRACTION_FAILED", message, "Increase contrast or provide a cleaner pattern image.")
