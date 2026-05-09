import statistics
from typing import List, Optional, Tuple


def polygon_to_anchor(polygon, mode: str = "top_left") -> Tuple[int, int]:
    if not polygon or len(polygon) < 4:
        return (0, 0)

    if mode == "top_left":
        min_y = min(p[1] for p in polygon)
        candidates = [p for p in polygon if p[1] <= min_y + 2]
        min_x = min(p[0] for p in candidates)
        return (min_y, min_x)

    elif mode == "center":
        cx = sum(p[0] for p in polygon) // len(polygon)
        cy = sum(p[1] for p in polygon) // len(polygon)
        return (cy, cx)

    elif mode == "baseline":
        max_y = max(p[1] for p in polygon)
        candidates = [p for p in polygon if p[1] >= max_y - 5]
        min_x = min(p[0] for p in candidates)
        return (max_y, min_x)

    return (0, 0)


def _find_gaps(values: List[int], tolerance: int) -> List[int]:
    if len(values) < 2:
        return []
    gaps = [values[i] - values[i - 1] for i in range(1, len(values))]
    return [i for i, g in enumerate(gaps, start=1) if g > tolerance]


def detect_columns(text_positions, image_width=None, config=None) -> List[List[Tuple[int, int, str]]]:
    if not text_positions:
        return []

    cfg = config or {}
    width = image_width or 2000

    base_tolerance = int(cfg.get("column_tolerance_ratio", 0.015) * width)
    min_gap = int(cfg.get("min_column_gap_ratio", 0.03) * width)

    sorted_items = sorted(text_positions, key=lambda t: t[1])
    x_vals = [t[1] for t in sorted_items]

    # Adaptive: if we have enough items, use median gap as threshold
    if len(x_vals) >= 4:
        gaps = [x_vals[i] - x_vals[i - 1] for i in range(1, len(x_vals))]
        pos_gaps = [g for g in gaps if g > 0]
        if pos_gaps:
            median_gap = statistics.median(pos_gaps)
            adaptive_gap = max(base_tolerance + min_gap, int(median_gap * 0.6))
        else:
            adaptive_gap = base_tolerance + min_gap
    else:
        adaptive_gap = base_tolerance + min_gap

    columns = []
    current_column = [sorted_items[0]]
    current_col_x = sorted_items[0][1]

    for item in sorted_items[1:]:
        _, x, _ = item
        if abs(x - current_col_x) > adaptive_gap:
            columns.append(sorted(current_column, key=lambda t: (t[0], t[1])))
            current_column = [item]
            current_col_x = x
        else:
            current_column.append(item)

    if current_column:
        columns.append(sorted(current_column, key=lambda t: (t[0], t[1])))

    columns.sort(key=lambda col: sum(t[1] for t in col) // len(col) if col else 0)
    return columns


def group_by_lines(items, image_height=None, config=None) -> List[List[Tuple[int, int, str]]]:
    if not items:
        return []

    cfg = config or {}
    height = image_height or 3000
    tolerance = int(cfg.get("line_tolerance_ratio", 0.025) * height)
    tolerance = max(tolerance, 20)

    sorted_items = sorted(items, key=lambda t: t[0])
    lines = []
    current_line = [sorted_items[0]]
    current_line_y = sorted_items[0][0]

    for item in sorted_items[1:]:
        y, _, _ = item
        if abs(y - current_line_y) <= tolerance:
            current_line.append(item)
        else:
            lines.append(sorted(current_line, key=lambda t: t[1]))
            current_line = [item]
            current_line_y = y

    if current_line:
        lines.append(sorted(current_line, key=lambda t: t[1]))

    return lines
