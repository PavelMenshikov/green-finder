<div align="center">

# 🌳 Green Zone Finder

**Find walking-distance parks, ponds & alleys near any address — via browser automation + computer vision.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=fff)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-FF4B4B?logo=streamlit&logoColor=fff)](https://streamlit.io)
[![Playwright](https://img.shields.io/badge/Playwright-1.58-45BA4B?logo=playwright&logoColor=fff)](https://playwright.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9-5C3EE8?logo=opencv&logoColor=fff)](https://opencv.org)
[![Open In Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://green-finder-kmxmwomrjql8ddbqfuvwbr.streamlit.app)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31-FF4B4B?logo=streamlit&logoColor=fff)](https://streamlit.io)
[![Playwright](https://img.shields.io/badge/Playwright-1.58-45BA4B?logo=playwright&logoColor=fff)](https://playwright.dev)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.9-5C3EE8?logo=opencv&logoColor=fff)](https://opencv.org)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.7-E92063?logo=pydantic&logoColor=fff)](https://docs.pydantic.dev)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=fff)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-f39f37)](#)

[Features](#features) • [Demo](#demo) • [Quick start](#quick-start) • [Configuration](#configuration) • [Deploy](#deploy)

---

</div>

**Motivation:** Yandex Maps doesn't expose green zone data via a public API.
This tool uses **Playwright** to open the map, takes a **screenshot**, and applies **OpenCV** color segmentation
to detect parks, water bodies, and walking paths within a configurable walking radius.

## Features

- 🗺️ **Any address** — works for any city, fuzzy search via Yandex Maps
- 🌿 **CV-powered detection** — parks (green mask), ponds (blue mask), alleys (Hough lines)
- 📍 **Real GPS coordinates** — pixel-to-GPS conversion for every detected zone
- 🚶 **Route links** — click to open Yandex Maps with walking route from target
- 🧠 **History** — all searches saved in SQLite with full results
- 🎛️ **Configurable** — zoom, walking radius, headless mode via `.env`

## Stack

| Layer | Technology | Badge |
|-------|-----------|-------|
| UI | [Streamlit](https://streamlit.io) | ![Streamlit](https://img.shields.io/badge/-FF4B4B?logo=streamlit) |
| Browser automation | [Playwright](https://playwright.dev) | ![Playwright](https://img.shields.io/badge/-45BA4B?logo=playwright) |
| Computer Vision | [OpenCV](https://opencv.org) | ![OpenCV](https://img.shields.io/badge/-5C3EE8?logo=opencv) |
| Validation | [Pydantic](https://docs.pydantic.dev) | ![Pydantic](https://img.shields.io/badge/-E92063?logo=pydantic) |
| Storage | SQLite | ![SQLite](https://img.shields.io/badge/-003B57?logo=sqlite) |

## Quick start

```bash
# 1. Clone
git clone https://github.com/YOUR_USER/green-finder
cd green-finder

# 2. Install deps
pip install -r requirements.txt

# 3. Install Playwright browser
playwright install chromium

# 4. Run
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

## Configuration

Copy `.env.example` → `.env` and tweak:

| Variable | Default | Description |
|----------|---------|-------------|
| `HEADLESS` | `false` | Run browser without visible window |
| `VIEWPORT_WIDTH` | `1920` | Browser window width |
| `SLOW_MO` | `100` | Delay between actions (ms) |
| `SEARCH_ZOOM` | `17` | Map zoom level (higher = closer) |
| `WALKING_MINUTES` | `20` | Walking radius in minutes |
| `WALKING_SPEED_KMH` | `5` | Average walking speed |
| `PROXY_SERVER` | — | Proxy for Yandex Maps (optional) |

## Deploy

### Streamlit Community Cloud

[![Deploy to Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → select your repo → branch `main` → file `app.py`
4. Add secrets in the dashboard:
   ```
   HEADLESS = "true"
   ```
5. Deploy 🚀

### Docker

```bash
docker build -t green-finder .
docker run -p 8501:8501 -e HEADLESS=true green-finder
```

## Project structure

```
green-finder/
├── app.py              # Streamlit entry point
├── src/
│   ├── browser.py      # Playwright browser manager + stealth
│   ├── detector.py     # OpenCV green zone detection
│   ├── scraper.py      # Yandex Maps interaction orchestrator
│   ├── models.py       # Pydantic data models
│   ├── config.py       # Settings (pydantic-settings)
│   └── database.py     # SQLite history storage
├── tests/              # pytest tests
├── data/               # Screenshots + SQLite DB
├── .env.example
├── requirements.txt
└── README.md
```

## How it works

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Playwright  │───>│  Screenshot  │───>│    OpenCV    │───>│  Streamlit   │
│  Яндекс.Карты │    │  (1920×1080) │    │  HSV masks   │    │  Table + Map │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                              │
                                              ▼
                                       🟩 Parks (green)
                                       🟦 Ponds (blue)
                                       ═══ Alleys (Hough lines)
```

1. **Playwright** opens Yandex Maps, searches for the address, applies stealth patches
2. **Screenshot** taken at configured zoom level
3. **OpenCV** converts to HSV, applies color masks:
   - Green → parks, forests, gardens
   - Blue → ponds, lakes, fountains
   - Canny + Hough → walking paths, alleys
4. **Contours** are analyzed, nearby zones merged
5. **Pixel → GPS** conversion using Mercator projection + URL coords
6. **Distance** calculated via haversine formula
7. **Results** displayed in Streamlit with data table + screenshot + route links

## Example output

| # | Type | Name | Distance | Walking | Coordinates | Route |
|---|------|------|----------|---------|-------------|-------|
| 1 | park | Парк / Зелёная зона | 120 m | 2 min | 55.751, 37.618 | 🚶 |
| 2 | pond | Пруд / Водоём | 340 m | 5 min | 55.753, 37.625 | 🚶 |
| 3 | alley | Прогулочная аллея | 510 m | 7 min | 55.748, 37.615 | 🚶 |

---

<div align="center">

**Built with** `💻` **by** [Your Name](https://github.com/YOUR_USER)

</div>
