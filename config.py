WIKI_URL = "https://en.wikipedia.org/wiki/Deaths_in_2025#December"
EN_WIKI_BASE = "https://en.wikipedia.org"
RU_WIKI_BASE = "https://ru.wikipedia.org"
MEDIAWIKI_API_URL = "https://en.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent": "WikipediaParserTest/1.0 (contact: test@example.com)"
}

EMPTY_PARAGRAPH_CLASS = "mw-empty-elt"
FIRST_PARAGRAPH_INDEX = 0
FALLBACK_PARAGRAPH_INDEX = 1

HTTP_TIMEOUT = 10
HTTP_TOO_MANY_REQUESTS = 403

REQUEST_DELAY_SECONDS = 3
RATE_LIMIT_BACKOFF_SECONDS = 60

STATE_FILE = "state.json"
CHECK_INTERVAL = 300

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "test@example.com"
SMTP_PASS = "password"
TO_EMAIL = "receiver@example.com"
