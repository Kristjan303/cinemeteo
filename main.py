"""
Projekti teema: CineMeteo - Ilmast sõltuv meediaplaneerija
Autorid: Kristjan-Even Puusepp ja projektikaaslane
Allikad: Flet UI Docs (flet.dev), SQLite ametlik dokumentatsioon
Kirjeldus: Rakenduse alguspunkt ja meediahalduse visuaalne testimiskeskkond koos osade toega.
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


def main(page: ft.Page):
    """Käivitab Flet kasutajaliidese ja hoiab ekraani interaktsiooni."""
    page.title = "CineMeteo - Meedia & Osade Haldur"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.window.width = 900
    page.window.height = 750

    init_db()

    # --- Sisendkomponendid ---
    sisend_pealkiri = ft.TextField(
        label="Pealkiri",
        hint_text="nt. Attack on Titan või Interstellar",
        expand=True,
    )

    valik_tyyp = ft.Dropdown(
        label="Tüüp",
        width=130,
        value="anime",
        options=[
            ft.dropdown.Option("anime", "Anime"),
            ft.dropdown.Option("sari", "Sari"),
            ft.dropdown.Option("film", "Film"),
        ],
    )

    valik_staatus = ft.Dropdown(
        label="Staatus",
        width=160,
        value="plan_to_watch",
        options=[
            ft.dropdown.Option("plan_to_watch", "Plaanib vaadata"),
            ft.dropdown.Option("watching", "Vaatamisel"),
            ft.dropdown.Option("completed", "Vaadatud"),
        ],
    )

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
        """Loeb andmebaasist kirjed ja uuendab graafilist tabelit/kaarte."""
        nimekiri_kontainer.controls.clear()
        kirjed = loe_meedia_nimekiri(staatus_filter=filter_staatus.value)

        if not kirjed:
            nimekiri_kontainer.controls.append(
                ft.Text("Ühtegi kirjet ei leitud.", italic=True, color=ft.Colors.GREY_500)
            )
        else:
            for kirje in kirjed:
                m_id = kirje["id"]
                m_tyyp = kirje["media_type"]
                staatus = kirje["status"]

                peamine_rida = ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(kirje["title"], weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(
                                    f"Tüüp: {m_tyyp.upper()} | Olek: {staatus}",
                                    size=12,
                                    color=ft.Colors.LIGHT_BLUE_300 if staatus == "watching" else (
                                        ft.Colors.GREEN_300 if staatus == "completed" else ft.Colors.GREY_400
                                    ),
                                ),
                            ],
                            spacing=3,
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

                # Kui tegu on sarja või animega, teeme sellest lahtiklapitava ExpansionTile'i
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
                                expanded=False,
                            ),
                        )
                    )
                else:
                    kaardike = ft.Card(
                        content=ft.Container(padding=12, content=peamine_rida)
                    )

                nimekiri_kontainer.controls.append(kaardike)

        page.update()

    def vajuta_lisa(_):
        """Lisab uue kirje andmebaasi."""
        if not sisend_pealkiri.value.strip():
            page.open(ft.SnackBar(ft.Text("Palun sisesta pealkiri!")))
            return

        lisa_meedia(
            pealkiri=sisend_pealkiri.value.strip(),
            meedia_tyyp=valik_tyyp.value,
            staatus=valik_staatus.value,
        )
        sisend_pealkiri.value = ""
        varskenda_nimekirja()

    def vajuta_ep_toggle(episode_id, on_vaadatud):
        """Käivitub kui märgistatakse üksik episood."""
        toggle_episood_vaadatud(episode_id, on_vaadatud)
        varskenda_nimekirja()

    def vajuta_hooaeg_vaadatud(season_id):
        """Käivitub kui terve hooaeg märgistatakse vaadatuks."""
        margi_terve_hooaeg_vaadatuks(season_id, on_vaadatud=True)
        varskenda_nimekirja()

    def vajuta_staatus(meedia_id, uus_staatus):
        """Uuendab kirje üldstaatust."""
        uuenda_meedia_staatust(meedia_id, uus_staatus)
        varskenda_nimekirja()

    def vajuta_kustuta(meedia_id):
        """Kustutab kirje."""
        kustuta_meedia(meedia_id)
        varskenda_nimekirja()

    def filtreeri_muutus(_):
        """Filtri muutumisel uuendab vaadet."""
        varskenda_nimekirja()

    filter_staatus.on_change = filtreeri_muutus

    page.add(
        ft.Text("CineMeteo - Meedia & Osade Haldur", size=22, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        ft.Row(
            controls=[
                sisend_pealkiri,
                valik_tyyp,
                valik_staatus,
                ft.Button("Lisa nimekirja", icon=ft.Icons.ADD, on_click=vajuta_lisa),
            ]
        ),
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Salvestatud kirjed ja vaatamisjärg:", size=16, weight=ft.FontWeight.W_500),
                filter_staatus,
            ],
        ),
        nimekiri_kontainer,
    )

    varskenda_nimekirja()


if __name__ == "__main__":
    ft.run(main)