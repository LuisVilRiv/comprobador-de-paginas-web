import logging
import logging.handlers
from config import settings


def setup_logger(name: str) -> logging.Logger:
    """
    Devuelve un logger configurado con el nombre indicado.
    Aplica la configuración definida en settings.py.
    Se puede llamar desde cualquier módulo del proyecto.

    Uso:
        from config.logging_config import setup_logger
        logger = setup_logger(__name__)
        logger.info("Mensaje")
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Handler de consola (siempre activo)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler de fichero (opcional, configurable en settings)
    if settings.LOG_TO_FILE:
        settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB por fichero
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger