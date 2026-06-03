import csv
import os
from typing import List, Dict


def _resolve_field(row: Dict, *aliases: str, default="") -> str:
    """Return the first matching alias value from a CSV row dict."""
    for alias in aliases:
        if alias in row and row[alias] is not None:
            val = str(row[alias]).strip()
            if val:
                return val
    return default


def _safe_int(value: str) -> int:
    """Safely parse an integer, returning 0 on failure."""
    try:
        return int(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return 0


def read_trends_from_csv(file_path: str) -> List[Dict]:
    """
    Reads trending topics from a CSV file.

    Supports two column naming conventions:
      - New business format: topic, source_url
      - Legacy format:       trend_title, url

    Also accepts: title, post_url as additional aliases.

    Required columns (at least one alias must be present):
      - topic / trend_title / title
      - platform

    Recommended columns (optional, defaults to 0 or ""):
      - source_url / url / post_url
      - views, likes, comments, shares, saves
      - posted_date, creator, content_format, content_pillar, region, keyword
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Trends CSV not found at: {file_path}")

    trends = []
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError(f"CSV file is empty or has no header row: {file_path}")

        # Validate that at least a title field exists
        field_names_lower = [h.lower().strip() for h in reader.fieldnames]
        has_title = any(f in field_names_lower for f in ["topic", "trend_title", "title"])
        if not has_title:
            raise ValueError(
                f"CSV must have a 'topic', 'trend_title', or 'title' column. "
                f"Found: {list(reader.fieldnames)}"
            )

        for row in reader:
            # Normalize row keys to strip whitespace
            row = {k.strip(): v for k, v in row.items() if k}

            title = _resolve_field(row, "topic", "trend_title", "title", default="Untitled Trend")
            url = _resolve_field(row, "source_url", "url", "post_url", default="")
            platform = _resolve_field(row, "platform", default="Unknown")

            trends.append({
                "trend_title": title,
                "views": _safe_int(_resolve_field(row, "views", default="0")),
                "likes": _safe_int(_resolve_field(row, "likes", default="0")),
                "comments": _safe_int(_resolve_field(row, "comments", default="0")),
                "shares": _safe_int(_resolve_field(row, "shares", default="0")),
                "platform": platform,
                "url": url,
                # Extended fields (passed through for future use)
                "saves": _safe_int(_resolve_field(row, "saves", default="0")),
                "posted_date": _resolve_field(row, "posted_date", default=""),
                "creator": _resolve_field(row, "creator", default=""),
                "content_format": _resolve_field(row, "content_format", default=""),
                "content_pillar": _resolve_field(row, "content_pillar", default=""),
                "region": _resolve_field(row, "region", default=""),
                "keyword": _resolve_field(row, "keyword", default=""),
            })

    return trends
