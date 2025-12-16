import time
import json
import smtplib
import re
from datetime import date
from urllib.parse import unquote
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from config import *


MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

DAY_RE = re.compile(r"^\d{1,2}$")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(state), f, ensure_ascii=False, indent=2)


def parse_page_date(url):
    m = re.search(r"Deaths_in_([A-Za-z]+)_(\d{4})", url)
    if m:
        return MONTHS.get(m.group(1)), int(m.group(2))

    m = re.search(r"Deaths_in_(\d{4})", url)
    if m:
        return None, int(m.group(1))

    return None, None


def is_current_page(url):
    page_month, page_year = parse_page_date(url)
    today = date.today()

    if page_year != today.year:
        return False

    if page_month is None:
        return True

    return page_month == today.month


def extract_first_paragraph(html):
    soup = BeautifulSoup(html, "lxml")

    content = soup.find("div", id="mw-content-text")
    if not content:
        return ""

    paragraphs = content.find_all("p")
    if not paragraphs:
        return ""

    p = paragraphs[FIRST_PARAGRAPH_INDEX]

    if EMPTY_PARAGRAPH_CLASS in p.get("class", []):
        if len(paragraphs) > FALLBACK_PARAGRAPH_INDEX:
            p = paragraphs[FALLBACK_PARAGRAPH_INDEX]
        else:
            return ""

    for a in p.find_all("a"):
        a.unwrap()
    for sup in p.find_all("sup"):
        sup.decompose()

    return p.get_text(strip=True)


def find_ru_article(href):
    title = unquote(href.replace("/wiki/", ""))

    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "langlinks",
        "lllang": "ru",
    }

    try:
        r = requests.get(
            MEDIAWIKI_API_URL,
            params=params,
            headers=HEADERS,
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()

        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            links = page.get("langlinks")
            if links:
                ru_title = links[0]["*"]
                return f"{RU_WIKI_BASE}/wiki/{ru_title.replace(' ', '_')}"

    except requests.RequestException:
        pass

    return None


def get_text_and_url(href):
    urls = []

    ru_url = find_ru_article(href)
    if ru_url:
        urls.append(ru_url)

    urls.append(f"{EN_WIKI_BASE}{href}")

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)

            if r.status_code == HTTP_TOO_MANY_REQUESTS:
                time.sleep(RATE_LIMIT_BACKOFF_SECONDS)
                return "", url

            if r.status_code != 200:
                continue

            text = extract_first_paragraph(r.text)
            if text:
                return text, url

        except requests.RequestException:
            continue

        time.sleep(REQUEST_DELAY_SECONDS)

    return "", urls[-1]


def is_person_link(href: str) -> bool:
    if not href.startswith("/wiki/"):
        return False
    title = href[len("/wiki/"):]
    if not title:
        return False
    if ":" in title:
        return False
    return True


def extract_person_from_li(li: Tag):
    a = li.find("a", href=True)
    if not a:
        return None

    name = a.get_text(strip=True)
    href = a.get("href", "")

    if not name or not is_person_link(href):
        return None

    return name, href


def iter_entries():
    r = requests.get(WIKI_URL, headers=HEADERS, timeout=HTTP_TIMEOUT)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "lxml")
    content = soup.find("div", id="mw-content-text")
    if not content:
        return

    current = is_current_page(WIKI_URL)
    started = False

    root = content.contents[1] if len(content.contents) > 1 else None
    if not isinstance(root, Tag):
        return

    for node in root:
        if not isinstance(node, Tag):
            continue

        heading = node.find(["h2", "h3", "h4"], recursive=False)
        if heading:
            text = heading.get_text(strip=True)

            if current:
                if text in MONTHS:
                    started = True
            else:
                if DAY_RE.match(text):
                    started = True

            continue

        if not started:
            continue

        if node.name != "ul":
            continue

        for li in node.find_all("li", recursive=False):
            person = extract_person_from_li(li)
            if person:
                yield person


def send_email(subject, body):
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = TO_EMAIL

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=HTTP_TIMEOUT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

    except Exception as exc:
        print("SMTP unavailable:", exc)


def check_updates():
    state = load_state()

    for name, href in iter_entries():
        key = f"{name}|{href}"
        if key in state:
            continue

        time.sleep(REQUEST_DELAY_SECONDS)

        text, url = get_text_and_url(href)
        body = f"{name}\n\n{text}\n\n{url}"

        print("=== Новый пункт найден ===")
        print(body)
        print("==========================\n")

        send_email(f"Новая запись: {name}", body)

        state.add(key)
        save_state(state)


def main():
    while True:
        try:
            check_updates()
        except Exception as exc:
            print("Runtime error:", exc)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
