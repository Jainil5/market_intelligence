#!/usr/bin/env python3
"""Validate local configuration before running the API or smoke tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
PLACEHOLDERS = {
    "YOUR_PROJECT",
    "YOUR_SERVICE_ROLE_KEY",
    "change-this-to-a-long-random-secret",
}


def load_dotenv() -> None:
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def check(name: str, ok: bool, detail: str = "") -> bool:
    mark = "OK" if ok else "MISSING"
    suffix = f" — {detail}" if detail else ""
    print(f"[{mark}] {name}{suffix}")
    return ok


def main() -> int:
    load_dotenv()
    required = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "API_KEY"]
    all_ok = True
    for key in required:
        value = os.getenv(key, "").strip()
        ok = bool(value) and not any(p in value for p in PLACEHOLDERS)
        all_ok &= check(key, ok)

    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "").strip()
    check("SUPABASE_STORAGE_BUCKET (optional)", bool(bucket), "unset; CSV stays local only" if not bucket else bucket)

    if not ENV_PATH.exists():
        all_ok = False
        check(".env file", False, f"run: cp .env.example .env ({ENV_PATH})")
    else:
        check(".env file", True, str(ENV_PATH))

    if all_ok:
        try:
            from data_manager.services.health import check_supabase

            sb = check_supabase()
            all_ok &= check("Supabase connectivity", sb.get("ok", False), sb.get("detail", ""))
        except Exception as exc:
            all_ok = False
            check("Supabase connectivity", False, str(exc))

    if all_ok:
        print("\nSetup looks good. Next:")
        print("  uvicorn main:app --reload")
        print("  ./scripts/smoke_test.sh")
        return 0

    print("\nFix the items above, then re-run: python scripts/verify_setup.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
