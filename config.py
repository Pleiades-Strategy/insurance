"""
Centralized configuration for the bill collection pipeline.
All paths are relative to this file's directory (the repo root).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Repo root = directory containing this file
ROOT_DIR = Path(__file__).parent

# Load environment variables
load_dotenv(ROOT_DIR / ".env")

# Directories
DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = ROOT_DIR / "model"

# Database
DB_PATH = DATA_DIR / "insurance_bills.db"

# API keys
BILLTRACK50_KEY = os.getenv("billtrack50_key")
LEGISCAN_KEY = os.getenv("legiscan_key")
OPENAI_KEY = os.getenv("open_ai_key")
AIRTABLE_KEY = os.getenv("airtable_key")
AIRTABLE_BASE_ID = os.getenv("airtable_base_id")

# API endpoints
BILLTRACK50_API_URL = "https://www.billtrack50.com/BT50Api/2.1/json/billSheets/62344/bills"
LEGISCAN_API_URL = "https://api.legiscan.com/"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)