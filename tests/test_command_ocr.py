import sys
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TARGET_DIR = "C:\\Users\\elcha\\Desktop\\Te doy OCR"
PYTHON = "C:\\Users\\elcha\\ocr_env312\\Scripts\\python.exe"
SCRIPT = os.path.join(os.path.dirname(__file__), "..", "main.py")

SAMPLE_TEXTS = [
    "Informe de Resultados",
    "Ventas Q1: 45000",
    "Ventas Q2: 52000",
    "Crecimiento: +15.6%",
]


def create_test_image(target_dir):
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, "_ocr_test_temp.png")

    img = Image.new("RGB", (800, 500), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 36)
        except (IOError, OSError):
            font = ImageFont.load_default()

    y = 40
    for text in SAMPLE_TEXTS:
        draw.text((40, y), text, fill="black", font=font)
        y += 80

    img.save(path)
    return path


def test_ocr_command_pipeline():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR, exist_ok=True)

    image_path = create_test_image(TARGET_DIR)
    assert os.path.exists(image_path), "No se creo la imagen de prueba"

    try:
        result = subprocess.run(
            [PYTHON, SCRIPT, image_path, "--verbose"],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
            cwd=os.path.dirname(SCRIPT),
        )

        output = result.stdout

        assert "[OCR RESULT]" in output, "No se encontro [OCR RESULT] en el output"
        assert result.returncode == 0, f"main.py retorno codigo {result.returncode}"

        found = [t for t in SAMPLE_TEXTS if t.lower().replace(" ", "").replace(":", "") in output.lower().replace(" ", "").replace(":", "")]
        print(f"Textos detectados: {len(found)}/{len(SAMPLE_TEXTS)}")

        print("\n[PASS] OCR Command Pipeline: output valido")
        print("\n--- OUTPUT ---")
        print(output)

    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


if __name__ == "__main__":
    test_ocr_command_pipeline()
