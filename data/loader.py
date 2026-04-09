"""Load volleyball data from cache or live Balltime API."""

import json
import os
import sys
from pathlib import Path
from dataclasses import asdict

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "matches.json"


def load_from_cache():
    if not CACHE_FILE.exists():
        return None
    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def save_to_cache(matches):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = [asdict(m) for m in matches]
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, default=str)
    print(f"Saved {len(data)} matches to cache", file=sys.stderr)


def refresh_from_balltime():
    from dotenv import load_dotenv
    load_dotenv()
    from data.balltime import BalltimeClient, import_all_matches

    email = os.getenv("HUDL_EMAIL", "")
    password = os.getenv("HUDL_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("Set HUDL_EMAIL and HUDL_PASSWORD in .env")

    bt = BalltimeClient()
    result = bt.authenticate(email, password)
    if not result["ok"]:
        raise RuntimeError(f"Balltime auth failed: {result.get('error')}")

    matches = import_all_matches(bt)
    save_to_cache(matches)
    return [asdict(m) for m in matches]


def load_data():
    cached = load_from_cache()
    if cached:
        return cached
    return []
