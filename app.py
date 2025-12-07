import streamlit as st

from models import init_db
from logic import (
    get_last_album,
    set_last_album,
    toggle_listened,
    toggle_favorite,
    toggle_wishlist,
    get_album_by_id,
    get_user_album_state,
    get_albums_for_scope,
    get_album_reviews  # NEW
)


# ---------------------------
#  Ensure DB tables exist
# ---------------------------
init_db()  # safe to call; only creates missing tables

# ---------------------------
#  Sidebar controls
# ---------------------------
st.sidebar.title("navigation")

# Scope: all / listened 
scope = st.sidebar.selectbox(
    "Album scope",
    ("all", "listened"),
    index=0,
)

only_favorites = st.sidebar.checkbox("Only favorites", value=False)
only_wishlist = st.sidebar.checkbox("Only wishlist", value=False)

# Scope description
if scope == "all":
    st.sidebar.caption("All albums.")
elif scope == "listened":
    st.sidebar.caption("Only albums you marked as listened.")

# Show last album info (if any)
last = get_last_album()
if last is not None:
    artist_name = last.artist.name if last.artist else "Unknown artist"
    st.sidebar.markdown(
        f"**Last album:** {artist_name} — *{last.title}*"
    )


st.sidebar.write("---")

# ---------------------------
#  Build album list for this scope + filters
#  (this list will be the single source of truth)
# ---------------------------
albums_in_scope = get_albums_for_scope(scope, only_favorites, only_wishlist)

options = []
id_by_label = {}
if albums_in_scope:
    for a in albums_in_scope:
        artist_name = a.artist.name if a.artist else "Unknown"
        label = f"{artist_name} — {a.title}"
        options.append(label)
        id_by_label[label] = a.id

# Widget key depends on scope+filters so each combination has its own selection
widget_key = f"album_list_{scope}_{int(only_favorites)}_{int(only_wishlist)}"

# Initialise selection BEFORE any widgets that use this key are created
if options:
    # try to use last album if it is inside this scope
    initial_label = None
    if last is not None:
        for lbl, aid in id_by_label.items():
            if aid == last.id:
                initial_label = lbl
                break
    if initial_label is None:
        initial_label = options[0]

    if widget_key not in st.session_state:
        st.session_state[widget_key] = initial_label
    else:
        # ensure state is still valid for this options list
        if st.session_state[widget_key] not in options:
            st.session_state[widget_key] = initial_label

# ---------------------------
# show number in scope, filter
# ---------------------------
count_in_scope = len(albums_in_scope)

scope_names = {
    "all": "All albums",
    "listened": "Listened",
}

filter_bits = []
if only_favorites:
    filter_bits.append("favorites only")
if only_wishlist:
    filter_bits.append("wishlist only")

if filter_bits:
    filter_desc = ", ".join(filter_bits)
else:
    filter_desc = "no extra filters"

st.sidebar.caption(
    f"{scope_names[scope]} ({filter_desc}): {count_in_scope} albums"
)


# ---------------------------
# OSINT GPT SEARCH
# ---------------------------

OSINT_GPT_URL = "https://chatgpt.com/g/g-69341c4dd50c8191b1e0b520e369d2f9-goth-osint-archivist"


def render_osint_block(album):
    artist = album.artist.name if album.artist else "Unknown artist"
    title = album.title or "Unknown title"
    year = album.year or ""
    label = getattr(album, "label", "")

    # Short structured context for the user to copy if needed
    context_line = f"Artist: {artist} | Album: {title} | Year: {year} | Label: {label}"

    st.subheader("🔍 Smart OSINT Search")

    # Main button: opens your Custom GPT (no prefill possible for now)
    st.markdown(
        f"""
        <a href="{OSINT_GPT_URL}" target="_blank" style="text-decoration:none;">
           <button style="
               background:#7f4cff;
               color:white;
               padding:0.6rem 1.2rem;
               border:none;
               border-radius:8px;
               font-size:1rem;
               cursor:pointer;">
               Open Goth OSINT Archivist →
           </button>
        </a>
        """,
        unsafe_allow_html=True,
    )

    # Tiny helper line with ready-to-copy context
    
    st.write("")
    st.caption("Context to paste into the GPT, if needed:")
    st.code(context_line, language="text")



# ---------------------------
#  Main title
# ---------------------------
st.title("🦇 Undead Archive")


st.write(
    "Personal archived copy for 1930 music albums reviews from old.gothic.ru / gothic.ru 1997–2022; "
    "with your own listened / favorite / wishlist states."
)

# ---------------------------
#  Buttons row: operate on sidebar selection via session_state[widget_key]
# ---------------------------
col1, col2, col3 = st.columns(3)

if options:
    import random as _random

    # Current selection label from session_state (already initialised above)
    current_label = st.session_state.get(widget_key, options[0])
    if current_label not in options:
        current_label = options[0]
        st.session_state[widget_key] = current_label

    current_index = options.index(current_label)

    with col1:
        if st.button("🎲 Random in scope"):
            # avoid choosing the same item again
            filtered = [opt for opt in options if opt != current_label]
            if filtered:
                new_label = _random.choice(filtered)
            else:
                new_label = current_label

            st.session_state[widget_key] = new_label
            new_id = id_by_label[new_label]
            set_last_album(new_id)


    with col2:
        if st.button("⏮ Previous in scope"):
            if current_index > 0:
                new_label = options[current_index - 1]
                st.session_state[widget_key] = new_label
                new_id = id_by_label[new_label]
                set_last_album(new_id)

    with col3:
        if st.button("⏭ Next in scope"):
            if current_index < len(options) - 1:
                new_label = options[current_index + 1]
                st.session_state[widget_key] = new_label
                new_id = id_by_label[new_label]
                set_last_album(new_id)
else:
    with col1:
        st.button("🎲 Random in scope", disabled=True)
    with col2:
        st.button("⏮ Previous in scope", disabled=True)
    with col3:
        st.button("⏭ Next in scope", disabled=True)

# ---------------------------
#  Sidebar album list (radio) – created AFTER all session_state writes
# ---------------------------
st.sidebar.write("Albums in this scope:")

if not options:
    st.sidebar.caption("No albums in this scope yet.")
    selected_id = None
else:
    selected_label = st.sidebar.radio(
        " ",
        options,
        key=widget_key,
    )
    selected_id = id_by_label[selected_label]
    # keep last_album in sync even when user just clicks in the list
    set_last_album(selected_id)


# ---------------------------
#  Load current album object
# ---------------------------

if selected_id is None:
    st.write("---")
    st.write("No album selected yet. Change scope or add states to albums.")
    st.stop()

album = get_album_by_id(selected_id)

if album is None:
    st.write("---")
    st.error("Album not found in database (broken reference).")
    st.stop()



# ---------------------------
#  Show album info
# ---------------------------
st.write("---")

header_col1, header_col2 = st.columns([3, 1])

with header_col1:
    artist_name = album.artist.name if album.artist else "Unknown artist"
    st.subheader(f"{artist_name} — {album.title}")

    year_label = []
    if album.year:
        year_label.append(str(album.year))
    if album.label:
        year_label.append(album.label)
    if album.genre:
        year_label.append(album.genre)

    if year_label:
        st.caption(" | ".join(year_label))

#with header_col2:
#    with st.expander("Debug info"):
#        st.markdown(f"Album ID: `{album.id}`")


# ---------------------------
# 8.1 Show current status tags
# ---------------------------
st.write("### Your status for this album")

state = get_user_album_state(album.id)

col1, col2, col3 = st.columns(3)

with col1:
    listened_checked = st.checkbox(
        "Listened",
        value=bool(state["listened"]),
        key=f"listened_{album.id}",
    )
    if listened_checked != bool(state["listened"]):
        toggle_listened(album.id)

with col2:
    favorite_checked = st.checkbox(
        "Favorite",
        value=bool(state["favorite"]),
        key=f"favorite_{album.id}",
    )
    if favorite_checked != bool(state["favorite"]):
        toggle_favorite(album.id)

with col3:
    wishlist_checked = st.checkbox(
        "Wishlist",
        value=bool(state["wishlist"]),
        key=f"wishlist_{album.id}",
    )
    if wishlist_checked != bool(state["wishlist"]):
        toggle_wishlist(album.id)

st.write("---")
#-----
# OSINT block for this album
render_osint_block(album)

# ---------------------------
#  Show review text (Russian)
# ---------------------------

st.write("---")
st.write("### Original reviews (Russian)")

reviews = get_album_reviews(album.id)

if not reviews:
    st.info("No review text found for this album.")
else:
    for idx, rev in enumerate(reviews, start=1):
        if len(reviews) > 1:
            st.markdown(f"#### Review {idx}")

        meta_bits = []
        if rev.author:
            meta_bits.append(f"**Author:** {rev.author}")
        if rev.published_at:
            date_str = rev.published_at.strftime("%Y-%m-%d")
            meta_bits.append(f"**Published:** {date_str}")
        if rev.rating is not None:
            stars = "★" * rev.rating + "☆" * (5 - rev.rating)
            meta_bits.append(f"Rating: {rev.rating}/5 {stars}")
        if meta_bits:
            st.caption(" | ".join(meta_bits))

        text = (rev.review_text or "").strip()
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        if not paragraphs:
            st.write(text)
        else:
            for p in paragraphs:
                st.write(p)
                st.write("")

        st.write("---")


