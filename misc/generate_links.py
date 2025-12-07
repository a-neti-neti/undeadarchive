from urllib.parse import quote_plus

from models import SessionLocal, Album, AlbumLink, init_db


def main():
    # на всякий случай, создаёт таблицы, если их ещё нет
    init_db()
    db = SessionLocal()

    albums = db.query(Album).all()

    created = 0
    skipped_missing = 0

    for album in albums:
        # Нужны и артист, и название
        if not album.title or not album.artist:
            skipped_missing += 1
            continue

        # Уже есть youtube_search для этого альбома? Пропускаем
        existing = (
            db.query(AlbumLink)
            .filter_by(album_id=album.id, source="youtube_search")
            .first()
        )
        if existing:
            continue

        # Строка запроса для YouTube
        query_str = f"{album.artist.name} {album.title} full album"
        encoded = quote_plus(query_str)

        url = f"https://www.youtube.com/results?search_query={encoded}"

        link = AlbumLink(
            album_id=album.id,
            source="youtube_search",
            url=url,
        )
        db.add(link)
        created += 1

    db.commit()
    db.close()

    print(f"Created {created} youtube_search links.")
    print(f"Skipped {skipped_missing} albums without artist/title.")


if __name__ == "__main__":
    main()
