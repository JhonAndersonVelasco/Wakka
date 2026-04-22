"""
Arch Wiki application lists — scraping and local cache (no GUI dependencies).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

WIKI_CATEGORIES: dict[str, str] = {
    "Documents": "https://wiki.archlinux.org/title/List_of_applications/Documents",
    "Internet": "https://wiki.archlinux.org/title/List_of_applications/Internet",
    "Multimedia": "https://wiki.archlinux.org/title/List_of_applications/Multimedia",
    "Science": "https://wiki.archlinux.org/title/List_of_applications/Science",
    "Security": "https://wiki.archlinux.org/title/List_of_applications/Security",
    "Utilities": "https://wiki.archlinux.org/title/List_of_applications/Utilities",
    "Other": "https://wiki.archlinux.org/title/List_of_applications/Other",
}

WIKI_CACHE_FILE = os.path.expanduser("~/.cache/wakka/arch_wiki_apps.json")
WIKI_CACHE_DURATION = 24 * 60 * 60  # 24 hours


def fetch_wiki_applications_by_category() -> dict[str, list[dict[str, str]]]:
    """
    Scrape Arch Wiki application lists; results are cached on disk for WIKI_CACHE_DURATION.
    """
    os.makedirs(os.path.dirname(WIKI_CACHE_FILE), exist_ok=True)

    if os.path.exists(WIKI_CACHE_FILE):
        try:
            with open(WIKI_CACHE_FILE, encoding="utf-8") as f:
                cache_data = json.load(f)
            if time.time() - cache_data.get("timestamp", 0) < WIKI_CACHE_DURATION:
                logger.debug("Loading Arch Wiki app list from cache.")
                return cache_data.get("applications", {})
        except json.JSONDecodeError:
            logger.warning("Corrupt Arch Wiki cache JSON; re-scraping.")
        except OSError as e:
            logger.warning("Could not read Arch Wiki cache (%s); re-scraping.", e)

    applications_by_category: dict[str, list[dict[str, str]]] = {}

    for category_name, url in WIKI_CATEGORIES.items():
        logger.info("Scraping Arch Wiki category: %s", category_name)
        applications_by_category[category_name] = []

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            content_div = soup.find("div", {"class": "mw-parser-output"})
            if not content_div:
                continue

            for ul in content_div.find_all("ul"):
                for li in ul.find_all("li", recursive=False):
                    app_name = ""
                    description = ""

                    b_tag = li.find("b")
                    if not b_tag:
                        continue

                    a_tag_in_b = b_tag.find("a", href=True)
                    if a_tag_in_b:
                        app_name = a_tag_in_b.get_text(strip=True)
                    else:
                        app_name = b_tag.get_text(strip=True)

                    if len(app_name) < 2 or app_name.startswith("Jump"):
                        continue

                    description_parts = []
                    for sibling in b_tag.next_siblings:
                        if sibling.name in ("ul", "li"):
                            break
                        if isinstance(sibling, str):
                            description_parts.append(sibling.strip())
                        elif sibling.name == "span" and "mw-editsection" not in sibling.get("class", []):
                            description_parts.append(sibling.get_text(strip=True))
                    description = " ".join(filter(None, description_parts)).strip()
                    description = re.sub(r"^[—:\-\s]+", "", description).strip()

                    if app_name and app_name not in [a["name"] for a in applications_by_category[category_name]]:
                        applications_by_category[category_name].append(
                            {"name": app_name, "description": description}
                        )
        except Exception:
            logger.exception("Error parsing Arch Wiki category %s", category_name)

    try:
        with open(WIKI_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"timestamp": time.time(), "applications": applications_by_category},
                f,
                indent=2,
            )
    except OSError as e:
        logger.warning("Could not save Arch Wiki cache: %s", e)

    return applications_by_category
