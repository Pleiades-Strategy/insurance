import requests
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="bill_collection/.env")
api_key = os.getenv("billtrack50_key")
api_url = "https://www.billtrack50.com/BT50Api/2.1/json/billSheets/54300/bills"
DB_FILE = "bill_collection/data/raw_insurance_bills.db"

def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS bills (
        bill_id TEXT PRIMARY KEY,
        state TEXT,
        bill_number TEXT,
        title TEXT NOT NULL,
        summary TEXT,
        ai_summary TEXT,
        session TEXT,
        status TEXT,
        introduced_date TEXT,
        last_action_date TEXT,
        bill_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bill_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id TEXT,
        action_date TEXT NOT NULL,
        description TEXT NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print("SQLite database and tables created.")

def fetch_bills():
    headers = {'Authorization': f'apikey {api_key}'}
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error {response.status_code}: {response.text}")
        return []

def insert_bills(api_response):
    """Inserts bill metadata into the SQLite database."""
    if "bills" not in api_response:
        print("Invalid API response format")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        state = bill.get("stateCode", "")
        bill_number = bill.get("stateBillID", "")
        title = bill.get("billName", "")
        summary = bill.get("summary", "")
        ai_summary = bill.get("aiSummary", "")
        session = bill.get("session", "")
        status = bill.get("billProgress", "")
        introduced_date = bill.get("created", None)
        last_action_date = bill.get("lastActionDate", None)
        bill_url = bill.get("officialDocument", "")

        cursor.execute("""
            INSERT OR IGNORE INTO bills
            (bill_id, state, bill_number, title, summary, ai_summary, session, status, 
             introduced_date, last_action_date, bill_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (bill_id, state, bill_number, title, summary, ai_summary, session, status, 
              introduced_date, last_action_date, bill_url))

    conn.commit()
    conn.close()
    print(f"{len(api_response['bills'])} bills inserted into SQLite.")


def insert_sponsors(api_response):
    """Inserts bill sponsors into the SQLite database."""
    if "bills" not in api_response:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        sponsors = bill.get("sponsors", "")

        if sponsors:
            sponsor_list = sponsors.split(", ")
            for sponsor in sponsor_list:
                cursor.execute("""
                    INSERT INTO bill_sponsors (bill_id, legislator_name)
                    VALUES (?, ?);
                """, (bill_id, sponsor.strip()))

    conn.commit()
    conn.close()
    print("Sponsors inserted into SQLite.")

def insert_keywords(api_response):
    """Inserts bill keywords into the SQLite database."""
    if "bills" not in api_response:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        keywords = bill.get("keywords", "")

        if keywords:
            keyword_list = keywords.split(", ")
            for keyword in keyword_list:
                cursor.execute("""
                    INSERT INTO bill_keywords (bill_id, keyword)
                    VALUES (?, ?);
                """, (bill_id, keyword.strip()))

    conn.commit()
    conn.close()
    print("Keywords inserted into SQLite.")

def insert_actions(api_response):
    """Inserts bill actions into the SQLite database."""
    if "bills" not in api_response:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    for bill in api_response["bills"]:
        bill_id = bill.get("billID")
        last_action = bill.get("lastAction", "")
        last_action_date = bill.get("lastActionDate", None)

        if last_action and last_action_date:
            cursor.execute("""
                INSERT INTO bill_actions (bill_id, action_date, description)
                VALUES (?, ?, ?);
            """, (bill_id, last_action_date, last_action))

    conn.commit()
    conn.close()
    print("Actions inserted into SQLite.")

def run_script():
    print("doing my job")
    create_tables()
    api_response = fetch_bills()
    if api_response:
        insert_bills(api_response)
        insert_sponsors(api_response)
        insert_actions(api_response)
        insert_keywords(api_response)
    else:
        print("No bills to be found.")

if __name__ == "__main__":
    run_script()