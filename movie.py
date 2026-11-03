
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")

# Kasutaja sisestab otsitava teose nime
title = input("Sisesta filmi, seriaali või anime nimi: ")

# 1. Otsing filmide, seriaalide ja muude teoste seas
url = "https://api.themoviedb.org/3/search/multi"

params = {
    "api_key": API_KEY,
    "query": title,
    "language": "en-US"
}

response = requests.get(url, params=params)
data = response.json()

# Žanrite ID-de vastavus nimedele
genre_url = "https://api.themoviedb.org/3/genre/movie/list"
genre_response = requests.get(
    genre_url,
    params={"api_key": API_KEY}
)
genres = {
    genre["id"]: genre["name"]
    for genre in genre_response.json()["genres"]
}

# 2. Tulemuste kuvamine
for item in data["results"]:

    if item["media_type"] == "movie":
        name = item.get("title")
        release_date = item.get("release_date")
        overview = item.get("overview")
        item_id = item["id"]

        details_url = (
            f"https://api.themoviedb.org/3/movie/{item_id}"
        )

    elif item["media_type"] == "tv":
        name = item.get("name")
        release_date = item.get("first_air_date")
        overview = item.get("overview")
        item_id = item["id"]

        details_url = (
            f"https://api.themoviedb.org/3/tv/{item_id}"
        )

    else:
        continue

    print("\n" + "=" * 50)
    print("Pealkiri:", name)
    print("ID:", item_id)
    print("Tüüp:", item["media_type"])
    print("Väljalaske kuupäev:", release_date)
    print("Sünopsis:", overview)
    print("Poster:", item.get("poster_path"))

    # 3. Teose detailide pärimine
    details_response = requests.get(
        details_url,
        params={"api_key": API_KEY}
    )

    details = details_response.json()

    if item["media_type"] == "tv":

        print("\nHooajad:")

        for season in details.get("seasons", []):

            season_number = season["season_number"]

            # Eraldi hooaja detailide pärimine
            season_url = (
                f"https://api.themoviedb.org/3/tv/"
                f"{item_id}/season/{season_number}"
            )

            season_response = requests.get(
                season_url,
                params={"api_key": API_KEY}
            )

            season_data = season_response.json()

            print("\nHooaeg:", season_data.get("name"))
            print("Hooaja number:", season_number)

            # Episoodide kuvamine
            for episode in season_data.get("episodes", []):

                print("\nEpisood:", episode.get("name"))
                print("Episoodi number:", episode.get("episode_number"))
                print("Sünopsis:", episode.get("overview"))
                print("Väljalaske kuupäev:", episode.get("air_date"))
                print("Hinnang:", episode.get("vote_average"))

    # Žanrid
    genre_names = [
        genre["name"]
        for genre in details.get("genres", [])
    ]

    print("Žanrid:", ", ".join(genre_names))

    # 4. Treileri pärimine
    videos_url = f"https://api.themoviedb.org/3/{item['media_type']}/{item_id}/videos"

    videos_response = requests.get(
        videos_url,
        params={"api_key": API_KEY}
    )

    videos = videos_response.json()

    trailer = next(
        (
            video for video in videos.get("results", [])
            if video["site"] == "YouTube"
            and video["type"] == "Trailer"
        ),
        None
    )

    if trailer:
        print(
            "Treiler:",
            "https://www.youtube.com/watch?v=" + trailer["key"]
        )
    else:
        print("Treiler puudub")