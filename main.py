from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI
from pydantic import BaseModel

APP_NAME = "schema-first-extractor"
TOOL_NAME = "extract_structured_json"

ALLOWED_TYPES = {"string", "number", "boolean"}
MAX_TEXT_LENGTH = 5000

app = FastAPI(title=APP_NAME)


# ---------- Your existing deterministic extractor ----------
class ToolInput(BaseModel):
    text: str
    schema: Dict[str, str]


class MCPRequestSimple(BaseModel):
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


# ---------- Public endpoints ----------
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
    # Human-friendly definition (fine to keep)
    return {
        "app": APP_NAME,
        "tool": {
            "name": TOOL_NAME,
            "description": (
                "Deterministic, heuristic, best-effort, non-exhaustive extraction of structured "
                "JSON from messy human text according to a caller-provided simple schema. "
                "Extraction only; no inference, evaluation, recommendations, or decisions."
            ),
            "inputSchema": {  # NOTE: inputSchema (camelCase) is what many scanners expect
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "schema": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "field -> string|number|boolean",
                    },
                },
                "required": ["text", "schema"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "ok": {"type": "boolean"},
                    "result": {"type": "object"},
                    "error": {"type": "object"},
                },
                "required": ["ok"],
            },
            "annotations": {
                "readOnlyHint": True,
                "openWorldHint": False,
                "destructiveHint": False,
            },
        },
    }


# ---------- MCP JSON-RPC compatibility (for Scan Tools) ----------
class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[int, str, None] = None
    method: str
    params: Optional[Dict[str, Any]] = None


def _jsonrpc_ok(req_id: Union[int, str, None], result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_err(req_id: Union[int, str, None], code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


TOOLS = [
    {
        "name": TOOL_NAME,
        "description": (
            "Deterministic extraction of structured JSON from messy text according to a caller-provided schema."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "schema": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["text", "schema"],
        },
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": False,
            "destructiveHint": False,
        },
    }
]


@app.post("/mcp")
def mcp_invoke(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supports BOTH:
    A) Simple invoke: {"tool": "...", "input": {...}}  (your existing style)
    B) JSON-RPC: {"jsonrpc":"2.0","id":1,"method":"tools/list"} (Scan Tools style)
    """
    # --- B) JSON-RPC path ---
    if isinstance(payload, dict) and "method" in payload and "jsonrpc" in payload:
        try:
            req = JSONRPCRequest(**payload)
        except Exception as e:
            return _jsonrpc_err(None, -32600, "Invalid Request", {"detail": str(e)})

        method = req.method
        params = req.params or {}

        if method == "initialize":
            return _jsonrpc_ok(
                req.id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": APP_NAME, "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            )

        if method == "tools/list":
            return _jsonrpc_ok(req.id, {"tools": TOOLS})

        if method == "tools/call":
            name = (params.get("name") or "").strip()
            arguments = params.get("arguments") or {}
            if name != TOOL_NAME:
                return _jsonrpc_err(req.id, -32602, "Unknown tool", {"name": name})

            try:
                tool_input = ToolInput(**arguments)
            except Exception as e:
                return _jsonrpc_err(req.id, -32602, "Invalid tool arguments", {"detail": str(e)})

            result = extract_structured_json(tool_input)
            # MCP tool result format: content array (safe and common)
            return _jsonrpc_ok(req.id, {"content": [{"type": "text", "text": str(result)}]})

        return _jsonrpc_err(req.id, -32601, "Method not found", {"method": method})

    # --- A) Simple invoke path ---
    try:
        req2 = MCPRequestSimple(**payload)
    except Exception as e:
        return _invalid(f"Invalid request body. {e}")

    if req2.tool != TOOL_NAME:
        return _invalid("Unknown tool.")
    return extract_structured_json(req2.input)
