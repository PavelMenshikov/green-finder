import numpy as np
import cv2
from src.detector import GreenZoneDetector, DetectionConfig


def test_detect_returns_list():
    detector = GreenZoneDetector()
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    image[100:200, 100:200] = [50, 180, 50]
    zones = detector.detect(image)
    assert isinstance(zones, list)


def test_detect_green_zone():
    detector = GreenZoneDetector()
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(image, (50, 50), (200, 200), (50, 200, 50), -1)
    zones = detector.detect(image)
    assert any(z.zone_type == "park" for z in zones)


def test_detect_pond():
    detector = GreenZoneDetector()
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.rectangle(image, (300, 300), (400, 400), (200, 100, 50), -1)
    zones = detector.detect(image)
    assert any(z.zone_type == "pond" for z in zones)


def test_merge_nearby_zones():
    detector = GreenZoneDetector(config=DetectionConfig(merge_distance_px=50))
    from src.models import GreenZone, GeoPoint

    zones = [
        GreenZone(zone_type="park", centroid=GeoPoint(lat=100, lng=100)),
        GreenZone(zone_type="park", centroid=GeoPoint(lat=110, lng=105)),
    ]
    merged = detector._merge_nearby(zones)
    assert len(merged) <= len(zones)


def test_empty_image():
    detector = GreenZoneDetector()
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    zones = detector.detect(image)
    assert len(zones) == 0
