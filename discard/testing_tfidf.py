import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from keywords_module import combined_stopwords, tag_keywords
import numpy as np
import json
import re
import spacy

# config
INPUT_DB_FILE = "bill_collection/data/raw_insurance_bills.db"
OUTPUT_DB_FILE = "bill_collection/data/insurance_bills.db"
TABLE_NAME = "bills"
TEXT_COLUMN = "full_text"
ID_COLUMN = "bill_id"
TAG_COLUMN = "keyword_tags"
nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
LOG_FILE = "tagging_log.txt"

# tag definitions


# text preprocessing
def preprocess_text(text):
    text = text.lower()
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    
    doc = nlp(text)
    tokens = [token.lemma_ for token in doc if not token.is_stop and len(token) > 2]
    return " ".join(tokens)

# add keywords column
def ensure_column_exists(db_path, table, column):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [col[1] for col in cursor.fetchall()]
    if column not in columns:
        print(f"Adding '{column}' column to table '{table}'")
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")
        conn.commit()
    else:
        print(f"Column '{column}' already exists. Cleared its contents.")
        cursor.execute(f"UPDATE {table} SET {column} = NULL")
        conn.commit()
    conn.close()

# get docs from table
def load_documents_from_db(db_path, table, text_column, id_column):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f"SELECT {id_column}, {text_column} FROM {table}"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [(row[0],row[1]) for row in rows if row[0] is not None and row[1] is not None]

# tf-idf tagging
def tag_from_tfidf(tfidf_vec, feature_names, tag_keywords, top_n=20, verbose=False):
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
    if verbose:
        print("Top TF-IDF terms:", list(top_terms))
        print("Matched tags:", matched_tags)
        print("Triggering keywords:", tag_log)   
    
    return matched_tags, tag_log, top_terms

# write tags into table
def update_tags_in_db(db_path, table, id_column, tag_column, updates):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for bill_id, tags in updates.items():
        tag_str = json.dumps(tags)
        cursor.execute(f"""
            UPDATE {table}
            SET {tag_column} = ?
            WHERE {id_column} = ?
        """, (tag_str, bill_id))
    conn.commit()
    conn.close()

# logging results
def write_log_file(log_path, tag_results):
    with open(log_path, "w") as f:
        for bill_id, (tags, triggers, top_terms) in tag_results.items():
            f.write(f"Bill ID: {bill_id}\n")
            f.write(f"Matched Tags: {tags}\n")
            f.write(f"Triggering Keywords: {triggers}\n")
            f.write(f"Top TF-IDF Terms: {list(top_terms)}\n")
            f.write("-" * 50 + "\n")

# main execution
if __name__ == "__main__":
    ensure_column_exists(INPUT_DB_FILE,TABLE_NAME,TAG_COLUMN)
    documents = load_documents_from_db(INPUT_DB_FILE, TABLE_NAME, TEXT_COLUMN, ID_COLUMN)

    # preprocess & vectorize
    texts = [preprocess_text(doc[1]) for doc in documents]
    vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words=combined_stopwords)
    tfidf_matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    # tagging 
    bill_tag_updates = {}
    log_details = {}

    for i, row in enumerate(documents):
        bill_id = row[0]
        tf_idf_vec = tfidf_matrix[i]
        tags, triggers, top_terms = tag_from_tfidf(tf_idf_vec, feature_names, tag_keywords)
        bill_tag_updates[bill_id] = tags
        log_details[bill_id] = (tags, triggers, top_terms)


    update_tags_in_db(OUTPUT_DB_FILE, TABLE_NAME, ID_COLUMN, TAG_COLUMN, bill_tag_updates)
    write_log_file(LOG_FILE, log_details)
    print(f"Tagging complete. Tags written to database.")