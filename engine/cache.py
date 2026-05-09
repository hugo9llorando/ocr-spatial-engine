import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger("ocr_spatial")


class OcrCache:
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except OSError as e:
            logger.warning("No se pudo crear directorio de cache: %s", e)

    def _make_key(self, image_path: str) -> Optional[str]:
        try:
            stat = os.stat(image_path)
            raw = f"{image_path}:{stat.st_size}:{stat.st_mtime_ns}"
            return hashlib.sha256(raw.encode()).hexdigest()[:16]
        except OSError:
            return None

    def get(self, image_path: str) -> Optional[dict]:
        key = self._make_key(image_path)
        if not key:
            return None
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if not os.path.exists(cache_file):
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.debug("Error leyendo cache: %s", e)
            return None

    def set(self, image_path: str, data: dict) -> None:
        key = self._make_key(image_path)
        if not key:
            return
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.warning("No se pudo escribir cache: %s", e)
