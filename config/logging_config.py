"""
LOGGING_CONFIG.PY - Configuración del Sistema de Logs

DESCRIPCIÓN:
Este módulo proporciona una configuración centralizada para el sistema de logging
del proyecto. Implementa logs rotativos con manejo de archivos y salida a consola.

CARACTERÍSTICAS:
- Logs con rotación automática (5MB por archivo, 3 archivos de respaldo)
- Formato personalizado configurable
- Niveles de log ajustables (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Salida simultánea a consola y archivo (opcional)

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTACIONES
# ═══════════════════════════════════════════════════════════════════════════════

import logging
import logging.handlers

# Importar configuración de settings
from config import settings

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES
# ═══════════════════════════════════════════════════════════════════════════════


def setup_logger(name: str) -> logging.Logger:
    """
    Crea y configura un logger con el nombre especificado.

    Args:
        name (str): Nombre del logger (usualmente __name__ del módulo).

    Returns:
        logging.Logger: Logger configurado con handlers de consola y archivo.

    Example:
        >>> from config.logging_config import setup_logger
        >>> logger = setup_logger(__name__)
        >>> logger.info("Inicio del proceso de auditoría")

    Note:
        - Los handlers solo se agregan si el logger no tiene handlers existentes
        - El nivel de log se obtiene de settings.LOG_LEVEL
        - El formato se obtiene de settings.LOG_FORMAT
        - La rotación de archivos previene el crecimiento ilimitado de logs
    """
    logger = logging.getLogger(name)

    # Evitar agregar handlers duplicados si el logger ya está configurado
    if logger.handlers:
        return logger

    # Configurar nivel de log (por defecto INFO si no es válido)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Crear formatter con el formato configurado
    formatter = logging.Formatter(settings.LOG_FORMAT)

    # Handler de consola (siempre activo)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler de fichero (opcional, configurable en settings)
    if settings.LOG_TO_FILE:
        # Crear directorio de logs si no existe
        settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Configurar handler rotativo (5MB por archivo, 3 archivos de respaldo)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB por fichero
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Evitar propagación a loggers padre
    logger.propagate = False
    return logger
