__all__: list[str] = []

# Enumerations
LOG_LEVEL_SILENT: int
LOG_LEVEL_FATAL: int
LOG_LEVEL_ERROR: int
LOG_LEVEL_WARNING: int
LOG_LEVEL_INFO: int
LOG_LEVEL_DEBUG: int
LOG_LEVEL_VERBOSE: int
ENUM_LOG_LEVEL_FORCE_INT: int
LogLevel = int
"""One of [LOG_LEVEL_SILENT, LOG_LEVEL_FATAL, LOG_LEVEL_ERROR, LOG_LEVEL_WARNING, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG, LOG_LEVEL_VERBOSE, ENUM_LOG_LEVEL_FORCE_INT]"""



# Functions
def getLogLevel() -> LogLevel: ...

def setLogLevel(logLevel: LogLevel) -> LogLevel: ...


