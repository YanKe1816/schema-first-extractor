from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

APP_NAME = "schema-first-extractor"
TOOL_NAME = "extract_structured_json"

ALLOWED_TYPES = {"string", "number", "boolean"}
MAX_TEXT_LENGTH = 5000

app = FastAPI(title=APP_NAME)


class ToolInput(BaseModel):
    text: str
    schema: Dict[str, str]


class MCPRequest(BaseModel):
    tool: str
    input: ToolInput


def _blocked(message: str) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": "BLOCKED", "message": message}}


def _invalid(message: str) -> Dict[str, Any]:
    return {"ok": False, "error": {"code": "INVALID_INPUT", "message": message}}


def _validate_input(payload: ToolInput) -> Optional[Dict[str, Any]]:
    if not isinstance(payload.text, str):
        return _invalid("Field 'text' must be a string.")
    if len(payload.text) > MAX_TEXT_LENGTH:
        return _blocked("Input text exceeds the maximum length.")
    if not isinstance(payload.schema, dict) or not payload.schema:
        return _invalid("Field 'schema' must be a non-empty object.")
    for key, value in payload.schema.items():
        if not isinstance(key, str) or not key:
            return _invalid("Schema keys must be non-empty strings.")
        if value not in ALLOWED_TYPES:
            return _blocked("Schema contains unsupported field types.")
    return None


def _extract_string(field: str, text: str) -> Optional[str]:
    patterns = [
        rf"{re.escape(field)}\s*:\s*([^,.;\n]+)",
        rf"{re.escape(field)}\s+is\s+([^,.;\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    if field == "name":
        match = re.match(r"^([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text.strip())
        if match:
            return match.group(1)
    if field == "city":
        match = re.search(r"in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text)
        if match:
            return match.group(1)
    if field == "job":
        match = re.search(r"works as\s+([^,.;\n]+)", text)
        if match:
            return match.group(1).strip()
    if field == "email":
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        if match:
            return match.group(0)
    if field == "phone":
        match = re.search(r"\b1\d{10}\b", text)
        if match:
            return match.group(0)
    return None


def _extract_number(field: str, text: str) -> Optional[int]:
    if field in {"birth_year", "year"}:
        match = re.search(r"(19\d{2}|20\d{2})", text)
        if match:
            return int(match.group(1))
    match = re.search(r"(-?\d+)", text)
    if match:
        return int(match.group(1))
    return None


def _extract_boolean(field: str, text: str) -> Optional[bool]:
    pattern = rf"{re.escape(field)}\s*:\s*(true|false)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match:
        return match.group(1).lower() == "true"
    return None


def extract_structured_json(payload: ToolInput) -> Dict[str, Any]:
    error = _validate_input(payload)
    if error:
        return error

    text = payload.text
    schema = payload.schema

    data: Dict[str, Any] = {}
    missing_fields: List[str] = []
    notes: List[str] = []

    for field, field_type in schema.items():
        value: Optional[Any] = None
        if field_type == "string":
            value = _extract_string(field, text)
        elif field_type == "number":
            value = _extract_number(field, text)
        elif field_type == "boolean":
            value = _extract_boolean(field, text)

        if value is None:
            missing_fields.append(field)
            notes.append(f"Field '{field}' not found in input text.")
        else:
            data[field] = value

    return {
        "ok": True,
        "result": {
            "data": data,
            "missing_fields": missing_fields,
            "notes": notes,
        },
    }


@app.get("/health")
def health() -> Dict[str, bool]:
    return {"ok": True}


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "service": APP_NAME,
        "description": (
            "Platform-governed MCP-compatible service exposing a single deterministic "
            "extraction tool."
        ),
        "mcp_endpoint": "/mcp",
        "health_endpoint": "/health",
        "notes": (
            "No UI. No external calls. No persistence. Runs only on explicit tool invocation."
        ),
    }


@app.get("/mcp")
def mcp_definition() -> Dict[str, Any]:
    return {
        "app": APP_NAME,
        "tool": {
            "name": TOOL_NAME,
            "description": (
                "Deterministic, heuristic, best-effort, non-exhaustive extraction of structured "
                "JSON from messy human text according to a caller-provided simple schema. "
                "Extraction only; no inference, evaluation, recommendations, or decisions."
            ),
            "input": {
                "text": "string",
                "schema": "object of field -> string|number|boolean",
            },
            "output": {
                "ok": "boolean",
                "result?": {
                    "data": "object",
                    "missing_fields": "string[]",
                    "notes": "string[]",
                },
                "error?": {"code": "string", "message": "string"},
            },
            "safety": {
                "ReadOnlyHint": True,
                "OpenWorldHint": False,
                "DestructiveHint": False,
                "notes": (
                    "Read-only extraction with no external calls and no destructive actions."
                ),
            },
        },
    }


@app.post("/mcp")
def mcp_invoke(request: MCPRequest) -> Dict[str, Any]:
    if request.tool != TOOL_NAME:
        return _invalid("Unknown tool.")
    return extract_structured_json(request.input)
