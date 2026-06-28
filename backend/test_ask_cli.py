"""Quick CLI test for AskAI backend chat endpoint."""

import json
import sys
import urllib.error
import urllib.request

API_URL = "http://127.0.0.1:8000/api/ask-ai/chat"
QUESTION = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "List top 5 table names in this database."


def main() -> None:
    payload = json.dumps({"question": QUESTION}).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(body.get("response", body))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        print(f"HTTP {exc.code}: {detail}")
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        print("Backend is not running. Start it with:")
        print(
            "C:\\WORK\\goodSassDashboard2\\01_myENV\\Scripts\\python.exe "
            "-m uvicorn main:app --app-dir C:\\WORK\\goodSassDashboard2\\backend --reload --host 127.0.0.1 --port 8000"
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
