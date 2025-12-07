from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone

# For now, SQLite. This will create goth_reviews.db in this folder.
DATABASE_URL = "sqlite:///goth_reviews.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


Base = declarative_base()


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    country = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    albums = relationship("Album", back_populates="artist")


class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True)
    artist_id = Column(Integer, ForeignKey("artists.id"))
    title = Column(String, index=True)
    year = Column(Integer, nullable=True)
    label = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    review_url = Column(Text, nullable=True)
    cover_url = Column(Text, nullable=True)  # NEW: album cover image

    artist = relationship("Artist", back_populates="albums")
    reviews = relationship("Review", back_populates="album", cascade="all, delete-orphan")
    user_links = relationship("UserAlbum", back_populates="album")
    links = relationship("AlbumLink", back_populates="album", cascade="all, delete-orphan")




class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True)
    album_id = Column(Integer, ForeignKey("albums.id"))
    author = Column(String, nullable=True)
    rating = Column(Integer, nullable=True)          # NEW: numeric rating
    published_at = Column(DateTime, nullable=True)   # NEW: publication date
    review_text = Column(Text)

    album = relationship("Album", back_populates="reviews")


# ------------------------------
# USER-ALBUM RELATIONSHIP TABLE
# ------------------------------

class UserAlbum(Base):
    # 1. SQL table name
    __tablename__ = "user_albums"

    # 2. Primary key
    id = Column(Integer, primary_key=True)

    # 3. For now you are the only user, always user_id = 1
    user_id = Column(Integer, nullable=False, default=1)

    # 4. Link to albums.id (each row refers to one album)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False)

    # 5. Status for your flow:
    #    not_listened / listened / favorite / wishlist
    listened = Column(Integer, default=0)   # 0=False, 1=True
    favorite = Column(Integer, default=0)
    wishlist = Column(Integer, default=0)

    # 6. Optional rating (you can ignore it)
    #rating = Column(Integer, nullable=True)

    # 7. Optional personal notes
    #notes = Column(Text, nullable=True)

    # 8. Auto-updated timestamp (good habit)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 9. Relationship back to Album model, so you can do row.album.title
    album = relationship("Album", back_populates="user_links")

    # 10. Ensure user cannot have duplicate entries for the same album
    __table_args__ = (
        UniqueConstraint("user_id", "album_id", name="uq_user_album"),
    )

# -------------------------
# ALBUM LINKS TABLE
# -------------------------

class AlbumLink(Base):
    __tablename__ = "album_links"

    id = Column(Integer, primary_key=True)

    # Which album this link belongs to
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=False)

    # Source of link: youtube / spotify / bandcamp etc.
    source = Column(String(50), nullable=False)

    # The actual link
    url = Column(Text, nullable=False)

    # Relationship back to Album
    album = relationship("Album", back_populates="links")

# -------------------------
# USER SETTINGS TABLE
# -------------------------

class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, default=1)

    # If user last opened album #432, store 432 here
    last_album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)

    # Random mode ON/OFF (True/False)
    random_mode_enabled = Column(Integer, default=1)  # 1 = ON, 0 = OFF

    # Optional: timestamp
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    last_album = relationship("Album")


def init_db():
    Base.metadata.create_all(engine)
