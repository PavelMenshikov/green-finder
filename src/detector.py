import cv2
import numpy as np
from src.models import GreenZone, GeoPoint
from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectionConfig:
    green_hue_range: tuple[int, int] = (35, 85)
    green_sat_min: int = 30
    green_val_min: int = 30
    blue_hue_range: tuple[int, int] = (100, 130)
    min_contour_area: int = 500
    merge_distance_px: int = 20


class GreenZoneDetector:
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()

    def detect(self, image: np.ndarray) -> list[GreenZone]:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        zones: list[GreenZone] = []

        zones.extend(self._detect_by_color(hsv, "park", self.config.green_hue_range))
        zones.extend(self._detect_by_color(hsv, "pond", self.config.blue_hue_range))
        zones.extend(self._detect_walking_paths(image, hsv))

        merged = self._merge_nearby(zones)
        return sorted(merged, key=lambda z: z.area_pixels or 0, reverse=True)

    def _detect_by_color(
        self, hsv: np.ndarray, zone_type: str, hue_range: tuple[int, int]
    ) -> list[GreenZone]:
        lower = np.array([hue_range[0], self.config.green_sat_min, self.config.green_val_min])
        upper = np.array([hue_range[1], 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        zones = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.config.min_contour_area:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            zones.append(
                GreenZone(
                    zone_type=zone_type,
                    area_pixels=int(area),
                    centroid=GeoPoint(lat=float(cy), lng=float(cx)),
                    source="cv_detection",
                )
            )
        return zones

    def _detect_walking_paths(
        self, image: np.ndarray, hsv: np.ndarray
    ) -> list[GreenZone]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(
            edges, rho=1, theta=np.pi / 180, threshold=30, minLineLength=40, maxLineGap=10
        )
        if lines is None:
            return []

        mask = np.zeros(gray.shape, np.uint8)
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > 50:
                cv2.line(mask, (x1, y1), (x2, y2), 255, 3)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        zones = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 200:
                continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            zones.append(
                GreenZone(
                    zone_type="alley",
                    area_pixels=int(area),
                    centroid=GeoPoint(lat=float(cy), lng=float(cx)),
                    source="cv_path_detection",
                )
            )
        return zones

    def _merge_nearby(self, zones: list[GreenZone]) -> list[GreenZone]:
        if not zones:
            return zones
        merged = []
        used = set()
        for i, z1 in enumerate(zones):
            if i in used:
                continue
            group = [z1]
            used.add(i)
            for j, z2 in enumerate(zones):
                if j in used:
                    continue
                if z1.centroid and z2.centroid:
                    dist = np.sqrt(
                        (z1.centroid.lat - z2.centroid.lat) ** 2
                        + (z1.centroid.lng - z2.centroid.lng) ** 2
                    )
                    if dist < self.config.merge_distance_px:
                        group.append(z2)
                        used.add(j)
            if len(group) > 1:
                avg_lat = sum(z.centroid.lat for z in group) / len(group)
                avg_lng = sum(z.centroid.lng for z in group) / len(group)
                total_area = sum(z.area_pixels or 0 for z in group)
                merged.append(
                    GreenZone(
                        zone_type=group[0].zone_type,
                        area_pixels=total_area,
                        centroid=GeoPoint(lat=avg_lat, lng=avg_lng),
                        source="cv_detection",
                    )
                )
            else:
                merged.append(z1)
        return merged
