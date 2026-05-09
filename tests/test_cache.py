import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.cache import OcrCache


def test_cache_miss(tmp_path):
    cache_dir = str(tmp_path / "cache")
    cache = OcrCache(cache_dir)
    result = cache.get("nonexistent.png")
    assert result is None


def test_cache_set_and_get(tmp_path):
    image = str(tmp_path / "test.png")
    with open(image, "w") as f:
        f.write("fake image content")

    cache_dir = str(tmp_path / "cache")
    cache = OcrCache(cache_dir)

    data = {"texts": ["hola"]}
    cache.set(image, data)
    result = cache.get(image)
    assert result == data


def test_cache_corrupted_file(tmp_path):
    image = str(tmp_path / "test.png")
    with open(image, "w") as f:
        f.write("data")

    cache_dir = str(tmp_path / "cache")
    os.makedirs(cache_dir, exist_ok=True)
    bad_file = os.path.join(cache_dir, "bad.json")
    with open(bad_file, "w") as f:
        f.write("not json")

    cache = OcrCache(cache_dir)
    with open(image, "rb") as f:
        content = f.read()
    stat = os.stat(image)
    raw = f"{image}:{stat.st_size}:{stat.st_mtime_ns}"
    import hashlib
    key = hashlib.sha256(raw.encode()).hexdigest()[:16]
    os.rename(bad_file, os.path.join(cache_dir, f"{key}.json"))

    result = cache.get(image)
    assert result is None
