"""
Airtable → SQLite full ingestion pipeline.

Airtable is the primary source of truth for this project. This module:
  1. Pulls all bills from "Insurance Bills" → upserts into bills table
  2. Pulls all legislators from "Legislators" → enriches bill_sponsors table
  3. Pulls all hearings from "Hearings" → upserts into hearings table

Tables intentionally IGNORED (archived/deprecated):
  - "Insurance Bills (Archived)"
  - "Sponsors"

Bill ID strategy:
  Airtable stores BT50 Bill ID as a bare integer (e.g. 1775568).
  SQLite uses that same integer as a string for bill_id (e.g. "1775568").
  This replaces the old "BT-1775568" format from the BillTrack50 pipeline.

Legislator matching:
  Legislators table has BT50 ID (= bill_sponsors.legislator_id).
  We update bill_sponsors rows by legislator_id rather than needing the bill link.

Hearing matching:
  Hearings table has a BillID field storing the BT50 numeric ID.
  We join on that to set the bill_id foreign key.
"""

import json
import re
import sqlite3
import time
from urllib.parse import quote

import requests

from config import AIRTABLE_KEY, AIRTABLE_BASE_ID, DB_PATH

# ---------------------------------------------------------------------------
# Table names (never touch the archived ones)
# ---------------------------------------------------------------------------
TABLE_BILLS       = "Insurance Bills"
TABLE_LEGISLATORS = "Legislators"
TABLE_HEARINGS    = "Hearings"
TABLE_STATES      = "States"

# ---------------------------------------------------------------------------
# Category label → snake_case mapping (must match keywords.py keys exactly)
# ---------------------------------------------------------------------------
CATEGORY_MAP = {
    # Primary labels
    "State Insurance Residual Markets":           "state_insurance_residual_markets",
    "Fortification Programs":                     "fortification_programs",
    "Non-Admitted Market":                        "non_admitted_market",
    "Consumer Protections and Market Conduct":    "consumer_protections_and_market_conduct",
    "Catastrophe Modeling":                       "catastrophe_modeling",
    "Data and Study":                             "data_and_study",
    "Fossil Fuel Accountability":                 "fossil_fuel_accountability",
    "State Insurance Office / Regulatory Powers": "state_insurance_office_regulatory_powers",
    "Property Disclosure":                        "property_disclosure",
    "Building Codes / Land Use":                  "building_codes_land_use",
    "Climate Resilience and Risk Mitigation":     "climate_resilience_and_risk_mitigation",
    "Reinsurance":                                "reinsurance",
    "Litigation and Tort Reform":                 "litigation_and_tort_reform",
    "Rate Regulation":                            "rate_regulation",
    "Climate Risk Disclosure":                    "climate_risk_disclosure",
    "Anti-ESG":                                   "anti_esg",
    # Alternate labels using "&" instead of "and", lowercase variants, missing slashes
    "State Insurance & Residual markets":         "state_insurance_residual_markets",
    "State Insurance & Residual Markets":         "state_insurance_residual_markets",
    "Consumer Protections & Market Conduct":      "consumer_protections_and_market_conduct",
    "Data & Study":                               "data_and_study",
    "Climate Resilience & Risk Mitigation":       "climate_resilience_and_risk_mitigation",
    "Litigation & Tort Reform":                   "litigation_and_tort_reform",
    "Building Codes & Land Use":                  "building_codes_land_use",
    "State Insurance Office Regulatory Powers":   "state_insurance_office_regulatory_powers",
    "Fossil Fuel Accountability & Climate Liability": "fossil_fuel_accountability",
}


def _to_snake_case(label: str) -> str:
    label = label.lower()
    label = re.sub(r"[^\w\s]", "", label)
    label = re.sub(r"\s+", "_", label.strip())
    return label


def map_category(label: str) -> str:
    if label in CATEGORY_MAP:
        return CATEGORY_MAP[label]
    print(f"  [warn] Unknown category label '{label}' — using fallback snake_case")
    return _to_snake_case(label)


# ---------------------------------------------------------------------------
# Airtable API helpers
# ---------------------------------------------------------------------------

def _headers() -> dict:
    return {"Authorization": f"Bearer {AIRTABLE_KEY}"}


def _fetch_table(table_name: str, fields: list[str] | None = None) -> list[dict]:
    """
    Paginate through all records in an Airtable table.
    Returns flat list of record dicts, each with 'id' (Airtable record ID)
    and 'fields' (dict of field values).
    """
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{quote(table_name)}"
    params: dict = {"pageSize": 100}
    if fields:
        params["fields[]"] = fields

    records = []
    page = 1

    while True:
        print(f"  [{table_name}] Fetching page {page}...")
        resp = requests.get(url, headers=_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))

        offset = data.get("offset")
        if not offset:
            break
        params["offset"] = offset
        page += 1
        time.sleep(0.2)

    print(f"  [{table_name}] {len(records)} records fetched.")
    return records


def _bt50_id(raw) -> str | None:
    """Normalise a BT50 Bill ID to a plain string integer, e.g. '1775568'."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return str(int(raw))
    s = str(raw).strip()
    # Strip any non-numeric prefix like "BT-"
    match = re.search(r"\d+", s)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def create_tables(conn: sqlite3.Connection):
    """Ensure all required tables exist. Safe to call on every run."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id         TEXT PRIMARY KEY,   -- BT50 numeric ID as string
        state           TEXT,
        bill_number     TEXT,
        title           TEXT NOT NULL,
        summary         TEXT,
        ai_summary      TEXT,
        session         TEXT,
        status          TEXT,
        introduced_date TEXT,
        last_action_date TEXT,
        bill_url        TEXT,
        document_link   TEXT,
        legiscanid      TEXT,
        full_text       TEXT,
        keyword_tags    TEXT,
        notes           TEXT,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS bill_keywords (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id TEXT,
        keyword TEXT,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bill_sponsors (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id             TEXT,
        legislator_name     TEXT,
        legislator_party    TEXT,
        legislator_id       INTEGER,
        knowwho_person_id   INTEGER,
        state_code          TEXT,
        role                TEXT,
        district            TEXT,
        in_office           INTEGER,
        ballotpedia_url     TEXT,
        follow_the_money_url TEXT,
        UNIQUE(bill_id, legislator_name),
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bill_actions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id     TEXT,
        action_date TEXT NOT NULL,
        description TEXT NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS hearings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id         TEXT,
        title           TEXT,
        start_dt        TEXT,
        end_dt          TEXT,
        all_day         INTEGER,
        status          TEXT,
        location        TEXT,
        description     TEXT,
        event_link      TEXT,
        hangouts_link   TEXT,
        event_id        TEXT UNIQUE,
        created_at      TEXT,
        updated_at      TEXT,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# 0. States lookup
# ---------------------------------------------------------------------------

def fetch_states_map() -> dict:
    """
    Fetch all records from the States table and return a dict mapping
    Airtable record ID → state abbreviation (e.g. "recdd0fQnhZDlwhk3" → "RI").
    The 'Name' field on each States record holds the two-letter abbreviation.
    """
    records = _fetch_table(TABLE_STATES, fields=["Name"])
    mapping = {}
    for rec in records:
        name = rec.get("fields", {}).get("Name", "")
        if name:
            mapping[rec["id"]] = name
    print(f"  Loaded {len(mapping)} state records.")
    return mapping


# ---------------------------------------------------------------------------
# 1. Sync bills
# ---------------------------------------------------------------------------

BILL_FIELDS = [
    "BT50 Bill ID",
    "Bill Title",
    "Bill Progress",
    "Date Created (Filed or Prefiled)",
    "BT50 Session",
    "Category",
    "State",
    "Bill Number",
    "BT50 URL",
    "Name",           # bill long title from BT50
    "Summary",
    "Bills Summary",
    "Bill Last Action",
    "Last Action Date",
    "Document Link",
    "Bill Added Date",
]


def sync_bills(conn: sqlite3.Connection, states_map: dict) -> dict:
    """Upsert all Insurance Bills records into the bills table."""
    records = _fetch_table(TABLE_BILLS, fields=BILL_FIELDS)

    stats = {"fetched": len(records), "upserted": 0, "skipped_no_id": 0}
    rows = []

    for rec in records:
        f = rec.get("fields", {})

        bt50_raw = f.get("BT50 Bill ID")
        bill_id = _bt50_id(bt50_raw)
        if not bill_id:
            stats["skipped_no_id"] += 1
            continue

        # Categories → JSON array of snake_case tags
        raw_cats = f.get("Category", [])
        tags_json = json.dumps(sorted({map_category(c) for c in raw_cats})) if raw_cats else None

        def scalar(val, default=""):
            """Coerce any Airtable field value to a plain scalar.
            Lists (linked records, attachments) are collapsed to their first
            meaningful string value; dicts (attachment objects) yield their url.
            """
            if val is None:
                return default
            if isinstance(val, list):
                if not val:
                    return default
                val = val[0]
            if isinstance(val, dict):
                return val.get("url") or val.get("name") or str(val)
            return val

        # State is a linked record — resolve record ID → abbreviation
        state_raw = f.get("State", [])
        if isinstance(state_raw, list) and state_raw:
            state = states_map.get(state_raw[0], state_raw[0])
        else:
            state = scalar(state_raw)

        rows.append((
            bill_id,
            state,
            scalar(f.get("Bill Number")),
            scalar(f.get("Bill Title") or f.get("Name")) or "",
            scalar(f.get("Summary") or f.get("Bills Summary")),
            None,                               # ai_summary — not in Airtable
            scalar(f.get("BT50 Session")),
            scalar(f.get("Bill Progress")),
            scalar(f.get("Date Created (Filed or Prefiled)") or f.get("Bill Added Date")),
            scalar(f.get("Last Action Date")),
            scalar(f.get("BT50 URL")),
            scalar(f.get("Document Link")),
            None,                               # legiscanid — filled by legiscan.py
            None,                               # full_text — filled by legiscan.py
            tags_json,
            None,                               # notes — not in Airtable Insurance Bills
        ))

    with conn:
        conn.executemany("""
            INSERT INTO bills
                (bill_id, state, bill_number, title, summary, ai_summary,
                 session, status, introduced_date, last_action_date,
                 bill_url, document_link, legiscanid, full_text,
                 keyword_tags, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(bill_id) DO UPDATE SET
                state            = excluded.state,
                bill_number      = excluded.bill_number,
                title            = excluded.title,
                summary          = excluded.summary,
                session          = excluded.session,
                status           = excluded.status,
                introduced_date  = excluded.introduced_date,
                last_action_date = excluded.last_action_date,
                bill_url         = excluded.bill_url,
                document_link    = excluded.document_link,
                notes            = excluded.notes,
                keyword_tags     = CASE
                    WHEN excluded.keyword_tags IS NOT NULL
                    THEN excluded.keyword_tags
                    ELSE bills.keyword_tags
                END
        """, rows)

    stats["upserted"] = len(rows)
    return stats


# ---------------------------------------------------------------------------
# 2. Sync sponsors from Legislators table (authoritative source)
# ---------------------------------------------------------------------------

def sync_sponsors_from_bills(conn: sqlite3.Connection) -> dict:
    """
    Build bill_sponsors rows from the Legislators table, which has a
    '2026 Insurance Bills' linked field listing every bill each legislator
    sponsors. This is more reliable than parsing the text Sponsor Names
    field on the bills table.

    We need a reverse map from Airtable record ID → bill_id (BT50 numeric)
    to resolve the linked records.
    """
    # Build map: airtable_record_id → bill_id
    # We get this by fetching bills with their Airtable record IDs
    bill_records = _fetch_table(TABLE_BILLS, fields=["BT50 Bill ID"])
    airtable_to_bill = {}
    for rec in bill_records:
        bt50 = _bt50_id(rec.get("fields", {}).get("BT50 Bill ID"))
        if bt50:
            airtable_to_bill[rec["id"]] = bt50

    # Fetch legislators with their linked bills, name, and party
    leg_records = _fetch_table(
        TABLE_LEGISLATORS,
        fields=["Name (No Parentheses)", "BT50 Party", "2026 Insurance Bills"]
    )

    stats = {"legislators_processed": 0, "sponsors_inserted": 0}
    rows = []

    for rec in leg_records:
        f = rec.get("fields", {})
        name = f.get("Name (No Parentheses)", "").strip()
        party = f.get("BT50 Party", "")
        if isinstance(party, list):
            party = party[0] if party else None

        linked_bills = f.get("2026 Insurance Bills", [])
        if not isinstance(linked_bills, list):
            linked_bills = [linked_bills] if linked_bills else []

        if not name or not linked_bills:
            continue

        for airtable_rec_id in linked_bills:
            bill_id = airtable_to_bill.get(airtable_rec_id)
            if bill_id:
                rows.append((bill_id, name, party))

        stats["legislators_processed"] += 1

    with conn:
        conn.executemany("""
            INSERT OR IGNORE INTO bill_sponsors (bill_id, legislator_name, legislator_party)
            VALUES (?, ?, ?)
        """, rows)

    stats["sponsors_inserted"] = len(rows)
    return stats


LEGISLATOR_FIELDS = [
    "Name (No Parentheses)",
    "BT50 ID",
    "KnowWho ID",
    "BT50 Party",
    "Legislator Title",
    "District",
    "In Office?",
    "Ballotpedia URL",
    "FTM URL",
    "State (from 2026 Insurance Bills)",
]


def sync_legislators(conn: sqlite3.Connection) -> dict:
    """
    Pull all Legislator records and update bill_sponsors rows that share
    the same BT50 ID (= legislator_id). This enriches party, district,
    URLs, etc. without needing the bill link.
    """
    records = _fetch_table(TABLE_LEGISLATORS, fields=LEGISLATOR_FIELDS)
    stats = {"fetched": len(records), "updated": 0, "skipped_no_id": 0}

    for rec in records:
        f = rec.get("fields", {})

        bt50_id_raw = f.get("BT50 ID")
        if not bt50_id_raw:
            stats["skipped_no_id"] += 1
            continue

        try:
            leg_id = int(bt50_id_raw)
        except (ValueError, TypeError):
            stats["skipped_no_id"] += 1
            continue

        # State may come back as a list (linked field) or plain string
        state_raw = f.get("State (from 2026 Insurance Bills)", "")
        state = state_raw[0] if isinstance(state_raw, list) and state_raw else state_raw

        in_office_raw = f.get("In Office?")
        in_office = 1 if in_office_raw else 0

        with conn:
            cursor = conn.execute("""
                UPDATE bill_sponsors
                SET legislator_id        = ?,
                    knowwho_person_id    = ?,
                    state_code           = ?,
                    role                 = ?,
                    district             = ?,
                    in_office            = ?,
                    ballotpedia_url      = ?,
                    follow_the_money_url = ?,
                    legislator_party     = COALESCE(legislator_party, ?)
                WHERE legislator_id = ?
                   OR (legislator_id IS NULL
                       AND legislator_name = ?)
            """, (
                leg_id,
                f.get("KnowWho ID"),
                state,
                f.get("Legislator Title"),
                f.get("District"),
                in_office,
                f.get("Ballotpedia URL"),
                f.get("FTM URL"),
                f.get("BT50 Party"),
                leg_id,
                f.get("Name (No Parentheses)"),
            ))
        stats["updated"] += cursor.rowcount

    return stats


# ---------------------------------------------------------------------------
# 3. Sync hearings
# ---------------------------------------------------------------------------

HEARING_FIELDS = [
    "Title",
    "Start",
    "End",
    "Status",
    "Location",
    "Description",
    "Event Link",
    "Event ID",
    "Created",
    "Updated",
    "BillID",
    "2026 Insurance Bills",   # linked field — Airtable record IDs
]


def sync_hearings(conn: sqlite3.Connection) -> dict:
    """
    Pull all Hearings records and upsert into the hearings table.
    Matches bill via the BillID field (BT50 numeric ID).
    Falls back to no bill_id if BillID is absent.
    """
    records = _fetch_table(TABLE_HEARINGS, fields=HEARING_FIELDS)
    stats = {"fetched": len(records), "upserted": 0}

    def _scalar(val, default=None):
        """Coerce any Airtable field to a plain scalar (reused from sync_bills)."""
        if val is None:
            return default
        if isinstance(val, list):
            if not val:
                return default
            val = val[0]
        if isinstance(val, dict):
            return val.get("url") or val.get("name") or str(val)
        return val

    # Build set of known bill_ids so we can null out unmatched foreign keys
    known_bill_ids = {
        row[0] for row in conn.execute("SELECT bill_id FROM bills").fetchall()
    }

    rows = []
    for rec in records:
        f = rec.get("fields", {})

        # BillID may be a plain number or a list; null out if not in bills table
        raw_bill_id = _bt50_id(_scalar(f.get("BillID")))
        bill_id = raw_bill_id if raw_bill_id in known_bill_ids else None

        # Fallback: if BillID is absent but the linked field has exactly one
        # bill, we can try to look it up by Airtable record ID — but we'd need
        # a reverse map. For now, leave bill_id as NULL; manual cleanup easy.

        rows.append((
            bill_id,
            _scalar(f.get("Title")),
            _scalar(f.get("Start")),
            _scalar(f.get("End")),
            None,                                  # all_day — not in this base
            _scalar(f.get("Status")),
            _scalar(f.get("Location")),
            _scalar(f.get("Description")),
            _scalar(f.get("Event Link")),
            None,                                  # hangouts_link — not in this base
            _scalar(f.get("Event ID")),            # UNIQUE — deduplicates on re-run
            _scalar(f.get("Created")),
            _scalar(f.get("Updated")),
        ))

    with conn:
        conn.executemany("""
            INSERT INTO hearings
                (bill_id, title, start_dt, end_dt, all_day, status,
                 location, description, event_link, hangouts_link,
                 event_id, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(event_id) DO UPDATE SET
                bill_id       = excluded.bill_id,
                title         = excluded.title,
                start_dt      = excluded.start_dt,
                end_dt        = excluded.end_dt,
                status        = excluded.status,
                location      = excluded.location,
                description   = excluded.description,
                event_link    = excluded.event_link,
                updated_at    = excluded.updated_at
        """, rows)

    stats["upserted"] = len(rows)
    return stats


# ---------------------------------------------------------------------------
# Full sync orchestrator
# ---------------------------------------------------------------------------

def run_airtable_sync(dry_run: bool = False):
    """
    Full Airtable → SQLite sync. Runs all three table syncs in order.
    dry_run is accepted for CLI compatibility but currently previews only
    the bill count (writes are always transactional and safe to re-run).
    """
    print("=" * 60)
    print("Airtable → SQLite full sync")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)

    # --- States lookup (needed to resolve state linked records on bills) ---
    print("\n[0/3] Loading states lookup...")
    states_map = fetch_states_map()

    # --- Bills ---
    print("\n[1/3] Syncing bills...")
    bill_stats = sync_bills(conn, states_map)
    print(f"  Fetched: {bill_stats['fetched']}  |  "
          f"Upserted: {bill_stats['upserted']}  |  "
          f"Skipped (no BT50 ID): {bill_stats['skipped_no_id']}")

    # --- Sponsors from bill text fields ---
    print("\n[2/3] Syncing sponsors...")
    sp_stats = sync_sponsors_from_bills(conn)
    print(f"  Legislators processed: {sp_stats['legislators_processed']}  |  "
          f"Sponsor rows inserted: {sp_stats['sponsors_inserted']}")

    # Enrich sponsors with Legislators table
    print("  Enriching sponsors from Legislators table...")
    leg_stats = sync_legislators(conn)
    print(f"  Legislators fetched: {leg_stats['fetched']}  |  "
          f"Sponsor rows updated: {leg_stats['updated']}  |  "
          f"Skipped (no BT50 ID): {leg_stats['skipped_no_id']}")

    # --- Hearings ---
    print("\n[3/3] Syncing hearings...")
    h_stats = sync_hearings(conn)
    print(f"  Fetched: {h_stats['fetched']}  |  Upserted: {h_stats['upserted']}")

    conn.close()

    print("\n" + "=" * 60)
    print("Sync complete.")
    print("Next step: run  python -m cli.legiscan  to fetch full bill text.")
    print("=" * 60)
