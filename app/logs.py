import logging
import sys
from datetime import datetime
from typing import Any


class FormatoLog(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nivel = record.levelname
        modulo = record.module
        mensaje = record.getMessage()
        return f"[{timestamp}] [{nivel}] [{modulo}] {mensaje}"


def configurar_logs() -> logging.Logger:
    logger = logging.getLogger("dental_academy")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(FormatoLog())
        logger.addHandler(handler)

    return logger


logger = configurar_logs()
