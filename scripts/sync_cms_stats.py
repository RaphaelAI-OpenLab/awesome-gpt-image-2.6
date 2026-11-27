#!/usr/bin/env python3
"""Sync only the CMS count and update time in the root READMEs."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from i18n import LANGUAGES, ROOT, filename, ui


MARKER = re.compile(r"^<!-- cms-stats (pending|([0-9]+) ([0-9TZ:-]+)) -->$", re.M)


@dataclass(frozen=True)
class CmsStats:
    count: int
    synced_at: datetime


def stats_marker(stats: CmsStats | None) -> str:
    if stats is None:
        return "<!-- cms-stats pending -->"
    return f"<!-- cms-stats {stats.count} {stats.synced_at:%Y-%m-%dT%H:%M:%SZ} -->"


def read_cms_stats() -> CmsStats | None:
    cms_file = ROOT / "content" / "cms-materials.json"
    if cms_file.is_file():
        try:
            store = json.loads(cms_file.read_text(encoding="utf-8"))
            synced_at = store.get("synced_at")
            total = store.get("total_cms_records")
            if isinstance(total, int) and not isinstance(total, bool) and isinstance(synced_at, str) and synced_at:
                return CmsStats(total, datetime.fromisoformat(synced_at))
        except (OSError, ValueError, TypeError):
            pass
    readme = ROOT / filename("en")
    match = MARKER.search(readme.read_text(encoding="utf-8")) if readme.exists() else None
    if match is None or match[1] == "pending":
        return None
    return CmsStats(int(match[2]), datetime.fromisoformat(match[3]))


def cms_rows(language: str, stats: CmsStats | None, fallback_time: datetime) -> tuple[str, str]:
    updated = (stats.synced_at if stats else fallback_time).astimezone(timezone.utc)
    if language in ("zh-CN", "zh-TW"):
        weekday = "一二三四五六日"[updated.weekday()]
        updated_label = f"{updated.year}年{updated.month}月{updated.day}日星期{weekday} UTC {updated:%H:%M:%S}"
    else:
        updated_label = f"{updated:%Y-%m-%d} UTC {updated:%H:%M:%S}"
    label = ui("CMS materials", "CMS 素材总数", language)
    updated_name = ui("Last updated", "最后更新", language)
    count = stats.count if stats else "—"
    return (
        f"| 🗂️ {label} | **{count}** |",
        f"| 🔄 {updated_name} | **{updated_label}** |",
    )


def replace_readme_stats(content: str, language: str, stats: CmsStats) -> str:
    content, replaced = MARKER.subn(lambda _: stats_marker(stats), content)
    if replaced != 1:
        raise ValueError(f"Expected one CMS statistics marker in {filename(language)}.")

    for row in cms_rows(language, stats, stats.synced_at):
        prefix = row.split(" | **", 1)[0]
        pattern = rf"^{re.escape(prefix)} \| \*\*[^\n]+\*\* \|$"
        content, replaced = re.subn(pattern, lambda _: row, content, flags=re.M)
        if replaced != 1:
            raise ValueError(f"Expected one row for {prefix[2:]} in {filename(language)}.")
    return content


def fetch_material_count(base_url: str, token: str) -> int:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or not re.fullmatch(r"[A-Za-z0-9._~-]+", token)
    ):
        raise ValueError("Set CMS_BASE_URL to the HTTPS origin and configure CMS_READ_TOKEN.")
    query = urlencode({"aggregate[count]": "id"})
    request = Request(
        f"{base_url.rstrip('/')}/items/materials?{query}",
        headers={"Accept": "application/json", "User-Agent": "Raphael-CMS-Stats/1.0"},
    )
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    with urlopen(request, timeout=20) as response:
        rows = json.load(response)["data"]

    count = rows[0]["count"]["id"]
    if type(count) is int and count >= 0:
        return count
    if isinstance(count, str) and re.fullmatch(r"[0-9]+", count):
        return int(count)
    raise ValueError("CMS returned an invalid material count.")


def main() -> int:
    try:
        count = fetch_material_count(os.environ.get("CMS_BASE_URL", ""), os.environ.get("CMS_READ_TOKEN", ""))
        stats = CmsStats(count, datetime.now(timezone.utc).replace(microsecond=0))
        updates = {}
        for language in LANGUAGES:
            path = ROOT / filename(language)
            updates[path] = replace_readme_stats(path.read_text(encoding="utf-8"), language, stats)
        for path, content in updates.items():
            path.write_text(content, encoding="utf-8")
    except HTTPError as exc:
        print(f"CMS statistics request failed (HTTP {exc.code}).", file=sys.stderr)
        return 1
    except (URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"CMS statistics sync failed: {exc}", file=sys.stderr)
        return 1
    print(f"Synced {count} CMS materials to {len(updates)} READMEs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
