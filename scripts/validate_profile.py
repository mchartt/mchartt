"""Validate the files that GitHub actually embeds in the profile README.

Uses only the Python standard library so it runs on GitHub Actions without
installing dependencies. Validation is intentionally read-only.
"""
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "{http://www.w3.org/2000/svg}"


class ReadmeImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()
        self.picture_sources = []
        self.picture_fallbacks = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "source" and "srcset" in attrs:
            self.picture_sources.append(attrs["srcset"])
        if tag == "img" and attrs.get("src", "").startswith("./assets/"):
            self.picture_fallbacks.append(attrs["src"])
        if tag in ("img", "source"):
            for attr in ("src", "srcset"):
                value = attrs.get(attr, "")
                # README uses one image per srcset, no responsive density lists.
                if value.startswith("./assets/"):
                    self.paths.add(value.split("?", 1)[0][2:])


def validate():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    images = ReadmeImages()
    images.feed(readme)
    if not images.paths:
        raise ValueError("README contains no local image references")
    if len(images.picture_sources) != len(images.picture_fallbacks):
        raise ValueError("Every dark-mode picture needs a light-mode image fallback")

    for rel in sorted(images.paths):
        path = ROOT / rel
        if not path.is_file():
            raise FileNotFoundError(f"README references missing asset: {rel}")
        if path.suffix == ".svg":
            root = ET.parse(path).getroot()
            if root.tag != SVG_NS + "svg":
                raise ValueError(f"Invalid SVG root: {rel}")
            if not root.attrib.get("viewBox"):
                raise ValueError(f"Missing SVG viewBox: {rel}")
            if root.find(SVG_NS + "title") is None and not root.attrib.get("aria-label"):
                raise ValueError(f"Missing accessible SVG title: {rel}")

    # Check the output of both renderers even if the README changes later.
    for stem in ("header", "contributions", "snake", "languages"):
        for theme in ("dark", "light"):
            path = ROOT / "assets" / f"{stem}.{theme}.svg"
            if not path.exists():
                raise FileNotFoundError(path)
            ET.parse(path)
        dark = (ROOT / "assets" / f"{stem}.dark.svg").read_bytes()
        light = (ROOT / "assets" / f"{stem}.light.svg").read_bytes()
        if dark == light:
            raise ValueError(f"Dark/light {stem} are identical")

    data = json.loads((ROOT / "assets/activity.json").read_text(encoding="utf-8"))
    first, last = date.fromisoformat(data["from_date"]), date.fromisoformat(data["to_date"])
    if last - first != timedelta(days=364):
        raise ValueError("Activity calendar must cover exactly 365 days")
    if any(not isinstance(data[key], int) or data[key] < 0
           for key in ("total", "active_days", "current_streak", "longest_streak_in_window")):
        raise ValueError("Invalid contribution statistics")
    if not (data["active_days"] <= 365 and
            data["current_streak"] <= data["longest_streak_in_window"] <= 365):
        raise ValueError("Impossible streak statistics")
    print(f"Validated {len(images.paths)} README images, 8 generated SVGs and 365-day activity data")


if __name__ == "__main__":
    validate()
