"""
LegiScan API integration for fetching full bill text.
Replaces the old CSV-based manual mapping with automated API search:
  1. Search by state + bill_number → get LegiScan bill_id
  2. Get bill details → find the latest text document ID
  3. Fetch bill text → decode PDF or HTML to plain text
"""

import requests
import sqlite3
import time
import base64
import tempfile
import logging
from bs4 import BeautifulSoup
try:
    from PyPDF2 import PdfReader
except ImportError:
    from pypdf import PdfReader

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import LEGISCAN_KEY, LEGISCAN_API_URL, DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Rate limiting: stay well within LegiScan's limits
REQUEST_DELAY = 0.3  # seconds between API calls


def _legiscan_request(params):
    """Make a rate-limited request to the LegiScan API."""
    params["key"] = LEGISCAN_KEY
    time.sleep(REQUEST_DELAY)
    try:
        response = requests.get(LEGISCAN_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ERROR":
            logger.warning(f"LegiScan API error: {data.get('alert', {}).get('message', 'Unknown')}")
            return None
        return data
    except requests.RequestException as e:
        logger.error(f"LegiScan request failed: {e}")
        return None


def search_bill(state, bill_number):
    """
    Search LegiScan for a bill by state and bill number.
    Returns the LegiScan bill_id, or None if not found.
    """
    # Clean up bill number for search (e.g., "AB 123" → "AB123", "HB 1234" → "HB1234")
    clean_bill = bill_number.strip().replace(" ", "")

    data = _legiscan_request({
        "op": "search",
        "state": state,
        "bill": clean_bill,
    })

    if not data:
        return None

    search_results = data.get("searchresult", {})

    # searchresult has numeric keys for results + a 'summary' key
    for key, result in search_results.items():
        if key == "summary":
            continue
        if isinstance(result, dict):
            # Match on bill number (case-insensitive)
            result_bill = result.get("bill_number", "").replace(" ", "")
            if result_bill.upper() == clean_bill.upper():
                bill_id = result.get("bill_id")
                logger.info(f"Found LegiScan bill_id {bill_id} for {state} {bill_number}")
                return bill_id

    # If exact match not found, take the first result as best match
    for key, result in search_results.items():
        if key == "summary":
            continue
        if isinstance(result, dict):
            bill_id = result.get("bill_id")
            logger.info(f"Best match LegiScan bill_id {bill_id} for {state} {bill_number}")
            return bill_id

    logger.warning(f"No LegiScan results for {state} {bill_number}")
    return None


def fetch_bill_details(legiscan_bill_id):
    """
    Get bill details from LegiScan, including the latest text document ID.
    Returns the text_id for the most recent bill text, or None.
    """
    data = _legiscan_request({
        "op": "getBill",
        "id": legiscan_bill_id,
    })

    if not data:
        return None

    bill = data.get("bill", {})
    texts = bill.get("texts", [])

    if not texts:
        logger.warning(f"No text documents for LegiScan bill {legiscan_bill_id}")
        return None

    # Get the most recent text document (last in list)
    latest_text = texts[-1]
    text_id = latest_text.get("doc_id") or latest_text.get("text_id")
    logger.info(f"Found text_id {text_id} for LegiScan bill {legiscan_bill_id}")
    return text_id


def fetch_bill_text(text_id):
    """
    Fetch and decode the full text of a bill from LegiScan.
    Handles both PDF and HTML formats.
    Returns plain text string, or None on failure.
    """
    data = _legiscan_request({
        "op": "getBillText",
        "id": text_id,
    })

    if not data:
        return None

    text_data = data.get("text", {})
    mime = text_data.get("mime", "")
    encoded_doc = text_data.get("doc", "")

    if not encoded_doc:
        logger.warning(f"Empty document for text_id {text_id}")
        return None

    if mime == "application/pdf":
        return _extract_text_from_pdf(encoded_doc)
    elif mime == "text/html":
        return _extract_text_from_html(encoded_doc)
    else:
        logger.warning(f"Unsupported MIME type: {mime} for text_id {text_id}")
        return None


def _extract_text_from_pdf(encoded_doc):
    """Decode base64 PDF and extract text."""
    try:
        pdf_bytes = base64.b64decode(encoded_doc)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        reader = PdfReader(tmp_path)
        paragraphs = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            for para in page_text.split("\n\n"):
                clean = " ".join(para.split())
                if clean:
                    paragraphs.append(clean)

        return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return None


def _extract_text_from_html(encoded_doc):
    """Decode base64 HTML and extract clean text."""
    try:
        html = base64.b64decode(encoded_doc).decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "header", "footer", "nav"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"HTML extraction failed: {e}")
        return None


def enrich_bill(state, bill_number):
    """
    Full enrichment pipeline for a single bill:
    search → get details → fetch text.
    Returns (legiscan_id, full_text) or (None, None).
    """
    # Step 1: Search for the bill
    legiscan_id = search_bill(state, bill_number)
    if not legiscan_id:
        return None, None

    # Step 2: Get the text document ID
    text_id = fetch_bill_details(legiscan_id)
    if not text_id:
        return legiscan_id, None

    # Step 3: Fetch and decode the text
    full_text = fetch_bill_text(text_id)
    return legiscan_id, full_text


def enrich_all_bills(db_path=None, force=False, limit=None):
    """
    Enrich all bills in the database with LegiScan full text.
    Skips bills that already have full_text unless force=True.
    Returns dict of {bill_id: status} for each bill processed.
    """
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Ensure columns exist
    cursor.execute("PRAGMA table_info(bills)")
    columns = [col[1] for col in cursor.fetchall()]
    if "legiscanid" not in columns:
        cursor.execute("ALTER TABLE bills ADD COLUMN legiscanid TEXT")
    if "full_text" not in columns:
        cursor.execute("ALTER TABLE bills ADD COLUMN full_text TEXT")
    conn.commit()

    # Get bills to process
    if force:
        cursor.execute("SELECT bill_id, state, bill_number FROM bills")
    else:
        cursor.execute(
            "SELECT bill_id, state, bill_number FROM bills WHERE full_text IS NULL"
        )

    bills = cursor.fetchall()
    if limit:
        bills = bills[:limit]

    results = {}
    total = len(bills)
    print(f"Enriching {total} bills with LegiScan full text...")

    for i, (bill_id, state, bill_number) in enumerate(bills, 1):
        print(f"  [{i}/{total}] {state} {bill_number}...", end=" ")

        legiscan_id, full_text = enrich_bill(state, bill_number)

        if legiscan_id:
            cursor.execute(
                "UPDATE bills SET legiscanid = ? WHERE bill_id = ?",
                (str(legiscan_id), bill_id),
            )

        if full_text:
            cursor.execute(
                "UPDATE bills SET full_text = ? WHERE bill_id = ?",
                (full_text, bill_id),
            )
            print(f"OK ({len(full_text)} chars)")
            results[bill_id] = "enriched"
        elif legiscan_id:
            print("found bill, no text available")
            results[bill_id] = "no_text"
        else:
            print("not found on LegiScan")
            results[bill_id] = "not_found"

        conn.commit()  # Commit after each bill so progress isn't lost

    conn.close()

    # Summary
    enriched = sum(1 for s in results.values() if s == "enriched")
    no_text = sum(1 for s in results.values() if s == "no_text")
    not_found = sum(1 for s in results.values() if s == "not_found")
    print(f"\nDone. Enriched: {enriched}, No text: {no_text}, Not found: {not_found}")

    return results


if __name__ == "__main__":
    enrich_all_bills()
