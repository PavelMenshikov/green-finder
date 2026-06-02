import math
import re
import time
from typing import Optional

import cv2
import numpy as np

from src.browser import BrowserManager
from src.detector import GreenZoneDetector
from src.models import SearchResult, GreenZone, GeoPoint
from src.config import settings


class GreenZoneScraper:
    def __init__(self):
        self.browser = BrowserManager()
        self.detector = GreenZoneDetector()

    def search(self, address: str, city: str = "Москва") -> SearchResult:
        result = SearchResult(address=address.strip(), city=city.strip())
        self.browser.start()
        page = self.browser.new_page()

        try:
            page.goto(settings.yandex_maps_url, wait_until="networkidle")
            self._accept_cookies(page)

            query = f"{city}, {address}" if city else address
            self._search_address(page, query)
            time.sleep(3)
            self._zoom_to_level(page, settings.search_zoom)
            time.sleep(2)

            center, zoom = self._extract_map_state(page)
            result.center_coords = center
            result.map_zoom = zoom

            screenshot_path = self.browser.screenshot(page, self._safe_name(f"{city}_{address}"))
            result.screenshot_path = str(screenshot_path)

            image = cv2.imdecode(np.fromfile(str(screenshot_path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                result.status = "error: failed to read screenshot"
                return result

            zones = self.detector.detect(image)
            zones = self._name_zones(zones, image)

            if center and zoom:
                zones = self._pixel_to_gps(zones, image, center, zoom)
                zones = self._estimate_distances(zones, image, center)

            result.green_zones = zones
            result.status = "completed"

        except Exception as e:
            result.status = f"error: {e}"
        finally:
            self.browser.stop()

        return result

    # ── address helpers ──────────────────────────────────────────────

    def _safe_name(self, raw: str) -> str:
        return re.sub(r"[^\w\s-]", "", raw)[:60]

    # ── browser interactions ────────────────────────────────────────

    def _accept_cookies(self, page):
        for sel in [
            "button:has-text('Принять')",
            "button:has-text('Согласен')",
            "button:has-text('OK')",
            "[class*=accept]",
            "[class*=cookie] button",
        ]:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    time.sleep(1)
                    return
            except Exception:
                continue

    def _search_address(self, page, query: str):
        try:
            inp = page.locator("input[class*='search']").first
            inp.fill(query)
            inp.press("Enter")
            time.sleep(3)
        except Exception:
            try:
                page.keyboard.press("/")
                time.sleep(1)
                page.keyboard.type(query, delay=50)
                page.keyboard.press("Enter")
                time.sleep(3)
            except Exception:
                pass

    def _zoom_to_level(self, page, zoom: int):
        for _ in range(zoom - 10):
            page.keyboard.press("=")
            time.sleep(0.2)

    def _extract_map_state(self, page) -> tuple[Optional[GeoPoint], Optional[int]]:
        try:
            url = page.url
            ll_match = re.search(r"[?&]ll=([\d.]+)%2C([\d.]+)", url)
            z_match = re.search(r"[?&]z=(\d+)", url)
            if ll_match:
                return GeoPoint(lat=float(ll_match.group(2)), lng=float(ll_match.group(1))), \
                       int(z_match.group(1)) if z_match else settings.search_zoom
        except Exception:
            pass
        return None, None

    # ── zone naming ─────────────────────────────────────────────────

    def _name_zones(self, zones: list[GreenZone], image: np.ndarray) -> list[GreenZone]:
        h, w = image.shape[:2]
        for z in zones:
            if not z.centroid:
                continue
            x = int(np.clip(z.centroid.lng, 0, w - 1))
            y = int(np.clip(z.centroid.lat, 0, h - 1))
            pixel = image[y, x]
            z.name = self._guess_name(z.zone_type, pixel)
        return zones

    @staticmethod
    def _guess_name(t: str, pixel) -> str:
        if t == "pond":
            return "Пруд / Водоём"
        if t == "alley":
            return "Прогулочная аллея"
        if t == "park":
            return "Парк / Зелёная зона" if np.mean(pixel) > 100 else "Сквер"
        return "Зелёная зона"

    # ── pixel → GPS conversion ─────────────────────────────────────

    def _pixel_to_gps(
        self, zones: list[GreenZone], image: np.ndarray,
        center: GeoPoint, zoom: int,
    ) -> list[GreenZone]:
        h, w = image.shape[:2]
        res = 156543.03 * math.cos(math.radians(center.lat)) / (2 ** zoom)

        for z in zones:
            if not z.centroid:
                continue
            dx = (z.centroid.lng - w / 2) * res
            dy = (h / 2 - z.centroid.lat) * res
            lat = center.lat + dy / 111320.0
            lng = center.lng + dx / (111320.0 * math.cos(math.radians(center.lat)))
            z.centroid = GeoPoint(lat=round(lat, 6), lng=round(lng, 6))

        return zones

    # ── distance from center ───────────────────────────────────────

    def _estimate_distances(
        self, zones: list[GreenZone], image: np.ndarray, center: GeoPoint,
    ) -> list[GreenZone]:
        for z in zones:
            if not z.centroid:
                continue
            d = self._haversine(center.lat, center.lng, z.centroid.lat, z.centroid.lng)
            z.distance_meters = round(d, 1)
            z.walking_minutes = round(d / (settings.walking_speed_kmh * 1000 / 60), 1)
        return zones

    @staticmethod
    def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
