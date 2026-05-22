"""
CLI entry point for syncing all data from Airtable into SQLite.

Pulls from three Airtable tables (in order):
  1. Insurance Bills  → bills table (upsert) + keyword_tags
  2. Insurance Bills  → bill_sponsors (sponsor name/party from text field)
     Legislators      → bill_sponsors enrichment (party, district, URLs, etc.)
  3. Hearings         → hearings table (upsert)

Tables intentionally ignored: "Insurance Bills (Archived)", "Sponsors"

After this sync, run LegiScan to populate full_text:
    python -m cli.legiscan

Usage:
    python -m cli.sync_airtable
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.airtable import run_airtable_sync
from config import AIRTABLE_KEY, AIRTABLE_BASE_ID


def main():
    if not AIRTABLE_KEY:
        print("ERROR: airtable_key not set in .env")
        print("  Get a Personal Access Token at https://airtable.com/create/tokens")
        print("  Required scope: data.records:read on your base")
        sys.exit(1)

    if not AIRTABLE_BASE_ID:
        print("ERROR: airtable_base_id not set in .env")
        print("  Find it in your Airtable URL: airtable.com/appXXXXXXXXXXXXXX/...")
        sys.exit(1)

    run_airtable_sync()


if __name__ == "__main__":
    main()
