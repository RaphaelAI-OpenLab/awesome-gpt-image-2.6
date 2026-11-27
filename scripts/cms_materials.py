"""CMS-synced GPT Image 2.6 materials: storage contract, validation, and rendering."""

from __future__ import annotations

import datetime as dt
import re
from urllib.parse import urlsplit

from common import (
    GENERATED_MARKER, ROOT, code_block, html_attr, localized, md_link, md_text,
    md_url, read_json, render_gallery_cta,
)
from i18n import DETAIL_LANGUAGES, detail_language, filename, ui
from presentation import language_nav

CMS_MATERIALS_PATH = "content/cms-materials.json"
DEFAULT_MEDIA_BASE_URL = "https://awesome.raphael.app/materials/"
HOME_CARD_LIMIT = 6
HOME_TABLE_LIMIT = 60


def media_base_url(config: dict) -> str:
    cms = config.get("cms") or {}
    base = str(cms.get("media_base_url") or DEFAULT_MEDIA_BASE_URL).strip()
    return base if base.endswith("/") else base + "/"


def is_approved_cms_media_url(url: str, config: dict) -> bool:
    if not isinstance(url, str) or not url.strip():
        return False
    base = media_base_url(config)
    if not url.startswith(base):
        return False
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and not parts.username
        and not parts.query
        and not parts.fragment
        and not re.search(r"[\s<>]", url)
    )


def read_cms_store() -> dict:
    path = ROOT / CMS_MATERIALS_PATH
    if not path.is_file():
        return {
            "collection": "materials",
            "cms_base_url": "",
            "media_base_url": DEFAULT_MEDIA_BASE_URL,
            "synced_at": None,
            "total_cms_records": 0,
            "items": [],
        }
    return read_json(CMS_MATERIALS_PATH)


def read_cms_materials() -> list[dict]:
    store = read_cms_store()
    items = store.get("items") or []
    return [item for item in items if isinstance(item, dict)]


def cms_page_path(item: dict, language: str) -> str:
    return f"cases/{item['id']}/{filename(detail_language(language))}"


def validate_cms_materials(config: dict, cases: list[dict], prompts: list[dict], errors: list[str]) -> None:
    path = ROOT / CMS_MATERIALS_PATH
    if not path.is_file():
        return
    try:
        store = read_json(CMS_MATERIALS_PATH)
    except (OSError, ValueError) as exc:
        errors.append(f"{CMS_MATERIALS_PATH}: {exc}")
        return
    if not isinstance(store, dict):
        errors.append(f"{CMS_MATERIALS_PATH}: expected an object")
        return

    categories = {cat["id"] for cat in config["categories"]}
    used_ids = {item["id"] for item in cases if item.get("id")} | {item["id"] for item in prompts if item.get("id")}
    seen_ids: set[str] = set()
    seen_cms_ids: set[str] = set()

    total = store.get("total_cms_records")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        errors.append(f"{CMS_MATERIALS_PATH}.total_cms_records: expected non-negative integer")

    synced_at = store.get("synced_at")
    if synced_at is not None:
        try:
            parsed = dt.datetime.fromisoformat(synced_at)
            if parsed.utcoffset() != dt.timedelta(0):
                raise ValueError("UTC required")
        except (TypeError, ValueError):
            errors.append(f"{CMS_MATERIALS_PATH}.synced_at: expected ISO 8601 UTC timestamp or null")

    items = store.get("items")
    if not isinstance(items, list):
        errors.append(f"{CMS_MATERIALS_PATH}.items: expected an array")
        return

    for idx, item in enumerate(items):
        label = f"cms-materials[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: expected an object")
            continue
        item_id = item.get("id", "")
        if not isinstance(item_id, str) or not re.fullmatch(r"cms-[a-z0-9][a-z0-9-]*", item_id):
            errors.append(f"{label}.id: expected slug starting with 'cms-'")
        elif item_id in seen_ids or item_id in used_ids:
            errors.append(f"{label}.id: duplicate ID {item_id!r}")
        else:
            seen_ids.add(item_id)

        cms_id = item.get("cms_id", "")
        if not isinstance(cms_id, str) or not cms_id.strip():
            errors.append(f"{label}.cms_id: required")
        elif cms_id in seen_cms_ids:
            errors.append(f"{label}.cms_id: duplicate CMS ID {cms_id!r}")
        else:
            seen_cms_ids.add(cms_id)

        if not isinstance(item.get("title"), str) or not item["title"].strip():
            errors.append(f"{label}.title: required non-empty text")
        if not isinstance(item.get("prompt"), str) or not item["prompt"].strip():
            errors.append(f"{label}.prompt: required non-empty text")
        if item.get("category") not in categories:
            errors.append(f"{label}.category: unknown category {item.get('category')!r}")

        image_url = item.get("image_url")
        if image_url is not None and not is_approved_cms_media_url(image_url, config):
            errors.append(f"{label}.image_url: must stay under approved R2 prefix {media_base_url(config)}")

        for url_key in ("source_url", "author_url"):
            val = item.get(url_key)
            if val is not None:
                parts = urlsplit(str(val))
                if parts.scheme != "https" or not parts.hostname or parts.username or re.search(r"[\s<>]", str(val)):
                    errors.append(f"{label}.{url_key}: expected HTTPS URL or null")

        added_at = item.get("added_at")
        if not isinstance(added_at, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", added_at):
            errors.append(f"{label}.added_at: expected YYYY-MM-DD")


def render_cms_detail(item: dict, config: dict, language: str) -> str:
    """Render standalone bilingual Markdown case page for a CMS-synced item."""
    if language not in DETAIL_LANGUAGES:
        raise ValueError("Untranslated CMS details must route to English or Simplified Chinese")
    zh = language == "zh-CN"
    choose = lambda en, cn: cn if zh else en
    root_prefix = "../../"
    home = "../../README.zh-CN.md" if zh else "../../README.md"
    cat_map = {cat["id"]: localized(cat["label"], language) for cat in config["categories"]}
    cat_label = cat_map.get(item["category"], item["category"])

    lines = [
        GENERATED_MARKER,
        "",
        f"# {md_text(item['title'])}",
        "",
        md_link(choose("← Back to all cases", "← 返回全部案例"), f"{home}#cms-latest"),
        "",
        language_nav(language, prefix=root_prefix, detail=True),
        "",
        f"**{choose('Creator-reported model', '作者自报模型')} · CMS** · `{cat_label}` · {item['added_at']}",
        "",
    ]

    if item.get("image_url"):
        img_url = item["image_url"]
        alt = html_attr(item["title"])
        lines += [
            f"## {choose('Images / GIFs', '图片 / GIF')}",
            "",
            f'<a href="{html_attr(img_url)}"><img src="{html_attr(img_url)}" alt="{alt}" width="700" /></a>',
            "",
            md_link(choose("View image at original source", "查看 R2 高清原图"), img_url),
            "",
        ]

    lines += [
        f"## {choose('Original prompt', '原始提示词')}",
        "",
        code_block(item["prompt"]),
        "",
        f"## {choose('Attribution and verification', '来源与核对信息')}",
        "",
        f"- ID: `{item['id']}` (CMS: `{item['cms_id']}`)",
    ]

    if item.get("author"):
        author_md = md_link(item["author"], item["author_url"]) if item.get("author_url") else md_text(item["author"])
        lines.append(f"- {choose('Author: ', '作者：')}{author_md}")
    if item.get("source_url"):
        lines.append(f"- {md_link(choose('Original source', '原始来源'), item['source_url'])}")
    if item.get("r2_object_key"):
        lines.append(f"- R2: `{item['r2_object_key']}`")
    if item.get("tags"):
        lines.append(f"- Tags: {', '.join(f'`{md_text(tag)}`' for tag in item['tags'])}")
    lines.append(f"- {choose('Collected: ', '收录：')}{item['added_at']} (UTC)")
    if item.get("matched_curated_case_id"):
        curated_route = f"../{item['matched_curated_case_id']}/{filename(language)}"
        lines.append(f"- {md_link(choose('Source details', '关联精选案例详情'), curated_route)}")
    if item.get("notes"):
        lines += ["", f"> {md_text(item['notes'])}"]

    lines += [
        "",
        render_gallery_cta(config, language, item["id"]),
        "",
        choose(
            "Attribution does not grant a media license. Repository MIT terms do not cover third-party outputs. Media is served via external R2 storage rather than committed into Git.",
            "标注来源不等于取得素材许可。仓库 MIT 协议不覆盖第三方输出；媒体文件通过外部 R2 外链提供，不存入 Git 仓库。",
        ),
        "",
    ]
    return "\n".join(lines)


def render_cms_home_section(config: dict, items: list[dict], language: str) -> list[str]:
    """Render compact CMS feed in root README without risking GitHub's 512 KB cap."""
    if not items:
        return []

    c = lambda en, cn=None: ui(en, cn, language)
    cat_map = {cat["id"]: localized(cat["label"], language) for cat in config["categories"]}
    lines = [
        '<a id="cms-latest"></a>',
        "",
        "## 🆕 " + c("Recently added", "最近收录") + f" ({len(items)})",
        "",
    ]

    if language not in DETAIL_LANGUAGES:
        lines += [
            md_link(c("Recently added", "最近收录") + f" ({len(items)}) →", "README.md#cms-latest"),
            "",
        ]
        return lines

    zh = language == "zh-CN"
    choose = lambda en, cn: cn if zh else en
    lines += [
        choose(
            f"Automatically synced from Directus CMS (`content/cms-materials.json`). Images load directly from first-party R2 links without bloating Git; every entry has a standalone detail page under `cases/cms-*/`.",
            f"由 GitHub Actions 从 Directus CMS 自动拉取至 `content/cms-materials.json`。图片均使用第一方 R2 外链加载不撑爆仓库，每条素材都在 `cases/cms-*/` 生成独立详情页。",
        ),
        "",
    ]

    featured_cms = items[:HOME_CARD_LIMIT]
    lines.append("<table>")
    for start in range(0, len(featured_cms), 2):
        lines.append("<tr>")
        for item in featured_cms[start:start + 2]:
            detail_route = cms_page_path(item, language)
            title_esc = html_attr(item["title"])
            prompt_snippet = item["prompt"].strip().replace("\n", " ")
            if len(prompt_snippet) > 140:
                prompt_snippet = prompt_snippet[:137].rstrip() + "…"
            img_html = ""
            if item.get("image_url"):
                img_html = f'<a href="{html_attr(detail_route)}"><img src="{html_attr(item["image_url"])}" alt="{title_esc}" width="360" /></a><br />'
            meta_bits = [html_attr(cat_map.get(item["category"], item["category"])), html_attr(item["added_at"])]
            if item.get("author"):
                meta_bits.append(html_attr(item["author"]))
            lines.append(
                f'<td width="50%" valign="top">{img_html}'
                f'<strong><a href="{html_attr(detail_route)}">{title_esc}</a></strong><br />'
                f'<sub>{" · ".join(meta_bits)}</sub><br />'
                f'<sub>{html_attr(prompt_snippet)}</sub></td>'
            )
        if len(featured_cms[start:start + 2]) == 1:
            lines.append('<td width="50%"></td>')
        lines.append("</tr>")
    lines += ["</table>", ""]

    table_items = items[:HOME_TABLE_LIMIT]
    lines += [
        f"| # | {c('Added', '收录日期')} | {c('Example', '案例')} | {c('Category', '分类')} | {c('Author', '作者')} | {c('Original source', '原始来源')} |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for idx, item in enumerate(table_items, 1):
        detail_route = cms_page_path(item, language)
        title_link = md_link(item["title"], detail_route)
        cat_label = md_text(cat_map.get(item["category"], item["category"]))
        author_cell = md_link(item["author"], item["author_url"]) if item.get("author") and item.get("author_url") else md_text(item.get("author") or "—")
        links = []
        if item.get("source_url"):
            links.append(md_link(choose("Post", "原帖"), item["source_url"]))
        if item.get("image_url"):
            links.append(md_link("R2", item["image_url"]))
        source_cell = " · ".join(links) if links else "—"
        lines.append(f"| {idx} | {item['added_at']} | {title_link} | {cat_label} | {author_cell} | {source_cell} |")

    if len(items) > HOME_TABLE_LIMIT:
        lines += [
            "",
            choose(
                f"Showing the latest {HOME_TABLE_LIMIT} of {len(items)} synced CMS items. Browse the complete JSON archive in [`content/cms-materials.json`](content/cms-materials.json).",
                f"上方展示最新 {HOME_TABLE_LIMIT} / {len(items)} 条 CMS 同步素材；完整记录请查看 [`content/cms-materials.json`](content/cms-materials.json)。",
            ),
        ]
    lines.append("")
    return lines
