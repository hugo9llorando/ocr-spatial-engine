import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.export import format_text_output, format_json_output, format_csv_output, format_markdown_output, export_results


def make_columns():
    return [
        [(10, 20, "A1"), (30, 25, "A2")],
        [(15, 200, "B1"), (35, 205, "B2")],
    ]


def test_format_text_columns_mode():
    cols = make_columns()
    result = format_text_output(cols, mode="columns")
    assert "A1 A2" in result
    assert "B1 B2" in result


def test_format_text_rows_mode():
    cols = make_columns()
    result = format_text_output(cols, mode="rows")
    assert "A1" in result
    assert "B1" in result


def test_format_text_empty():
    assert format_text_output([], mode="columns") == ""
    assert format_text_output([[]], mode="columns") == ""


def test_format_json():
    cols = make_columns()
    result = format_json_output(cols, {"method": "test"})
    assert result["metadata"]["method"] == "test"
    assert "timestamp" in result["metadata"]
    assert len(result["columns"]) == 2
    assert len(result["columns"][0]["lines"]) == 1


def test_format_json_content():
    cols = [[(10, 30, "test_text")]]
    result = format_json_output(cols, {})
    first_text = result["columns"][0]["lines"][0]["texts"][0]
    assert first_text["content"] == "test_text"
    assert first_text["position"] == {"y": 10, "x": 30}


def test_format_csv():
    cols = make_columns()
    result = format_csv_output(cols)
    assert "column,line,x,y,text" in result
    assert "A1" in result
    assert "B2" in result


def test_export_results_txt():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "out")
        export_results("hello", {}, "", base, ["txt"])
        files = os.listdir(tmp)
        assert any(f.startswith("out_") and f.endswith(".txt") for f in files)


def test_export_results_json():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "out")
        export_results("", {"key": "val"}, "", base, ["json"])
        files = os.listdir(tmp)
        json_files = [f for f in files if f.endswith(".json")]
        assert len(json_files) == 1
        with open(os.path.join(tmp, json_files[0]), encoding="utf-8") as f:
            assert json.load(f)["key"] == "val"


def test_export_results_csv():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "out")
        export_results("", {}, "a,b,c\n1,2,3", base, ["csv"])
        files = os.listdir(tmp)
        assert any(f.endswith(".csv") for f in files)


def test_export_results_all():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "out")
        export_results("hi", {"k": "v"}, "x,y\n1,2", base, ["txt", "json", "csv"])
        files = os.listdir(tmp)
        assert sum(1 for f in files if f.endswith((".txt", ".json", ".csv"))) >= 3


def test_format_markdown():
    cols = [[(10, 30, "titulo")], [(15, 200, "dato")]]
    result = format_markdown_output(cols, "test.png")
    assert "test.png" in result
    assert "titulo" in result
    assert "dato" in result


def test_format_markdown_single_column():
    cols = [[(10, 30, "unico")]]
    result = format_markdown_output(cols)
    assert "unico" in result


def test_export_results_md():
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "out")
        export_results("", {}, "", base, ["md"], markdown_output="# Test")
        files = os.listdir(tmp)
        assert any(f.endswith(".md") for f in files)
