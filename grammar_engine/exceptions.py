class GrammarEngineError(Exception):
    """Error base de la librería."""
    pass


class GrammarError(GrammarEngineError):
    """Errores relacionados con gramáticas."""
    pass


class ValidationError(GrammarEngineError):
    """Errores de validación sintáctica."""
    pass


class RuleError(GrammarEngineError):
    """Errores durante la aplicación de reglas."""
    pass


class InterpretationError(GrammarEngineError):
    """Errores semánticos."""
    pass