#!/usr/bin/env python3
"""Pull GPT Image 2.6 materials from Directus CMS into content/cms-materials.json."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from cms_materials import CMS_MATERIALS_PATH, is_approved_cms_media_url, media_base_url, read_cms_store
from common import ROOT, read_json
from source_cases import read_cases

PAGE_SIZE = 100
FIELDS = (
    "id,title,prompt,status,author_x_url,source_post_url,source_published_at,"
    "tags,notes,date_created,date_updated,image_url,r2_object_key"
)
ALLOWED_STATUSES = {"ready", "published"}

CATEGORY_KEYWORDS = (
    ("gif-animation", ("gif", "sprite", "loop", "animation", "frames", "像素精灵", "动图", "循环动画")),
    ("svg-design-assets", ("svg", "vector", "logo", "icon", "sticker", "贴纸", "徽标", "矢量")),
    ("markup-edits", ("markup", "annotate", "recolor", "replace", "edit this", "inpaint", "局部编辑", "换装", "修改")),
    ("infographics", ("infographic", "diagram", "chart", "x-ray", "xray", "x 光", "解剖", "信息图", "图解", "科普")),
    ("posters-typography", ("poster", "typography", "card", "cover", "flyer", "magazine", "贺卡", "海报", "封面", "排版", "字体")),
    ("brand-products", ("product", "beverage", "packaging", "bottle", "brand", "ad", "commercial", "fanta", "商品", "包装", "广告", "饮品")),
    ("interiors-architecture", ("interior", "architecture", "room", "building", "balcony", "bedroom", "elevator", "建筑", "室内", "卧室", "阳台", "电梯")),
    ("characters-consistency", ("portrait", "selfie", "woman", "man", "character", "hanfu", "kimono", "肖像", "自拍", "汉服", "和服", "人像", "角色")),
)


def validate_cms_env(base_url: str, token: str, collection: str) -> None:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or not re.fullmatch(r"[A-Za-z0-9._~-]+", token)
        or not re.fullmatch(r"[A-Za-z0-9_]+", collection)
    ):
        raise ValueError("Set CMS_BASE_URL to the HTTPS origin, configure CMS_READ_TOKEN, and check cms.collection.")


def fetch_all_materials(base_url: str, token: str, collection: str) -> list[dict]:
    """Fetch all records from Directus collection with deterministic pagination."""
    validate_cms_env(base_url, token, collection)
    rows: list[dict] = []
    offset = 0
    while True:
        query = urlencode({
            "fields": FIELDS,
            "sort": "-date_created,-id",
            "limit": PAGE_SIZE,
            "offset": offset,
        })
        request = Request(
            f"{base_url.rstrip('/')}/items/{collection}?{query}",
            headers={"Accept": "application/json", "User-Agent": "Raphael-CMS-Sync/2.0"},
        )
        request.add_unredirected_header("Authorization", f"Bearer {token}")
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        batch = payload.get("data")
        if not isinstance(batch, list):
            raise ValueError("CMS returned an invalid items payload.")
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def extract_author_handle(author_url: str | None, source_url: str | None) -> str:
    for candidate in (author_url, source_url):
        if not candidate:
            continue
        parts = urlsplit(candidate)
        host = (parts.hostname or "").lower().removeprefix("www.")
        segments = [seg for seg in parts.path.split("/") if seg]
        if host in ("x.com", "twitter.com") and segments:
            return "@" + segments[0].lstrip("@")
        if host == "github.com" and segments:
            return "@" + segments[0]
    return ""


def normalize_https_url(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    parts = urlsplit(cleaned)
    if parts.scheme != "https" or not parts.hostname or parts.username or re.search(r"[\s<>]", cleaned):
        return None
    return cleaned


def iso_date_part(value: str | None) -> str | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    candidate = value[:10]
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
        return candidate
    return None


def classify_category(title: str, prompt: str, tags: list[str], valid_categories: set[str]) -> str:
    haystack = " ".join([title, prompt[:600], " ".join(tags)]).lower()
    for category_id, keywords in CATEGORY_KEYWORDS:
        if category_id in valid_categories and any(kw in haystack for kw in keywords):
            return category_id
    return "characters-consistency" if "characters-consistency" in valid_categories else sorted(valid_categories)[0]


def normalize_records(
    raw_rows: list[dict],
    config: dict,
    curated_url_map: dict[str, str],
) -> tuple[list[dict], int]:
    valid_categories = {cat["id"] for cat in config["categories"]}
    items: list[dict] = []
    seen_slugs: set[str] = set()

    for row in raw_rows:
        status = str(row.get("status") or "").strip().lower()
        if status and status not in ALLOWED_STATUSES:
            continue
        cms_id = str(row.get("id") or "").strip()
        title = str(row.get("title") or "").strip()
        prompt = str(row.get("prompt") or "").strip()
        if not cms_id or not title or not prompt:
            continue

        short_hex = re.sub(r"[^a-z0-9]", "", cms_id.lower())[:8]
        slug = f"cms-{short_hex}"
        if slug in seen_slugs:
            slug = f"cms-{re.sub(r'[^a-z0-9]', '', cms_id.lower())[:12]}"
        seen_slugs.add(slug)

        raw_tags = row.get("tags")
        tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()] if isinstance(raw_tags, list) else []

        image_url = normalize_https_url(row.get("image_url"))
        if image_url and not is_approved_cms_media_url(image_url, config):
            image_url = None
        if not image_url and isinstance(row.get("r2_object_key"), str) and row["r2_object_key"].strip():
            key = row["r2_object_key"].strip().lstrip("/")
            base_origin = f"{urlsplit(media_base_url(config)).scheme}://{urlsplit(media_base_url(config)).netloc}/"
            candidate = base_origin + key
            if is_approved_cms_media_url(candidate, config):
                image_url = candidate

        source_url = normalize_https_url(row.get("source_post_url"))
        author_url = normalize_https_url(row.get("author_x_url"))
        author = extract_author_handle(author_url, source_url)
        added_at = iso_date_part(row.get("date_created")) or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        items.append({
            "id": slug,
            "cms_id": cms_id,
            "title": title,
            "prompt": prompt,
            "category": classify_category(title, prompt, tags, valid_categories),
            "tags": tags,
            "image_url": image_url,
            "r2_object_key": str(row.get("r2_object_key") or "").strip() or None,
            "author": author,
            "author_url": author_url,
            "source_url": source_url,
            "source_published_at": iso_date_part(row.get("source_published_at")),
            "added_at": added_at,
            "date_created": str(row.get("date_created") or "").strip() or None,
            "status": status or "ready",
            "notes": str(row.get("notes") or "").strip() or None,
            "matched_curated_case_id": curated_url_map.get(source_url) if source_url else None,
        })

    items.sort(key=lambda x: (x.get("date_created") or x["added_at"], x["cms_id"]), reverse=True)
    return items, len(raw_rows)


def sync_to_disk(
    base_url: str,
    token: str,
    *,
    force_timestamp: bool = False,
    now: datetime | None = None,
) -> tuple[bool, int, int]:
    config = read_json("site.config.json")
    collection = str((config.get("cms") or {}).get("collection") or "materials")
    cases = read_cases()
    prompts = read_json("content/prompts.json")
    curated_url_map: dict[str, str] = {}
    for entry in cases + prompts:
        src = (entry.get("source") or {}).get("url")
        if src:
            curated_url_map[src] = entry["id"]

    raw_rows = fetch_all_materials(base_url, token, collection)
    items, total_count = normalize_records(raw_rows, config, curated_url_map)

    existing = read_cms_store()
    previous_items = existing.get("items") or []
    previous_total = existing.get("total_cms_records")
    data_changed = (
        items != previous_items
        or total_count != previous_total
        or existing.get("collection") != collection
        or existing.get("cms_base_url") != base_url.rstrip("/")
        or existing.get("media_base_url") != media_base_url(config)
        or not (ROOT / CMS_MATERIALS_PATH).is_file()
    )

    if not data_changed and not force_timestamp:
        return False, len(items), total_count

    ts = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    payload = {
        "collection": collection,
        "cms_base_url": base_url.rstrip("/"),
        "media_base_url": media_base_url(config),
        "synced_at": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_cms_records": total_count,
        "items": items,
    }
    target = ROOT / CMS_MATERIALS_PATH
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True, len(items), total_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-timestamp", action="store_true", help="Refresh synced_at even if CMS items are unchanged.")
    args = parser.parse_args()
    try:
        changed, synced_items, total_count = sync_to_disk(
            os.environ.get("CMS_BASE_URL", ""),
            os.environ.get("CMS_READ_TOKEN", ""),
            force_timestamp=args.force_timestamp,
        )
    except HTTPError as exc:
        print(f"CMS materials sync request failed (HTTP {exc.code}).", file=sys.stderr)
        return 1
    except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"CMS materials sync failed: {exc}", file=sys.stderr)
        return 1

    if changed:
        print(f"Synced {synced_items} CMS materials (total records: {total_count}) into {CMS_MATERIALS_PATH}.")
    else:
        print(f"No CMS changes detected ({synced_items} materials, total records: {total_count}); skipped timestamp churn.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
