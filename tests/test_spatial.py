import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.spatial import polygon_to_anchor, detect_columns, group_by_lines


def test_polygon_to_anchor():
    poly = [(10, 20), (100, 20), (100, 60), (10, 60)]
    y, x = polygon_to_anchor(poly)
    assert y == 20 and x == 10, f"top_left fail: ({y}, {x})"
    print("  [OK] polygon_to_anchor top_left")

    y, x = polygon_to_anchor(poly, mode="center")
    assert y == 40 and x == 55, f"center fail: ({y}, {x})"
    print("  [OK] polygon_to_anchor center")

    y, x = polygon_to_anchor(poly, mode="baseline")
    assert y == 60, f"baseline y fail: {y}"
    print("  [OK] polygon_to_anchor baseline")

    y, x = polygon_to_anchor([], mode="top_left")
    assert y == 0 and x == 0, f"empty polygon fail: ({y}, {x})"
    print("  [OK] polygon_to_anchor empty")


def test_detect_columns_single():
    items = [(10, 20, "A"), (50, 25, "B"), (100, 22, "C")]
    cols = detect_columns(items, image_width=1000)
    assert len(cols) == 1, f"Expected 1 column, got {len(cols)}"
    assert len(cols[0]) == 3
    print("  [OK] detect_columns single column")


def test_detect_columns_double():
    items = [
        (10, 20, "A"), (50, 25, "B"),
        (10, 300, "C"), (50, 305, "D")
    ]
    cols = detect_columns(items, image_width=1000)
    assert len(cols) == 2, f"Expected 2 columns, got {len(cols)}"
    print("  [OK] detect_columns double column")


def test_group_by_lines():
    items = [(10, 20, "A"), (15, 30, "B"), (100, 25, "C")]
    lines = group_by_lines(items, image_height=1000)
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"
    assert len(lines[0]) == 2
    assert len(lines[1]) == 1
    print("  [OK] group_by_lines")


def test_group_by_lines_tolerance():
    items = [(10, 20, "A"), (12, 30, "B"), (15, 40, "C"), (200, 25, "D")]
    lines = group_by_lines(items, image_height=1000)
    assert len(lines) == 2, f"Expected 2 lines, got {len(lines)}"
    print("  [OK] group_by_lines with tolerance")


if __name__ == "__main__":
    print("\n[TEST] Spatial Engine Tests\n")
    test_polygon_to_anchor()
    test_detect_columns_single()
    test_detect_columns_double()
    test_group_by_lines()
    test_group_by_lines_tolerance()
    print("\n[PASS] All spatial tests passed\n")
