import json
import urllib.request

BASE_URL = "http://localhost:8000"


def fetch(path: str) -> None:
    url = f"{BASE_URL}{path}"
    with urllib.request.urlopen(url) as response:
        body = response.read().decode("utf-8")
        status = response.status
    print(f"GET {path} -> {status}")
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(body)


def main() -> None:
    fetch("/")
    fetch("/health")
    fetch("/mcp")


if __name__ == "__main__":
    main()
