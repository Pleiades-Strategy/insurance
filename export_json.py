"""
Export the SQLite database to a static JSON file for GitHub Pages hosting.

Usage:
    python export_json.py

Writes: docs/data.json

The docs/ folder is what GitHub Pages serves when configured to use /docs on main.
Run this script after each Airtable sync, then commit and push.
"""

import json
import sqlite3
from pathlib import Path

ROOT    = Path(__file__).parent
DB_PATH = ROOT / "data" / "insurance_bills.db"
OUT_DIR = ROOT / "docs"
OUT_FILE = OUT_DIR / "data.json"


def rows(cursor, query, args=()):
    cursor.execute(query, args)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def main():
    if not DB_PATH.exists():
        print(f"❌  Database not found at {DB_PATH}")
        print("   Run `python cli/ingest.py` first.")
        return

    OUT_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    print("Exporting bills...")
    bills = rows(c, """
        SELECT
            b.bill_id, b.state, b.bill_number, b.title, b.status,
            b.session, b.introduced_date, b.last_action_date,
            b.bill_url, b.document_link, b.keyword_tags, b.summary,
            b.legiscanid, b.notes,
            (b.full_text IS NOT NULL AND b.full_text != '') AS has_text,
            b.full_text,
            GROUP_CONCAT(
                bs.legislator_name || '||' ||
                COALESCE(bs.legislator_party,'') || '||' ||
                COALESCE(bs.role,'') || '||' ||
                COALESCE(bs.district,'') || '||' ||
                COALESCE(bs.state_code,'') || '||' ||
                COALESCE(bs.in_office,'0') || '||' ||
                COALESCE(bs.ballotpedia_url,'') || '||' ||
                COALESCE(bs.follow_the_money_url,''),
                ';;'
            ) AS sponsors_raw
        FROM bills b
        LEFT JOIN bill_sponsors bs ON b.bill_id = bs.bill_id
        GROUP BY b.bill_id
        ORDER BY b.last_action_date DESC
    """)

    # Parse sponsors_raw into structured objects
    for bill in bills:
        raw = bill.pop("sponsors_raw") or ""
        sponsors = []
        for entry in raw.split(";;"):
            parts = entry.split("||")
            if len(parts) == 8 and parts[0]:
                sponsors.append({
                    "legislator_name":      parts[0],
                    "legislator_party":     parts[1],
                    "role":                 parts[2],
                    "district":             parts[3],
                    "state_code":           parts[4],
                    "in_office":            parts[5] == "1",
                    "ballotpedia_url":      parts[6],
                    "follow_the_money_url": parts[7],
                })
        bill["sponsors"] = sponsors

    print(f"  {len(bills)} bills exported")

    print("Exporting hearings...")
    hearings = rows(c, """
        SELECT h.bill_id, h.title, h.start_dt, h.end_dt, h.status,
               h.location, h.description, h.event_link,
               b.state, b.bill_number, b.title AS bill_title
        FROM hearings h
        LEFT JOIN bills b ON h.bill_id = b.bill_id
        ORDER BY h.start_dt DESC
    """)
    print(f"  {len(hearings)} hearings exported")

    print("Building summary stats...")
    def scalar(q):
        c.execute(q)
        return c.fetchone()[0]

    total   = scalar("SELECT COUNT(*) FROM bills")
    states  = scalar("SELECT COUNT(DISTINCT state) FROM bills")
    enacted = scalar("SELECT COUNT(*) FROM bills WHERE status = 'Signed/Enacted/Adopted'")
    active  = scalar("""SELECT COUNT(*) FROM bills
                        WHERE status IN ('Introduced','In Committee','Crossed Over','Passed')""")
    dead      = scalar("SELECT COUNT(*) FROM bills WHERE status = 'Dead'")
    with_text = scalar("SELECT COUNT(*) FROM bills WHERE full_text IS NOT NULL AND full_text != ''")

    # Charts data
    by_status = rows(c, """
        SELECT status, COUNT(*) as count FROM bills
        WHERE status IS NOT NULL GROUP BY status ORDER BY count DESC
    """)
    by_state = rows(c, """
        SELECT state, COUNT(*) as count FROM bills
        WHERE state IS NOT NULL GROUP BY state ORDER BY count DESC LIMIT 20
    """)

    cat_counts = {}
    for (tags,) in c.execute("SELECT keyword_tags FROM bills WHERE keyword_tags IS NOT NULL"):
        try:
            for t in json.loads(tags):
                cat_counts[t] = cat_counts.get(t, 0) + 1
        except Exception:
            pass
    by_category = sorted(
        [{"category": k, "count": v} for k, v in cat_counts.items()],
        key=lambda x: x["count"], reverse=True
    )

    # Legislators
    legislators = rows(c, """
        SELECT
            bs.legislator_name, bs.legislator_party, bs.role, bs.district,
            bs.state_code, bs.in_office, bs.ballotpedia_url, bs.follow_the_money_url,
            COUNT(DISTINCT bs.bill_id) AS bill_count,
            GROUP_CONCAT(DISTINCT b.state) AS states_active
        FROM bill_sponsors bs
        LEFT JOIN bills b ON bs.bill_id = b.bill_id
        GROUP BY bs.legislator_name
        ORDER BY bill_count DESC
        LIMIT 300
    """)

    conn.close()

    payload = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total": total, "states": states, "enacted": enacted,
            "active": active, "dead": dead, "with_text": with_text,
        },
        "charts": {
            "by_status":   by_status,
            "by_state":    by_state,
            "by_category": by_category,
        },
        "bills":       bills,
        "hearings":    hearings,
        "legislators": legislators,
    }

    OUT_FILE.write_text(json.dumps(payload, default=str, ensure_ascii=False), encoding="utf-8")
    size_mb = OUT_FILE.stat().st_size / 1_000_000
    print(f"\n✅  Exported to {OUT_FILE}  ({size_mb:.1f} MB)")
    print("   Commit the docs/ folder and push to GitHub.")
    print("   Enable GitHub Pages → Source: main branch, /docs folder.")


if __name__ == "__main__":
    main()
