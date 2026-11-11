"""
Projekti teema: CineMeteo - Ilmast sõltuv meediaplaneerija
Autorid: Kristjan-Even Puusepp ja projektikaaslane
Allikad: Flet UI Docs (flet.dev), SQLite ametlik dokumentatsioon, TMDB API
Kirjeldus: Rakenduse alguspunkt koos lokaalse andmebaasi ja TMDB reaalajas otsingu testimisega.
"""

import flet as ft
from database import (
    init_db,
    lisa_meedia,
    loe_meedia_nimekiri,
    uuenda_meedia_staatust,
    kustuta_meedia,
    loe_hooajad_ja_episoodid,
    toggle_episood_vaadatud,
    margi_terve_hooaeg_vaadatuks,
)
from services.tmdb import otsi_meediat_tmdb, lae_sarja_struktuur_tmdb
from services.weather import loe_ilmastik


def main(page: ft.Page):
    """Käivitab Flet kasutajaliidese ja juhib ekraanide olekuid."""
    page.title = "CineMeteo - Meediahaldur & TMDB Testija"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 950
    page.window.height = 800

    init_db()

    # ==========================================
    # ILMASTIKURIBI (Task: Reaalajas ilmastik)
    # ==========================================
    ilm_tekst = ft.Text("Laen ilmateadet...", size=14, weight=ft.FontWeight.W_500)
    ilm_detailid = ft.Text("", size=12, color=ft.Colors.GREY_400)
    ilm_ikoon = ft.Icon(ft.Icons.WB_SUNNY, color=ft.Colors.AMBER_300, size=24)
    linna_otsing = ft.TextField(
        hint_text="Muuda linna...",
        dense=True,
        width=150,
        content_padding=8,
    )

    def uuenda_ilmavaadet(linna_nimi=None):
        """Pärib ilmateate ja uuendab päiseriba."""
        andmed = loe_ilmastik(linn=linna_nimi)

        # Valime sobiva Flet ikooni vastavalt normaliseeritud kategooriale ja päevale/ööle
        cond = andmed["condition"]
        is_day = andmed["is_day"]

        if cond == "Clear":
            ilm_ikoon.name = ft.Icons.WB_SUNNY if is_day else ft.Icons.NIGHTLIGHT_ROUND
            ilm_ikoon.color = ft.Colors.AMBER_400 if is_day else ft.Colors.INDIGO_200
        elif cond == "Rain":
            ilm_ikoon.name = ft.Icons.WATER_DROP
            ilm_ikoon.color = ft.Colors.LIGHT_BLUE_400
        elif cond == "Snow":
            ilm_ikoon.name = ft.Icons.AC_UNIT
            ilm_ikoon.color = ft.Colors.CYAN_200
        elif cond == "Thunderstorm":
            ilm_ikoon.name = ft.Icons.FLASH_ON
            ilm_ikoon.color = ft.Colors.DEEP_PURPLE_200
        else:
            ilm_ikoon.name = ft.Icons.CLOUD
            ilm_ikoon.color = ft.Colors.GREY_300

        ilm_tekst.value = f"{andmed['city']}: {andmed['temp']}°C, {andmed['condition']}"
        ilm_detailid.value = f"Tuul: {andmed['wind_speed']} m/s | Aeg: {andmed['day_night'].capitalize()}"
        page.update()

    def vajuta_uuenda_linn(_):
        if linna_otsing.value.strip():
            uuenda_ilmavaadet(linna_otsing.value.strip())
            linna_otsing.value = ""

    linna_otsing.on_submit = vajuta_uuenda_linn

    ilma_kontainer = ft.Container(
        padding=ft.Padding(12, 8, 12, 8),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=8,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment="center",
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment="center",
                    controls=[
                        ilm_ikoon,
                        ft.Column(
                            spacing=1,
                            controls=[
                                ilm_tekst,
                                ilm_detailid,
                            ],
                        ),
                    ],
                ),
                ft.Row(
                    spacing=6,
                    vertical_alignment="center",
                    controls=[
                        linna_otsing,
                        ft.IconButton(
                            icon=ft.Icons.REFRESH,
                            tooltip="Uuenda asukoha ilma",
                            on_click=lambda _: uuenda_ilmavaadet(),
                        ),
                    ],
                ),
            ],
        ),
    )

    # ==========================================
    # 1. TAB: MINU NIMEKIRI (LOKAALNE SQLite)
    # ==========================================
    filter_staatus = ft.Dropdown(
        label="Filtreeri staatust",
        width=160,
        value="koik",
        options=[
            ft.dropdown.Option("koik", "Kõik staatused"),
            ft.dropdown.Option("plan_to_watch", "Plaanib vaadata"),
            ft.dropdown.Option("watching", "Vaatamisel"),
            ft.dropdown.Option("completed", "Vaadatud"),
        ],
    )

    nimekiri_kontainer = ft.Column(spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    def varskenda_nimekirja():
        """Loeb andmebaasist kirjed ja renderdab nimekirja."""
        nimekiri_kontainer.controls.clear()
        kirjed = loe_meedia_nimekiri(staatus_filter=filter_staatus.value)

        if not kirjed:
            nimekiri_kontainer.controls.append(
                ft.Text("Ühtegi salvestatud kirjet ei leitud.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            for kirje in kirjed:
                m_id = kirje["id"]
                m_tyyp = kirje["media_type"]
                staatus = kirje["status"]

                peamine_rida = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Image(
                                    src=kirje["poster_url"] or "https://via.placeholder.com/60x90?text=No+Poster",
                                    width=45,
                                    height=65,
                                    fit="cover",
                                    border_radius=4,
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(kirje["title"], weight=ft.FontWeight.BOLD, size=16),
                                        ft.Text(
                                            f"Tüüp: {m_tyyp.upper()} | Olek: {staatus} | Hinne: ★ {kirje['rating']}",
                                            size=12,
                                            color=ft.Colors.LIGHT_BLUE_300 if staatus == "watching" else (
                                                ft.Colors.GREEN_300 if staatus == "completed" else ft.Colors.GREY_400
                                            ),
                                        ),
                                    ],
                                    spacing=3,
                                ),
                            ],
                            spacing=12,
                        ),
                        ft.Row(
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                    tooltip="Märgi kõik vaadatuks",
                                    icon_color=ft.Colors.GREEN_400 if staatus == "completed" else ft.Colors.GREY_400,
                                    on_click=lambda _, item_id=m_id: vajuta_staatus(item_id, "completed"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                                    tooltip="Märgi vaatamisel olevaks",
                                    icon_color=ft.Colors.AMBER_400 if staatus == "watching" else ft.Colors.GREY_400,
                                    on_click=lambda _, item_id=m_id: vajuta_staatus(item_id, "watching"),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_OUTLINE,
                                    icon_color=ft.Colors.RED_400,
                                    tooltip="Kustuta kirje",
                                    on_click=lambda _, item_id=m_id: vajuta_kustuta(item_id),
                                ),
                            ]
                        ),
                    ],
                )

                if m_tyyp in ("sari", "anime"):
                    hooajad = loe_hooajad_ja_episoodid(m_id)
                    alam_elemendid = []

                    for h in hooajad:
                        s_id = h["id"]
                        h_tiitel = f"Hooaeg {h['season_number']} ({h['status']})"

                        ep_nupud = []
                        for ep in h["episodes"]:
                            ep_id = ep["id"]
                            ep_nupud.append(
                                ft.Checkbox(
                                    label=f"{ep['title']} (Ep {ep['episode_number']})",
                                    value=bool(ep["is_watched"]),
                                    on_change=lambda e, eid=ep_id: vajuta_ep_toggle(eid, e.control.value),
                                )
                            )

                        alam_elemendid.append(
                            ft.Container(
                                padding=10,
                                margin=ft.Margin(15, 0, 0, 5),
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                border_radius=6,
                                content=ft.Column(
                                    controls=[
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Text(h_tiitel, weight=ft.FontWeight.W_600),
                                                ft.TextButton(
                                                    "Märgi terve hooaeg vaadatuks",
                                                    on_click=lambda _, sid=s_id: vajuta_hooaeg_vaadatud(sid),
                                                ),
                                            ],
                                        ),
                                        ft.Row(controls=ep_nupud, wrap=True, spacing=15),
                                    ]
                                ),
                            )
                        )

                    kaardike = ft.Card(
                        content=ft.Container(
                            padding=8,
                            content=ft.ExpansionTile(
                                        title=peamine_rida,
                                        controls=alam_elemendid,
                                        expanded=m_id in avatud_dropdownid,
                                        on_change=lambda e, item_id=m_id: dropdowni_olek(e, item_id),
                                    )
                        )
                    )
                else:
                    kaardike = ft.Card(
                        content=ft.Container(padding=12, content=peamine_rida)
                    )

                nimekiri_kontainer.controls.append(kaardike)

        page.update()

    def vajuta_ep_toggle(episode_id, on_vaadatud):
        toggle_episood_vaadatud(episode_id, on_vaadatud)
        varskenda_nimekirja()

    def vajuta_hooaeg_vaadatud(season_id):
        margi_terve_hooaeg_vaadatuks(season_id, on_vaadatud=True)
        varskenda_nimekirja()

    def vajuta_staatus(meedia_id, uus_staatus):
        uuenda_meedia_staatust(meedia_id, uus_staatus)
        varskenda_nimekirja()

    def vajuta_kustuta(meedia_id):
        kustuta_meedia(meedia_id)
        varskenda_nimekirja()
        
    avatud_dropdownid = set()

    def dropdowni_olek(e, item_id):
        if e.control.expanded:
            avatud_dropdownid.add(item_id)
        else:
            avatud_dropdownid.discard(item_id)

    filter_staatus.on_change = lambda _: varskenda_nimekirja()

    tab_nimekiri_sisu = ft.Column(
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Minu salvestatud vaatamisjärg:", size=16, weight=ft.FontWeight.W_500),
                    filter_staatus,
                ],
            ),
            nimekiri_kontainer,
        ],
        expand=True,
    )

    # ==========================================
    # 2. TAB: TMDB OTSING JA VISUAALNE TAGASISIDE
    # ==========================================
    otsingu_sisend = ft.TextField(
        label="Otsi filmi, seriaali või anime nime TMDB-st",
        hint_text="nt. Interstellar, Arcane, Attack on Titan...",
        expand=True,
    )

    laadimis_indikaator = ft.ProgressBar(visible=False)
    otsingu_tulemused_kontainer = ft.Column(spacing=15, scroll=ft.ScrollMode.AUTO, expand=True)

    def vajuta_lisa_tmdb_kirje(teos: dict):
        """Lisab TMDB teose lokaalsesse andmebaasi koos reaalsete hooaegadega."""
        hooajad = None
        if teos["media_type"] in ("sari", "anime"):
            page.snack_bar = ft.SnackBar(ft.Text(f"Laen sarja '{teos['title']}' osade nimekirja..."))
            page.snack_bar.open = True
            page.update()
            hooajad = lae_sarja_struktuur_tmdb(teos["tmdb_id"])

        try:
            lisa_meedia(
                pealkiri=teos["title"],
                meedia_tyyp=teos["media_type"],
                tmdb_id=teos["tmdb_id"],
                poster_url=teos["poster_url"],
                hinne=teos["rating"],
                staatus="plan_to_watch",
                hooajad_info=hooajad,
            )
            page.snack_bar = ft.SnackBar(ft.Text(f"'{teos['title']}' lisatud nimekirja!"))
            page.snack_bar.open = True
            varskenda_nimekirja()
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text(f"'{teos['title']}' on juba sinu nimekirjas!"))
            page.snack_bar.open = True
            page.update()
            
    def tee_tmdb_otsing(_):
        """Käivitab TMDB otsingu ja renderdab visuaalsed kaardid."""
        paring = otsingu_sisend.value.strip()
        if not paring:
            return

        laadimis_indikaator.visible = True
        otsingu_tulemused_kontainer.controls.clear()
        page.update()

        tulemused = otsi_meediat_tmdb(paring)
        laadimis_indikaator.visible = False

        if not tulemused:
            otsingu_tulemused_kontainer.controls.append(
                ft.Text("TMDB-st vasteid ei leitud. Kontrolli otsisõna või API võtit.", color=ft.Colors.GREY_400)
            )
        else:
            for teos in tulemused:
                zanrid_str = ", ".join(teos["genres"]) if teos["genres"] else "Määramata"

                kaart = ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.START,
                            vertical_alignment="start",
                            controls=[
                                ft.Image(
                                    src=teos["poster_url"] or "https://via.placeholder.com/100x150?text=No+Poster",
                                    width=90,
                                    height=135,
                                    fit="cover",
                                    border_radius=6,
                                ),
                                ft.Column(
                                    expand=True,
                                    spacing=4,
                                    controls=[
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Text(
                                                    f"{teos['title']} ({teos['release_date'][:4]})",
                                                    weight=ft.FontWeight.BOLD,
                                                    size=16,
                                                ),
                                                ft.Text(f"★ {teos['rating']}", color=ft.Colors.AMBER_400, size=14),
                                            ],
                                        ),
                                        ft.Text(
                                            f"Tüüp: {teos['media_type'].upper()} | Žanrid: {zanrid_str}",
                                            size=12,
                                            color=ft.Colors.GREY_400,
                                        ),
                                        ft.Text(
                                            teos["overview"],
                                            size=12,
                                            max_lines=3,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.END,
                                            controls=[
                                                ft.Button(
                                                    "Lisa minu nimekirja",
                                                    icon=ft.Icons.BOOKMARK_ADD,
                                                    on_click=lambda _, t=teos: vajuta_lisa_tmdb_kirje(t),
                                                )
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    )
                )
                otsingu_tulemused_kontainer.controls.append(kaart)

        page.update()

    otsingu_sisend.on_submit = tee_tmdb_otsing

    tab_otsing_sisu = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    otsingu_sisend,
                    ft.Button("Otsi TMDB-st", icon=ft.Icons.SEARCH, on_click=tee_tmdb_otsing),
                ]
            ),
            laadimis_indikaator,
            otsingu_tulemused_kontainer,
        ],
        expand=True,
    )

    # --- PÕHILEHE VAATED JA VAATEVAHETUS ---
    tab_valitud_sisu = ft.Container(content=tab_nimekiri_sisu, expand=True)

    def vaheta_vaade(e):
        """Vahetab aktiivset vaadet SegmentedButtoni valiku järgi."""
        valik = e.control.selected or []
        if "nimekiri" in valik:
            tab_valitud_sisu.content = tab_nimekiri_sisu
            varskenda_nimekirja()
        elif "otsing" in valik:
            tab_valitud_sisu.content = tab_otsing_sisu
        page.update()

    vaadete_lüliti = ft.SegmentedButton(
        selected=["nimekiri"],  # NB! list ['...'], MITTE hulk {'...'}
        allow_multiple_selection=False,
        on_change=vaheta_vaade,
        segments=[
            ft.Segment(
                value="nimekiri",
                label=ft.Text("Minu Nimekiri"),
                icon=ft.Icon(ft.Icons.LIST_ALT),
            ),
            ft.Segment(
                value="otsing",
                label=ft.Text("TMDB Otsing"),
                icon=ft.Icon(ft.Icons.SEARCH),
            ),
        ],
    )

    page.add(
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("CineMeteo - Meedia & Ilmaplaneerija", size=22, weight=ft.FontWeight.BOLD),
                vaadete_lüliti,
            ],
        ),
        ilma_kontainer,
        ft.Divider(),
        tab_valitud_sisu,
    )

    varskenda_nimekirja()
    uuenda_ilmavaadet()  # Laeb käivitusel kohe ilma


if __name__ == "__main__":
    ft.run(main)