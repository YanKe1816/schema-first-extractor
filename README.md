# schema-first-extractor

This repository provides a platform-governed App that exposes exactly one tool: `extract_structured_json`. The tool performs deterministic, heuristic, best-effort, non-exhaustive extraction of structured JSON from human text using a caller-provided simple schema. It does not provide advice, decisions, judgments, or evaluations.

## Platform Questions

### 1) Who is this App?
- **App name:** `schema-first-extractor`
- **Purpose:** Deterministically extract structured JSON from text using a caller-provided schema. No recommendations or decisions are produced.
- **Contact:** `owner@example.com`

### 2) What does it do?
- Exposes a single function-style tool: `extract_structured_json`.
- Accepts a JSON payload with `text` and a schema object describing desired fields and primitive types.
- Returns one of the three explicit feedback contract states (success, failure, blocked).

### 3) What does it NOT do?
- No inference, recommendation, evaluation, or decision-making.
- No external calls, networking, or persistence.
- No destructive actions.
- Extraction may be incomplete and is reported via `missing_fields` and factual `notes`.
- Failure or blocked execution is valid and expected when input is invalid, unsupported, or too large.

### 4) Can it be safely disabled?
- No persistent state and no external dependencies.
- Can be stopped or replaced without data loss.
- All failures are explicit and return `error` with `code` and `message`.

---

## Endpoints
- `GET /health` -> `{ "ok": true }`
- `GET /mcp` -> tool definition (includes safety fuses)
- `POST /mcp` -> tool invocation

---

## Tool Definition

**Tool name:** `extract_structured_json`

**Description:**
Deterministic, heuristic, best-effort, non-exhaustive extraction of structured JSON from messy human text according to a caller-provided simple schema. It performs extraction only and does not provide advice, evaluation, or decisions.

**Input:**
```json
{
  "text": "string",
  "schema": {
    "fieldA": "string",
    "fieldB": "number",
    "fieldC": "boolean"
  }
}
```

**Output (fixed schema):**
```json
{
  "ok": "boolean",
  "result?": {
    "data": "object",
    "missing_fields": "string[]",
    "notes": "string[]"
  },
  "error?": {
    "code": "string",
    "message": "string"
  }
}
```

Constraints:
- When `ok=true`, `result` is required.
- When `ok=false`, `error` is required.
- `result.data` contains only fields declared in the input schema.
- `missing_fields` lists schema fields not found in the text.
- `notes` contains only factual statements (no recommendations or judgments).

---

## Feedback Contract (Three Explicit States)

1) **Success**
```json
{ "ok": true, "result": { "data": { ... }, "missing_fields": [], "notes": [] } }
```

2) **Failure** (invalid input)
```json
{ "ok": false, "error": { "code": "INVALID_INPUT", "message": "..." } }
```

3) **Blocked Execution** (unsupported or out-of-scope input)
```json
{ "ok": false, "error": { "code": "BLOCKED", "message": "..." } }
```

Silent failure is not permitted. A failure or blocked response is a valid outcome.

---

## Safety and Governance Constraints

The tool is intentionally constrained and must remain so:
- `ReadOnlyHint: true` - read-only extraction, no writes or persistence.
- `OpenWorldHint: false` - no external calls, no network access.
- `DestructiveHint: false` - no destructive actions.

These are governance constraints and are enforced in the tool definition and documentation.

---

## Examples

These examples demonstrate format only. They do not represent guaranteed coverage or accuracy. The extraction heuristics are language-agnostic and non-exhaustive, and no semantic understanding or reasoning is performed.

### Example 1
Input:
```json
{
  "text": "John Doe, born in 1989, currently lives in Seattle and works as a software engineer. Phone number 5551234567.",
  "schema": {
    "name": "string",
    "birth_year": "number",
    "city": "string",
    "job": "string",
    "phone": "string"
  }
}
```
Output:
```json
{
  "ok": true,
  "result": {
    "data": {
      "name": "John Doe",
      "birth_year": 1989,
      "city": "Seattle",
      "job": "software engineer",
      "phone": "5551234567"
    },
    "missing_fields": [],
    "notes": []
  }
}
```

### Example 2
Input:
```json
{
  "text": "Alice Smith works in Austin. Email is alice.smith@example.com.",
  "schema": {
    "name": "string",
    "city": "string",
    "job": "string",
    "email": "string"
  }
}
```
Output:
```json
{
  "ok": true,
  "result": {
    "data": {
      "name": "Alice Smith",
      "city": "Austin",
      "email": "alice.smith@example.com"
    },
    "missing_fields": ["job"],
    "notes": ["Field 'job' not found in input text."]
  }
}
```

---

## Local Run
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Local Test (Examples 1 & 2)
```bash
python scripts/test_examples.py
```

---

## Render Deployment
- Use `render.yaml`. The start command is included.

---

## Disclaimer
- This App performs deterministic extraction only.
- No advice, diagnosis, evaluation, or decision-making is provided.
- Invalid or out-of-scope input returns an explicit failure or blocked response.
