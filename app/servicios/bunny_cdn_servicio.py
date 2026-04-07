import requests
import os
from typing import Optional, Dict, Any
from app.logs import logger
from app.config import obtener_configuracion

config = obtener_configuracion()


class BunnyCDNServicio:
    """Servicio para gestionar archivos en Bunny CDN (Storage)"""

    STORAGE_HOST = "storage.bunnycdn.com"

    def __init__(self, api_key: str = None, storage_zone: str = None):
        self.api_key = api_key or config.BUNNY_API_KEY
        self.storage_zone = storage_zone or config.BUNNY_STORAGE_ZONE

    def _obtener_config(self) -> Optional[Dict[str, str]]:
        """Obtiene la configuración de Bunny desde la base de datos"""
        from app.database import SessionLocal
        from app.modelos import ConfiguracionBunny

        sesion = SessionLocal()
        try:
            config_bd = (
                sesion.query(ConfiguracionBunny).filter(ConfiguracionBunny.activo == True).first()
            )
            if config_bd:
                return {"api_key": config_bd.api_key, "storage_zone": config_bd.storage_zone}
        finally:
            sesion.close()
        return None

    def subir_archivo(
        self,
        nombre_archivo: str,
        contenido: bytes,
        ruta: str = "",
        tipo_contenido: str = "application/octet-stream",
    ) -> Optional[Dict[str, Any]]:
        """Sube un archivo a Bunny CDN Storage"""

        ruta_final = f"{self.storage_zone}/{ruta}".strip("/")

        url = f"https://{self.STORAGE_HOST}/{ruta_final}/{nombre_archivo}"

        headers = {"AccessKey": self.api_key, "Content-Type": tipo_contenido}

        try:
            logger.info(f"Subiendo archivo a Bunny CDN: {nombre_archivo}")

            respuesta = requests.put(url, headers=headers, data=contenido, timeout=300)

            if respuesta.status_code in [200, 201]:
                logger.info(f"Archivo subido exitosamente: {nombre_archivo}")
                return {
                    "success": True,
                    "url": f"https://{self.storage_zone}.bunnycdn.com/{ruta}/{nombre_archivo}",
                    "nombre": nombre_archivo,
                    "ruta": ruta,
                }
            else:
                logger.error(f"Error al subir archivo: {respuesta.status_code} - {respuesta.text}")
                return None
        except Exception as e:
            logger.error(f"Excepción al subir archivo: {e}")
            return None

    def eliminar_archivo(self, nombre_archivo: str, ruta: str = "") -> bool:
        """Elimina un archivo de Bunny CDN Storage"""

        ruta_final = f"{self.storage_zone}/{ruta}".strip("/")

        url = f"https://{self.STORAGE_HOST}/{ruta_final}/{nombre_archivo}"

        headers = {"AccessKey": self.api_key}

        try:
            respuesta = requests.delete(url, headers=headers, timeout=30)

            if respuesta.status_code in [200, 204]:
                logger.info(f"Archivo eliminado: {nombre_archivo}")
                return True
            else:
                logger.error(f"Error al eliminar archivo: {respuesta.status_code}")
                return False
        except Exception as e:
            logger.error(f"Excepción al eliminar archivo: {e}")
            return False

    def obtener_url_publica(self, nombre_archivo: str, ruta: str = "") -> str:
        """Obtiene la URL pública de un archivo"""
        return f"https://{self.storage_zone}.bunnycdn.com/{ruta}/{nombre_archivo}"

    def listar_archivos(self, ruta: str = "") -> Optional[list]:
        """Lista los archivos en un directorio"""

        url = f"https://{self.STORAGE_HOST}/{self.storage_zone}/{ruta}"

        headers = {"AccessKey": self.api_key, "Accept": "application/json"}

        try:
            respuesta = requests.get(url, headers=headers, timeout=30)

            if respuesta.status_code == 200:
                return respuesta.json()
            return None
        except Exception as e:
            logger.error(f"Error al listar archivos: {e}")
            return None
