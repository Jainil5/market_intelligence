import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("PRICE_HISTORY_DIR", ROOT_DIR / "data_manager" / "data" / "historical_prices"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
INDIA_TZ = "Asia/Kolkata"
