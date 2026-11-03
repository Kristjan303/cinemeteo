"""
Projekti teema: CineMeteo - Ilmast sõltuv meediaplaneerija
Fail: services/tmdb.py
Kirjeldus: TMDB API päringud meedia otsimiseks ja detailide laadimiseks.
Standard: PEP 257 docstringid, PEP 8 stiil.
"""

import requests
from config import TMDB_API_KEY

BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Vahemälu žanrite nimede hoidmiseks
_GENRE_CACHE = {}


def lae_zanrid():
    """Pärib ja salvestab vahemällu TMDB filmi- ja seriaaližanrid."""
    global _GENRE_CACHE
    if _GENRE_CACHE:
        return _GENRE_CACHE

    if not TMDB_API_KEY:
        return {}

    try:
        # Laeme nii filmide kui telesarjade žanrid
        for endpoint in ("genre/movie/list", "genre/tv/list"):
            res = requests.get(
                f"{BASE_URL}/{endpoint}",
                params={"api_key": TMDB_API_KEY, "language": "en-US"},
                timeout=5,
            )
            if res.status_code == 200:
                for item in res.json().get("genres", []):
                    _GENRE_CACHE[item["id"]] = item["name"]
    except Exception as e:
        print(f"Žanrite laadimise viga: {e}")

    return _GENRE_CACHE


def otsi_meediat_tmdb(paring: str):
    """Otsib TMDB-st filme ja sarju antud märksõna järgi.

    Parameetrid:
        paring (str): Otsitav tekst.

    Tagastab:
        list[dict]: Vormindatud nimekiri leitud teostest.
    """
    if not TMDB_API_KEY or not paring.strip():
        return []

    zanrid = lae_zanrid()
    url = f"{BASE_URL}/search/multi"
    params = {
        "api_key": TMDB_API_KEY,
        "query": paring.strip(),
        "language": "en-US",
    }

    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            return []

        tulemused = []
        for item in res.json().get("results", []):
            m_type = item.get("media_type")
            if m_type not in ("movie", "tv"):
                continue

            # Tuvastame anime žanri (ID 16 = Animation) ja päritolumaa järgi
            genre_ids = item.get("genre_ids", [])
            origin_country = item.get("origin_country", [])
            if 16 in genre_ids and ("JP" in origin_country or m_type == "tv"):
                tuvastatud_tyyp = "anime"
            elif m_type == "movie":
                tuvastatud_tyyp = "film"
            else:
                tuvastatud_tyyp = "sari"

            poster_path = item.get("poster_path")
            poster_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else None

            # Nimetame žanrid
            zanri_nimed = [zanrid[gid] for gid in genre_ids if gid in zanrid]

            tulemused.append({
                "tmdb_id": item.get("id"),
                "title": item.get("title") or item.get("name"),
                "media_type": tuvastatud_tyyp,
                "release_date": item.get("release_date") or item.get("first_air_date") or "Teadmata",
                "rating": round(item.get("vote_average", 0.0), 1),
                "overview": item.get("overview", "Sünopsis puudub."),
                "poster_url": poster_url,
                "genres": zanri_nimed[:3],
            })

        return tulemused
    except Exception as e:
        print(f"TMDB otsingu viga: {e}")
        return []


def lae_sarja_struktuur_tmdb(tmdb_id: int):
    """Pärib sarja või anime hooajad ja osade arvu andmebaasi lisamiseks."""
    if not TMDB_API_KEY:
        return []

    url = f"{BASE_URL}/tv/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}

    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            return []

        data = res.json()
        hooajad = []
        for season in data.get("seasons", []):
            s_nr = season.get("season_number", 0)
            if s_nr > 0:  # Jätame eriosad (season 0) vahele
                hooajad.append({
                    "season_number": s_nr,
                    "title": season.get("name") or f"Hooaeg {s_nr}",
                    "episode_count": season.get("episode_count", 0),
                })
        return hooajad
    except Exception as e:
        print(f"Sarja struktuuri pärimise viga: {e}")
        return []