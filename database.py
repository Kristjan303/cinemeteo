"""
Projekti teema: CineMeteo - Ilmast sõltuv meediaplaneerija
Fail: database.py
Kirjeldus: SQLite andmebaasi seadistamine, tabelite initsialiseerimine ja CRUD päringud.
Standard: PEP 257 docstringid, PEP 8 stiil.
"""

import sqlite3
from config import DB_PATH


def get_db_connection():
    """Loob ja tagastab SQLite andmebaasiühenduse sõnastikupõhise reateisendusega.

    Tagastab:
        sqlite3.Connection: Konfigureeritud ühendusobjekt.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initsialiseerib andmebaasi tabelid juhul, kui neid veel ei eksisteeri."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Tabel MediaItem
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS MediaItem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                media_type TEXT CHECK(media_type IN ('film', 'sari', 'anime')) NOT NULL,
                tmdb_id INTEGER UNIQUE,
                poster_url TEXT,
                rating REAL DEFAULT 0.0,
                status TEXT CHECK(status IN ('plan_to_watch', 'watching', 'completed')) DEFAULT 'plan_to_watch',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Tabel Season (Sarjade ja animede hooajad)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Season (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id INTEGER NOT NULL,
                season_number INTEGER NOT NULL,
                title TEXT,
                status TEXT CHECK(status IN ('plan_to_watch', 'watching', 'completed')) DEFAULT 'plan_to_watch',
                FOREIGN KEY (media_id) REFERENCES MediaItem(id) ON DELETE CASCADE,
                UNIQUE(media_id, season_number)
            )
        """)

        # 3. Tabel Episode (Üksikud osad)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Episode (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                episode_number INTEGER NOT NULL,
                title TEXT,
                is_watched INTEGER DEFAULT 0,
                watched_at TIMESTAMP,
                FOREIGN KEY (season_id) REFERENCES Season(id) ON DELETE CASCADE,
                UNIQUE(season_id, episode_number)
            )
        """)

        # 4. Tabel UserSettings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS UserSettings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.commit()


def lisa_meedia(pealkiri, meedia_tyyp, tmdb_id=None, poster_url=None, hinne=0.0, staatus="plan_to_watch", hooajad_info=None):
    """Lisab andmebaasi uue meediaüksuse ja vajadusel selle hooajad ning episoodid.

    Parameetrid:
        pealkiri (str): Filmi, sarja või anime pealkiri.
        meedia_tyyp (str): Üks valikutest: 'film', 'sari', 'anime'.
        tmdb_id (int, valikuline): TMDB identifikaator.
        poster_url (str, valikuline): Pildi veebiaadress.
        hinne (float): Kasutaja või TMDB hinne (0.0 - 10.0).
        staatus (str): 'plan_to_watch', 'watching' või 'completed'.
        hooajad_info (list[dict], valikuline): Nimekiri hooaegadest, nt [{'season_number': 1, 'episode_count': 12}].

    Tagastab:
        int: Vastloodud kirje ID.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO MediaItem (title, media_type, tmdb_id, poster_url, rating, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pealkiri, meedia_tyyp, tmdb_id, poster_url, hinne, staatus))
        media_id = cursor.lastrowid

        # Kui tegu on sarja või animega ja struktuur anti kaasa (või genereerime vaikimisi Season 1)
        if meedia_tyyp in ("sari", "anime"):
            if not hooajad_info:
                # Kui täpseid osi ei antud, loome näitena 1. hooaja 4 osaga testimiseks
                hooajad_info = [{"season_number": 1, "episode_count": 4}]

            for h in hooajad_info:
                s_num = h.get("season_number", 1)
                cursor.execute("""
                    INSERT INTO Season (media_id, season_number, title, status)
                    VALUES (?, ?, ?, ?)
                """, (media_id, s_num, f"Hooaeg {s_num}", staatus))
                season_id = cursor.lastrowid

                ep_count = h.get("episode_count", 1)
                is_w = 1 if staatus == "completed" else 0
                for ep_idx in range(1, ep_count + 1):
                    cursor.execute("""
                        INSERT INTO Episode (season_id, episode_number, title, is_watched)
                        VALUES (?, ?, ?, ?)
                    """, (season_id, ep_idx, f"Osa {ep_idx}", is_w))

        conn.commit()
        return media_id


def uuenda_kaskaad_staatust(cursor, season_id):
    """Arvutab episoodide põhjal ümber hooaja ja kogu meedia staatuse."""
    # 1. Kontrolli hooaja osade statistikat
    cursor.execute("""
        SELECT COUNT(id) AS total, SUM(is_watched) AS watched
        FROM Episode
        WHERE season_id = ?
    """, (season_id,))
    s_stats = cursor.fetchone()
    total_ep = s_stats["total"] or 0
    watched_ep = s_stats["watched"] or 0

    if watched_ep == 0:
        new_s_status = "plan_to_watch"
    elif watched_ep == total_ep:
        new_s_status = "completed"
    else:
        new_s_status = "watching"

    cursor.execute("UPDATE Season SET status = ? WHERE id = ?", (new_s_status, season_id))

    # 2. Leia meedia ID ja kontrolli kõigi hooaegade kõiki osi
    cursor.execute("SELECT media_id FROM Season WHERE id = ?", (season_id,))
    media_id = cursor.fetchone()["media_id"]

    cursor.execute("""
        SELECT COUNT(e.id) AS total_all, SUM(e.is_watched) AS watched_all
        FROM Episode e
        JOIN Season s ON e.season_id = s.id
        WHERE s.media_id = ?
    """, (media_id,))
    m_stats = cursor.fetchone()
    total_all = m_stats["total_all"] or 0
    watched_all = m_stats["watched_all"] or 0

    if watched_all == 0:
        new_m_status = "plan_to_watch"
    elif watched_all == total_all:
        new_m_status = "completed"
    else:
        new_m_status = "watching"

    cursor.execute("UPDATE MediaItem SET status = ? WHERE id = ?", (new_m_status, media_id))


def toggle_episood_vaadatud(episode_id, on_vaadatud):
    """Märgib episoodi vaadatuks või mitte ja uuendab staatuseid automaatselt."""
    val = 1 if on_vaadatud else 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Episode 
            SET is_watched = ?, watched_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (val, episode_id))

        cursor.execute("SELECT season_id FROM Episode WHERE id = ?", (episode_id,))
        season_id = cursor.fetchone()["season_id"]

        uuenda_kaskaad_staatust(cursor, season_id)
        conn.commit()


def margi_terve_hooaeg_vaadatuks(season_id, on_vaadatud=True):
    """Märgib hooaja kõik osad korraga vaadatuks või mittevaadatuks."""
    val = 1 if on_vaadatud else 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Episode SET is_watched = ? WHERE season_id = ?", (val, season_id))
        uuenda_kaskaad_staatust(cursor, season_id)
        conn.commit()


def loe_hooajad_ja_episoodid(media_id):
    """Tagastab konkreetse meediaüksuse hooajad koos episoodidega."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Season WHERE media_id = ? ORDER BY season_number ASC", (media_id,))
        hooajad = [dict(r) for r in cursor.fetchall()]

        for h in hooajad:
            cursor.execute("SELECT * FROM Episode WHERE season_id = ? ORDER BY episode_number ASC", (h["id"],))
            h["episodes"] = [dict(r) for r in cursor.fetchall()]

        return hooajad


def uuenda_meedia_staatust(meedia_id, uus_staatus, uus_hinne=None):
    """Uuendab meediaüksuse staatust ja vajadusel viib selle edasi ka episoodidele."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if uus_hinne is not None:
            cursor.execute("UPDATE MediaItem SET status = ?, rating = ? WHERE id = ?", (uus_staatus, uus_hinne, meedia_id))
        else:
            cursor.execute("UPDATE MediaItem SET status = ? WHERE id = ?", (uus_staatus, meedia_id))

        # Kui kogu teos märgiti completed või plan_to_watch, sünkroonitakse ka alamosad
        if uus_staatus == "completed":
            cursor.execute("""
                UPDATE Episode SET is_watched = 1 
                WHERE season_id IN (SELECT id FROM Season WHERE media_id = ?)
            """, (meedia_id,))
            cursor.execute("UPDATE Season SET status = 'completed' WHERE media_id = ?", (meedia_id,))
        elif uus_staatus == "plan_to_watch":
            cursor.execute("""
                UPDATE Episode SET is_watched = 0 
                WHERE season_id IN (SELECT id FROM Season WHERE media_id = ?)
            """, (meedia_id,))
            cursor.execute("UPDATE Season SET status = 'plan_to_watch' WHERE media_id = ?", (meedia_id,))

        conn.commit()


def kustuta_meedia(meedia_id):
    """Kustutab meediaüksuse ja seotud kirjed."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM MediaItem WHERE id = ?", (meedia_id,))
        conn.commit()


def loe_meedia_nimekiri(staatus_filter=None, tyyp_filter=None):
    """Pärib andmebaasist meediakirjed filtrite alusel."""
    query = "SELECT * FROM MediaItem WHERE 1=1"
    params = []

    if staatus_filter and staatus_filter != "koik":
        query += " AND status = ?"
        params.append(staatus_filter)

    if tyyp_filter and tyyp_filter != "koik":
        query += " AND media_type = ?"
        params.append(tyyp_filter)

    query += " ORDER BY id DESC"

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]