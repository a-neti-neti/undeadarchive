from models import Base, engine, UserAlbum, AlbumLink, UserSettings

Base.metadata.create_all(bind=engine)

print("New tables created.")
