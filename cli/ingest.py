"""
CLI for bill ingestion pipeline.
Usage:
    python cli/ingest.py              # Sync bills from Airtable and enrich with full text
    python cli/ingest.py --force      # Re-fetch LegiScan text for all bills
    python cli/ingest.py --limit 10   # Test with 10 bills
    python cli/ingest.py --skip-text  # Only sync Airtable metadata, skip LegiScan enrichment
"""

import argparse
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.airtable import run_airtable_sync
from ingestion.legiscan import enrich_all_bills


def main():
    parser = argparse.ArgumentParser(description="Sync bills from Airtable and enrich with LegiScan full text.")
    parser.add_argument("--force", action="store_true", help="Re-fetch LegiScan text for all bills, including those already enriched")
    parser.add_argument("--limit", type=int, default=None, help="Limit LegiScan enrichment to N bills (for testing)")
    parser.add_argument("--skip-text", action="store_true", help="Skip LegiScan text enrichment")
    args = parser.parse_args()

    # Step 1: Sync bills and sponsors from Airtable
    run_airtable_sync()

    if args.skip_text:
        print("\nSkipping LegiScan enrichment (--skip-text).")
        return

    # Step 2: Enrich with LegiScan full text
    print("\n" + "=" * 60)
    print("Step 2: Enriching with LegiScan full text...")
    print("=" * 60)
    results = enrich_all_bills(force=args.force, limit=args.limit)

    print("\n" + "=" * 60)
    print("Ingestion complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
