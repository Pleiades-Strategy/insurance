"""
Fetches insurance-related bills from BillTrack50 API and stores them in SQLite.
"""

import requests
import sqlite3
import re
import time
from config import BILLTRACK50_KEY, BILLTRACK50_API_URL, DB_PATH


def create_tables(db_path=None):
    """Create the database schema if it doesn't exist."""
    db = db_path or DB_PATH
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id          TEXT PRIMARY KEY,
        state            TEXT,
        bill_number      TEXT,
        title            TEXT NOT NULL,
        summary          TEXT,
        ai_summary       TEXT,
        session          TEXT,
        status           TEXT,
        introduced_date  TEXT,
        last_action_date TEXT,
        bill_url         TEXT,
        document_link    TEXT,
        legiscanid       TEXT,
        full_text        TEXT,
        keyword_tags     TEXT,
        notes            TEXT,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS bill_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id TEXT,
        keyword TEXT,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bill_sponsors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id TEXT,
        legislator_name TEXT,
        legislator_party TEXT,
        legislator_id INTEGER,
        knowwho_person_id INTEGER,
        state_code TEXT,
        role TEXT,
        district TEXT,
        in_office INTEGER,
        ballotpedia_url TEXT,
        follow_the_money_url TEXT,
        UNIQUE(bill_id, legislator_name),
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bill_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id TEXT,
        action_date TEXT NOT NULL,
        description TEXT NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS hearings (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id       TEXT,
        title         TEXT,
        start_dt      TEXT,
        end_dt        TEXT,
        all_day       INTEGER,
        status        TEXT,
        location      TEXT,
        description   TEXT,
        event_link    TEXT,
        hangouts_link TEXT,
        event_id      TEXT UNIQUE,
        created_at    TEXT,
        updated_at    TEXT,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print("Database schema ready.")


def fetch_bills():
    """Fetch all bills from BillTrack50 API."""
    headers = {"Authorization": f"apikey {BILLTRACK50_KEY}"}
    response = requests.get(BILLTRACK50_API_URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"Fetched {len(data.get('bills', []))} bills from BillTrack50.")
        return data
    else:
        print(f"BillTrack50 API error {response.status_code}: {response.text}")
        return {}


def insert_bills(api_response, db_path=None):
    """Insert bill metadata into the database. Skips existing bills."""
    if "bills" not in api_response:
        print("Invalid API response format — no 'bills' key.")
        return 0

    db = db_path or DB_PATH
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    count = 0

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        cursor.execute("""
            INSERT OR IGNORE INTO bills
            (bill_id, state, bill_number, title, summary, ai_summary, session,
             status, introduced_date, last_action_date, bill_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            bill_id,
            bill.get("stateCode", ""),
            bill.get("stateBillID", ""),
            bill.get("billName", ""),
            bill.get("summary", ""),
            bill.get("aiSummary", ""),
            bill.get("session", ""),
            bill.get("billProgress", ""),
            bill.get("created", None),
            bill.get("lastActionDate", None),
            bill.get("officialDocument", ""),
        ))
        if cursor.rowcount > 0:
            count += 1

    conn.commit()
    conn.close()
    print(f"Inserted {count} new bills ({len(api_response['bills'])} total from API).")
    return count


def insert_sponsors(api_response, db_path=None):
    """Insert bill sponsors. Only inserts new sponsors, preserving existing legislator details."""
    if "bills" not in api_response:
        return

    db = db_path or DB_PATH
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    pattern = r"(.+?)\s*\(([^)]+)\)\s*\*?"

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        sponsors = bill.get("sponsors", "")

        if sponsors:
            for sponsor in sponsors.split(","):
                sponsor = sponsor.strip()
                match = re.match(pattern, sponsor)

                if match:
                    name = match.group(1).strip()
                    party = match.group(2).strip()
                else:
                    name = sponsor
                    party = None

                # INSERT OR IGNORE skips the row if (bill_id, legislator_name)
                # already exists, preserving any legislator details already fetched
                cursor.execute(
                    "INSERT OR IGNORE INTO bill_sponsors (bill_id, legislator_name, legislator_party) VALUES (?, ?, ?);",
                    (bill_id, name, party),
                )

    conn.commit()
    conn.close()
    print("Sponsors updated.")


def insert_keywords(api_response, db_path=None):
    """Insert bill keywords from BillTrack50. Clears existing first."""
    if "bills" not in api_response:
        return

    db = db_path or DB_PATH
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        keywords = bill.get("keywords", "")

        cursor.execute("DELETE FROM bill_keywords WHERE bill_id = ?", (bill_id,))

        if keywords:
            for keyword in keywords.split(", "):
                cursor.execute(
                    "INSERT INTO bill_keywords (bill_id, keyword) VALUES (?, ?);",
                    (bill_id, keyword.strip()),
                )

    conn.commit()
    conn.close()
    print("Keywords updated.")


def insert_actions(api_response, db_path=None):
    """Insert latest bill actions."""
    if "bills" not in api_response:
        return

    db = db_path or DB_PATH
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        last_action = bill.get("lastAction", "")
        last_action_date = bill.get("lastActionDate", None)

        if last_action and last_action_date:
            # Only insert if this action doesn't already exist
            cursor.execute(
                """SELECT COUNT(*) FROM bill_actions
                   WHERE bill_id = ? AND action_date = ? AND description = ?""",
                (bill_id, last_action_date, last_action),
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO bill_actions (bill_id, action_date, description) VALUES (?, ?, ?);",
                    (bill_id, last_action_date, last_action),
                )

    conn.commit()
    conn.close()
    print("Actions updated.")


def fetch_legislator_details(db_path=None):
    """Look up legislator details from BillTrack50 for sponsors missing that info."""
    db = db_path or DB_PATH
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Find unique legislators that haven't been looked up yet
    cursor.execute("""
        SELECT DISTINCT bs.legislator_name, b.state
        FROM bill_sponsors bs
        JOIN bills b ON bs.bill_id = b.bill_id
        WHERE bs.legislator_id IS NULL
    """)
    unique_sponsors = cursor.fetchall()

    if not unique_sponsors:
        print("All sponsors already have legislator details.")
        conn.close()
        return

    print(f"Looking up details for {len(unique_sponsors)} unique legislators...")

    for name, state in unique_sponsors:
        # Call BillTrack50 legislators API
        headers = {"Authorization": f"apikey {BILLTRACK50_KEY}"}
        params = {
            "legislatorName": name,
            "stateCodes": state,
        }
        response = requests.get(
            "https://www.billtrack50.com/BT50Api/2.1/json/legislators",
            headers=headers,
            params=params,
        )

        if response.status_code != 200:
            print(f"  API error for {name}: {response.status_code}")
            continue

        data = response.json()
        legislators = data.get("legislators", [])

        if not legislators:
            print(f"  No results for {name} ({state}), skipping.")
            continue

        # Take the first result
        leg = legislators[0]

        # Update ALL rows for this legislator across all their sponsored bills
        cursor.execute("""
            UPDATE bill_sponsors
            SET legislator_id = ?,
                knowwho_person_id = ?,
                state_code = ?,
                role = ?,
                district = ?,
                in_office = ?,
                ballotpedia_url = ?,
                follow_the_money_url = ?
            WHERE legislator_name = ?
            AND bill_id IN (SELECT bill_id FROM bills WHERE state = ?)
        """, (
            leg.get("legislatorID"),
            leg.get("knowWhoPersonID"),
            leg.get("stateCode"),
            leg.get("role"),
            leg.get("district"),
            1 if leg.get("inOffice") else 0,
            leg.get("ballotpediaURL"),
            leg.get("followTheMoneyUrl"),
            name,
            state,
        ))

        print(f"  Updated {name} ({state}) — {leg.get('role', '')} {leg.get('district', '')}")

        time.sleep(0.3)  # Rate limiting

    conn.commit()
    conn.close()
    print("Legislator details updated.")


def run_ingestion(db_path=None):
    """Full BillTrack50 ingestion pipeline."""
    db = db_path or DB_PATH
    create_tables(db)
    api_response = fetch_bills()

    if not api_response or "bills" not in api_response:
        print("No bills fetched.")
        return 0

    count = insert_bills(api_response, db)
    insert_sponsors(api_response, db)
    insert_actions(api_response, db)
    insert_keywords(api_response, db)
    fetch_legislator_details(db)
    return len(api_response["bills"])


if __name__ == "__main__":
    run_ingestion()
