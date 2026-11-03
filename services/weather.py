"""
Projekti teema: CineMeteo - Ilmast sõltuv meediaplaneerija
Fail: services/weather.py
Kirjeldus: Reaalajas ilmastiku pärimine koordinaatide või linna järgi ning parameetrite normaliseerimine.
Standard: PEP 257 docstringid, PEP 8 stiil.
"""

import datetime
import requests
from config import WEATHER_API_KEY, DEFAULT_CITY


def tuvasta_asukoht_ip_kaudu():
    """Tuvastab kasutaja ligikaudse asukoha IP-aadressi järgi.

    Tagastab:
        tuple[str, float, float]: (linn, laiuskraad, pikkuskraad)
    """
    try:
        res = requests.get("http://ip-api.com/json/", timeout=4)
        if res.status_code == 200:
            andmed = res.json()
            linn = andmed.get("city") or DEFAULT_CITY
            lat = andmed.get("lat", 58.38)
            lon = andmed.get("lon", 26.72)
            return linn, lat, lon
    except Exception as e:
        print(f"IP-asukoha tuvastuse tõrge: {e}")

    return DEFAULT_CITY, 58.38, 26.72


def _maarata_paev_voi_oo(dt_epoch: int, sunrise: int, sunset: int) -> str:
    """Tuvastab päikesetõusu ja -loojangu võrdluses, kas on päev või öö."""
    if sunrise and sunset:
        return "päev" if sunrise <= dt_epoch < sunset else "öö"
    # Tagavaravariandina vaatame lokaalset kellaaega (kell 07:00 - 20:00 on päev)
    tund = datetime.datetime.now().hour
    return "päev" if 7 <= tund < 20 else "öö"


def _paringu_varuvariant_open_meteo(lat: float, lon: float, linn: str) -> dict:
    """Varuvariant juhuks, kui OpenWeatherMap võti puudub või päring nurjub (Open-Meteo, API võtit pole vaja)."""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "timezone": "auto",
        }
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            curr = res.json().get("current_weather", {})
            w_code = curr.get("weathercode", 0)

            # WMO koodide teisendus põhikategooriateks
            if w_code == 0:
                kategooria = "Clear"
            elif w_code in (1, 2, 3):
                kategooria = "Clouds"
            elif w_code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
                kategooria = "Rain"
            elif w_code in (71, 73, 75, 77, 85, 86):
                kategooria = "Snow"
            elif w_code in (95, 96, 99):
                kategooria = "Thunderstorm"
            else:
                kategooria = "Clouds"

            is_day = curr.get("is_day", 1) == 1
            return {
                "city": linn,
                "temp": round(float(curr.get("temperature", 0.0)), 1),
                "condition": kategooria,
                "wind_speed": round(float(curr.get("windspeed", 0.0)) / 3.6, 1),  # km/h -> m/s
                "day_night": "päev" if is_day else "öö",
                "is_day": is_day,
                "description": f"{kategooria} ({'päev' if is_day else 'öö'})",
                "icon_url": None,
            }
    except Exception as e:
        print(f"Open-Meteo varupäringu tõrge: {e}")

    return {
        "city": linn,
        "temp": 18.0,
        "condition": "Clear",
        "wind_speed": 3.0,
        "day_night": "päev",
        "is_day": True,
        "description": "Selge (vaikimisi)",
        "icon_url": None,
    }


def loe_ilmastik(linn: str = None, lat: float = None, lon: float = None) -> dict:
    """Pärib reaalajas ilma kas koordinaatide, linna nime või automaatse IP järgi.

    Normaliseerib väljundi järgmisteks parameetriteks:
    - city: Linna nimetus
    - temp: Temperatuur (°C)
    - condition: Põhikategooria ('Rain', 'Snow', 'Clear', 'Clouds', 'Thunderstorm')
    - wind_speed: Tuule kiirus (m/s)
    - day_night: 'päev' või 'öö'
    - is_day: bool (True kui päev)
    - description: Lühikirjeldus
    - icon_url: OpenWeatherMapi ikooni aadress

    Tagastab:
        dict: Normaliseeritud ilmaandmete sõnastik.
    """
    # 1. Kui asukohta pole täpsustatud, tuvastame IP järgi
    if not linn and (lat is None or lon is None):
        linn, lat, lon = tuvasta_asukoht_ip_kaudu()

    # 2. Kontrollime OpenWeatherMap API võtme olemasolu
    if not WEATHER_API_KEY:
        return _paringu_varuvariant_open_meteo(lat or 58.38, lon or 26.72, linn or DEFAULT_CITY)

    # 3. Teeme päringu OpenWeatherMapi
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "et",
    }

    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    else:
        params["q"] = linn

    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code != 200:
            # Tõrke korral kasutame võtmevaba varuvarianti
            return _paringu_varuvariant_open_meteo(lat or 58.38, lon or 26.72, linn or DEFAULT_CITY)

        data = res.json()
        w_main = data.get("weather", [{}])[0]
        sys_data = data.get("sys", {})

        dt_epoch = data.get("dt", 0)
        sunrise = sys_data.get("sunrise", 0)
        sunset = sys_data.get("sunset", 0)

        day_or_night = _maarata_paev_voi_oo(dt_epoch, sunrise, sunset)
        icon_code = w_main.get("icon")

        # Kaardistame ja normaliseerime põhikategooria
        raw_condition = w_main.get("main", "Clouds")
        if raw_condition in ("Drizzle", "Mist", "Rain"):
            norm_condition = "Rain"
        elif raw_condition in ("Snow",):
            norm_condition = "Snow"
        elif raw_condition in ("Clear",):
            norm_condition = "Clear"
        elif raw_condition in ("Thunderstorm",):
            norm_condition = "Thunderstorm"
        else:
            norm_condition = "Clouds"

        return {
            "city": data.get("name", linn),
            "temp": round(data["main"]["temp"], 1),
            "condition": norm_condition,
            "wind_speed": round(data.get("wind", {}).get("speed", 0.0), 1),
            "day_night": day_or_night,
            "is_day": (day_or_night == "päev"),
            "description": w_main.get("description", "").capitalize(),
            "icon_url": f"https://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else None,
        }

    except Exception as e:
        print(f"Ilma pärimisel tekkis erind: {e}")
        return _paringu_varuvariant_open_meteo(lat or 58.38, lon or 26.72, linn or DEFAULT_CITY)