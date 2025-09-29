import logging
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_BASE_URL = os.getenv("GITHUB_BASE_URL", "https://github.com/search")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("github-crawler")