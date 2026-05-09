"""Enriquecimiento de imágenes mediante Gemini API.

Envía la imagen a Gemini 3 Flash Preview (o fallback)
para obtener descripción contextual de la escena.
"""

import os
import time
import logging
from typing import Optional

import cv2

from google.genai import types

logger = logging.getLogger("ocr_spatial")

_GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

_DEFAULT_PROMPT = (
    "Describe esta imagen en detalle. ¿Qué ves? "
    "Identifica objetos, personas, texto notable, escena y contexto general. "
    "Responde en español."
)

_MAX_IMAGE_BYTES = 15 * 1024 * 1024
_MAX_PIXELS = 2_000_000


def _get_api_key(api_key: Optional[str] = None) -> Optional[str]:
    return api_key or os.environ.get("GEMINI_API_KEY")


def _resize_image(image_path: str) -> tuple[bytes, str, bool]:
    size = os.path.getsize(image_path)
    mime = _guess_mime(image_path)

    if size < _MAX_IMAGE_BYTES:
        with open(image_path, "rb") as f:
            return f.read(), mime, False

    img = cv2.imread(image_path)
    if img is None:
        with open(image_path, "rb") as f:
            return f.read(), mime, False

    h, w = img.shape[:2]
    if w * h > _MAX_PIXELS:
        scale = (_MAX_PIXELS / (w * h)) ** 0.5
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.info("Imagen redimensionada: %dx%d -> %dx%d", w, h, new_w, new_h)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buf.tobytes(), "image/jpeg", True


def _guess_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {
        ".png": "image/png", ".webp": "image/webp",
        ".gif": "image/gif", ".bmp": "image/bmp",
    }.get(ext, "image/jpeg")


def enrich_image(
    image_path: str,
    prompt: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    start = time.perf_counter()
    result = {
        "success": False,
        "description": "",
        "model": "",
        "error": None,
        "elapsed_ms": 0,
    }

    key = _get_api_key(api_key)
    if not key:
        result["error"] = "GEMINI_API_KEY no configurada"
        logger.error(result["error"])
        return result

    if not os.path.isfile(image_path):
        result["error"] = f"Archivo no encontrado: {image_path}"
        logger.error(result["error"])
        return result

    try:
        image_bytes, mime_type, _ = _resize_image(image_path)
    except Exception as e:
        result["error"] = f"Error al leer imagen: {e}"
        logger.error(result["error"])
        return result

    prompt_text = prompt or _DEFAULT_PROMPT
    last_error = None

    from google import genai

    for model in _GEMINI_MODELS:
        try:
            client = genai.Client(api_key=key)

            contents = types.Content(
                role="user",
                parts=[
                    types.Part(text=prompt_text),
                    types.Part(
                        inline_data=types.Blob(
                            mime_type=mime_type,
                            data=image_bytes,
                        )
                    ),
                ],
            )

            logger.info("Enviando a Gemini (modelo: %s)...", model)
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config={"max_output_tokens": 2048},
            )

            description = response.text if response and response.text else ""
            elapsed = int((time.perf_counter() - start) * 1000)

            result.update({
                "success": True,
                "description": description.strip(),
                "model": model,
                "elapsed_ms": elapsed,
            })
            logger.info("Gemini respondió en %d ms (modelo: %s)", elapsed, model)
            return result

        except Exception as e:
            last_error = e
            logger.warning("Modelo %s falló: %s", model, e)
            continue

    elapsed = int((time.perf_counter() - start) * 1000)
    result.update({
        "error": f"Gemini no disponible: {last_error}",
        "elapsed_ms": elapsed,
    })
    logger.error("Gemini falló tras %d intento(s): %s", len(_GEMINI_MODELS), last_error)
    return result
