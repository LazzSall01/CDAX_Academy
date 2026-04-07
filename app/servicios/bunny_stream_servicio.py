import requests
import time
import json
from typing import Optional, Dict, Any
from app.logs import logger
from app.config import obtener_configuracion

config = obtener_configuracion()


class BunnyStreamServicio:
    """Servicio para gestionar videos en Bunny Stream"""

    BASE_URL = "https://video.bunnycdn.com"

    def __init__(self, api_key: str = None, library_id: str = None):
        self.api_key = api_key or config.BUNNY_API_KEY
        self.library_id = library_id or config.BUNNY_LIBRARY_ID
        self.headers = {
            "AccessKey": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

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
                return {"api_key": config_bd.api_key, "library_id": config_bd.library_id}
        finally:
            sesion.close()
        return None

    def crear_video(self, titulo: str, collection_id: str = None) -> Optional[Dict[str, Any]]:
        """Crea un objeto de video en Bunny Stream"""
        url = f"{self.BASE_URL}/library/{self.library_id}/videos"

        data = {"title": titulo}
        if collection_id:
            data["collectionId"] = collection_id

        try:
            logger.info(f"Creando video en Bunny: {titulo}")
            respuesta = requests.post(url, headers=self.headers, json=data, timeout=30)

            if respuesta.status_code == 201:
                video_data = respuesta.json()
                logger.info(f"Video creado exitosamente: {video_data.get('guid')}")
                return video_data
            else:
                logger.error(f"Error al crear video: {respuesta.status_code} - {respuesta.text}")
                return None
        except Exception as e:
            logger.error(f"Excepción al crear video: {e}")
            return None

    def subir_video(self, video_id: str, archivo_contenido: bytes) -> bool:
        """Sube el archivo de video a Bunny Stream"""
        url = f"{self.BASE_URL}/library/{self.library_id}/videos/{video_id}"

        try:
            logger.info(f"Subiendo video {video_id} a Bunny Stream...")

            headers_upload = {"AccessKey": self.api_key}

            respuesta = requests.put(
                url, headers=headers_upload, data=archivo_contenido, timeout=600
            )

            if respuesta.status_code in [200, 201]:
                logger.info(f"Video subido exitosamente: {video_id}")
                return True
            else:
                logger.error(f"Error al subir video: {respuesta.status_code} - {respuesta.text}")
                return False
        except Exception as e:
            logger.error(f"Excepción al subir video: {e}")
            return False

    def obtener_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de un video"""
        url = f"{self.BASE_URL}/library/{self.library_id}/videos/{video_id}"

        try:
            respuesta = requests.get(url, headers=self.headers, timeout=30)

            if respuesta.status_code == 200:
                return respuesta.json()
            return None
        except Exception as e:
            logger.error(f"Error al obtener video: {e}")
            return None

    def verificar_estado(self, video_id: str) -> str:
        """Verifica el estado de procesamiento de un video"""
        video = self.obtener_video(video_id)
        if video:
            if video.get("encodingProgress") == 100 and video.get("status") == 1:
                return "LISTO"
            elif video.get("status") == 2:
                return "ERROR"
            elif video.get("encodingProgress", 0) > 0:
                return "PROCESANDO"
        return "DESCONOCIDO"

    def obtener_url_reproduccion(self, video_id: str, hostname: str = None) -> Optional[str]:
        """Obtiene la URL de reproducción del video"""
        if not hostname:
            hostname = config.BUNNY_HOSTNAME

        return f"https://{hostname}/videos/{video_id}"

    def obtener_thumbnail(self, video_id: str, hostname: str = None) -> Optional[str]:
        """Obtiene la URL del thumbnail del video"""
        if not hostname:
            hostname = config.BUNNY_HOSTNAME

        return f"https://{hostname}/thumbs/{video_id}.jpg"

    def eliminar_video(self, video_id: str) -> bool:
        """Elimina un video de Bunny Stream"""
        url = f"{self.BASE_URL}/library/{self.library_id}/videos/{video_id}"

        try:
            respuesta = requests.delete(url, headers=self.headers, timeout=30)

            if respuesta.status_code in [200, 204]:
                logger.info(f"Video eliminado: {video_id}")
                return True
            else:
                logger.error(f"Error al eliminar video: {respuesta.status_code}")
                return False
        except Exception as e:
            logger.error(f"Excepción al eliminar video: {e}")
            return False

    def esperar_procesamiento(self, video_id: str, timeout: int = 300) -> bool:
        """Espera hasta que el video esté listo"""
        intervalo = 5
        tiempo_esperado = 0

        while tiempo_esperado < timeout:
            estado = self.verificar_estado(video_id)
            logger.info(f"Estado del video {video_id}: {estado}")

            if estado == "LISTO":
                return True
            elif estado == "ERROR":
                return False

            time.sleep(intervalo)
            tiempo_esperado += intervalo

        logger.warning(f"Timeout esperando procesamiento del video {video_id}")
        return False
