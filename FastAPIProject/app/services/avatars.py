from __future__ import annotations

from pathlib import Path


AVATAR_ITEMS = [
    {"id": 1, "file": "yellow_slime.svg", "color": "#FFD700", "name": "Yellow Slime"},
    {"id": 2, "file": "blue_slime.svg", "color": "#4169E1", "name": "Blue Slime"},
    {"id": 3, "file": "purple_slime.svg", "color": "#800080", "name": "Purple Slime"},
    {"id": 4, "file": "red_slime.svg", "color": "#DC143C", "name": "Red Slime"},
    {"id": 5, "file": "light_blue_slime.svg", "color": "#87CEEB", "name": "Light Blue Slime"},
]

DEFAULT_AVATAR_FILE = "yellow_slime.svg"


def get_avatar_catalog() -> list[dict]:
    return [dict(item) for item in AVATAR_ITEMS]


def get_avatar_meta(file_name: str | None) -> dict | None:
    if not file_name:
        return None
    for item in AVATAR_ITEMS:
        if item["file"] == file_name:
            return dict(item)
    return None


def is_valid_avatar_file(file_name: str | None) -> bool:
    if not file_name:
        return False
    return any(item["file"] == file_name for item in AVATAR_ITEMS)


def avatar_assets_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "avatars"
