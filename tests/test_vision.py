import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from engine.vision import analyze_image, describe_vision, _age_to_range


def test_analyze_empty_image():
    from PIL import Image
    img = Image.new("RGB", (50, 50), "black")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f.name)
        path = f.name
    try:
        result = analyze_image(path)
        assert "image_size" in result
        assert result["error"] is None
        assert isinstance(result["faces_detected"], int)
        assert isinstance(describe_vision(result), str)
    finally:
        os.remove(path)


def test_age_to_range():
    assert _age_to_range(None) == "desconocido"
    assert _age_to_range(2) == "0-2"
    assert _age_to_range(5) == "4-6"
    assert _age_to_range(10) == "8-12"
    assert _age_to_range(20) == "15-24"
    assert _age_to_range(30) == "25-37"
    assert _age_to_range(42) == "38-47"
    assert _age_to_range(55) == "48-59"
    assert _age_to_range(65) == "60+"


def test_invalid_path():
    result = analyze_image("nonexistent.jpg")
    assert result["error"] is not None
    assert result["faces_detected"] == 0
