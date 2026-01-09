import json
import urllib.request

BASE_URL = "http://localhost:8000"

EXAMPLE_1 = {
    "tool": "extract_structured_json",
    "input": {
        "text": (
            "John Doe, born in 1989, currently lives in Seattle and works as a software "
            "engineer. Phone number 5551234567."
        ),
        "schema": {
            "name": "string",
            "birth_year": "number",
            "city": "string",
            "job": "string",
            "phone": "string",
        },
    },
}

EXAMPLE_2 = {
    "tool": "extract_structured_json",
    "input": {
        "text": "Alice Smith works in Austin. Email is alice.smith@example.com.",
        "schema": {
            "name": "string",
            "city": "string",
            "job": "string",
            "email": "string",
        },
    },
}


def call(payload):
    req = urllib.request.Request(
        f"{BASE_URL}/mcp",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    print("Example 1:")
    print(json.dumps(call(EXAMPLE_1), ensure_ascii=False, indent=2))
    print("\nExample 2:")
    print(json.dumps(call(EXAMPLE_2), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
