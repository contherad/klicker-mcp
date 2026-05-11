#!/usr/bin/env python
"""Save your Ahrefs API key."""

from pathlib import Path

CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
CREDENTIALS_DIR.mkdir(exist_ok=True)

print("=" * 60)
print("Ahrefs API Key Setup")
print("=" * 60)
print()

api_key = input("Paste your Ahrefs API key: ").strip()

if not api_key:
    print("API key is required.")
    exit(1)

# Save as simple text file
txt_path = CREDENTIALS_DIR / "ahrefs-api-key.txt"
txt_path.write_text(api_key)

# Also save as JSON (optional)
json_path = CREDENTIALS_DIR / "ahrefs-credentials.json"
import json
json.dump({"api_key": api_key}, json_path.open("w"), indent=2)

print(f"\nSaved to:")
print(f"  {txt_path}")
print(f"  {json_path}")
print("\nYou're ready to use Ahrefs with the MCP server!")