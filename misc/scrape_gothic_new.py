# scrape_gothic_new.py

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models import SessionLocal, Artist, Album, Review


BASE_URL = "https://gothic.ru"

# TODO: put the real URL of the "Полный список рецензий" page here.
# If it's exactly the page you copied, paste that URL:
INDEX_URL = "https://gothic.ru/review/"  # or the full_list page, adjust manually


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def parse_index() -> list[str]:
    """
    Parse the 'full list of reviews' page and return a list of review URLs.
    We just collect all <ul class="review-list"> -> <li><a href="...">
    """
    soup = fetch(INDEX_URL)

    urls: list[str] = []

    for ul in soup.select("ul.review-list"):
        for a in ul.select("li > a"):
            href = a.get("href")
            if not href:
                continue
            full_url = urljoin(BASE_URL, href)
            urls.append(full_url)

    # Deduplicate, sort for stable processing
    urls = sorted(set(urls))
    return urls


def split_title(full_title: str):
    """
    Input: 'THE 69 EYES “Universal Monsters” (2016)'
    Output: (artist_name, album_title, year_int or None)
    """
    s = full_title.strip()

    # Extract year from '(YYYY)' at the end
    year = None
    m_year = re.search(r"\((\d{4})\)\s*$", s)
    if m_year:
        year = int(m_year.group(1))
        s = s[: m_year.start()].strip()

    # Try to extract album name between «» or “” or ""
    album = None
    artist = None

    m_quotes = re.search(r"[«“\"](?P<album>.+?)[»”\"]", s)
    if m_quotes:
        album = m_quotes.group("album").strip()
        artist = s[: m_quotes.start()].strip()
    else:
        # Fallback: if no quotes, we just treat whole string as both
        artist = s.strip()
        album = s.strip()

    return artist, album, year


def get_or_create_artist(db, name: str) -> Artist:
    name = (name or "").strip()
    if not name:
        name = "Unknown"

    artist = db.query(Artist).filter(Artist.name == name).one_or_none()
    if artist is None:
        artist = Artist(name=name)
        db.add(artist)
        db.commit()
        db.refresh(artist)
    return artist


def parse_review_page(url: str) -> dict:
    """
    Parse one review page on the new gothic.ru site.
    Returns a dict with keys:
    artist_name, album_title, year, review_text, author, rating, review_url, cover_url
    """
    soup = fetch(url)

    # Title: prefer header h3
    h3 = soup.select_one("div.header h3")
    if h3:
        title_text = h3.get_text(strip=True)
    else:
        # Fallback: last breadcrumbs piece, or URL
        crumbs = soup.select("div.breadcrumbs")
        if crumbs:
            title_text = crumbs[-1].get_text(strip=True)
        else:
            title_text = url

    artist_name, album_title, year = split_title(title_text)

    # Review text: all <p> inside div.review-content
    review_div = soup.select_one("div.review-content")
    paragraphs = []
    if review_div:
        for p in review_div.find_all("p"):
            txt = p.get_text(" ", strip=True)
            if txt:
                paragraphs.append(txt)
    review_text = "\n\n".join(paragraphs).strip()

    # Rating and author
    rating = None
    author = None

    for p in soup.find_all("p"):
        strong = p.find("strong")
        if not strong:
            continue
        label = strong.get_text(strip=True)
        text = p.get_text(" ", strip=True)

        if "Оценка" in label:
            # Extract 9 from "Оценка: 9/10"
            m = re.search(r"(\d+)", text)
            if m:
                rating = int(m.group(1))

        elif "Автор" in label:
            author = text.replace(label, "").replace(":", "").strip()

    # normalize to 1–5 scale
    if rating is not None:
        rating = max(1, min(5, round(rating / 2)))


    # Cover URL
    cover_url = None
    img = soup.select_one("div.review-content img.review-cover")
    if img and img.get("src"):
        cover_url = urljoin(BASE_URL, img["src"])

    return {
        "artist_name": artist_name,
        "album_title": album_title,
        "year": year,
        "review_text": review_text,
        "author": author,
        "rating": rating,
        #"review_url": url,
        "cover_url": cover_url,
    }


def import_review(db, data: dict):
    """
    Insert album + review into DB if not already present.

    De-duplication rule:
    - if an Album with same (artist_id, title) exists, we don't create a new one.
      Instead we can update review_url, cover_url, rating/author if they were missing.
    """

    artist = get_or_create_artist(db, data["artist_name"])

    existing_album = (
        db.query(Album)
        .filter(
            Album.title == data["album_title"],
            Album.artist_id == artist.id,
        )
        .one_or_none()
    )

    if existing_album:
        # Update some fields if empty and new data is available
        changed = False

        #if not existing_album.review_url and data["review_url"]:
            #existing_album.review_url = data["review_url"]
            #changed = True

        if not existing_album.cover_url and data["cover_url"]:
            existing_album.cover_url = data["cover_url"]
            changed = True

        # If there is already a Review linked to this album, we may update it
        if existing_album.review:
            r = existing_album.review
            if r.author is None and data["author"]:
                r.author = data["author"]
                changed = True
            if r.rating is None and data["rating"] is not None:
                r.rating = data["rating"]
                changed = True
            if data["review_text"] and not r.review_text:
                r.review_text = data["review_text"]
                changed = True
        else:
            # No review yet – create one and link it
            review = Review(
                album_id=existing_album.id,
                author=data["author"],
                rating=data["rating"],
                published_at=None,  # no date on page
                review_text=data["review_text"] or "",
            )
            db.add(review)
            changed = True

        if changed:
            db.commit()
        return

    # No album yet → create album, then review
    album = Album(
        artist_id=artist.id,
        title=data["album_title"],
        year=data["year"],
        label=None,
        genre=None,
        #review_url=data["review_url"],
        cover_url=data["cover_url"],
    )
    db.add(album)
    db.commit()      # ensure album.id is assigned
    db.refresh(album)

    review = Review(
        album_id=album.id,
        author=data["author"],
        rating=data["rating"],
        published_at=None,
        review_text=data["review_text"] or "",
    )
    db.add(review)
    db.commit()


def scrape_all():
    db = SessionLocal()

    urls = parse_index()
    print(f"Found {len(urls)} review URLs on new gothic.ru index")

    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] {url}")
        try:
            data = parse_review_page(url)
            import_review(db, data)
        except Exception as e:
            print(f"Error on {url}: {e}")

    db.close()


if __name__ == "__main__":
    scrape_all()
