"""
Bill Similarity Engine.
Uses TF-IDF cosine similarity to find bills with similar legislative text.
"""

import sqlite3
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH
from keywords import combined_stopwords
from tagging.tfidf_tagger import preprocess_text


class SimilarityEngine:
    """
    Builds a TF-IDF index over all bills and computes cosine similarity.

    Usage:
        engine = SimilarityEngine()
        engine.build_index()
        results = engine.find_similar("1754760", top_n=5)
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or str(DB_PATH)
        self.bill_ids = []
        self.bill_metadata = {}  # bill_id → {state, bill_number, title, keyword_tags}
        self.tfidf_matrix = None
        self.vectorizer = None
        self.feature_names = None

    def build_index(self):
        """
        Load all bills with full text, preprocess, and build TF-IDF matrix.
        This is the main setup step — call once, then query multiple times.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bill_id, state, bill_number, title, keyword_tags, full_text
            FROM bills
            WHERE full_text IS NOT NULL
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("No bills with full text found in the database.")
            return

        # Store metadata for display
        self.bill_ids = []
        texts = []
        for bill_id, state, bill_number, title, keyword_tags, full_text in rows:
            self.bill_ids.append(str(bill_id))
            self.bill_metadata[str(bill_id)] = {
                "state": state,
                "bill_number": bill_number,
                "title": title,
                "tags": json.loads(keyword_tags) if keyword_tags else [],
            }
            texts.append(preprocess_text(full_text))

        # Build TF-IDF matrix
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            stop_words=combined_stopwords,
            max_features=10000,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self.feature_names = self.vectorizer.get_feature_names_out()

        print(f"Index built: {len(self.bill_ids)} bills, {len(self.feature_names)} features.")

    def find_similar(self, bill_id, top_n=10, state=None, tag=None):
        """
        Find the top N most similar bills to the given bill_id.

        Args:
            bill_id: BillTrack50 bill ID (string or int)
            top_n: Number of results to return
            state: Optional state filter (e.g., "CA")
            tag: Optional tag filter (e.g., "wildfire_risk")

        Returns:
            List of dicts: [{bill_id, state, bill_number, title, tags, score}, ...]
        """
        bill_id = str(bill_id)

        if bill_id not in self.bill_ids:
            print(f"Bill {bill_id} not found in index.")
            return []

        idx = self.bill_ids.index(bill_id)
        bill_vec = self.tfidf_matrix[idx]

        # Compute similarity against all other bills
        similarities = cosine_similarity(bill_vec, self.tfidf_matrix)[0]

        # Build results (excluding the query bill itself)
        results = []
        for i, score in enumerate(similarities):
            other_id = self.bill_ids[i]
            if other_id == bill_id:
                continue

            meta = self.bill_metadata[other_id]

            # Apply filters
            if state and meta["state"] != state.upper():
                continue
            if tag and tag not in meta["tags"]:
                continue

            results.append({
                "bill_id": other_id,
                "state": meta["state"],
                "bill_number": meta["bill_number"],
                "title": meta["title"],
                "tags": meta["tags"],
                "score": round(float(score), 4),
            })

        # Sort by similarity score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    def explain_similarity(self, bill_id_a, bill_id_b):
        """
        Show the top shared TF-IDF terms that explain why two bills are similar.

        Returns:
            Dict with similarity score and list of shared important terms.
        """
        bill_id_a = str(bill_id_a)
        bill_id_b = str(bill_id_b)

        if bill_id_a not in self.bill_ids or bill_id_b not in self.bill_ids:
            print("One or both bill IDs not found in index.")
            return {}

        idx_a = self.bill_ids.index(bill_id_a)
        idx_b = self.bill_ids.index(bill_id_b)

        vec_a = self.tfidf_matrix[idx_a].toarray()[0]
        vec_b = self.tfidf_matrix[idx_b].toarray()[0]

        # Find terms where both bills have nonzero TF-IDF scores
        shared_mask = (vec_a > 0) & (vec_b > 0)
        shared_indices = np.where(shared_mask)[0]

        # Score shared terms by their combined importance
        shared_terms = []
        for i in shared_indices:
            combined_score = vec_a[i] + vec_b[i]
            shared_terms.append((self.feature_names[i], round(float(combined_score), 4)))

        shared_terms.sort(key=lambda x: x[1], reverse=True)

        score = cosine_similarity(
            self.tfidf_matrix[idx_a], self.tfidf_matrix[idx_b]
        )[0][0]

        return {
            "score": round(float(score), 4),
            "shared_terms": shared_terms[:20],
            "bill_a": self.bill_metadata.get(bill_id_a, {}),
            "bill_b": self.bill_metadata.get(bill_id_b, {}),
        }

    def get_bill_info(self, bill_id):
        """Get metadata for a bill by ID."""
        bill_id = str(bill_id)
        return self.bill_metadata.get(bill_id)
