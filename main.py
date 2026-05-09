#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spatial OCR Engine — Entry Point
Procesa imágenes con PaddleOCR y ordena según disposición espacial.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from engine.ocr import logger, CONFIG, load_config
from engine.processor import run_ocr_pipeline
from engine.export import (
    format_text_output, format_json_output,
    format_csv_output, format_markdown_output, export_results
)
from services.watcher import start_file_watcher


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(
        description="OCR espacial con soporte multi-columna",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ejemplos:\n"
            "  main.py                     # Procesar imagen más reciente\n"
            "  main.py img.jpg             # Archivo específico\n"
            "  main.py -i img.png --watch   # Vigilancia continua\n"
            "  main.py --batch ./fotos      # Procesar todo un directorio\n"
        )
    )
    parser.add_argument("image", nargs="?", help="Ruta a la imagen")
    parser.add_argument("-i", "--input", dest="image_alt", help="Ruta alternativa")
    parser.add_argument("-m", "--mode", choices=["columns", "rows"], default="columns")
    parser.add_argument("--no-columns", action="store_true")
    parser.add_argument("-e", "--export", choices=["txt", "json", "csv", "md", "all", "none"], default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-w", "--watch", action="store_true")
    parser.add_argument("--batch", metavar="DIR", help="Procesar todas las imágenes en un directorio")
    parser.add_argument("--debug", action="store_true", help="Mostrar información detallada de posición")
    parser.add_argument("-g", "--gemini", action="store_true", help="Enriquecer con Gemini Vision (descripción contextual)")
    return parser.parse_args()


def print_debug(result: dict) -> None:
    print("\n[DEBUG]")
    for i, (y, x, text) in enumerate(result.get("raw_positions", [])):
        print(f"  [{i}] y={y:4d} x={x:4d}  \"{text}\"")
    print(f"  Columnas detectadas: {len(result.get('columns', []))}")


def process_image(image_path: str, multi_column: bool = True, read_mode: str = "columns", debug: bool = False) -> str | None:
    result = run_ocr_pipeline(image_path, multi_column, read_mode)
    if result is None:
        return None

    print("[OCR RESULT]")
    print(result["text_output"])

    if debug:
        print_debug(result)

    return result["text_output"]


def process_and_export(image_path: str, args) -> str | None:
    multi_column = not args.no_columns
    result = run_ocr_pipeline(image_path, multi_column, args.mode)
    if result is None:
        return None

    print("[OCR RESULT]")
    print(result["text_output"])

    if args.debug:
        print_debug(result)

    if args.gemini:
        prompt = CONFIG.get("gemini_prompt")
        from engine.enrichment import enrich_image
        enrichment = enrich_image(image_path, prompt=prompt)
        if enrichment["success"]:
            print(f"\n[GEMINI VISION] ({enrichment['model']} - {enrichment['elapsed_ms']}ms)")
            print(enrichment["description"])
        elif enrichment["error"]:
            print(f"\n[GEMINI VISION] Error: {enrichment['error']}")

    if args.export and args.export != "none":
        base = os.path.splitext(image_path)[0]
        formats = ["txt", "json", "csv", "md"] if args.export == "all" else [args.export]
        md_output = format_markdown_output(result["columns"], os.path.basename(image_path))
        export_results(
            result["text_output"], result["json_output"],
            result["csv_output"], base, formats,
            markdown_output=md_output,
        )

    return result["text_output"]


def main():
    if sys.platform == "win32":
        import io
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    args = parse_args()

    if args.watch:
        logger.info("Modo vigilancia")
        start_file_watcher()
        return

    if args.batch:
        import glob as _glob
        dir_path = args.batch
        if not os.path.isdir(dir_path):
            logger.error("Directorio no encontrado: %s", dir_path)
            sys.exit(1)

        exts = CONFIG.get("watch_extensions", [".jpg", ".jpeg", ".png", ".webp"])
        images = []
        for ext in exts:
            images.extend(_glob.glob(os.path.join(dir_path, f"*{ext}")))
            images.extend(_glob.glob(os.path.join(dir_path, f"*{ext.upper()}")))
        images.sort(key=os.path.getmtime)

        if not images:
            logger.info("No se encontraron imágenes en %s", dir_path)
            return

        logger.info("Procesando %d imagen(es) en %s", len(images), dir_path)
        ok = 0
        for img in images:
            logger.info("Procesando: %s", os.path.basename(img))
            if process_and_export(img, args) is not None:
                ok += 1
        logger.info("Completado: %d/%d exitosos", ok, len(images))
        return

    image_path = args.image or args.image_alt
    if not image_path:
        import glob as _glob
        temp_dir = CONFIG.get("temp_dir", "")
        if os.path.exists(temp_dir):
            exts = CONFIG.get("watch_extensions", [".jpg", ".jpeg", ".png", ".webp"])
            candidates = []
            for ext in exts:
                candidates.extend(_glob.glob(os.path.join(temp_dir, f"*{ext}")))
                candidates.extend(_glob.glob(os.path.join(temp_dir, f"*{ext.upper()}")))
            if candidates:
                image_path = max(candidates, key=os.path.getmtime)
                logger.info("Usando imagen más reciente: %s", os.path.basename(image_path))
        if not image_path:
            logger.error("No se encontraron imágenes para procesar")
            sys.exit(1)

    if not os.path.exists(image_path):
        logger.error("Archivo no encontrado: %s", image_path)
        sys.exit(1)

    result = process_and_export(image_path, args)
    sys.exit(0 if result is not None else 1)


if __name__ == "__main__":
    main()
