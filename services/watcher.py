import json
import os
import time
import threading
import glob
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.ocr import log, CONFIG
from engine.processor import run_ocr_pipeline
from engine.export import export_results


def load_processed_files():
    db_path = CONFIG.get("processed_files_db", "")
    try:
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                processed = set()
                for file_path in data.get("processed_files", []):
                    if os.path.exists(file_path):
                        processed.add(file_path)
                return processed
    except (json.JSONDecodeError, IOError) as e:
        log("warning", f"Error cargando procesados: {e}")
    return set()


def save_processed_files(processed):
    db_path = CONFIG.get("processed_files_db", "")
    try:
        data = {
            "processed_files": list(processed),
            "last_update": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        log("error", f"Error guardando procesados: {e}")


def flash_feedback(message, duration=0.9):
    print(f"\r{' ' * 80}\r[{time.strftime('%H:%M:%S')}] {message}", end="", flush=True)

    def clear():
        time.sleep(duration)
        print(f"\r{' ' * 80}\r", end="", flush=True)

    threading.Thread(target=clear, daemon=True).start()


def scan_for_new_images(processed):
    temp_dir = CONFIG.get("temp_dir", "")
    if not os.path.exists(temp_dir):
        return []

    extensions = CONFIG.get("watch_extensions", [".jpg", ".jpeg", ".png", ".webp"])
    all_images = []
    for ext in extensions:
        all_images.extend(glob.glob(os.path.join(temp_dir, f"*{ext}")))
        all_images.extend(glob.glob(os.path.join(temp_dir, f"*{ext.upper()}")))

    return [img for img in all_images if img not in processed]


def process_image_file(image_path, processed):
    try:
        flash_feedback(f"Procesando: {os.path.basename(image_path)}")

        result = run_ocr_pipeline(image_path)
        if result is None:
            flash_feedback(f"✗ Falló OCR en: {os.path.basename(image_path)}", 2.0)
            return

        if not result["columns"]:
            flash_feedback(f"✗ Sin texto en: {os.path.basename(image_path)}", 2.0)
            return

        print("\n[OCR RESULT]")
        print(result["text_output"])

        processed.add(image_path)
        save_processed_files(processed)
        flash_feedback(f"✓ Completado: {os.path.basename(image_path)}")

    except Exception as e:
        log("error", f"Error procesando {image_path}: {e}")
        flash_feedback(f"✗ Error: {str(e)[:50]}", 2.0)


def start_file_watcher(process_callback=None):
    processed = load_processed_files()

    log("info", "Escaneo inicial...")
    initial = scan_for_new_images(processed)
    log("info", f"Encontradas {len(initial)} imagen(es) nueva(s)")
    for img in initial:
        process_image_file(img, processed)

    log("info", f"Vigilancia activa (cada {CONFIG.get('watch_interval', 5)}s)...")
    flash_feedback(f"Esperando imágenes en {CONFIG.get('temp_dir', '')}")

    try:
        while True:
            new_images = scan_for_new_images(processed)
            for img in new_images:
                process_image_file(img, processed)
            time.sleep(CONFIG.get("watch_interval", 5))
    except KeyboardInterrupt:
        log("info", "Vigilancia detenida")
    except Exception as e:
        log("error", f"Error en vigilancia: {e}")
