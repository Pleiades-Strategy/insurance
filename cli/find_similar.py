"""
CLI for finding similar bills.
Usage:
    python cli/find_similar.py --bill-id 1754760
    python cli/find_similar.py --bill-id 1754760 --top 5
    python cli/find_similar.py --bill-id 1754760 --state CA
    python cli/find_similar.py --bill-id 1754760 --tag wildfire_risk
    python cli/find_similar.py --bill-id 1754760 --explain 1839052
    python cli/find_similar.py --list                # show all bill IDs
    python cli/find_similar.py --list --state CA     # show CA bills only
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from similarity.engine import SimilarityEngine


def format_results_table(query_info, results):
    """Pretty-print similarity results as a table."""
    if query_info:
        tags_str = ", ".join(query_info.get("tags", [])) or "none"
        print(f"\nQuery: {query_info['state']} {query_info['bill_number']} — {query_info['title']}")
        print(f"Tags: [{tags_str}]")

    print("=" * 100)
    print(f"{'#':<4} {'Score':<8} {'State':<7} {'Bill#':<10} {'Tags':<30} {'Title'}")
    print("-" * 100)

    for i, r in enumerate(results, 1):
        tags_str = ", ".join(r["tags"][:3]) if r["tags"] else "—"
        title = r["title"][:45] + "..." if len(r["title"]) > 45 else r["title"]
        print(f"{i:<4} {r['score']:<8.4f} {r['state']:<7} {r['bill_number']:<10} {tags_str:<30} {title}")

    if not results:
        print("  No similar bills found matching your criteria.")
    print()


def format_explanation(explanation):
    """Pretty-print similarity explanation."""
    bill_a = explanation.get("bill_a", {})
    bill_b = explanation.get("bill_b", {})

    print(f"\nSimilarity: {explanation['score']:.4f}")
    print(f"  Bill A: {bill_a.get('state', '')} {bill_a.get('bill_number', '')} — {bill_a.get('title', '')}")
    print(f"  Bill B: {bill_b.get('state', '')} {bill_b.get('bill_number', '')} — {bill_b.get('title', '')}")
    print(f"\nTop shared terms (by combined TF-IDF weight):")
    print("-" * 50)

    for term, score in explanation.get("shared_terms", []):
        print(f"  {score:.4f}  {term}")
    print()


def list_bills(engine, state=None):
    """List all bills in the index."""
    print(f"\n{'Bill ID':<12} {'State':<7} {'Bill#':<10} {'Tags':<30} {'Title'}")
    print("-" * 100)

    count = 0
    for bill_id in engine.bill_ids:
        meta = engine.bill_metadata[bill_id]
        if state and meta["state"] != state.upper():
            continue

        tags_str = ", ".join(meta["tags"][:3]) if meta["tags"] else "—"
        title = meta["title"][:45] + "..." if len(meta["title"]) > 45 else meta["title"]
        print(f"{bill_id:<12} {meta['state']:<7} {meta['bill_number']:<10} {tags_str:<30} {title}")
        count += 1

    print(f"\n{count} bills total.\n")


def main():
    parser = argparse.ArgumentParser(description="Find bills similar to a given bill using TF-IDF cosine similarity.")
    parser.add_argument("--bill-id", type=str, help="BillTrack50 bill ID to query")
    parser.add_argument("--top", type=int, default=10, help="Number of similar bills to return (default: 10)")
    parser.add_argument("--state", type=str, default=None, help="Filter results by state (e.g., CA, FL)")
    parser.add_argument("--tag", type=str, default=None, help="Filter results by tag (e.g., wildfire_risk)")
    parser.add_argument("--explain", type=str, default=None, help="Show why two bills are similar (provide second bill ID)")
    parser.add_argument("--list", action="store_true", help="List all bills in the index")
    args = parser.parse_args()

    # Build the index
    print("Building similarity index...")
    engine = SimilarityEngine()
    engine.build_index()

    if not engine.bill_ids:
        print("No bills found. Run 'python cli/ingest.py' first.")
        return

    # List mode
    if args.list:
        list_bills(engine, state=args.state)
        return

    # Need a bill ID for similarity queries
    if not args.bill_id:
        parser.print_help()
        print("\nError: --bill-id is required (or use --list to see available bills).")
        return

    # Explain mode
    if args.explain:
        explanation = engine.explain_similarity(args.bill_id, args.explain)
        if explanation:
            format_explanation(explanation)
        return

    # Standard similarity query
    query_info = engine.get_bill_info(args.bill_id)
    results = engine.find_similar(
        args.bill_id,
        top_n=args.top,
        state=args.state,
        tag=args.tag,
    )
    format_results_table(query_info, results)


if __name__ == "__main__":
    main()
