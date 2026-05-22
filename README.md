# Bill Similarity Engine

A Python toolkit for tracking, tagging, and comparing state-level insurance legislation. Pulls bill metadata from BillTrack50, enriches bills with full legislative text from LegiScan, auto-tags them into policy categories using TF-IDF, and finds similar bills using cosine similarity.

## Setup

1. Clone the repo and install dependencies:
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

2. Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```

You'll need keys for [BillTrack50](https://www.billtrack50.com) and [LegiScan](https://legiscan.com/legiscan).

## Usage

All commands are run from the repo root.

### 1. Ingest bills

Pull bill metadata from BillTrack50 and fetch full text from LegiScan:

```bash
python cli/ingest.py                # full ingestion
python cli/ingest.py --limit 10     # test with 10 bills
python cli/ingest.py --skip-text    # metadata only, skip LegiScan
python cli/ingest.py --force        # re-fetch all, including already enriched
```

### 2. Tag bills

Run TF-IDF analysis to assign policy category tags:

```bash
python cli/retag.py
python cli/retag.py --log my_log.txt
```

Tags include: `wildfire_risk`, `flood_risk`, `insurance_access`, `insurer_of_last_resort`, `risk_mitigation`, `consumer_protection`, `climate_disclosure`, `reinsurance`, `polluter_pays`, `non_admitted`, `study_bill`, `federal_intervention`.

### 3. Find similar bills

Query bills by similarity:

```bash
python cli/find_similar.py --bill-id 1754760 --top 5
python cli/find_similar.py --bill-id 1754760 --state CA
python cli/find_similar.py --bill-id 1754760 --tag wildfire_risk
python cli/find_similar.py --bill-id 1754760 --explain 1839052
python cli/find_similar.py --list
python cli/find_similar.py --list --state FL
```

### 4. Train classifier (optional)

Train a multi-label logistic regression classifier on tagged bills:

```bash
python cli/train.py
python cli/train.py --test-size 0.3
```

## Project structure

```
bill_collection/
├── config.py              # Centralized paths and API config
├── keywords.py            # Policy category keyword dictionaries
├── ingestion/
│   ├── billtrack50.py     # BillTrack50 API client
│   └── legiscan.py        # LegiScan search + text extraction
├── tagging/
│   ├── tfidf_tagger.py    # TF-IDF keyword-based tagging
│   └── classifier.py      # ML classifier (logistic regression)
├── similarity/
│   └── engine.py          # Cosine similarity engine
├── cli/
│   ├── ingest.py          # Pull and enrich bills
│   ├── retag.py           # Re-run tagging
│   ├── find_similar.py    # Query similar bills
│   └── train.py           # Train classifier
├── data/                  # SQLite database (gitignored)
└── model/                 # Trained classifier (gitignored)
```

## Data pipeline

```
BillTrack50 API → metadata (title, state, sponsors, status)
        ↓
LegiScan API → full legislative text (PDF/HTML → plain text)
        ↓
TF-IDF Tagger → policy category tags
        ↓
Similarity Engine → cosine similarity between bills
```

## API dependencies

- **BillTrack50**: Bill metadata, sponsors, actions, keywords
- **LegiScan**: Full bill text (searched by state + bill number, decoded from base64 PDF/HTML)
