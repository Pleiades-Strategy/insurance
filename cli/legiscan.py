"""
CLI entry point for fetching full bill text from LegiScan.

Searches LegiScan by state + bill number for each bill in the database
that doesn't yet have full_text, then fetches and stores the decoded text.

Usage:
    # Fetch text for all bills missing it
    python -m cli.legiscan

    # Force re-fetch even for bills that already have text
    python -m cli.legiscan --force

    # Limit to first N bills (useful for testing)
    python -m cli.legiscan --limit 10
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.legiscan import enrich_all_bills
from config import LEGISCAN_KEY


def main():
    parser = argparse.ArgumentParser(
        description="Fetch full bill text from LegiScan for all bills in the database."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch text even for bills that already have it.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N bills (useful for testing).",
    )
    args = parser.parse_args()

    if not LEGISCAN_KEY:
        print("ERROR: legiscan_key not set in .env")
        sys.exit(1)

    enrich_all_bills(force=args.force, limit=args.limit)


if __name__ == "__main__":
    main()
