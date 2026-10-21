from __future__ import annotations

from adapters.antigravity.response_parser import parse_response


def test_raw_only():
    text = "Just some text without json."
    resp = parse_response(text)
    assert resp.raw_text == text
    assert resp.structured_output is None
    assert "warnings" in resp.metadata
    assert "No valid structured JSON output found" in resp.metadata["warnings"][0]


def test_valid_structured_output_codeblock():
    text = 'Here is my response:\n```json\n{"summary": "done"}\n```\nAll good.'
    resp = parse_response(text)
    assert resp.raw_text == text
    assert resp.structured_output == {"summary": "done"}
    assert "warnings" not in resp.metadata


def test_valid_structured_output_bare_codeblock():
    text = 'Here is my response:\n```\n{"summary": "done"}\n```\nAll good.'
    resp = parse_response(text)
    assert resp.raw_text == text
    assert resp.structured_output == {"summary": "done"}
    assert "warnings" not in resp.metadata


def test_valid_structured_output_pure_json():
    text = '{"summary": "done"}'
    resp = parse_response(text)
    assert resp.raw_text == text
    assert resp.structured_output == {"summary": "done"}
    assert "warnings" not in resp.metadata


def test_invalid_structured_output():
    text = '```json\n{"summary": "done"\n```'
    resp = parse_response(text)
    assert resp.raw_text == text
    assert resp.structured_output is None
    assert "warnings" in resp.metadata
