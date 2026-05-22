"""
CLI for re-running TF-IDF tagging on all bills.
Usage:
    python cli/retag.py
    python cli/retag.py --log custom_log.txt
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tagging.tfidf_tagger import run_tagging


def main():
    parser = argparse.ArgumentParser(description="Re-run TF-IDF tagging on all bills with full text.")
    parser.add_argument("--log", type=str, default="tagging_log.txt", help="Path for tagging log file")
    args = parser.parse_args()

    results = run_tagging(log_path=args.log)
    if results:
        # Summary of tag distribution
        from collections import Counter
        tag_counter = Counter()
        for tags in results.values():
            for t in tags:
                tag_counter[t] += 1
        print("\nTag distribution:")
        for tag, count in tag_counter.most_common():
            print(f"  {tag}: {count}")


if __name__ == "__main__":
    main()
