import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import settings
from src.database import HistoryDB
from src.scraper import GreenZoneScraper

st.set_page_config(
    page_title="Green Zone Finder",
    page_icon="🌳",
    layout="wide",
)

db = HistoryDB(settings.database_url)

EXAMPLE_ADDRESSES = [
    "ул. 1-я Машиностроения, д. 10",
    "ул. Шарикоподшипниковская",
    "ул. Автозаводская",
    "Красная площадь",
    "Тверская, 1",
]


def make_route_link(lat: float, lng: float, label: str) -> str:
    return f'<a href="https://yandex.ru/maps/?pt={lng},{lat}&z=17" target="_blank">{label}</a>'


def main():
    st.title("🌳 Green Zone Finder")
    st.markdown(
        "Находит ближайшие зелёные зоны (парки, пруды, аллеи) "
        "в пешей доступности от заданного адреса — через скриншот Яндекс.Карт + CV."
    )

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        address = st.text_input(
            "Адрес",
            placeholder="ул. 1-я Машиностроения, д. 10",
            help="Можно писать без города, без улицы — Яндекс сам поймёт",
        )

    with col2:
        city = st.text_input("Город", value="Москва")

    with col3:
        st.caption("Примеры")
        selected = st.selectbox("Быстрый ввод", [""] + EXAMPLE_ADDRESSES, label_visibility="collapsed")
        if selected:
            address = selected

    search_btn = st.button("🔍 Найти зелёные зоны", type="primary", use_container_width=True)

    if search_btn and address:
        address = address.strip()
        city = city.strip()

        with st.spinner("🔄 Открываю Яндекс.Карты, ищу зелёные зоны..."):
            scraper = GreenZoneScraper()
            result = scraper.search(address, city)

            zones_json = json.dumps(
                [z.model_dump() for z in result.green_zones],
                ensure_ascii=False,
                default=str,
            )

            db.save_search(
                address=address,
                city=city,
                status=result.status,
                screenshot_path=result.screenshot_path,
                green_zones_json=zones_json,
            )

            if result.status == "completed":
                _show_results(result)
            else:
                st.error(f"❌ Ошибка: {result.status}")

    elif search_btn and not address:
        st.warning("Введите адрес.")

    st.divider()
    show_history()


def _show_results(result):
    st.success(f"✅ Найдено зелёных зон: **{len(result.green_zones)}**")

    if result.center_coords:
        lat, lng = result.center_coords.lat, result.center_coords.lng
        st.caption(
            f"📍 Центр поиска: "
            f'<a href="https://yandex.ru/maps/?ll={lng},{lat}&z={result.map_zoom or 17}" '
            f'target="_blank">{lat:.6f}, {lng:.6f}</a>',
            unsafe_allow_html=True,
        )

    col_left, col_right = st.columns([1, 1])

    with col_left:
        if result.screenshot_path and Path(str(result.screenshot_path)).exists():
            st.image(
                str(result.screenshot_path),
                caption="🧠 Скриншот карты (зелёные зоны detected)",
                use_column_width=True,
            )

    with col_right:
        if result.green_zones:
            rows = []
            for i, z in enumerate(result.green_zones, 1):
                lat = z.centroid.lat if z.centroid else None
                lng = z.centroid.lng if z.centroid else None
                coords = f"{lat:.6f}, {lng:.6f}" if lat and lng else "—"
                route = (
                    f'<a href="https://yandex.ru/maps/?rtext='
                    f'{result.center_coords.lat},{result.center_coords.lng}'
                    f'~{lat},{lng}" target="_blank">🚶 Проложить</a>'
                    if lat and lng and result.center_coords
                    else "—"
                )
                rows.append({
                    "#": i,
                    "Тип": z.zone_type,
                    "Название": z.name or "—",
                    "Расстояние": f"{z.distance_meters:.0f} м" if z.distance_meters else "—",
                    "Пешком": f"{z.walking_minutes:.0f} мин" if z.walking_minutes else "—",
                    "Координаты": coords,
                    "Маршрут": route,
                })
            df = pd.DataFrame(rows)
            st.markdown("### 📋 Найденные зоны")
            st.write(
                df.to_html(escape=False, index=False),
                unsafe_allow_html=True,
            )
        else:
            st.info("🌿 Зелёные зоны не обнаружены. Попробуйте другой адрес или увеличьте зум.")

        with st.expander("📋 JSON результатов"):
            st.json([z.model_dump() for z in result.green_zones])


def show_history():
    st.subheader("📜 История поисков")
    history = db.get_history(limit=10)

    if not history:
        st.caption("Пока ничего не искали.")
        return

    for h in history:
        zones = h.get("green_zones", [])
        zone_count = len(zones)
        with st.expander(
            f"📍 {h['address']} ({h['city']}) — "
            f"{zone_count} зон • {h['searched_at'][:19]}"
        ):
            st.caption(f"Статус: {h['status']}")
            if h.get("screenshot_path") and Path(str(h["screenshot_path"])).exists():
                st.image(str(h["screenshot_path"]), width=400)
            if zones:
                rows = []
                for z in zones:
                    lat = z.get("centroid", {}).get("lat") if z.get("centroid") else None
                    lng = z.get("centroid", {}).get("lng") if z.get("centroid") else None
                    route = (
                        f'<a href="https://yandex.ru/maps/?pt={lng},{lat}&z=17" '
                        f'target="_blank">📍 Показать</a>'
                        if lat and lng
                        else "—"
                    )
                    rows.append({
                        "Тип": z.get("zone_type"),
                        "Название": z.get("name", "—"),
                        "Расстояние": f"{z.get('distance_meters', '—'):.0f} м"
                        if z.get("distance_meters")
                        else "—",
                        "Маршрут": route,
                    })
                st.write(
                    pd.DataFrame(rows).to_html(escape=False, index=False),
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
