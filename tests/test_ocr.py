import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.ocr import parse_ocr_output


def test_parse_ocr_json_valid():
    output = '{"res": {"rec_texts": ["hola", "mundo"], "rec_polys": [[[0,0],[10,0],[10,10],[0,10]], [[20,0],[30,0],[30,10],[20,10]]]}}'
    success, data = parse_ocr_output(output, success=True)
    assert success is True
    assert len(data["texts"]) == 2
    assert data["texts"] == ["hola", "mundo"]
    assert len(data["polygons"]) == 2


def test_parse_ocr_json_empty():
    output = '{"res": {"rec_texts": [], "rec_polys": []}}'
    success, data = parse_ocr_output(output, success=True)
    assert success is True
    assert data["texts"] == []
    assert data["polygons"] == []


def test_parse_ocr_extra_text():
    output = "stdout noise\n{\"res\": {\"rec_texts\": [\"uno\"], \"rec_polys\": [[[0,0],[5,0],[5,10],[0,10]]]}}\nmore noise"
    success, data = parse_ocr_output(output, success=True)
    assert success is True
    assert data["texts"] == ["uno"]


def test_parse_ocr_malformed():
    output = "not json at all"
    success, data = parse_ocr_output(output, success=True)
    assert success is False
    assert data["error"] == "parse_failed"


def test_parse_ocr_cli_failed():
    success, data = parse_ocr_output("", success=False)
    assert success is False
    assert data["error"] == "cli_failed"


def test_parse_ocr_skip_empty_texts():
    output = '{"res": {"rec_texts": ["", "  ", "valido"], "rec_polys": [[[0,0],[1,0],[1,1],[0,1]], [[2,0],[3,0],[3,1],[2,1]], [[4,0],[5,0],[5,1],[4,1]]]}}'
    success, data = parse_ocr_output(output, success=True)
    assert success is True
    assert data["texts"] == ["valido"]


def test_parse_ocr_without_res_key():
    output = '{"rec_texts": ["directo"], "rec_polys": [[[0,0],[1,0],[1,1],[0,1]]]}'
    success, data = parse_ocr_output(output, success=True)
    assert success is True
    assert data["texts"] == ["directo"]
