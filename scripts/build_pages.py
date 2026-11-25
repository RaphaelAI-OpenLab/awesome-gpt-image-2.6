#!/usr/bin/env python3
"""Build a lightweight, differentiated GitHub Pages prompt & API cheat sheet."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
from pathlib import Path

from common import ROOT, load_data, published, repo_url, tracked_url
from source_cases import read_cases, video_preview_path, visible

PAGES_URL_TEMPLATE = "https://{owner_lower}.github.io/{slug}/"


def build_dataset(config: dict, cases: list[dict], prompts: list[dict]) -> list[dict]:
    owner = config["project"]["repository_owner"]
    slug = config["project"]["repository_slug"]
    branch = config["project"]["default_branch"]
    raw_base = f"https://raw.githubusercontent.com/{owner}/{slug}/{branch}/"
    repo_base = f"https://github.com/{owner}/{slug}/blob/{branch}/"
    cat_labels = {cat["id"]: cat["label"]["en"] for cat in config["categories"]}

    records = []
    for item in cases:
        outputs = [m for m in item["media"] if m.get("path") and m.get("role", "output") != "reference"]
        thumb = ""
        media_kind = ""
        if outputs:
            first = outputs[0]
            media_kind = first["kind"]
            rel = video_preview_path(first) if first["kind"] == "video" else first["path"]
            thumb = raw_base + rel
        entries = item["prompt"].get("entries", [])
        prompt_text = "\n\n---\n\n".join(e["text"].strip() for e in entries if e.get("text", "").strip())
        records.append({
            "id": item["id"],
            "title": item["title"]["en"],
            "title_zh": item["title"].get("zh-CN", ""),
            "category": item["category"],
            "category_label": cat_labels.get(item["category"], item["category"]),
            "variants": item["model"]["variants"],
            "source_type": item["source"]["type"],
            "author": item["source"]["author"],
            "featured": bool(item.get("featured")),
            "has_prompt": bool(prompt_text),
            "prompt": prompt_text,
            "media_kind": media_kind,
            "thumb": thumb,
            "github_url": f"{repo_base}cases/{item['id']}/README.md",
            "anchor_url": f"https://github.com/{owner}/{slug}#source-case-{item['id']}",
        })
    for item in prompts:
        preview = item["preview"].get("path", "")
        records.append({
            "id": item["id"],
            "title": item["title"]["en"],
            "title_zh": item["title"].get("zh-CN", ""),
            "category": item["category"],
            "category_label": cat_labels.get(item["category"], item["category"]),
            "variants": [item["model"]["variant"]],
            "source_type": "tested-recipe",
            "author": item["source"]["author"],
            "featured": False,
            "has_prompt": bool(item.get("prompt", "").strip()),
            "prompt": item.get("prompt", "").strip(),
            "media_kind": "image" if preview else "",
            "thumb": raw_base + preview if preview else "",
            "github_url": f"{repo_base}cases/{item['id']}/README.md",
            "anchor_url": f"https://github.com/{owner}/{slug}#case-{item['id']}",
        })
    return records


def render_html(config: dict, records: list[dict]) -> str:
    owner = config["project"]["repository_owner"]
    slug = config["project"]["repository_slug"]
    repository = repo_url(config)
    pages_url = PAGES_URL_TEMPLATE.format(owner_lower=owner.lower(), slug=slug)
    gallery_url = tracked_url(config["brand"]["gallery_url"], "github_pages_cta", "en", config)
    prompt_total = sum(1 for r in records if r["has_prompt"])
    updated_date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    categories = [{"id": c["id"], "label": c["label"]["en"]} for c in config["categories"]]
    payload = json.dumps({"categories": categories, "records": records}, ensure_ascii=False).replace("</", "<\\/")

    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "GPT Image 2.6 Open-Source Prompt & API Cheat Sheet (Flare & Sunburst)",
        "description": f"Searchable open-source prompt index and OpenAI API quickstart for GPT Image 2.6 (ChatGPT Images 2.6) — {len(records)} visual examples covering Flare, Sunburst, native GIF, SVG vector, and markup-guided editing.",
        "url": pages_url,
        "dateModified": updated_date,
        "author": {"@type": "Organization", "name": owner, "url": f"https://github.com/{owner}"},
        "isBasedOn": repository,
        "codeRepository": repository,
        "license": f"{repository}/blob/main/LICENSE",
    }, ensure_ascii=False).replace("</", "<\\/")

    page_title = "GPT Image 2.6 & ChatGPT Images 2.6 — Open-Source Prompt & API Cheat Sheet"
    page_desc = (
        f"Searchable open-source prompt library & OpenAI API cheat sheet for GPT Image 2.6 "
        f"(ChatGPT Images 2.6): {len(records)} curated examples for Flare, Sunburst, native GIF, SVG vector, and markup-guided editing."
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(page_title)}</title>
  <meta name="description" content="{html.escape(page_desc)}" />
  <link rel="canonical" href="{html.escape(pages_url)}" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{html.escape(page_title)}" />
  <meta property="og:description" content="{html.escape(page_desc)}" />
  <meta property="og:url" content="{html.escape(pages_url)}" />
  <meta name="twitter:card" content="summary_large_image" />
  <script type="application/ld+json">{json_ld}</script>
  <script defer data-domain="raphaelai-openlab.github.io" src="https://plau.colorepistle.com/js/script.outbound-links.js"></script>
  <script>window.plausible = window.plausible || function() {{ (window.plausible.q = window.plausible.q || []).push(arguments); }};</script>
  <style>
    :root {{
      --bg: #fafafa;
      --surface: #ffffff;
      --border: #e5e7eb;
      --text: #111827;
      --muted: #4b5563;
      --accent: #1d4ed8;
      --accent-soft: #eff6ff;
      --code-bg: #0f172a;
      --code-fg: #e2e8f0;
      --radius: 12px;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #0b1120;
        --surface: #111827;
        --border: #1f2937;
        --text: #f3f4f6;
        --muted: #9ca3af;
        --accent: #60a5fa;
        --accent-soft: #172554;
        --code-bg: #020617;
        --code-fg: #e2e8f0;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.55;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px 20px 64px; }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 24px;
      margin-bottom: 24px;
    }}
    .eyebrow {{
      display: inline-block;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--accent);
      background: var(--accent-soft);
      padding: 4px 10px;
      border-radius: 999px;
      margin-bottom: 10px;
    }}
    h1 {{ margin: 0 0 10px; font-size: clamp(1.6rem, 3vw, 2.3rem); line-height: 1.2; }}
    .lead {{ margin: 0 0 18px; color: var(--muted); max-width: 78ch; }}
    .cta-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 9px 15px;
      border-radius: 8px;
      font-weight: 600;
      font-size: 14px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
    }}
    .btn.primary {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    .btn:hover {{ text-decoration: none; opacity: 0.92; }}
    .stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 18px;
      margin-top: 16px;
      font-size: 13px;
      color: var(--muted);
    }}
    .stats strong {{ color: var(--text); }}
    .api-box {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px 18px;
      margin-bottom: 24px;
    }}
    .api-box summary {{ cursor: pointer; font-weight: 600; font-size: 15px; }}
    .api-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; margin-top: 14px; }}
    pre {{
      margin: 0;
      padding: 14px;
      background: var(--code-bg);
      color: var(--code-fg);
      border-radius: 8px;
      overflow-x: auto;
      font-size: 12.5px;
      line-height: 1.5;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    }}
    .controls {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: var(--bg);
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .search-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    input[type="search"] {{
      flex: 1 1 280px;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      font-size: 14px;
    }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--muted);
      border-radius: 999px;
      padding: 5px 11px;
      font-size: 12.5px;
      cursor: pointer;
    }}
    .chip.active {{ background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 18px; }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .thumb-wrap {{
      aspect-ratio: 16 / 10;
      background: var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border-bottom: 1px solid var(--border);
    }}
    .thumb-wrap img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .card-body {{ padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; flex: 1; }}
    .card-title {{ margin: 0; font-size: 15.5px; line-height: 1.35; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 6px; font-size: 11.5px; color: var(--muted); }}
    .badge {{
      padding: 2px 7px;
      border-radius: 6px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 600;
    }}
    .prompt-preview {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
    }}
    .card-actions {{ margin-top: auto; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; font-size: 12.5px; }}
    .copy-btn {{
      padding: 6px 11px;
      font-size: 12.5px;
      border-radius: 7px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      cursor: pointer;
      font-weight: 600;
    }}
    .copy-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
    footer {{
      margin-top: 48px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
      font-size: 13px;
      color: var(--muted);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <span class="eyebrow">Open-Source Developer Reference · MIT Code</span>
      <h1>Awesome GPT Image 2.6 &amp; ChatGPT Images 2.6 — Prompt &amp; API Cheat Sheet</h1>
      <p class="lead">
        Fast, searchable open-source reference for <strong>GPT Image 2.6</strong> (<strong>ChatGPT Images 2.6</strong>):
        filter copyable prompts across <strong>Flare</strong> (<code>gpt-image-2.6-flare</code>) &amp;
        <strong>Sunburst</strong> (<code>gpt-image-2.6-sunburst</code>), native GIF animations, SVG vectors, and markup-guided edits.
        Maintained directly from the canonical GitHub repository.
      </p>
      <div class="cta-row">
        <a class="btn primary" href="{html.escape(repository)}">★ Star Awesome GPT Image 2.6 Prompts on GitHub</a>
        <a class="btn" href="{html.escape(repository)}/discussions">GitHub Discussions</a>
        <a class="btn" href="{html.escape(repository)}/blob/main/content/source-cases.json">JSON Dataset</a>
        <a class="btn" href="{html.escape(gallery_url)}" rel="noopener">Try online free on Raphael ↗</a>
      </div>
      <div class="stats">
        <span><strong>{len(records)}</strong> indexed entries</span>
        <span><strong>{prompt_total}</strong> entries with copyable prompts</span>
        <span><strong>8</strong> categories</span>
        <span>Updated <strong>{updated_date}</strong></span>
      </div>
    </header>

    <details class="api-box" open>
      <summary>⚡ OpenAI Images API Quickstart — gpt-image-2.6-sunburst &amp; gpt-image-2.6-flare (Python / cURL)</summary>
      <div class="api-grid">
        <pre><code>import base64
from openai import OpenAI

client = OpenAI()
res = client.images.generate(
    model="gpt-image-2.6-flare",  # or "gpt-image-2.6-sunburst"
    prompt="A looping pixel greenhouse sprinkler, seamless loop",
    output_format="gif",          # "png", "webp", "gif", or "svg"
    frame_count=8,
    frame_duration_ms=150,
)
with open("output.gif", "wb") as f:
    f.write(base64.b64decode(res.data[0].b64_json))</code></pre>
        <pre><code>curl https://api.openai.com/v1/images/generations \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $OPENAI_API_KEY" \\
  -d '{{
    "model": "gpt-image-2.6-sunburst",
    "prompt": "Minimalist bakery logo Field &amp; Flour, clean SVG vector",
    "output_format": "svg",
    "size": "1024x1024"
  }}'</code></pre>
      </div>
    </details>

    <section class="controls" aria-label="Filter prompts">
      <div class="search-row">
        <input id="q" type="search" placeholder="Search prompts, titles, authors, GIF, SVG, markup, Flare, Sunburst..." autocomplete="off" />
        <label style="font-size:13px;color:var(--muted);display:flex;align-items:center;gap:6px;">
          <input id="onlyPrompts" type="checkbox" checked /> Copyable prompts only
        </label>
        <span id="count" style="font-size:13px;color:var(--muted);"></span>
      </div>
      <div class="chips" id="catChips"></div>
      <div class="chips" id="varChips">
        <button class="chip active" data-variant="all">All variants</button>
        <button class="chip" data-variant="sunburst">Sunburst</button>
        <button class="chip" data-variant="flare">Flare</button>
        <button class="chip" data-variant="featured">Featured</button>
      </div>
    </section>

    <main class="grid" id="grid"></main>

    <footer>
      <span>
        Source repository: <a href="{html.escape(repository)}">RaphaelAI-OpenLab/awesome-gpt-image-2.6-prompts</a> ·
        <a href="{html.escape(repository)}/blob/main/LICENSE">MIT License (code &amp; docs)</a> ·
        <a href="{html.escape(repository)}/blob/main/docs/ATTRIBUTION.md">Attribution</a>
      </span>
      <span>Curated by <a href="{html.escape(gallery_url)}" rel="noopener">Raphael</a></span>
    </footer>
  </div>

  <script id="dataset" type="application/json">{payload}</script>
  <script>
    const data = JSON.parse(document.getElementById("dataset").textContent);
    let activeCat = "all";
    let activeVar = "all";
    const qEl = document.getElementById("q");
    const onlyEl = document.getElementById("onlyPrompts");
    const gridEl = document.getElementById("grid");
    const countEl = document.getElementById("count");
    const catChips = document.getElementById("catChips");

    function esc(s) {{
      return String(s).replace(/[&<>"']/g, m => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}})[m]);
    }}

    function buildCatChips() {{
      const allBtn = document.createElement("button");
      allBtn.className = "chip active";
      allBtn.dataset.cat = "all";
      allBtn.textContent = `All (${{data.records.length}})`;
      catChips.appendChild(allBtn);
      for (const c of data.categories) {{
        const n = data.records.filter(r => r.category === c.id).length;
        const btn = document.createElement("button");
        btn.className = "chip";
        btn.dataset.cat = c.id;
        btn.textContent = `${{c.label}} (${{n}})`;
        catChips.appendChild(btn);
      }}
      catChips.addEventListener("click", e => {{
        const btn = e.target.closest("button[data-cat]");
        if (!btn) return;
        activeCat = btn.dataset.cat;
        catChips.querySelectorAll(".chip").forEach(b => b.classList.toggle("active", b === btn));
        render();
      }});
    }}

    document.getElementById("varChips").addEventListener("click", e => {{
      const btn = e.target.closest("button[data-variant]");
      if (!btn) return;
      activeVar = btn.dataset.variant;
      document.querySelectorAll("#varChips .chip").forEach(b => b.classList.toggle("active", b === btn));
      render();
    }});

    function render() {{
      const term = qEl.value.trim().toLowerCase();
      const onlyPrompts = onlyEl.checked;
      const items = data.records.filter(r => {{
        if (onlyPrompts && !r.has_prompt) return false;
        if (activeCat !== "all" && r.category !== activeCat) return false;
        if (activeVar === "featured" && !r.featured) return false;
        if ((activeVar === "flare" || activeVar === "sunburst") && !r.variants.includes(activeVar)) return false;
        if (term) {{
          const hay = (r.title + " " + r.title_zh + " " + r.category_label + " " + r.author + " " + r.prompt + " " + r.variants.join(" ")).toLowerCase();
          if (!hay.includes(term)) return false;
        }}
        return true;
      }});
      countEl.textContent = `Showing ${{items.length}} of ${{data.records.length}}`;
      gridEl.innerHTML = items.map(r => {{
        const thumb = r.thumb ? `<a class="thumb-wrap" href="${{esc(r.anchor_url)}}" target="_blank" rel="noopener"><img src="${{esc(r.thumb)}}" alt="${{esc(r.title)}}" loading="lazy" /></a>` : "";
        const promptHtml = r.has_prompt
          ? `<pre class="prompt-preview">${{esc(r.prompt)}}</pre>`
          : `<div class="meta">Prompt not public at source — see GitHub case page.</div>`;
        const copyBtn = r.has_prompt ? `<button class="copy-btn" data-id="${{esc(r.id)}}">Copy prompt</button>` : "";
        const badges = [
          `<span class="badge">${{esc(r.category_label)}}</span>`,
          ...r.variants.filter(v => v !== "unspecified").map(v => `<span class="badge">${{esc(v)}}</span>`),
          r.featured ? `<span class="badge">Featured</span>` : "",
        ].join("");
        return `<article class="card">${{thumb}}<div class="card-body">
          <div class="meta">${{badges}}</div>
          <h2 class="card-title"><a href="${{esc(r.anchor_url)}}" target="_blank" rel="noopener">${{esc(r.title)}}</a></h2>
          ${{promptHtml}}
          <div class="card-actions">
            ${{copyBtn}}
            <a href="${{esc(r.github_url)}}" target="_blank" rel="noopener">GitHub case details →</a>
          </div>
        </div></article>`;
      }}).join("");
    }}

    gridEl.addEventListener("click", async e => {{
      const btn = e.target.closest("button.copy-btn");
      if (!btn) return;
      const rec = data.records.find(r => r.id === btn.dataset.id);
      if (!rec) return;
      try {{
        await navigator.clipboard.writeText(rec.prompt);
        if (window.plausible) window.plausible("Copy Prompt", {{ props: {{ case_id: rec.id, category: rec.category }} }});
        btn.textContent = "Copied ✓";
        setTimeout(() => btn.textContent = "Copy prompt", 1500);
      }} catch {{
        btn.textContent = "Copy failed";
      }}
    }});

    qEl.addEventListener("input", render);
    onlyEl.addEventListener("change", render);
    buildCatChips();
    render();
  </script>
</body>
</html>
"""


def build_site(out_dir: Path) -> None:
    config, prompts = load_data()
    cases = visible(read_cases())
    full_prompts = published(prompts)
    records = build_dataset(config, cases, full_prompts)
    owner = config["project"]["repository_owner"]
    slug = config["project"]["repository_slug"]
    pages_url = PAGES_URL_TEMPLATE.format(owner_lower=owner.lower(), slug=slug)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    (out_dir / "index.html").write_text(render_html(config, records), encoding="utf-8")
    (out_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {pages_url}sitemap.xml\n",
        encoding="utf-8",
    )
    (out_dir / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{pages_url}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="_site", help="Output directory for GitHub Pages artifact.")
    args = parser.parse_args()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    build_site(out_dir)
    print(f"Built GitHub Pages site in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
