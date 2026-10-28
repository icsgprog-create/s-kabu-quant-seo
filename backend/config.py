import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_OUTPUT_DIR = BASE_DIR / "frontend" / "data"
STOCKS_OUTPUT_DIR = DATA_OUTPUT_DIR / "stocks"
CACHE_DIR = BASE_DIR / "backend" / ".cache"

STOCKS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5-flash-lite")
AI_CACHE_EXPIRE_DAYS = 30
AI_REGENERATE_CHANGE_THRESHOLD = 0.10
JPX_LISTED_COMPANIES_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"

DEFAULT_TARGET_TICKERS = [
    {"code": "7203", "name": "トヨタ自動車", "sector": "輸送用機器"},
    {"code": "8306", "name": "三菱UFJフィナンシャル・グループ", "sector": "銀行業"},
    {"code": "8316", "name": "三井住友フィナンシャルグループ", "sector": "銀行業"},
    {"code": "9432", "name": "日本電信電話", "sector": "情報・通信業"},
    {"code": "9433", "name": "KDDI", "sector": "情報・通信業"},
    {"code": "8058", "name": "三菱商事", "sector": "卸売業"},
    {"code": "8001", "name": "伊藤忠商事", "sector": "卸売業"},
    {"code": "2914", "name": "日本たばこ産業", "sector": "食料品"},
    {"code": "4502", "name": "武田薬品工業", "sector": "医薬品"},
    {"code": "7751", "name": "キヤノン", "sector": "電気機器"},
    {"code": "6758", "name": "ソニーグループ", "sector": "電気機器"},
    {"code": "8766", "name": "東京海上ホールディングス", "sector": "保険業"},
    {"code": "1925", "name": "大和ハウス工業", "sector": "建設業"},
    {"code": "8591", "name": "オリックス", "sector": "その他金融業"},
    {"code": "9101", "name": "日本郵船", "sector": "海運業"},
    {"code": "3687", "name": "フィックスターズ", "sector": "情報・通信業"},
    {"code": "285A", "name": "キオクシアホールディングス", "sector": "電気機器"},
]
