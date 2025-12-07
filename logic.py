import random
from models import Artist, SessionLocal, UserAlbum, UserSettings,  Album, AlbumLink, Review
from sqlalchemy.orm import joinedload  
from sqlalchemy import and_




# --------------------------------------
# Helper: always get correct UserAlbum row
# --------------------------------------

def get_or_create_user_album(db, album_id: int):
    """
    Ensures that a UserAlbum row exists for this user+album.
    If it doesn't exist, it creates one.
    """

    ua = db.query(UserAlbum).filter_by(
        user_id=1,
        album_id=album_id
    ).one_or_none()

    if ua is None:
        ua = UserAlbum(
            user_id=1,
            album_id=album_id,
            listened=0,
            favorite=0,
            wishlist=0
        )
        db.add(ua)
        db.commit()
        db.refresh(ua)

    return ua


# --------------------------------------
# Toggle functions (simple and intuitive)
# --------------------------------------

def toggle_listened(album_id: int):
    db = SessionLocal()

    ua = get_or_create_user_album(db, album_id)

    # flip 0 to 1 or 1 to 0
    new_value = 1 if ua.listened == 0 else 0
    ua.listened = new_value

    db.commit()
    db.close()

    return new_value


def toggle_favorite(album_id: int):
    db = SessionLocal()
    ua = get_or_create_user_album(db, album_id)

    new_value = 1 if ua.favorite == 0 else 0
    ua.favorite = new_value

    db.commit()
    db.close()
    return new_value


def toggle_wishlist(album_id: int):
    db = SessionLocal()
    ua = get_or_create_user_album(db, album_id)

    new_value = 1 if ua.wishlist == 0 else 0
    ua.wishlist = new_value

    db.commit()
    db.close()
    return new_value



def get_user_album_state(album_id: int):
    """
    Read-only view of user state for a given album.
    Does NOT create rows if missing.
    Returns 0/1 for each flag.
    """
    db = SessionLocal()

    ua = (
        db.query(UserAlbum)
        .filter_by(user_id=1, album_id=album_id)
        .one_or_none()
    )

    db.close()

    if ua is None:
        return {"listened": 0, "favorite": 0, "wishlist": 0}

    return {
        "listened": ua.listened or 0,
        "favorite": ua.favorite or 0,
        "wishlist": ua.wishlist or 0,
    }


# --------------------------------------
# Track last opened album
# --------------------------------------

def set_last_album(album_id: int):
    db = SessionLocal()

    settings = db.query(UserSettings).filter_by(user_id=1).one_or_none()

    if settings is None:
        settings = UserSettings(
            user_id=1,
            last_album_id=album_id,
            random_mode_enabled=1
        )
        db.add(settings)
    else:
        settings.last_album_id = album_id

    db.commit()
    db.close()


def get_random_album(scope: str = "all",
                     only_favorites: bool = False,
                     only_wishlist: bool = False):
    """
    Pick a random album under the given scope and filters.
    scope: "all" / "listened" / "not_listened"
    """
    db = SessionLocal()

    # Use the common query builder so scope + favorites + wishlist all work
    query = build_album_query(db, scope, only_favorites, only_wishlist)

    # Get only IDs (cheap)
    album_ids = [row.id for row in query.with_entities(Album.id).all()]

    if not album_ids:
        db.close()
        return None

    random_id = random.choice(album_ids)

    # Load full album object if you want (artist/review etc.),
    # but app really only needs .id from it.
    album = (
        db.query(Album)
        .options(
            joinedload(Album.artist),
            joinedload(Album.reviews),
        )
        .filter(Album.id == random_id)
        .one_or_none()
    )

    db.close()
    return album

def get_album_by_id(album_id: int):
    """
    Load Album with its artist and review eagerly,
    so we can safely access album.artist and album.review
    after the session is closed.
    """
    db = SessionLocal()

    album = (
        db.query(Album)
        .options(
            joinedload(Album.artist),   # preload related artist
            joinedload(Album.reviews),   # preload related review
        )
        .filter(Album.id == album_id)
        .one_or_none()
    )

    db.close()
    return album

def get_album_reviews(album_id: int) -> list[Review]:
    """
    Return all reviews for a given album, ordered by date then id.
    """
    db = SessionLocal()
    reviews = (
        db.query(Review)
        .filter(Review.album_id == album_id)
        .order_by(Review.published_at.asc().nulls_last(), Review.id.asc())
        .all()
    )
    db.close()
    return reviews


def get_next_album(current_album_id: int,
                   scope: str = "all",
                   only_favorites: bool = False,
                   only_wishlist: bool = False):
    """
    Get the next album in ID order within the same scope + filters.
    """
    db = SessionLocal()

    query = build_album_query(db, scope, only_favorites, only_wishlist)

    next_album = (
        query
        .filter(Album.id > current_album_id)
        .order_by(Album.id.asc())
        .first()
    )

    db.close()
    return next_album


def get_prev_album(current_album_id: int,
                   scope: str = "all",
                   only_favorites: bool = False,
                   only_wishlist: bool = False):
    """
    Get the previous album in ID order within the same scope + filters.
    """
    db = SessionLocal()

    query = build_album_query(db, scope, only_favorites, only_wishlist)

    prev_album = (
        query
        .filter(Album.id < current_album_id)
        .order_by(Album.id.desc())
        .first()
    )

    db.close()
    return prev_album


def add_album_link(album_id: int, source: str, url: str):
    db = SessionLocal()

    link = AlbumLink(
        album_id=album_id,
        source=source,
        url=url
    )

    db.add(link)
    db.commit()
    db.close()

def get_album_links(album_id: int):
    db = SessionLocal()

    links = (
        db.query(AlbumLink)
        .filter_by(album_id=album_id)
        .all()
    )

    db.close()
    return links


def get_last_album():
    """
    Return last opened album with artist eagerly loaded,
    so we can safely access last.artist after session is closed.
    """
    db = SessionLocal()

    settings = db.query(UserSettings).filter_by(user_id=1).one_or_none()

    if settings is None or settings.last_album_id is None:
        db.close()
        return None

    album = (
        db.query(Album)
        .options(joinedload(Album.artist), joinedload(Album.reviews))
        .filter(Album.id == settings.last_album_id)
        .one_or_none()
    )

    db.close()
    return album


def get_albums_for_scope(scope: str = "all",
                         only_favorites: bool = False,
                         only_wishlist: bool = False):
    """
    Return list of albums for given scope and filters,
    sorted by Artist name + Album title, with artist eagerly loaded.
    """
    db = SessionLocal()
    try:
        query = build_album_query(db, scope, only_favorites, only_wishlist)

        # Join Artist so we can safely order by Artist.name
        query = (
            query
            .join(Artist, Album.artist_id == Artist.id)
            .options(joinedload(Album.artist))
        )

        albums = (
            query
            .order_by(
                Artist.name.asc(),
                Album.title.asc(),
                Album.year.asc().nulls_last()  # pure tiebreaker
            )
            .all()
        )

        return albums
    finally:
        db.close()


def build_album_query(db, scope: str,
                      only_favorites: bool = False,
                      only_wishlist: bool = False):
    """
    Build a base query over Album, with optional filters:
    - scope: "all" / "listened"
    - only_favorites: keep only albums with favorite=1
    - only_wishlist: keep only albums with wishlist=1

    NOTE:
    "not_listened" is handled separately in get_albums_for_scope().
    """

    query = db.query(Album)
    conditions = []
    join_user = False

    # LISTENED SCOPE --------------------------------
    if scope == "listened":
        join_user = True
        conditions.append(UserAlbum.user_id == 1)
        conditions.append(UserAlbum.listened == 1)

    # FAVORITE FILTER --------------------------------
    if only_favorites:
        join_user = True
        conditions.append(UserAlbum.user_id == 1)
        conditions.append(UserAlbum.favorite == 1)

    # WISHLIST FILTER --------------------------------
    if only_wishlist:
        join_user = True
        conditions.append(UserAlbum.user_id == 1)
        conditions.append(UserAlbum.wishlist == 1)

    # Join user_albums only if needed
    if join_user:
        query = query.join(UserAlbum, UserAlbum.album_id == Album.id)

    if conditions:
        query = query.filter(and_(*conditions))

    return query

