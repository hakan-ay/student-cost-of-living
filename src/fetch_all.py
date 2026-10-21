"""Runs every fetch script in order. One failing source does not stop the others; the exit code is 1 if any failed.

Usage:
    uv run python src/fetch_all.py
"""

import sys
import traceback

import fetch_ecb
import fetch_eurostat
import fetch_istat


def main() -> None:
    failed = []
    for module in (fetch_ecb, fetch_eurostat, fetch_istat):
        sys.argv = [module.__name__]  # each script parses its own (default) arguments
        try:
            module.main()
        except Exception:
            traceback.print_exc()
            failed.append(module.__name__)
    if failed:
        print(f"failed sources: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
