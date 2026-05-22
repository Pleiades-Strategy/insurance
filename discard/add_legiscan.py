import sqlite3
import requests
import csv
import os
from dotenv import load_dotenv
import base64
from PyPDF2 import PdfReader
import tempfile
from bs4 import BeautifulSoup


# Config
csv_file = 'bill_collection/legiscanids.csv'
db_file = "bill_collection/data/insurance_bills.db"
table_name = 'bills'
key_column = 'bill_id'
new_column = 'legiscanid'
other_column = 'full_text'

# Load API key from .env
load_dotenv(dotenv_path="bill_collection/.env")
legiscan_key = os.getenv("legiscan_key")

# Connect to SQLite
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Ensure columns exist
cursor.execute(f"PRAGMA table_info({table_name})")
columns = [col[1] for col in cursor.fetchall()]
if new_column not in columns:
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {new_column} TEXT")
if other_column not in columns:
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {other_column} TEXT")
else:
    print(f"Column '{other_column}' already exists. Clearing its contents...")
    cursor.execute(f"UPDATE {table_name} SET {other_column} = NULL")
    conn.commit()

# Parse PDF
def extract_text_from_pdf_base64(encoded_doc):
    try:
        pdf_bytes = base64.b64decode(encoded_doc)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
            tmp_pdf.write(pdf_bytes)
            tmp_pdf_path = tmp_pdf.name

        reader = PdfReader(tmp_pdf_path)
        paragraphs = []

        for page in reader.pages:
            page_text = page.extract_text() or ''
            raw_paragraphs = page_text.split('\n\n')

            for para in raw_paragraphs:
                clean_para = ' '.join(para.split())
                if clean_para:
                    paragraphs.append(clean_para)

        return '\n\n'.join(paragraphs)

    except Exception as e:
        print(f"PDF text extraction failed: {e}")
        return None
    
# Parse HTML
def extract_clean_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

# Function to fetch full text from LegiScan API
def fetch_bills(legiscan_id):
    try:
        response = requests.get(f"https://api.legiscan.com/?key={legiscan_key}&op=getBillText&id={legiscan_id}")
        response.raise_for_status()
        data = response.json()
        mime = data['text']['mime']
        encoded_doc = data['text']['doc']
        if mime == 'application/pdf':
            decoded_text = extract_text_from_pdf_base64(encoded_doc)
        elif mime == 'text/html':
            text = base64.b64decode(encoded_doc).decode("utf-8",errors="replace")
            decoded_text = extract_clean_text_from_html(text)
        else:
            print(f"Unsupported MIME type: {mime}")
            decoded_text = None
        return decoded_text
    except Exception as e:
        print(f"Error fetching bill ID {legiscan_id}: {e}")
        return None

# Read CSV and update database
with open(csv_file, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        billtrackid = row[key_column]
        legiscanid = row[new_column]

        # Update legiscanid column
        cursor.execute(
            f"""
            UPDATE {table_name}
            SET {new_column} = ?
            WHERE {key_column} = ?
            """,
            (legiscanid, billtrackid)
        )

        # Fetch and update full_text column
        full_text = fetch_bills(legiscanid)
        if full_text:
            cursor.execute(
                f"""
                UPDATE {table_name}
                SET {other_column} = ?
                WHERE {key_column} = ?
                """,
                (full_text, billtrackid)
            )

# Save changes and close connection
conn.commit()
conn.close()