"""
================================================================================
CONFIG/__INIT__.PY - Paquete de Configuración del Proyecto
================================================================================

DESCRIPCIÓN:
Este paquete contiene todos los módulos de configuración del sistema de auditoría
web, incluyendo ajustes generales, configuración de logging y parámetros del sistema.

MÓDULOS:
- settings: Configuración principal y variables de entorno
- logging_config: Configuración del sistema de logs

@version 1.0.0
@author Web Auditor Team
@since 2024
"""

from .logging_config import setup_logging

__all__ = ["setup_logging"]
