# scrape_gothic_paged.py

import time
import datetime
import requests
from bs4 import BeautifulSoup

from models import SessionLocal, Artist, Album, Review, init_db

BASE_URL = "http://reviews.gothic.ru"

RU_MONTHS = {
    "Января": 1,
    "Февраля": 2,
    "Марта": 3,
    "Апреля": 4,
    "Мая": 5,
    "Июня": 6,
    "Июля": 7,
    "Августа": 8,
    "Сентября": 9,
    "Октября": 10,
    "Ноября": 11,
    "Декабря": 12,
}

def parse_russian_date(date_str):
    """
    Convert '07 Октября 2002 г.' -> datetime.date(2002, 10, 7)
    """
    if not date_str:
        return None

    # Remove trailing 'г.' or 'г'
    cleaned = date_str.replace("г.", "").replace("г", "").strip()

    parts = cleaned.split()
    if len(parts) < 3:
        return None

    day = int(parts[0])
    month_name = parts[1]
    year = int(parts[2])

    month = RU_MONTHS.get(month_name)
    if not month:
        return None

    try:
        return datetime.date(year, month, day)
    except Exception:
        return None


def get_soup(url):
    """Download a page and return BeautifulSoup object."""
    resp = requests.get(url, timeout=15)
    # Site is old Russian; encoding is usually cp1251
    if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = "cp1251"
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_reviews_from_page(page_num):
    """
    Fetch one ?page=N and parse all review blocks on that page.
    Returns a list of dicts with parsed data.
    """
    url = f"{BASE_URL}/?page={page_num}"
    print(f"Fetching page {page_num}: {url}")
    soup = get_soup(url)

    reviews_data = []

    # TODO: adjust this selector after inspecting ?page=8 in browser.
    # Find the repeating container that wraps ONE review.
    # For now we use a placeholder and will refine it.
    
    # Each full review starts with a header table that has bgcolor="10022A"
    review_blocks = soup.select('table[bgcolor="10022A"]')
    print(f"  Found {len(review_blocks)} candidate blocks")


    for block in review_blocks:
        data = parse_review_block(block, url)
        if data:
            reviews_data.append(data)

    return reviews_data


def parse_review_block(block, page_url):
    """
    Parse ONE review block into
    artist_name, album_title, year, label, rating, published_at, review_text.
    """
    # 1. Title line, e.g.:
    #    A SPELL INSIDE "Hit" / (p) 2002 Triton
    # Title line is inside <a class="reviewtitle"><span>...</span></a>
    title_el = block.select_one("a.reviewtitle span")
    if not title_el:
        return None

    title_line = title_el.get_text(" ", strip=True)
    if not title_line:
        return None

    # 2. Full review text container
    # Full review text sits in the first <span class="main"> after the header table
    main_span = block.find_next("span", class_="main")
    if main_span:
        review_text = main_span.get_text("\n", strip=True)
    else:
        review_text = ""

    # 3. Rough parsing of artist / album / year / label from title_line
    artist_name = None
    album_title = None
    year = None
    label = None

    # Example pattern:
    # A SPELL INSIDE "Hit" / (p) 2002 Triton
    line = title_line

    # Extract album title inside quotes if present
    if '"' in line:
        parts = line.split('"')
        # parts: [before, album, after]
        if len(parts) >= 3:
            artist_part = parts[0]
            album_title = parts[1].strip()
            tail = parts[2]
        else:
            artist_part = line
            tail = ""
    else:
        artist_part = line
        tail = ""

    artist_name = artist_part.strip(" -/")

    import re
    year_match = re.search(r"\b(19|20)\d{2}\b", line)
    if year_match:
        try:
            year = int(year_match.group(0))
        except ValueError:
            year = None

    # Very rough label extraction: text after year
    if year_match:
        label_text = line[year_match.end():].strip(" /-")
        if label_text:
            label = label_text

    # Basic sanity check: must have artist and album OR some text
    if not artist_name and not album_title and not review_text:
        return None

    # 4. Author is in the first <span class="author"> after the header
    author = None
    author_span = block.find_next("span", class_="author")
    if author_span:
        author = author_span.get_text(strip=True)


    # 5. Rating from icons after author_span (two-step strategy)
    rating = None
    if author_span:
        from bs4 import Tag

        icons = []

        def collect_icons(start_node):
            node = start_node
            while node and not (isinstance(node, Tag) and node.name.lower() == "hr"):
                if isinstance(node, Tag) and node.name.lower() == "img":
                    icons.append(node)
                node = node.next_sibling

        # First try: icons directly after <span class="author">
        collect_icons(author_span.next_sibling)

        # Fallback: icons after parent (e.g. <a><span class="author">...</span></a>)
        if not icons and isinstance(author_span.parent, Tag):
            collect_icons(author_span.parent.next_sibling)

        if icons:
            rating = len(icons)



    # 6. Published date in the right-hand <td align="right">
    published_at = None
    published_td = block.find("td", align="right")
    if published_td:
        text = published_td.get_text(" ", strip=True)
        raw_date = text.replace("опубликовано", "").strip()
        published_at = parse_russian_date(raw_date)


    # 7. Cover URL from /cd/ image in main_span
    cover_url = None
    if main_span:
        cover_img = main_span.find("img", src=lambda s: s and "/cd/" in s)
        if cover_img and cover_img.get("src"):
            cover_url = cover_img["src"]
            if cover_url.startswith("/"):
                cover_url = BASE_URL + cover_url

    return {
        "artist_name": artist_name or "Unknown Artist",
        "album_title": album_title or "Unknown Album",
        "year": year,
        "label": label,
        "rating": rating,
        "published_at": published_at,
        "review_text": review_text,
        "review_url": page_url,
        "cover_url": cover_url,
        "author": author,
    }


def upsert_review(session, data):
    """
    Insert or update Artist, Album, Review in the database.
    """
    artist_name = data["artist_name"]
    album_title = data["album_title"]

    # 1. Artist
    artist = session.query(Artist).filter_by(name=artist_name).first()
    if not artist:
        artist = Artist(name=artist_name)
        session.add(artist)
        session.flush()  # assign artist.id

    # 2. Album
    album = (
        session.query(Album)
        .filter_by(artist_id=artist.id, title=album_title)
        .first()
    )
    if not album:
        album = Album(
            artist_id=artist.id,
            title=album_title,
            year=data["year"],
            label=data["label"],
            genre=None,
            cover_url=data["cover_url"],
        )
        session.add(album)
        session.flush()  # assign album.id

    # 3. Upsert Review (allow multiple reviews per album)
    review = (
        session.query(Review)
        .filter_by(
            album_id=album.id,
            author=data["author"],
            published_at=data["published_at"],
        )
        .first()
    )

    if not review:
        review = Review(
            album_id=album.id,
            author=data["author"],
            rating=data["rating"],
            published_at=data["published_at"],
            review_text=data["review_text"],
        )
        session.add(review)
    else:
        # optional: keep DB idempotent if you re-scrape
        review.rating = data["rating"]
        review.review_text = data["review_text"]


    session.commit()


MAX_PAGE = 61

def main():
    init_db()
    session = SessionLocal()

    for page in range(0, MAX_PAGE + 1):
        print(f"Scraping page {page}...")

        reviews = extract_reviews_from_page(page)

        if not reviews:
            print(f"No reviews found on page {page} – stopping.")
            break

        print(f"Saving {len(reviews)} reviews from page {page}")
        for data in reviews:
            upsert_review(session, data)

        time.sleep(1)

    session.close()


if __name__ == "__main__":
    main()
