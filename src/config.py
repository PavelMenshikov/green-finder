from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    slow_mo: int = 100

    proxy_server: Optional[str] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None

    yandex_maps_url: str = "https://yandex.ru/maps"
    search_zoom: int = 17
    walking_minutes: int = 20
    walking_speed_kmh: float = 5.0

    save_screenshots: bool = True
    screenshots_dir: str = "data/screenshots"

    database_url: str = "sqlite:///data/history.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def walking_radius_meters(self) -> float:
        return (self.walking_speed_kmh * 1000 / 60) * self.walking_minutes

    @property
    def screenshots_path(self) -> Path:
        p = Path(self.screenshots_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def proxy_config(self) -> Optional[dict]:
        if self.proxy_server:
            config = {"server": self.proxy_server}
            if self.proxy_username:
                config["username"] = self.proxy_username
            if self.proxy_password:
                config["password"] = self.proxy_password
            return config
        return None


settings = Settings()
