# export_albums_metadata.py

from models import SessionLocal, Album, Artist
from sqlalchemy.orm import joinedload


def export_albums_metadata(path: str = "albums_metadata.txt") -> None:
    db = SessionLocal()

    # Load all albums with artist, sorted alphabetically
    albums = (
        db.query(Album)
        .options(joinedload(Album.artist))
        .join(Artist, Album.artist_id == Artist.id)
        .order_by(
            Artist.name.asc(),
            Album.title.asc(),
            Album.year.asc().nulls_last()
        )
        .all()
    )

    lines: list[str] = []
    lines.append("Source: gothic.ru / old.gothic.ru reviews archive")
    lines.append("")  # blank line

    for album in albums:
        artist_name = album.artist.name if album.artist else "Unknown artist"
        title = album.title or "Unknown title"

        parts = [f"Artist: {artist_name}", f"Album: {title}"]

        if album.year:
            parts.append(f"Year: {album.year}")
        if getattr(album, "label", None):
            parts.append(f"Label: {album.label}")

        lines.append(" | ".join(parts))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    db.close()
    print(f"Exported {len(albums)} albums to {path}")


if __name__ == "__main__":
    export_albums_metadata()
