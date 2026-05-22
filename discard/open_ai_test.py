import os
import sqlite3
import requests
from openai import OpenAI
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
from limits import RateLimitItemPerMinute
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
import logging

load_dotenv(dotenv_path="bill_collection/.env")
open_ai_key = os.getenv("open_ai_key")
client = OpenAI(api_key=open_ai_key)
api_key = os.getenv("billtrack50_key")
api_url = "https://www.billtrack50.com/BT50Api/2.1/json/billSheets/54300/bills"

logging.basicConfig(filename="openai_test.log", level=logging.INFO, format="%(asctime)s - %(message)s")

MAX_RPM = 3
MAX_TPM = 600000
storage = MemoryStorage()
rate_limiter = MovingWindowRateLimiter(storage)
rate_limit_item = RateLimitItemPerMinute(MAX_RPM)
current_rpm = 0
current_tokens = 0
last_checked = datetime.now()

def is_rate_limited():
    return not rate_limiter.test(rate_limit_item, "openai_request")



def reset_counters():
    global current_rpm, current_tokens, last_checked
    if (datetime.now() - last_checked).seconds >= 60:
        current_rpm = 0
        current_tokens = 0
        last_checked = datetime.now()

db_file = "insurance_testing.db"

def create_tables(db):
    conn = sqlite3.connect(db)
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

    conn = sqlite3.connect(db_file)
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

    conn = sqlite3.connect(db_file)
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

def insert_actions(api_response):
    """Inserts bill actions into the SQLite database."""
    if "bills" not in api_response:
        return

    conn = sqlite3.connect(db_file)
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

def create_db(db_file):
    create_tables(db_file)
    api_response = fetch_bills()
    if api_response:
        insert_bills(api_response)
        insert_sponsors(api_response)
        insert_actions(api_response)
    else:
        print("No bills to be found.")

def get_bills(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    today = datetime.today()
    one_week_ago = today - timedelta(days=7)
    one_week_ahead = today + timedelta(days=7)
    start_date = one_week_ago.strftime("%m/%d/%Y")
    end_date = one_week_ahead.strftime("%m/%d/%Y")  

    query = """
    SELECT bill_id, title, state, last_action_date, summary
    FROM bills
    WHERE last_action_date >= ? AND last_action_date <= ?
    ORDER BY last_action_date DESC
    LIMIT 5;
    """
    
    cursor.execute(query, (start_date, end_date))
    bills = cursor.fetchall()
    conn.close()
    return bills

def get_keywords_from_openai(summary):
    if is_rate_limited():
        print("Rate limit reached. Waiting before making a request...")
        time.sleep(20)
    prompt = f"Extract keywords from the following bill summary:\n\n{summary}\n\nKeywords:"
    try:
        response = client.completions.create(
            model="gpt-3.5-turbo",
            prompt=prompt,
            max_tokens=50,
            temperature=0.5
        )
        tokens_used = response['usage']['total_tokens']
        keywords_text = response.choices[0].text.strip()
        keywords = [keyword.strip() for keyword in keywords_text.split(",")]
        if current_tokens > MAX_TPM:
            print("Token limit exceeded, waiting to reset token counter.")
            time.sleep(60)
            current_tokens = 0
        current_rpm += 1
        print("Response received:", response)
        logging.info(f"API Query successful. RPM: {current_rpm}, Tokens used: {tokens_used}")
        return keywords
    except Exception as e:
        logging.error(f"Error extracting keywords: {e}")
        print(f"Error extracting keywords: {e}")
        return []
    
def insert_keywords(bill_id, keywords):
    """Insert extracted keywords into the bill_keywords table."""
    if not keywords:
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for keyword in keywords:
        cursor.execute("""
            INSERT INTO bill_keywords (bill_id, keyword)
            VALUES (?, ?);
        """, (bill_id, keyword))

    conn.commit()
    conn.close()
    
def process_bills():
    bills = get_bills(db_file)
    
    for bill in bills:
        bill_id, title, _, _, summary = bill
        keywords = get_keywords_from_openai(summary)
        
        if keywords:
            insert_keywords(bill_id, keywords)
            logging.info(f"Keywords for Bill ID {bill_id} inserted successfully.")
        else:
            logging.warning(f"No keywords extracted for Bill ID {bill_id}.")

if __name__ == "__main__":
    create_db(db_file)
    process_bills()