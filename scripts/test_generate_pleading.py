#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests


def main():
    parser = argparse.ArgumentParser(description="Test /agents/legal-basis/generate-pleading route")
    parser.add_argument("conversation_id", help="Conversation ID (Mongo ObjectId)")
    parser.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"), help="API base URL (default http://127.0.0.1:8000)")
    args = parser.parse_args()

    url = f"{args.base_url}/api/agents/legal-basis/generate-pleading"
    try:
        resp = requests.post(url, json={"conversation_id": args.conversation_id})
        print("Status:", resp.status_code)
        try:
            data = resp.json()
            print("JSON:")
            print(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception:
            print("Text:")
            print(resp.text)
        if resp.status_code >= 400:
            sys.exit(1)
        sys.exit(0)
    except Exception as e:
        print("Error calling API:", e)
        sys.exit(2)


if __name__ == "__main__":
    main() 