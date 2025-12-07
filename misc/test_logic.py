from logic import toggle_listened, toggle_favorite, toggle_wishlist, set_last_album, get_last_album

# Toggle listening for album 1
print("Listened:", toggle_listened(1))

# Toggle favorite for album 1
print("Favorite:", toggle_favorite(1))

# Toggle wishlist
print("Wishlist:", toggle_wishlist(1))

# Set last album to 1
set_last_album(1)

# Retrieve last album
album = get_last_album()
print("Last album:", album.id, album.title)

