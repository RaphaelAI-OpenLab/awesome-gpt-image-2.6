"""README layout inspired by YouMind; all copy and rendering are project-specific."""
import datetime as dt

from i18n import DETAIL_LANGUAGES, ui
from presentation import language_nav, repo_badges
from common import GENERATED_MARKER, localized, md_link, md_text, published, repo_url, tracked_url
from source_cases import read_cases, render_inline_case, visible
from browse import category_case_counts, gallery_url_for_language, render_browse
from cms_materials import read_cms_materials, render_cms_home_section
from sync_cms_stats import cms_rows, stats_marker

FULL_README_LANGUAGES = DETAIL_LANGUAGES

API_PYTHON_SNIPPET = """```python
import base64
from openai import OpenAI

client = OpenAI()  # Reads OPENAI_API_KEY from environment

# 1) High-detail still image with GPT-Image-2.6 Sunburst (or "gpt-image-2.6-flare" for speed)
image = client.images.generate(
    model="gpt-image-2.6-sunburst",
    prompt="Editorial studio photo of a cobalt ceramic vase on warm oak, soft morning light",
    size="1024x1024",
    quality="high",
)

# 2) Native looping GIF prompt (output_format="gif", 2-16 frames)
gif = client.images.generate(
    model="gpt-image-2.6-flare",
    prompt="A tiny lantern-carrying monkey in a snowy pine forest at dusk, seamless loop animation",
    output_format="gif",
    frame_count=8,
    frame_duration_ms=150,
)
with open("loop.gif", "wb") as f:
    f.write(base64.b64decode(gif.data[0].b64_json))

# 3) Editable SVG vector prompt (output_format="svg")
svg = client.images.generate(
    model="gpt-image-2.6-sunburst",
    prompt="Minimalist bakery logo 'Field & Flour', clean vector silhouette, warm balanced negative space",
    output_format="svg",
)
with open("logo.svg", "wb") as f:
    f.write(base64.b64decode(svg.data[0].b64_json))
```"""

API_CURL_SNIPPET = """```bash
curl https://api.openai.com/v1/images/generations \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $OPENAI_API_KEY" \\
  -d '{
    "model": "gpt-image-2.6-flare",
    "prompt": "Minimalist geometric bakery logo on cream paper, clean vector aesthetic",
    "size": "1024x1024",
    "output_format": "svg"
  }'
```"""


def render_home(config, prompts, language, render_prompt, cms_stats):
    c = lambda en, cn=None: ui(en, cn, language)
    cases = visible(read_cases())
    full = published(prompts)
    cms_items = read_cms_materials()
    full_edition = language in FULL_README_LANGUAGES
    case_prefix = '' if full_edition else 'README.md'
    brand = config['brand']
    gallery_url = brand.get('gallery_url') or brand['home_url']
    localized_gallery_url = gallery_url_for_language(gallery_url, language)
    repository = repo_url(config)
    title = c('Awesome {model} Prompts', '{model} 提示词大全').format(model=config['project']['model_family'])

    def heading(anchor, en, cn):
        return [f'<a id="{anchor}"></a>', '', '## ' + c(en, cn), '']

    lines = [
        GENERATED_MARKER, '', '<a id="top"></a>', '',
        f'[![{title}](assets/hero/raphael-gpt-image-2-6-hero-v1.png)]({tracked_url(brand["home_url"], "hero", language, config)})', '',
        '# 🚀 ' + title, '',
        repo_badges(config, language), '',
        '> 🎨 ' + c(
            'A curated collection of GPT Image 2.6 & ChatGPT Images 2.6 prompts and visual examples — covering Flare & Sunburst, native GIF prompts, SVG vector prompts, and markup-guided editing.',
            'GPT Image 2.6（ChatGPT Images 2.6）创意提示词与视觉案例精选合集，涵盖 Flare 与 Sunburst、原生 GIF 提示词、SVG 矢量提示词与标注引导局部编辑。',
        ), '',
        '> ⚠️ **' + c('Copyright notice', '版权声明') + c('**: ', '**：')
        + c('This collection includes prompts and examples from public sources and independently generated images for educational purposes only. If you believe any content infringes your rights, please ',
            '本仓库收录公开来源的提示词与案例，以及独立生成的图片，仅供教育目的使用。如果您认为任何内容侵犯了您的权利，请')
        + md_link(c('open an issue', '提交 issue'), repository + '/issues/new?template=report-problem.yml')
        + c(', and we will remove it immediately.', '，我们将立即移除。'),
        '', '---', '',
        language_nav(language), '', '---', '',
    ]
    if language not in DETAIL_LANGUAGES:
        lines += [
            c('This language edition translates the repository interface. Full case details are currently available in English and Simplified Chinese.',
              '本语言版本翻译仓库界面；完整案例详情目前提供英文与简体中文。'), '',
            c('Case titles, descriptions and detail pages are shown in English when a translation is not available. Original prompts and source quotations are not translated.',
              '案例标题、描述与详情缺少对应译文时明确使用英文；原始提示词与来源引文不翻译。'), '',
        ]

    lines += heading('gallery', '🌐 View in Web Gallery', '🌐 在网页图库中查看')
    lines += [
        '**' + md_link(
            '👉 ' + c('Browse the {brand} {model} prompt gallery', '浏览 {brand} {model} 提示词图库').format(
                brand=brand['name'], model=config['project']['model_family']
            ),
            tracked_url(gallery_url, 'top_cta', language, config),
        ) + '**', '',
    ]
    if full:
        lines += ['**' + md_link('📝 ' + c('Full prompts', '完整提示词'), case_prefix + '#collection') + '**', '']
    lines += [
        c('Why create on the website?', '为什么去网站创作？'), '',
        '| ' + c('Feature', '功能') + ' | GitHub README | ' + c('{brand} website', '{brand} 网页端').format(brand=brand['name']) + ' |',
        '| --- | --- | --- |',
    ]
    comparison = [
        ('🆓', 'Free generation', 'Browse cases and prompts', 'Free basic generation, no sign-up or credit card'),
        ('✍️', 'Prompt workflow', 'Copy available prompts', 'Paste a prompt and generate'),
        ('🖼️', 'Reference image editing', 'View reference images and input requirements', 'Upload references to guide image creation and edits'),
        ('🤖', 'Model choice', 'See which model each case uses', 'Choose from GPT Image, Seedream, Nano Banana and more'),
        ('🎨', 'Styles and sizes', 'Check styles and settings recorded by the source', 'Choose a style, aspect ratio and output format'),
        ('🔄', 'Variations', 'Compare collected examples', 'Generate up to 4 images per prompt'),
        ('🛠️', 'Image tools', 'Read editing workflows', 'Remove backgrounds, upscale, expand and edit images'),
        ('📱', 'Mobile', 'Read cases', 'Generate and edit in your mobile browser'),
    ]
    for icon, feature, readme, website in comparison:
        lines += ['| ' + icon + ' ' + c(feature) + ' | ' + c(readme) + ' | ' + c(website) + ' |']
    lines += [
        '', c('Free generation uses the basic mode. Other models have their own credit and plan requirements, shown on the website.',
              '免费生图使用基础模式；其他模型按网页显示的积分与套餐要求使用。'), '',
        md_link(c('Browse all cases in this repository →', '浏览仓库内全部案例 →'), '#all-cases'), '',
    ]
    if brand.get('model_page_url') and brand.get('model_available'):
        lines += [md_link(c('Verified model entry', '已核验模型入口'), tracked_url(brand['model_page_url'], 'model_entry', language, config)), '']
    promo = config['cross_promo']
    if promo['enabled']:
        lines += [
            md_link(localized(promo['title'], language), tracked_url(promo['url'], 'cross_promo', language, config)),
            localized(promo['description'], language), '',
        ]
        if promo['image_path']:
            lines += [f"![{md_text(localized(promo['title'], language))}]({promo['image_path']})", '']

    lines += heading('categories', '🏷️ Browse by category', '🏷️ 按分类浏览')
    lines += [render_browse(config, language, cases, anchor_prefix=case_prefix)]

    lines += [''] + heading('contents', '📖 Contents', '📖 目录')
    toc = [
        ('#about', 'What is GPT Image 2.6 (ChatGPT Images 2.6)?', '什么是 GPT Image 2.6（ChatGPT Images 2.6）？'),
        ('#api-quickstart', 'OpenAI API Quickstart (Flare & Sunburst)', 'OpenAI API 速查（Flare 与 Sunburst）'),
        ('#statistics', 'Statistics', '统计数据'),
        ('#featured', 'Featured cases', '精选案例'),
        ('#all-cases', 'All cases', '全部案例'),
        *((('#cms-latest', 'Recently added', '最近收录'),) if cms_items else ()),
        (case_prefix + '#collection' if full else '#collection', 'Full prompts', '完整提示词'),
        ('#using', 'How to use', '如何使用'),
        ('#contribute', 'Contribute', '如何贡献'),
        ('#license', 'License', '许可证'),
        ('#acknowledgements', 'Acknowledgements', '致谢'),
        ('#star-history', 'Star history', 'Star 历史'),
    ]
    for target, en, cn in toc:
        lines.append('- ' + md_link(c(en, cn), target))

    lines += [''] + heading('about', '🤔 What is GPT Image 2.6 (ChatGPT Images 2.6)?', '🤔 什么是 GPT Image 2.6（ChatGPT Images 2.6）？')
    lines += [
        c(
            'OpenAI introduced Images 2.6 (ChatGPT Images 2.6 / GPT Image 2.6) on November 4, 2026, with two API model variants — `gpt-image-2.6-sunburst` and `gpt-image-2.6-flare`. This collection organizes copyable prompts and visual examples for image generation, markup-guided editing, native GIF animation prompts, and SVG vector prompts. Variant support is recorded per case rather than assumed.',
            'OpenAI 于 2026 年 11 月 4 日发布 Images 2.6（ChatGPT Images 2.6 / GPT Image 2.6），提供 `gpt-image-2.6-sunburst` 与 `gpt-image-2.6-flare` 两个 API 模型版本。本合集整理了可复制的图像生成、标注引导局部编辑、原生 GIF 动图与 SVG 矢量提示词及案例；具体版本支持情况按每个案例记录，不作推定。',
        ), '',
        md_link(c('Official announcement', '官方发布说明'), config['project']['official_url'])
        + ' · ' + md_link(c('Model documentation', '模型文档'), config['project']['model_docs_url']), '',
        '### ' + c('GPT-Image-2.6 Flare vs Sunburst & Key Workflows', 'GPT-Image-2.6 Flare vs Sunburst 与核心工作流'), '',
        '| ' + c('Workflow / Variant', '版本 / 工作流') + ' | ' + c('Best for', '适用场景') + ' | ' + c('Explore examples', '查看案例') + ' |',
        '| --- | --- | --- |',
        '| ' + c('GPT-Image-2.6 Sunburst (`gpt-image-2.6-sunburst`)', 'GPT-Image-2.6 Sunburst（`gpt-image-2.6-sunburst`）') + ' | ' + c('Higher detail, complex layouts, exact typography, multi-step character consistency, native GIF & SVG outputs', '高细节画面、复杂排版与精准文字渲染、多轮角色一致性、原生 GIF 与 SVG 输出') + ' | ' + md_link(c('Featured cases', '精选案例'), '#featured') + ' |',
        '| ' + c('GPT-Image-2.6 Flare (`gpt-image-2.6-flare`)', 'GPT-Image-2.6 Flare（`gpt-image-2.6-flare`）') + ' | ' + c('Low-latency rapid iteration, quick drafts, high-throughput generation, markup edits, GIF & SVG outputs', '低延迟快速迭代、草图探索、批量高吞吐出图、局部标注编辑、GIF 与 SVG 输出') + ' | ' + md_link(c('All cases', '全部案例'), case_prefix + '#all-cases') + ' |',
        '| ' + c('Native GIF Prompts', '原生 GIF 提示词（Native GIF Prompts）') + ' | ' + c('Seamless looping animated GIFs (`output_format: gif`, 2–16 frames) for stickers, demos, and storyboards', '无缝循环动图（`output_format: gif`，2–16 帧），适合表情包、产品演示与动态分镜') + ' | ' + md_link(localized(next(cat['label'] for cat in config['categories'] if cat['id'] == 'gif-animation'), language), case_prefix + '#category-gif-animation') + ' |',
        '| ' + c('SVG Vector Prompts', 'SVG 矢量提示词（SVG Vector Prompts）') + ' | ' + c('Clean editable vector logos, icons, UI concepts, and design assets (`output_format: svg`)', '清晰可编辑的矢量 Logo、图标、界面概念稿与设计素材（`output_format: svg`）') + ' | ' + md_link(localized(next(cat['label'] for cat in config['categories'] if cat['id'] == 'svg-design-assets'), language), case_prefix + '#category-svg-design-assets') + ' |',
        '| ' + c('Markup-Guided Editing', '标注引导局部编辑（Markup-Guided Editing）') + ' | ' + c('Circle or annotate a reference photo to recolor objects, swap items, or localize layouts accurately', '在参考图上画圈或标注，精准完成局部换色、物件替换与多语言版式本地化') + ' | ' + md_link(localized(next(cat['label'] for cat in config['categories'] if cat['id'] == 'markup-edits'), language), case_prefix + '#category-markup-edits') + ' |',
        '',
    ]

    lines += heading('api-quickstart', '⚡ OpenAI API Quickstart (Flare & Sunburst)', '⚡ OpenAI API 速查（Flare 与 Sunburst）')
    lines += [
        c(
            'Copy a prompt from this collection and run it directly with the OpenAI Images API (`gpt-image-2.6-flare` for speed or `gpt-image-2.6-sunburst` for higher detail).',
            '从本合集复制任意提示词，即可直接通过 OpenAI Images API 调用（追求速度选 `gpt-image-2.6-flare`，追求高细节选 `gpt-image-2.6-sunburst`）。',
        ), '',
        API_PYTHON_SNIPPET, '',
        API_CURL_SNIPPET, '',
    ]

    by_id = {item['id']: item for item in cases}
    selected = [by_id[case_id] for case_id in config['presentation']['featured_case_ids'] if case_id in by_id]
    selected = selected[:config['presentation']['featured_limit']]
    case_numbers = {item['id']: number for number, item in enumerate(
        (item for category in config['categories'] for item in cases if item['category'] == category['id']), 1)}
    updated = dt.datetime.fromisoformat(config['presentation']['updated_at'])
    prompt_count = len(full) + sum(len(item['prompt'].get('entries', [])) for item in cases)
    lines += heading('statistics', '📊 Statistics', '📊 统计数据')
    lines += [
        '| **' + c('Metric', '指标') + '** | **' + c('Count', '数量') + '** |',
        '| --- | --- |',
        '| 📝 ' + c('Total prompts', '提示词总数') + f' | **{prompt_count}** |',
        '| ⭐ ' + c('Featured', '精选') + f' | **{len(selected)}** |',
        *cms_rows(language, cms_stats, updated), '', stats_marker(cms_stats), '',
    ]

    lines += heading('featured', '🔥 Featured cases', '🔥 精选案例')
    if selected:
        for item in selected:
            lines += [render_inline_case(item, language, case_numbers[item['id']], config, featured=True, case_anchor_prefix=case_prefix).rstrip(), '', '---', '']
    else:
        lines += [c('No source-linked cases published yet.', '尚未发布来源案例。'), '']
    lines += [
        c('Video previews are still frames; open the linked file for motion. Reference images and source posters are labelled separately.',
          '视频预览是首帧静态图，点击可打开动画文件；参考图与来源封面均单独标注。'), '',
    ]

    lines += heading('all-cases', '📋 All cases', '📋 全部案例')
    if not full:
        lines += ['<a id="collection"></a>', '']
    if full_edition:
        number = 0
        for category in config['categories']:
            lines += [f'<a id="category-{category["id"]}"></a>', '', '### ' + localized(category['label'], language), '']
            group = [x for x in cases if x['category'] == category['id']]
            if group:
                for item in group:
                    number += 1
                    lines += [render_inline_case(item, language, number, config).rstrip(), '', '---', '']
            else:
                lines += [c('No source-linked cases in this category yet.', '此分类尚无来源案例。'), '']
        if full:
            lines += heading('collection', '📝 Full prompts', '📝 完整提示词')
            for item in full:
                lines += [render_prompt(item, config, language).rstrip(), '', '---', '']
    else:
        lines += [
            c(
                'This localized edition includes the translated overview, API quickstart, live statistics, and all featured cases. To avoid duplicating untranslated English prompts across 14 files, browse the full {count}-case index by category below or open the localized web gallery.',
                '本语言版本提供本地化简介、API 速查、实时统计与全部精选案例。为避免在 14 个文件中重复堆砌未翻译的英文提示词，请在下方按分类跳转查看完整 {count} 个案例，或前往本地化网页图库。',
            ).format(count=len(cases)), '',
            '| ' + c('Category', '分类') + ' | ' + c('Cases', '案例数') + ' | ' + c('Explore examples', '查看案例') + ' |',
            '| --- | ---: | --- |',
        ]
        for category, count in category_case_counts(config, cases):
            cat_id = category['id']
            cat_label = localized(category['label'], language)
            lines.append(f'| {md_text(cat_label)} | **{count}** | {md_link(c("Read in English", "查看英文版"), f"README.md#category-{cat_id}")} |')
        lines += [
            '',
            '**' + md_link(
                '👉 ' + c('Read the full collection in English (all {count} cases) →', '在英文主文档查看全部 {count} 个案例 →').format(count=len(cases)),
                'README.md#all-cases',
            ) + '**', '',
            md_link(
                c('Open localized {brand} web gallery ↗', '打开 {brand} 中文网页图库 ↗').format(brand=brand['name']),
                tracked_url(localized_gallery_url, 'localized_all_cases', language, config),
            ), '',
        ]

    lines += render_cms_home_section(config, cms_items, language)

    lines += heading('using', '📚 How to use', '📚 如何使用')
    lines += [
        '1. ' + c('Open a case from a category or featured card.', '从分类或精选卡片进入案例。'),
        '2. ' + c('Read its model evidence, required inputs, source and reuse limits.', '查看模型依据、必需输入、原始来源与素材使用限制。'),
        '3. ' + c('Follow the original prompt link when available. A missing prompt stays missing; do not infer it from an image.',
                 '有原始提示词时前往来源阅读。没有公开提示词时保持缺失，不根据图片臆造。'), '',
    ]
    lines += heading('contribute', '🤝 How to contribute', '🤝 如何贡献')
    lines += [
        c('Add source cases to content/source-cases.json and complete prompts to content/prompts.json. The generator builds the index and bilingual detail pages.',
          '来源案例写入 content/source-cases.json，完整提示词写入 content/prompts.json。生成器维护索引与中英文详情页。'), '',
        md_link(c('Contribution guide', '贡献指南'), 'CONTRIBUTING.md')
        + ' · ' + md_link(c('Source case and media guide', '案例与素材维护指南'), 'docs/SOURCE_CASES.md')
        + ' · ' + md_link(c('Language guide', '多语言说明'), 'docs/LANGUAGES.md'), '',
    ]
    lines += heading('license', '📄 License', '📄 许可证')
    lines += [
        c('Code, original documentation and decorative SVG placeholders use MIT. Third-party prompts and media retain their own terms and have item-level provenance and reuse status. The adapted README layout is credited separately below.',
          '代码、原创说明与装饰性 SVG 占位图采用 MIT。第三方提示词及素材保留各自条款，逐项记录来源与使用状态。改编的 README 结构另见下方署名。'), '',
        md_link(c('Repository license', '仓库许可证'), 'LICENSE')
        + ' · ' + md_link(c('Attribution notes', '署名说明'), 'docs/ATTRIBUTION.md'), '',
    ]
    lines += heading('acknowledgements', '🙏 Acknowledgements', '🙏 致谢')
    lines += [
        c('README structure adapted from YouMind OpenLab’s awesome-nano-banana-pro-prompts under CC BY 4.0. Adapted for GPT Image 2.6 with new copy, data, local detail pages and explicit placeholders; no creative examples or media were copied.',
          'README 结构参考并改编自 YouMind OpenLab 的 awesome-nano-banana-pro-prompts（CC BY 4.0）。已替换为 GPT Image 2.6 的文案、数据、仓库内详情页与明确占位符；未复制其创意案例或图片素材。'), '',
        md_link('YouMind README', 'https://github.com/YouMind-OpenLab/awesome-nano-banana-pro-prompts/blob/main/README_zh.md')
        + ' · ' + md_link('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/')
        + ' · ' + md_link(c('Attribution notes', '署名说明'), 'docs/ATTRIBUTION.md'), '',
        c('Thanks to OpenAI and the original creators credited on each case page.', '感谢 OpenAI 与各案例详情页标注的原作者。'), '',
    ]
    lines += heading('star-history', '⭐ Star history', '⭐ Star 历史')
    lines += [
        md_link(c('Star history', 'Star 历史'), 'https://star-history.com/#' + config['project']['repository_owner'] + '/' + config['project']['repository_slug'] + '&Date')
        + ' · ' + md_link(c('View stargazers', '查看 Star 用户'), repository + '/stargazers'), '',
    ]
    if repository:
        lines += [md_link(c('Star / follow this repository', 'Star / 关注本仓库'), repository), '']
    lines += [
        md_link('↑ ' + c('Back to top', '返回顶部'), '#top'), '', '---', '',
        c('Curated by Raphael.', '由 Raphael 整理。') + ' ' + md_link(c('Homepage', '主页'), tracked_url(brand['home_url'], 'footer', language, config)), '',
        c('Generated from structured source data. Edit the datasets and regenerate; do not edit this file directly.',
          '由结构化数据自动生成。请修改数据源并重新生成，不直接编辑本文件。'), '',
    ]
    return '\n'.join(lines)
