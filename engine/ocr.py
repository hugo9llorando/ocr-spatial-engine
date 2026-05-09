import json
import logging
import os
import subprocess
import sys
from typing import Any, Optional

logger = logging.getLogger("ocr_spatial")

CONFIG: dict[str, Any] = {}
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

CONFIG_SCHEMA: dict[str, dict] = {
    "temp_dir": {"type": str, "required": True},
    "paddleocr_path": {"type": str, "required": True},
    "venv_python": {"type": str, "required": False},
    "lang": {"type": str, "required": False, "default": "es"},
    "timeout_seconds": {"type": int, "required": False, "default": 120},
    "line_tolerance_ratio": {"type": float, "required": False, "default": 0.025},
    "column_tolerance_ratio": {"type": float, "required": False, "default": 0.015},
    "min_column_gap_ratio": {"type": float, "required": False, "default": 0.03},
    "export_formats": {"type": list, "required": False, "default": []},
    "watch_mode": {"type": bool, "required": False, "default": False},
    "watch_interval": {"type": (int, float), "required": False, "default": 5},
    "processed_files_db": {"type": str, "required": False, "default": ""},
    "debounce_seconds": {"type": (int, float), "required": False, "default": 2},
    "watch_extensions": {"type": list, "required": False, "default": [".jpg", ".jpeg", ".png", ".webp"]},
    "min_texts_for_columns": {"type": int, "required": False, "default": 3},
    "ocr_retries": {"type": int, "required": False, "default": 2},
}


def _check_type(value: Any, expected_type) -> bool:
    if isinstance(expected_type, tuple):
        return isinstance(value, expected_type)
    return isinstance(value, expected_type)


def load_config() -> None:
    global CONFIG
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Config no encontrado: {_CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Config inválido: {e}", file=sys.stderr)
        sys.exit(1)

    errors = []
    for key, spec in CONFIG_SCHEMA.items():
        if key in raw:
            if not _check_type(raw[key], spec["type"]):
                errors.append(f"  {key}: se esperaba {spec['type'].__name__}, se obtuvo {type(raw[key]).__name__}")
        elif spec.get("required"):
            errors.append(f"  {key}: clave obligatoria faltante")

    if errors:
        print("[ERROR] Config inválido:\n" + "\n".join(errors), file=sys.stderr)
        sys.exit(1)

    CONFIG.update(raw)
    for key, spec in CONFIG_SCHEMA.items():
        if key not in CONFIG and "default" in spec:
            CONFIG[key] = spec["default"]

    logger.info(f"Config cargado: {os.path.basename(_CONFIG_PATH)}")


def log(level: str, message: str) -> None:
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    logger.log(level_map.get(level, logging.INFO), "%s", message)


load_config()

PADDLEOCR_AVAILABLE = False
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    logger.debug("PaddleOCR disponible vía API nativa")
except ImportError:
    logger.debug("PaddleOCR no disponible nativamente, se usará CLI")


def run_paddleocr(image_path: str) -> tuple[bool, dict]:
    max_retries = CONFIG.get("ocr_retries", 2)
    for attempt in range(1, max_retries + 1):
        success, data = _run_paddleocr_once(image_path)
        if success or attempt == max_retries:
            return success, data
        logger.warning("Reintento %d/%d para %s", attempt, max_retries, os.path.basename(image_path))
    return False, {"error": "max_retries_exceeded"}


def _run_paddleocr_once(image_path: str) -> tuple[bool, dict]:
    if PADDLEOCR_AVAILABLE:
        try:
            logger.info("OCR nativo: %s", os.path.basename(image_path))
            ocr = PaddleOCR(lang=CONFIG["lang"], use_textline_orientation=True)
            result = ocr.predict(image_path)

            texts: list[str] = []
            polygons: list[list] = []
            if result and len(result) > 0:
                res_dict = result[0]
                if isinstance(res_dict, dict):
                    rec_texts = res_dict.get("rec_texts", []) or []
                    rec_polys = res_dict.get("rec_polys", []) or []

                    for i, text in enumerate(rec_texts):
                        if isinstance(text, bytes):
                            text = text.decode("utf-8", errors="replace")
                        elif not isinstance(text, str):
                            text = str(text)
                        text = text.strip()
                        if text:
                            texts.append(text)
                            poly = rec_polys[i] if i < len(rec_polys) else []
                            if hasattr(poly, "tolist"):
                                poly = poly.tolist()
                            polygons.append(poly if poly else [(0, 0), (0, 0), (0, 0), (0, 0)])

            return True, {"texts": texts, "polygons": polygons, "method": "native"}

        except Exception as e:
            logger.warning("API nativa falló, usando CLI: %s", e)

    paddleocr_path = CONFIG.get("paddleocr_path", "")
    if not os.path.isfile(paddleocr_path):
        logger.error("Ejecutable no encontrado: %s", paddleocr_path)
        return False, {"error": "executable_not_found"}

    try:
        logger.info("OCR CLI: %s", os.path.basename(image_path))
        result = subprocess.run(
            [paddleocr_path, "ocr", "-i", image_path,
             "--use_textline_orientation", "True",
             "--lang", CONFIG["lang"]],
            capture_output=True, text=True, timeout=CONFIG["timeout_seconds"],
            encoding="utf-8", errors="replace"
        )
        output = result.stdout + result.stderr
        return parse_ocr_output(output, result.returncode == 0)

    except subprocess.TimeoutExpired:
        logger.error("Timeout (%ss)", CONFIG["timeout_seconds"])
        return False, {"error": "timeout"}
    except Exception as e:
        logger.error("Error OCR: %s", e)
        return False, {"error": str(e)}


def parse_ocr_output(output: str, success: bool = True) -> tuple[bool, dict]:
    if not success:
        return False, {"error": "cli_failed"}

    from ast import literal_eval
    import re

    output = output.strip()

    try:
        data = json.loads(output)
        return _extract_from_dict(data)
    except json.JSONDecodeError:
        pass

    brace_start = output.find("{")
    if brace_start != -1:
        count = 0
        for i in range(brace_start, len(output)):
            if output[i] == "{":
                count += 1
            elif output[i] == "}":
                count -= 1
                if count == 0:
                    try:
                        data = json.loads(output[brace_start:i + 1])
                        return _extract_from_dict(data)
                    except (json.JSONDecodeError, KeyError):
                        pass
                    try:
                        data = literal_eval(output[brace_start:i + 1])
                        return _extract_from_dict(data, is_literal=True)
                    except (SyntaxError, ValueError):
                        pass
                    break

    logger.warning("No se pudo parsear output OCR")
    return False, {"texts": [], "polygons": [], "error": "parse_failed"}


def _extract_from_dict(data, is_literal=False) -> tuple[bool, dict]:
    texts: list[str] = []
    polygons: list[list] = []

    if isinstance(data, dict) and "res" in data:
        res = data["res"]
    elif isinstance(data, dict):
        res = data
    else:
        return False, {"texts": [], "polygons": [], "error": "unexpected_format"}

    rec_texts = res.get("rec_texts", []) or []
    rec_polys = res.get("rec_polys", []) or []

    for i, text in enumerate(rec_texts):
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        elif not isinstance(text, str):
            text = str(text)
        text = text.strip()
        if not text:
            continue
        texts.append(text)

        if i < len(rec_polys):
            poly = rec_polys[i]
            if hasattr(poly, "tolist"):
                poly = poly.tolist()
            if isinstance(poly, (list, tuple)) and len(poly) == 4:
                polygons.append([(int(p[0]), int(p[1])) for p in poly])
            else:
                polygons.append([(0, 0), (0, 0), (0, 0), (0, 0)])
        else:
            polygons.append([(0, 0), (0, 0), (0, 0), (0, 0)])

    return True, {"texts": texts, "polygons": polygons, "method": "parsed"}


def get_image_dimensions(image_path: str) -> Optional[tuple[int, int]]:
    try:
        from PIL import Image
        img = Image.open(image_path)
        logger.debug("Dimensiones: %dx%d", img.width, img.height)
        return img.width, img.height
    except FileNotFoundError:
        logger.warning("Archivo no encontrado: %s", image_path)
    except Exception as e:
        logger.warning("No se pudieron obtener dimensiones de %s: %s", image_path, e)
    return None
