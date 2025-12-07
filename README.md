# 🦇 UNDEAD ARCHIVE — Gothic Reviews Companion

Personal offline companion app for the legendary gothic.ru / old.gothic.ru reviews archive  
(1997–2022, 1930 albums).

This project turns a static review dump into a small living tool:

- browse albums with artist and year info  
- mark them as **Listened / Favorite / Wishlist**  
- read original Russian reviews  
- open a dedicated **Goth OSINT GPT** to hunt for listening sources and metadata  

All powered by a local **Streamlit** app and a bundled SQLite database.

---

## 🖼 Screenshots


---

## 📦 What is inside

- `goth_reviews.db` — SQLite database with:
  - artists  
  - albums  
  - original Russian reviews  
  - user states (listened, favorite, wishlist)

- `app.py` — Streamlit UI  
- `logic.py` — app logic  
- `models.py` — SQLAlchemy models  
- `run_app.bat` — Windows launcher  
- `run_app.sh` — macOS / Linux launcher  
- `requirements.txt` — dependencies  

---

## ▶ Running the app

### 🪟 Windows

```bat
run_app.bat
```

Stop the app with **CTRL+C**.

---

### 🍏 macOS / 🐧 Linux

```bash
chmod +x run_app.sh
./run_app.sh
```

Stop the app with **CTRL+C**.

---

## 🧷 Core features

- album navigation (all / listened)
- random / next / previous buttons
- per‑album states (listened, favorite, wishlist)
- Russian review text with authors & dates
- fully integrated OSINT button using a dedicated Custom GPT

---

## 🛠 Tech stack

- Python 3  
- Streamlit  
- SQLAlchemy  
- SQLite  

---

## 🧛‍♀️ Rights, origin & acknowledgements

All reviews belong to **their original authors**  
and originate from **gothic.ru / old.gothic.ru** (1997–2022).

This project is **not affiliated** with the site or its owners.  
It is a personal archival and study tool.

> ✨ A tiny note:  
> This project is the fulfillment of a childhood dream —  
> to preserve and explore the music that shaped an entire generation (and finally listen to all these 1930 albums, marking listened as "listened", hehehe).  
> Twenty years later… the archive finally lives.

---

## 🗺 Roadmap

- multi‑user support  
- search bar for albums  
- optional caching  
- Streamlit Cloud deployment  

---

## ⚖ License

This project is released under the **MIT License**.  
See the `LICENSE` file for details.
