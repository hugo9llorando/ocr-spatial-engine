#!/usr/bin/env python3
"""Live Verify -- Integration test. Creates image, runs OCR, checks output."""

import sys
import os
import json
import tempfile
import shutil
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.spatial import polygon_to_anchor, detect_columns, group_by_lines


def create_test_image(path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[SKIP] Pillow not available")
        return False

    img = Image.new("RGB", (600, 200), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except (OSError, IOError):
        font = ImageFont.load_default()

    draw.text((20, 20), "Titulo: Informe", fill="black", font=font)
    draw.text((20, 60), "Columna 1: Datos A", fill="black", font=font)
    draw.text((300, 60), "Columna 2: Datos B", fill="black", font=font)
    draw.text((20, 100), "Python 3.14", fill="black", font=font)
    draw.text((300, 100), "OCR Testing", fill="black", font=font)
    draw.text((20, 140), "Resultado: OK", fill="black", font=font)
    img.save(path)
    return True


def test_ocr_engine():
    print("\n[LIVE] Live Verification -- OCR Spatial Engine\n")

    test_dir = tempfile.mkdtemp(prefix="ocr_test_")
    test_img = os.path.join(test_dir, "test_live.png")

    if not create_test_image(test_img):
        print("  [!] Could not create test image (PIL missing)")
        return False

    print(f"  [OK] Test image: {test_img}")

    from engine.ocr import run_paddleocr, get_image_dimensions, CONFIG, load_config
    load_config()

    print("  Running OCR...")
    success, data = run_paddleocr(test_img)

    if not success:
        print(f"  [FAIL] OCR failed: {data.get('error', 'unknown')}")
        return False

    texts = data.get("texts", [])
    print(f"  [OK] OCR done: {len(texts)} texts extracted")

    if len(texts) < 3:
        print(f"  [!] Few texts detected ({len(texts)}), OCR quality may be low")
    else:
        print("  [OK] Text count acceptable")

    polygons = data.get("polygons", [])
    text_positions = []
    for i, text in enumerate(texts):
        y, x = polygon_to_anchor(polygons[i]) if i < len(polygons) else (i * 50, 0)
        text_positions.append((y, x, text))
    text_positions = [t for t in text_positions if t[2]]

    dimensions = get_image_dimensions(test_img)
    img_width, img_height = dimensions if dimensions else (None, None)

    if len(text_positions) > 3:
        columns = detect_columns(text_positions, img_width, CONFIG)
    else:
        columns = [sorted(text_positions, key=lambda t: (t[0], t[1]))]

    print(f"  [OK] Columns detected: {len(columns)}")

    from engine.export import format_text_output, format_json_output, format_csv_output
    text_output = format_text_output(columns)
    json_output = format_json_output(columns, data)
    csv_output = format_csv_output(columns)

    print("\n  === TEXT OUTPUT ===")
    for line in text_output.split("\n"):
        print(f"  | {line}")

    assert isinstance(text_output, str), "text_output must be str"
    assert isinstance(json_output, dict), "json_output must be dict"
    assert "columns" in json_output, "json_output must have 'columns' key"
    assert isinstance(csv_output, str), "csv_output must be str"

    print("\n  [OK] TXT format valid")
    print("  [OK] JSON format valid")
    print("  [OK] CSV format valid")

    shutil.rmtree(test_dir, ignore_errors=True)
    print("\n[PASS] LIVE VERIFY PASSED\n")
    return True


if __name__ == "__main__":
    success = test_ocr_engine()
    sys.exit(0 if success else 1)
