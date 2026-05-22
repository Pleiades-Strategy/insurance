import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, hamming_loss
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
import joblib
from keywords_module import combined_stopwords
import os
import ast

# load data
conn = sqlite3.connect("bill_collection/data/insurance_bills.db")
panda_df = pd.read_sql_query("SELECT full_text, keyword_tags FROM bills WHERE keyword_tags IS NOT NULL", conn)
conn.close()
print(f"Number of samples loaded: {len(panda_df)}")
print(panda_df.head())

# preprocess
panda_df['labels'] = panda_df['keyword_tags'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
label_counts = pd.Series([item for sublist in panda_df['labels'] for item in sublist]).value_counts()
print(label_counts)
mlb = MultiLabelBinarizer()
y = mlb.fit_transform(panda_df['labels'])


# test / train split
X_train, X_test, y_train, y_test = train_test_split(panda_df['full_text'], y, test_size=0.2, random_state=42)




# pipeline
model = Pipeline([
    ('tfidf', TfidfVectorizer(ngram_range=(1,3), stop_words=combined_stopwords)),
    ('clf', OneVsRestClassifier(LogisticRegression(max_iter=1000, class_weight='balanced')))
])

# train
model.fit(X_train,y_train)
y_pred = model.predict(X_test)
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=mlb.classes_))
print("Test accuracy:", model.score(X_test, y_test))
print("Hamming Loss:", hamming_loss(y_test, y_pred))

os.makedirs("bill_collection/model", exist_ok=True)
joblib.dump((model, mlb), "bill_collection/model/bill_classifier.pkl")


