class SsCdfError(Exception):
    pass


class SsCdfVersionError(SsCdfError):
    pass


class SsCdfValidationError(SsCdfError):
    pass


class SsCdfReadError(SsCdfError):
    pass


class SsCdfWriteError(SsCdfError):
    pass
