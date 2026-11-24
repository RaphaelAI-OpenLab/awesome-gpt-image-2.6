#!/usr/bin/env python3
"""Sync pending AI prompt materials from Directus CMS into GitHub and write back raw URLs.

Two-phase execution prevents dead links if `git push` fails:
  1. `fetch`: download images for pending/failed items into assets/cms-materials/YYYY/MM/<id>.<ext>,
              regenerate content/cms-materials.json, and save pending writebacks to a temp file.
  2. `writeback`: after `git push` succeeds, PATCH github_image_url / github_file_path / status='synced'
                  back to Directus (and record sync_error for any failed items).
"""

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

ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "assets" / "cms-materials"
INDEX_PATH = ROOT / "content" / "cms-materials.json"
DEFAULT_REPO = "RaphaelAI-OpenLab/awesome-gpt-image-2.6-prompts"
DEFAULT_BRANCH = "main"
COLLECTION = "materials"
USER_AGENT = "Raphael-CMS-Sync/1.0"
MAX_IMAGE_BYTES = 15 * 1024 * 1024  # 15 MiB safety limit

EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_config(base_url: str, token: str) -> tuple[str, str]:
    base_url = base_url.strip().rstrip("/")
    token = token.strip()
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
    ):
        raise ValueError("DIRECTUS_URL / CMS_BASE_URL must be a valid HTTPS origin (e.g. https://raphael-cms.colorepistle.com).")
    if not token or not re.fullmatch(r"[A-Za-z0-9._~-]+", token):
        raise ValueError("DIRECTUS_API_TOKEN is missing or invalid.")
    return base_url, token


def api_request(
    base_url: str,
    token: str,
    method: str,
    path: str,
    body: dict | None = None,
    *,
    expect_json: bool = True,
    timeout: int = 30,
):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json" if expect_json else "*/*",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    req.add_unredirected_header("Authorization", f"Bearer {token}")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if expect_json:
            return json.loads(raw.decode("utf-8")) if raw else {}
        return raw, resp.headers.get("Content-Type", "")


def detect_image_ext(data: bytes, content_type: str = "", filename: str = "") -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    mime = content_type.split(";", 1)[0].strip().lower()
    if mime in EXT_BY_MIME:
        return EXT_BY_MIME[mime]
    suffix = Path(filename).suffix.lower()
    if suffix in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return ".jpg" if suffix == ".jpeg" else suffix
    return None


def safe_id(item_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "", str(item_id))
    if not cleaned:
        raise ValueError(f"Invalid item id: {item_id!r}")
    return cleaned


def year_month_for(item: dict) -> tuple[str, str]:
    raw_dt = item.get("date_created") or item.get("source_published_at")
    if isinstance(raw_dt, str) and len(raw_dt) >= 7:
        m = re.match(r"^(\d{4})-(\d{2})", raw_dt)
        if m:
            return m.group(1), m.group(2)
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}", f"{now.month:02d}"


def build_raw_url(repo: str, branch: str, rel_path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{rel_path}"


def fetch_all_items(base_url: str, token: str, query_params: dict[str, str]) -> list[dict]:
    items: list[dict] = []
    page = 1
    limit = 100
    while True:
        params = dict(query_params)
        params["limit"] = str(limit)
        params["page"] = str(page)
        res = api_request(base_url, token, "GET", f"/items/{COLLECTION}?{urlencode(params)}")
        batch = res.get("data") or []
        items.extend(batch)
        if len(batch) < limit:
            break
        page += 1
    return items


def serialize_index_item(item: dict, overrides: dict | None = None) -> dict:
    merged = dict(item)
    if overrides:
        merged.update(overrides)
    return {
        "id": merged.get("id"),
        "title": merged.get("title"),
        "prompt": merged.get("prompt"),
        "author_x_url": merged.get("author_x_url"),
        "source_post_url": merged.get("source_post_url"),
        "source_published_at": merged.get("source_published_at"),
        "github_file_path": merged.get("github_file_path"),
        "github_image_url": merged.get("github_image_url"),
        "status": merged.get("status"),
        "tags": merged.get("tags") or [],
        "notes": merged.get("notes"),
        "synced_at": merged.get("synced_at"),
        "date_created": merged.get("date_created"),
    }


def cmd_fetch(base_url: str, token: str, repo: str, branch: str, state_file: Path) -> int:
    pending = fetch_all_items(
        base_url,
        token,
        {
            "filter[status][_in]": "pending,failed",
            "fields": "*,source_image.id,source_image.type,source_image.filename_download",
            "sort": "date_created,id",
        },
    )

    synced_updates: list[dict] = []
    failed_updates: list[dict] = []
    now_iso = utc_now_iso()

    for item in pending:
        item_id = str(item["id"])
        src = item.get("source_image")
        file_id = src.get("id") if isinstance(src, dict) else (src if isinstance(src, str) else None)
        filename = src.get("filename_download", "") if isinstance(src, dict) else ""

        if not file_id:
            failed_updates.append({"id": item_id, "error": "Missing source_image file in Directus."})
            print(f"[SKIP/FAIL] {item_id}: missing source_image", file=sys.stderr)
            continue

        try:
            raw_bytes, content_type = api_request(
                base_url,
                token,
                "GET",
                f"/assets/{file_id}",
                expect_json=False,
                timeout=60,
            )
            if not raw_bytes:
                raise ValueError("Downloaded image file is empty.")
            if len(raw_bytes) > MAX_IMAGE_BYTES:
                raise ValueError(f"Image exceeds max size ({len(raw_bytes)} bytes > {MAX_IMAGE_BYTES}).")
            ext = detect_image_ext(raw_bytes, content_type, filename)
            if not ext:
                raise ValueError(f"Unsupported image format (content-type={content_type!r}, filename={filename!r}).")

            yyyy, mm = year_month_for(item)
            rel_path = f"assets/cms-materials/{yyyy}/{mm}/{safe_id(item_id)}{ext}"
            dest = ROOT / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw_bytes)

            raw_url = build_raw_url(repo, branch, rel_path)
            synced_updates.append(
                {
                    "id": item_id,
                    "github_file_path": rel_path,
                    "github_image_url": raw_url,
                    "status": "synced",
                    "synced_at": now_iso,
                    "sync_error": None,
                }
            )
            print(f"[FETCHED] {item_id} -> {rel_path} ({len(raw_bytes)} bytes)")
        except Exception as exc:
            failed_updates.append({"id": item_id, "error": str(exc)[:500]})
            print(f"[ERROR] {item_id}: {exc}", file=sys.stderr)

    # Rebuild content/cms-materials.json from all synced/published items + newly fetched items
    already_synced = fetch_all_items(
        base_url,
        token,
        {
            "filter[status][_in]": "synced,published",
            "fields": "id,title,prompt,author_x_url,source_post_url,source_published_at,github_file_path,github_image_url,status,tags,notes,synced_at,date_created",
            "sort": "-date_created,id",
        },
    )

    by_id: dict[str, dict] = {}
    for row in already_synced:
        by_id[str(row["id"])] = serialize_index_item(row)

    pending_map = {str(p["id"]): p for p in pending}
    for upd in synced_updates:
        base_row = pending_map[upd["id"]]
        by_id[upd["id"]] = serialize_index_item(base_row, upd)

    sorted_items = sorted(
        by_id.values(),
        key=lambda x: ((x.get("date_created") or ""), str(x.get("id") or "")),
        reverse=True,
    )

    existing_items = []
    if INDEX_PATH.exists():
        try:
            existing_items = json.loads(INDEX_PATH.read_text(encoding="utf-8")).get("items", [])
        except Exception:
            existing_items = []

    if sorted_items != existing_items or not INDEX_PATH.exists():
        payload = {
            "updated_at": now_iso if sorted_items else None,
            "count": len(sorted_items),
            "items": sorted_items,
        }
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[INDEX] Wrote {len(sorted_items)} items to {INDEX_PATH.relative_to(ROOT)}")
    else:
        print(f"[INDEX] Unchanged ({len(sorted_items)} items)")

    state = {"synced": synced_updates, "failed": failed_updates}
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SUMMARY] fetched={len(synced_updates)} failed={len(failed_updates)}")
    return 0


def cmd_writeback(base_url: str, token: str, state_file: Path) -> int:
    if not state_file.exists():
        print("[WRITEBACK] No state file found; nothing to update.")
        return 0
    state = json.loads(state_file.read_text(encoding="utf-8"))
    errors = 0

    for upd in state.get("synced", []):
        item_id = upd["id"]
        body = {
            "github_file_path": upd["github_file_path"],
            "github_image_url": upd["github_image_url"],
            "status": "synced",
            "synced_at": upd["synced_at"],
            "sync_error": None,
        }
        try:
            api_request(base_url, token, "PATCH", f"/items/{COLLECTION}/{item_id}", body)
            print(f"[WRITEBACK OK] {item_id} -> {upd['github_image_url']}")
        except Exception as exc:
            errors += 1
            print(f"[WRITEBACK ERR] {item_id}: {exc}", file=sys.stderr)

    for fail in state.get("failed", []):
        item_id = fail["id"]
        body = {
            "status": "failed",
            "sync_error": fail["error"],
        }
        try:
            api_request(base_url, token, "PATCH", f"/items/{COLLECTION}/{item_id}", body)
            print(f"[MARKED FAILED] {item_id}: {fail['error']}")
        except Exception as exc:
            errors += 1
            print(f"[WRITEBACK FAIL-MARK ERR] {item_id}: {exc}", file=sys.stderr)

    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch", "writeback"])
    parser.add_argument("--state-file", default="/tmp/directus-sync-state.json")
    args = parser.parse_args()

    base_url_raw = os.environ.get("DIRECTUS_URL") or os.environ.get("CMS_BASE_URL") or ""
    token_raw = os.environ.get("DIRECTUS_API_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY") or DEFAULT_REPO
    branch = os.environ.get("SYNC_TARGET_BRANCH") or DEFAULT_BRANCH

    try:
        base_url, token = validate_config(base_url_raw, token_raw)
        if args.action == "fetch":
            return cmd_fetch(base_url, token, repo, branch, Path(args.state_file))
        return cmd_writeback(base_url, token, Path(args.state_file))
    except HTTPError as exc:
        print(f"Directus HTTP error ({exc.code}): {exc.reason}", file=sys.stderr)
        return 1
    except (URLError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Sync failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
