import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
STATE_DIR = ROOT / "state"
DATA_DIR.mkdir(exist_ok=True)
STATE_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "news.db"
DEFAULT_CSV_PATH = DATA_DIR / "articles.csv"

# Crawl
BASE_INDEX_URL = "https://news.gbimonthly.com/tw/article/index.php"
USER_AGENT = "Mozilla/5.0 (compatible; GBI-Pipeline/1.0)"
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.5"))
PAGES_TO_SCAN = int(os.getenv("PAGES_TO_SCAN", "2"))

# LLM
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# Misc
DEFAULT_TIMEOUT = 20