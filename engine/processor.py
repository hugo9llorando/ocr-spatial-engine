import os
from typing import Optional

from .ocr import logger, run_paddleocr, get_image_dimensions, CONFIG
from .spatial import detect_columns, polygon_to_anchor
from .export import format_text_output, format_json_output, format_csv_output
from .cache import OcrCache

_ocr_cache: Optional[OcrCache] = None


def _get_cache() -> Optional[OcrCache]:
    global _ocr_cache
    if _ocr_cache is None:
        cache_dir = CONFIG.get("temp_dir", "")
        if cache_dir:
            _ocr_cache = OcrCache(os.path.join(cache_dir, "ocr_cache"))
    return _ocr_cache


def run_ocr_pipeline(
    image_path: str,
    multi_column: bool = True,
    read_mode: str = "columns",
) -> Optional[dict]:
    dimensions = get_image_dimensions(image_path)
    img_width, img_height = dimensions if dimensions else (None, None)

    cache = _get_cache()
    cached = cache.get(image_path) if cache else None
    if cached:
        logger.info("Cache hit: %s", os.path.basename(image_path))
        data = cached["ocr_data"]
    else:
        success, data = run_paddleocr(image_path)
        if not success:
            logger.error("OCR falló: %s", data.get("error", "unknown"))
            return None

    texts = data.get("texts", [])
    polygons = data.get("polygons", [])
    if not texts:
        logger.warning("No se detectó texto")
        return {
            "text_output": "",
            "json_output": {"metadata": data, "columns": []},
            "csv_output": "column,line,x,y,text\n",
            "columns": [],
            "metadata": data,
        }

    logger.info("Extraídos %d elemento(s)", len(texts))

    text_positions = []
    for i, text in enumerate(texts):
        y, x = polygon_to_anchor(polygons[i]) if i < len(polygons) else (i * 50, 0)
        text_positions.append((y, x, text))
    text_positions = [t for t in text_positions if t[2]]

    min_texts = CONFIG.get("min_texts_for_columns", 3)
    if multi_column and len(text_positions) >= min_texts:
        columns = detect_columns(text_positions, img_width, CONFIG)
    else:
        columns = [sorted(text_positions, key=lambda t: (t[0], t[1]))]

    result = {
        "text_output": format_text_output(columns, mode=read_mode),
        "json_output": format_json_output(columns, data),
        "csv_output": format_csv_output(columns),
        "columns": columns,
        "metadata": data,
        "raw_positions": text_positions,
    }

    if cache and not cached:
        cache.set(image_path, {"ocr_data": data})

    return result
