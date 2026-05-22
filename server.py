"""
Dashboard API server for the Insurance Bill Tracker.

Usage:
    python server.py          # starts on http://localhost:5050
    python server.py --port 8080

Opens the dashboard automatically in your browser.
No extra dependencies — uses only Python stdlib + sqlite3.
"""

import argparse
import json
import os
import sqlite3
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "insurance_bills.db"
DASHBOARD_PATH = ROOT / "dashboard.html"

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Route handlers  (each returns a JSON-serialisable value)
# ---------------------------------------------------------------------------

def handle_summary(_params):
    conn = get_conn()
    total      = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
    states     = conn.execute("SELECT COUNT(DISTINCT state) FROM bills").fetchone()[0]
    active     = conn.execute(
        "SELECT COUNT(*) FROM bills WHERE status IN ('Introduced','In Committee','Crossed Over','Passed')"
    ).fetchone()[0]
    enacted    = conn.execute(
        "SELECT COUNT(*) FROM bills WHERE status = 'Signed/Enacted/Adopted'"
    ).fetchone()[0]
    dead       = conn.execute(
        "SELECT COUNT(*) FROM bills WHERE status = 'Dead'"
    ).fetchone()[0]
    with_text  = conn.execute("SELECT COUNT(*) FROM bills WHERE full_text IS NOT NULL AND full_text != ''").fetchone()[0]
    conn.close()
    return {"total": total, "states": states, "active": active,
            "enacted": enacted, "dead": dead, "with_text": with_text}


def handle_bills(params):
    state    = params.get("state", [None])[0]
    status   = params.get("status", [None])[0]
    category = params.get("category", [None])[0]
    search   = params.get("search", [None])[0]
    limit    = int(params.get("limit", ["200"])[0])
    offset   = int(params.get("offset", ["0"])[0])

    where, args = [], []

    if state:
        where.append("b.state = ?")
        args.append(state)
    if status:
        where.append("b.status = ?")
        args.append(status)
    if category:
        where.append("b.keyword_tags LIKE ?")
        args.append(f"%{category}%")
    if search:
        s = f"%{search}%"
        where.append("(b.title LIKE ? OR b.bill_number LIKE ? OR b.summary LIKE ?)")
        args += [s, s, s]

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_conn()
    count = conn.execute(
        f"SELECT COUNT(*) FROM bills b {where_sql}", args
    ).fetchone()[0]

    rows = conn.execute(f"""
        SELECT
            b.bill_id, b.state, b.bill_number, b.title, b.status,
            b.session, b.introduced_date, b.last_action_date,
            b.bill_url, b.document_link, b.keyword_tags, b.summary,
            b.legiscanid,
            (b.full_text IS NOT NULL AND b.full_text != '') AS has_text,
            GROUP_CONCAT(DISTINCT bs.legislator_name || ' (' || COALESCE(bs.legislator_party,'?') || ')') AS sponsors
        FROM bills b
        LEFT JOIN bill_sponsors bs ON b.bill_id = bs.bill_id
        {where_sql}
        GROUP BY b.bill_id
        ORDER BY b.last_action_date DESC NULLS LAST
        LIMIT ? OFFSET ?
    """, args + [limit, offset]).fetchall()
    conn.close()

    return {"total": count, "bills": rows_to_list(rows)}


def handle_bill_detail(params):
    bill_id = params.get("id", [None])[0]
    if not bill_id:
        return {"error": "missing id"}

    conn = get_conn()
    bill = conn.execute("SELECT * FROM bills WHERE bill_id = ?", [bill_id]).fetchone()
    if not bill:
        conn.close()
        return {"error": "not found"}

    sponsors = conn.execute("""
        SELECT legislator_name, legislator_party, role, district,
               state_code, in_office, ballotpedia_url, follow_the_money_url
        FROM bill_sponsors WHERE bill_id = ?
        ORDER BY legislator_name
    """, [bill_id]).fetchall()

    hearings = conn.execute("""
        SELECT title, start_dt, end_dt, status, location, description, event_link
        FROM hearings WHERE bill_id = ?
        ORDER BY start_dt
    """, [bill_id]).fetchall()

    actions = conn.execute("""
        SELECT action_date, description FROM bill_actions
        WHERE bill_id = ? ORDER BY action_date DESC
    """, [bill_id]).fetchall()

    conn.close()
    return {
        "bill":     dict(bill),
        "sponsors": rows_to_list(sponsors),
        "hearings": rows_to_list(hearings),
        "actions":  rows_to_list(actions),
    }


def handle_charts(_params):
    conn = get_conn()

    by_status = rows_to_list(conn.execute("""
        SELECT status, COUNT(*) as count FROM bills
        WHERE status IS NOT NULL GROUP BY status ORDER BY count DESC
    """).fetchall())

    by_state = rows_to_list(conn.execute("""
        SELECT state, COUNT(*) as count FROM bills
        WHERE state IS NOT NULL GROUP BY state ORDER BY count DESC LIMIT 20
    """).fetchall())

    by_category_raw = conn.execute("""
        SELECT keyword_tags FROM bills WHERE keyword_tags IS NOT NULL
    """).fetchall()

    category_counts = {}
    for row in by_category_raw:
        try:
            tags = json.loads(row[0])
            for tag in tags:
                category_counts[tag] = category_counts.get(tag, 0) + 1
        except Exception:
            pass
    by_category = sorted(
        [{"category": k, "count": v} for k, v in category_counts.items()],
        key=lambda x: x["count"], reverse=True
    )

    conn.close()
    return {"by_status": by_status, "by_state": by_state, "by_category": by_category}


def handle_filters(_params):
    conn = get_conn()
    states   = [r[0] for r in conn.execute(
        "SELECT DISTINCT state FROM bills WHERE state IS NOT NULL ORDER BY state"
    ).fetchall()]
    statuses = [r[0] for r in conn.execute(
        "SELECT DISTINCT status FROM bills WHERE status IS NOT NULL ORDER BY status"
    ).fetchall()]
    conn.close()
    return {"states": states, "statuses": statuses}


def handle_legislators(params):
    search = params.get("search", [None])[0]
    party  = params.get("party", [None])[0]

    where, args = [], []
    if search:
        where.append("bs.legislator_name LIKE ?")
        args.append(f"%{search}%")
    if party:
        where.append("bs.legislator_party = ?")
        args.append(party)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_conn()
    rows = conn.execute(f"""
        SELECT
            bs.legislator_name, bs.legislator_party, bs.role, bs.district,
            bs.state_code, bs.in_office, bs.ballotpedia_url, bs.follow_the_money_url,
            COUNT(DISTINCT bs.bill_id) AS bill_count,
            GROUP_CONCAT(DISTINCT b.state) AS states_active
        FROM bill_sponsors bs
        LEFT JOIN bills b ON bs.bill_id = b.bill_id
        {where_sql}
        GROUP BY bs.legislator_name
        ORDER BY bill_count DESC
        LIMIT 300
    """, args).fetchall()
    conn.close()
    return {"legislators": rows_to_list(rows)}


def handle_hearings(_params):
    conn = get_conn()
    rows = conn.execute("""
        SELECT h.*, b.state, b.bill_number, b.title AS bill_title
        FROM hearings h
        LEFT JOIN bills b ON h.bill_id = b.bill_id
        ORDER BY h.start_dt DESC NULLS LAST
        LIMIT 200
    """).fetchall()
    conn.close()
    return {"hearings": rows_to_list(rows)}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

ROUTES = {
    "/api/summary":     handle_summary,
    "/api/bills":       handle_bills,
    "/api/bill":        handle_bill_detail,
    "/api/charts":      handle_charts,
    "/api/filters":     handle_filters,
    "/api/legislators": handle_legislators,
    "/api/hearings":    handle_hearings,
}


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Suppress per-request noise; only print errors
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(fmt, *args)

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/" or parsed.path == "/dashboard.html":
            if DASHBOARD_PATH.exists():
                self._send_file(DASHBOARD_PATH, "text/html; charset=utf-8")
            else:
                self._send_json({"error": "dashboard.html not found"}, 404)
            return

        handler = ROUTES.get(parsed.path)
        if handler:
            try:
                if not DB_PATH.exists():
                    self._send_json({"error": f"Database not found at {DB_PATH}. Run the ingestion pipeline first."}, 503)
                    return
                result = handler(params)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "not found"}, 404)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Insurance Bill Tracker dashboard server")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"⚠️  Warning: database not found at {DB_PATH}")
        print("   Run `python cli/ingest.py` first to populate it.")

    url = f"http://localhost:{args.port}"
    print(f"🏛️  Insurance Bill Tracker  →  {url}")
    print("   Press Ctrl+C to stop.\n")

    if not args.no_browser:
        webbrowser.open(url)

    server = HTTPServer(("localhost", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
