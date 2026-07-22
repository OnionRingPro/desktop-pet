from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.resource_utils import resource_path

MESSAGES_CONFIG = "config/messages.json"
HTTP_TIMEOUT_SECONDS = 10
USER_AGENT = "desktop-pet/1.0"

WMO_WEATHER_ZH = {
    0: "晴",
    1: "大部晴朗",
    2: "多云",
    3: "阴",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "冻毛毛雨",
    57: "冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴有冰雹",
    99: "强雷阵雨伴有冰雹",
}


@dataclass(frozen=True)
class Location:
    city: str
    latitude: float
    longitude: float


def load_fallback_city(config_path: Path | None = None) -> str:
    path = config_path or resource_path(MESSAGES_CONFIG)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            city = str(data.get("weather_city", "")).strip()
            if city:
                return city
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return ""


def _http_get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _weather_description(code: int) -> str:
    return WMO_WEATHER_ZH.get(code, "天气多变")


def _resolve_location_by_ip() -> Location:
    data = _http_get_json(
        "http://ip-api.com/json/?fields=status,message,city,lat,lon"
    )
    if data.get("status") != "success":
        message = str(data.get("message", "定位失败"))
        raise RuntimeError(message)

    city = str(data.get("city", "")).strip() or "你所在的城市"
    return Location(city=city, latitude=float(data["lat"]), longitude=float(data["lon"]))


def _resolve_location_by_city(city: str) -> Location:
    query = urllib.parse.urlencode(
        {
            "name": city,
            "count": 1,
            "language": "zh",
            "format": "json",
        }
    )
    data = _http_get_json(f"https://geocoding-api.open-meteo.com/v1/search?{query}")
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"找不到城市：{city}")

    place = results[0]
    name = str(place.get("name", city)).strip() or city
    admin1 = str(place.get("admin1", "")).strip()
    display_city = f"{name}（{admin1}）" if admin1 and admin1 not in name else name
    return Location(
        city=display_city,
        latitude=float(place["latitude"]),
        longitude=float(place["longitude"]),
    )


def _resolve_location() -> Location:
    try:
        return _resolve_location_by_ip()
    except (OSError, urllib.error.URLError, RuntimeError, TypeError, ValueError, KeyError):
        fallback_city = load_fallback_city()
        if fallback_city:
            return _resolve_location_by_city(fallback_city)
        raise RuntimeError("无法定位当前城市，请在 config/messages.json 设置 weather_city")


def _fetch_current_weather(location: Location) -> tuple[float, int]:
    query = urllib.parse.urlencode(
        {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,weather_code",
            "timezone": "auto",
        }
    )
    data = _http_get_json(f"https://api.open-meteo.com/v1/forecast?{query}")
    current = data.get("current") or {}
    temperature = float(current["temperature_2m"])
    weather_code = int(current["weather_code"])
    return temperature, weather_code


def fetch_weather_message() -> str:
    location = _resolve_location()
    temperature, weather_code = _fetch_current_weather(location)
    description = _weather_description(weather_code)
    temp_text = str(int(round(temperature)))
    return f"今天{location.city}{description}，{temp_text}°C～"


class WeatherWorker(QThread):
    result = Signal(str)

    def run(self) -> None:
        try:
            message = fetch_weather_message()
        except (OSError, urllib.error.URLError, RuntimeError, TypeError, ValueError, KeyError):
            message = "天气查询失败，稍后再问我吧。"
        self.result.emit(message)
