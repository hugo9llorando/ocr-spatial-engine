import csv
import io
import json
import os
import sys
from datetime import datetime
from typing import Any

from .spatial import group_by_lines


def format_text_output(columns: list[list[tuple[int, int, str]]], mode: str = "columns") -> str:
    output_lines: list[str] = []

    if mode == "columns":
        for col_idx, column in enumerate(columns):
            if col_idx > 0:
                output_lines.append("")
            lines = group_by_lines(column)
            for line in lines:
                line_text = " ".join(t[2] for t in line if t[2].strip())
                if line_text:
                    output_lines.append(line_text)

    elif mode == "rows":
        all_items = [item for col in columns for item in col]
        global_lines = group_by_lines(all_items)
        for line in global_lines:
            line_text = " ".join(t[2] for t in line if t[2].strip())
            if line_text:
                output_lines.append(line_text)

    return "\n".join(output_lines)


def format_json_output(columns: list[list[tuple[int, int, str]]], metadata: dict) -> dict:
    result: dict[str, Any] = {
        "metadata": {
            **metadata,
            "timestamp": datetime.now().isoformat(),
        },
        "columns": []
    }

    for col_idx, column in enumerate(columns):
        col_data: dict[str, Any] = {"index": col_idx, "lines": []}
        lines = group_by_lines(column)
        for line_idx, line in enumerate(lines):
            col_data["lines"].append({
                "index": line_idx,
                "texts": [
                    {"content": t[2], "position": {"y": t[0], "x": t[1]}}
                    for t in line if t[2].strip()
                ]
            })
        result["columns"].append(col_data)

    return result


def format_csv_output(columns: list[list[tuple[int, int, str]]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["column", "line", "x", "y", "text"])

    for col_idx, column in enumerate(columns):
        lines = group_by_lines(column)
        for line_idx, line in enumerate(lines):
            for y, x, text in line:
                if text.strip():
                    writer.writerow([col_idx, line_idx, x, y, text])

    return output.getvalue()


def format_markdown_output(columns: list[list[tuple[int, int, str]]], source: str = "") -> str:
    lines: list[str] = []
    if source:
        lines.append(f"# OCR Result: `{source}`\n")
    for col_idx, column in enumerate(columns):
        col_lines = group_by_lines(column)
        title = f"## Columna {col_idx + 1}" if len(columns) > 1 else ""
        if title:
            lines.append(title)
        for line in col_lines:
            line_text = " ".join(t[2] for t in line if t[2].strip())
            if line_text:
                lines.append(f"- {line_text}")
        if title:
            lines.append("")
    return "\n".join(lines)


def export_results(text_output: str, json_output: dict, csv_output: str, base_path: str, formats: list[str], markdown_output: str = "") -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for fmt in formats:
        try:
            if fmt == "txt":
                path = f"{base_path}_{timestamp}.txt"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text_output)
            elif fmt == "json":
                path = f"{base_path}_{timestamp}.json"
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(json_output, f, ensure_ascii=False, indent=2)
            elif fmt == "csv":
                path = f"{base_path}_{timestamp}.csv"
                with open(path, "w", encoding="utf-8", newline="") as f:
                    f.write(csv_output)
            elif fmt == "md" and markdown_output:
                path = f"{base_path}_{timestamp}.md"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(markdown_output)
            print(f"[OK] Exportado: {path}")
        except IOError as e:
            print(f"[ERROR] Exportando {fmt}: {e}", file=sys.stderr)
