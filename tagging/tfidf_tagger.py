"""
TF-IDF based bill tagging pipeline.
Analyzes full bill text and assigns policy category tags using
TF-IDF term importance matched against keyword dictionaries.
"""

import sqlite3
import numpy as np
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH
from keywords import combined_stopwords, tag_keywords


def preprocess_text(text):
    """
    Clean and lemmatize bill text for TF-IDF analysis.
    - Lowercase, remove numbers and punctuation
    - Lemmatize with spaCy, filter stopwords and short tokens
    """
    text = text.lower()
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def load_bills_with_text(db_path=None):
    """Load all bills that have full_text from the database."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("SELECT bill_id, full_text FROM bills WHERE full_text IS NOT NULL AND keyword_tags IS NULL")
    rows = cursor.fetchall()
    conn.close()
    return [(row[0], row[1]) for row in rows if row[0] and row[1]]


def tag_from_tfidf(tfidf_vec, feature_names, top_n=50):
    """
    Match top TF-IDF terms against the keyword dictionary to assign tags.
    Returns (matched_tags, triggering_keywords, top_terms).
    """
    top_indices = np.argsort(tfidf_vec.toarray()[0])[::-1][:top_n]
    top_terms = set([feature_names[i] for i in top_indices])

    matched_tags = []
    tag_log = {}

    for tag, keywords in tag_keywords.items():
        for keyword in keywords:
            if keyword.lower() in top_terms:
                matched_tags.append(tag)
                tag_log[tag] = keyword
                break

    return matched_tags, tag_log, top_terms


def update_tags_in_db(updates, db_path=None):
    """Write tag assignments back to the database."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # Ensure keyword_tags column exists
    cursor.execute("PRAGMA table_info(bills)")
    columns = [col[1] for col in cursor.fetchall()]
    if "keyword_tags" not in columns:
        cursor.execute("ALTER TABLE bills ADD COLUMN keyword_tags TEXT")

    for bill_id, tags in updates.items():
        tag_str = json.dumps(tags)
        cursor.execute(
            "UPDATE bills SET keyword_tags = ? WHERE bill_id = ?",
            (tag_str, bill_id),
        )

    conn.commit()
    conn.close()


def write_log_file(log_path, tag_results):
    """Write detailed tagging log for review."""
    with open(log_path, "w") as f:
        for bill_id, (tags, triggers, top_terms) in tag_results.items():
            f.write(f"Bill ID: {bill_id}\n")
            f.write(f"Matched Tags: {tags}\n")
            f.write(f"Triggering Keywords: {triggers}\n")
            f.write(f"Top TF-IDF Terms: {list(top_terms)}\n")
            f.write("-" * 50 + "\n")


def run_tagging(db_path=None, log_path="tagging_log.txt"):
    """
    Full tagging pipeline:
    1. Load bills with full text
    2. Preprocess and vectorize
    3. Match against keyword dictionary
    4. Write tags to database
    """
    documents = load_bills_with_text(db_path)
    if not documents:
        print("No bills with full text found.")
        return {}

    print(f"Tagging {len(documents)} bills...")

    # Preprocess and vectorize
    texts = [preprocess_text(doc[1]) for doc in documents]
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words=combined_stopwords)
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    # Tag each bill
    bill_tag_updates = {}
    log_details = {}

    for i, row in enumerate(documents):
        bill_id = row[0]
        tfidf_vec = tfidf_matrix[i]
        tags, triggers, top_terms = tag_from_tfidf(tfidf_vec, feature_names)
        bill_tag_updates[bill_id] = tags
        log_details[bill_id] = (tags, triggers, top_terms)

    # Write results
    update_tags_in_db(bill_tag_updates, db_path)
    write_log_file(log_path, log_details)
    print(f"Tagging complete. {len(bill_tag_updates)} bills tagged.")

    return bill_tag_updates


if __name__ == "__main__":
    run_tagging()
