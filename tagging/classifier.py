"""
Multi-label bill classifier using TF-IDF + Logistic Regression.
Trains on bills that have been tagged by the TF-IDF tagger,
then can predict tags for new bills.
"""

import sqlite3
import os
import ast
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, hamming_loss
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_PATH, MODEL_DIR
from keywords import combined_stopwords


def load_training_data(db_path=None):
    """Load bills with full_text and keyword_tags for training."""
    db = db_path or str(DB_PATH)
    conn = sqlite3.connect(db)
    df = pd.read_sql_query(
        "SELECT full_text, keyword_tags FROM bills WHERE keyword_tags IS NOT NULL AND full_text IS NOT NULL",
        conn,
    )
    conn.close()

    df["labels"] = df["keyword_tags"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) else x
    )
    # Filter out bills with empty tag lists
    df = df[df["labels"].apply(len) > 0]

    return df


def train_classifier(db_path=None, test_size=0.2):
    """
    Train a multi-label classifier on tagged bills.
    Returns (model, label_binarizer) and saves to model/ directory.
    """
    df = load_training_data(db_path)
    print(f"Training on {len(df)} labeled bills.")

    if len(df) < 5:
        print("Not enough labeled bills to train. Need at least 5.")
        return None, None

    # Label distribution
    label_counts = pd.Series(
        [item for sublist in df["labels"] for item in sublist]
    ).value_counts()
    print(f"\nLabel distribution:\n{label_counts}\n")

    # Encode labels
    mlb = MultiLabelBinarizer()
    y = mlb.fit_transform(df["labels"])

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        df["full_text"], y, test_size=test_size, random_state=42
    )

    # Build pipeline
    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 3), stop_words=combined_stopwords)),
        ("clf", OneVsRestClassifier(
            LogisticRegression(max_iter=1000, class_weight="balanced")
        )),
    ])

    # Train and evaluate
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    print("Classification Report:")
    print(classification_report(y_test, y_pred, target_names=mlb.classes_))
    print(f"Hamming Loss: {hamming_loss(y_test, y_pred):.4f}")

    # Save model
    MODEL_DIR.mkdir(exist_ok=True)
    model_path = MODEL_DIR / "bill_classifier.pkl"
    joblib.dump((model, mlb), model_path)
    print(f"Model saved to {model_path}")

    return model, mlb


def predict_tags(text, model_path=None):
    """Predict tags for a single bill text using the trained classifier."""
    path = model_path or (MODEL_DIR / "bill_classifier.pkl")
    model, mlb = joblib.load(path)
    prediction = model.predict([text])
    tags = mlb.inverse_transform(prediction)
    return list(tags[0]) if tags[0] else []


if __name__ == "__main__":
    train_classifier()
