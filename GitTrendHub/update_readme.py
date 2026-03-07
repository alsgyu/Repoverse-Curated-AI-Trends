import os
import json
import requests
import struct
import zlib
import hashlib
from datetime import datetime, timezone

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"

def load_projects(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_projects(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def parse_stars(val):
    if isinstance(val, (int, float)):
        return int(val)
    if not isinstance(val, str):
        return 0
    # Handle "163k+", "over 100k", etc.
    s = val.lower().replace('+', '').replace('over', '').replace(',', '').strip()
    if 'k' in s:
        try:
            return int(float(s.replace('k', '').strip()) * 1000)
        except:
            return 0
    try:
        return int(s)
    except:
        return 0

def format_desc_fixed(desc, max_chars=180, line_len=60, min_lines=4, max_lines=4):
    if not desc:
        desc = "No description provided"
    text = desc.replace("\n", " ").strip()
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    words = text.split()
    chunks = []
    current = ""
    for w in words:
        if not current:
            current = w
        elif len(current) + 1 + len(w) <= line_len:
            current += " " + w
        else:
            chunks.append(current)
            current = w
        if len(chunks) >= max_lines:
            break
    if current and len(chunks) < max_lines:
        chunks.append(current)
    chunks = chunks[:max_lines]
    if len(chunks) < min_lines:
        chunks.extend(["&nbsp;"] * (min_lines - len(chunks)))
    return "<br>".join(chunks)

def generate_transparent_png(filepath, width=1, height=1):
    # Minimal PNG writer with alpha channel (transparent).
    import struct
    import zlib
    row = bytes([0] + [0, 0, 0, 0] * width)  # filter byte + RGBA pixels
    raw = row * height
    compressed = zlib.compress(raw, level=9)

    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    with open(filepath, "wb") as f:
        f.write(png)

def generate_title_badge_svg(text, accent, width=360, height=38):
    safe_text = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text_x = 16
    text_y = height / 2 + 5
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#9bbcf3" stop-opacity="0.55"/>
    </linearGradient>
  </defs>
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="9" fill="url(#g)" stroke="#2b3340" stroke-opacity="0.55"/>
  <text x="{text_x}" y="{text_y}" text-anchor="start" font-family="Arial, sans-serif" font-size="20" font-weight="800" fill="#f7f9ff">{safe_text}</text>
</svg>"""

def language_color(name):
    if not name:
        return "#6e7681"
    palette = {
        "Python": "#3572A5",
        "JavaScript": "#f1e05a",
        "TypeScript": "#2b7489",
        "Java": "#b07219",
        "C++": "#f34b7d",
        "C": "#555555",
        "Go": "#00ADD8",
        "Rust": "#dea584",
        "Swift": "#F05138",
        "Kotlin": "#A97BFF",
        "Jupyter Notebook": "#DA5B0B",
        "Shell": "#89e051",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
    }
    return palette.get(name, "#6e7681")

def generate_language_badge_svg(lang, color, width=140, height=28):
    label = (lang or "N/A").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="8" fill="#0d1117" stroke="#30363d"/>
  <circle cx="12" cy="{height/2}" r="5" fill="{color}"/>
  <text x="24" y="{height/2+4}" font-family="Arial, sans-serif" font-size="12" fill="#c9d1d9">{label}</text>
</svg>"""

def fetch_repo_stats(repo_path, _api_errors=None):
    url = f"https://api.github.com/repos/{repo_path}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException:
        if _api_errors is not None:
            _api_errors.append((repo_path, "network"))
        return None
    if response.status_code == 200:
        return response.json()
    if _api_errors is not None:
        _api_errors.append((repo_path, response.status_code))
    return None

def generate_svg_card(e):
    # Modern SVG card identifying the repo stats
    accents = e.get("accents") or [e.get("accent", "#4dabf7")]
    accents = [a for a in accents if a]
    if not accents:
        accents = ["#4dabf7"]
    growth_color = "#3fb950" if e['growth'] > 0 else "#f85149"
    growth_icon = "▲" if e['growth'] > 0 else "▼"
    
    if len(accents) > 1:
        accent_rects = (
            f'<rect x="0.5" y="0.5" width="6" height="74" rx="3" fill="{accents[0]}"/>'
            f'<rect x="0.5" y="75.5" width="6" height="74" rx="3" fill="{accents[1]}"/>'
        )
    else:
        accent_rects = f'<rect x="0.5" y="0.5" width="6" height="149" rx="3" fill="{accents[0]}"/>'

    svg = f"""<svg width="400" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="399" height="149" rx="9.5" fill="#0d1117" stroke="#30363d"/>
  {accent_rects}
  <text x="20" y="35" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#58a6ff">{e['name']}</text>
  <text x="20" y="55" font-family="Arial, sans-serif" font-size="12" fill="#8b949e">{e['repo_path']}</text>
  
  <g transform="translate(20, 80)">
    <text x="0" y="0" font-family="Arial, sans-serif" font-size="14" fill="#e3b341" dominant-baseline="middle">★</text>
    <text x="14" y="0" font-family="Arial, sans-serif" font-size="14" fill="#c9d1d9" dominant-baseline="middle">{e['stars']:,} stars</text>
  </g>
  
  <g transform="translate(150, 80)">
    <text x="0" y="0" font-family="Arial, sans-serif" font-size="14" fill="#c9d1d9" dominant-baseline="middle">{e['forks']:,} forks</text>
  </g>
  
  <rect x="300" y="20" width="80" height="25" rx="5" fill="#21262d" stroke="#30363d"/>
  <text x="340" y="37" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#c9d1d9" text-anchor="middle">{e['language']}</text>
</svg>"""
    return svg

def generate_section_bar_png(filepath, color, width=8, height=220):
    # Minimal PNG writer (no external deps). Color is hex like "#ff6b6b".
    hex_color = color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # Each row: filter byte 0 + RGB pixels
    row = bytes([0] + [r, g, b] * width)
    raw = row * height
    compressed = zlib.compress(raw, level=9)

    def chunk(chunk_type, data):
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    with open(filepath, "wb") as f:
        f.write(png)

# Static TOC entries (id, title, description) for template
STATIC_TOC_ENTRIES = [
    ("how-to-contribute", "🤝 Community & Participation", "How to contribute, PR guide, community"),
    ("ai-resource-navigator", "🌐 AI Resource Navigator", "Curated links: trends, news, tool discovery"),
    ("data-summary", "📝 Data Summary", "Data source and last generated timestamp"),
]


def generate_toc(projects_data):
    """Build Table of Contents as a GitHub-rendered Markdown table."""
    items = []
    category_keys = list(projects_data.keys())
    for idx, category_key in enumerate(category_keys):
        category_data = projects_data[category_key]
        title = category_data.get("title", category_key.title())
        desc = category_data.get("description", "")
        repo_count = len(category_data.get("repos", []) or [])
        items.append((category_key, title, repo_count, desc))
    lines = [
        "| # | Section | Repos | What you'll find |",
        "|:--:|---|:--:|---|",
    ]
    for idx, (section_id, title, repo_count, desc) in enumerate(items, start=1):
        safe_desc = (desc or "").replace("\n", " ").strip()
        lines.append(f"| {idx} | [{title}](#{section_id}) | {repo_count} | {safe_desc} |")
    other_lines = ["**Other Sections**"]
    offset = len(items)
    for jdx, (sid, title, desc) in enumerate(STATIC_TOC_ENTRIES, start=1):
        safe_desc = (desc or "").replace("\n", " ").strip()
        other_lines.append(f"- {offset + jdx}. [{title}](#{sid}) — {safe_desc}")
    return "\n".join(lines + [""] + other_lines)

def extract_leading_emoji(title, fallback="🔼"):
    if not title:
        return fallback
    token = title.split()[0]
    if token and not token[0].isalnum():
        return token
    return fallback

def generate_markdown(projects_data, base_dir):
    md_lines = []
    assets_dir = os.path.join(base_dir, "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    title_dir = os.path.join(assets_dir, "title_badges")
    if not os.path.exists(title_dir):
        os.makedirs(title_dir)
    spacer_path = os.path.join(assets_dir, "spacer.png")
    if not os.path.exists(spacer_path):
        generate_transparent_png(spacer_path, width=1, height=1)
    
    all_enriched_repos = []
    dynamic_sections = []
    search_index = {"sections": []}
    api_errors = []
    
    # Soft but distinct accent colors per section (order-aligned with projects.json)
    accent_palette = [
        "#ff6b6b",  # coral
        "#4dabf7",  # blue
        "#51cf66",  # green
        "#ffa94d",  # orange
        "#845ef7",  # violet
        "#20c997",  # teal
        "#ffd43b",  # yellow
        "#ff922b",  # deep orange
    ]
    category_keys = list(projects_data.keys())
    accent_by_category = {
        key: accent_palette[idx % len(accent_palette)]
        for idx, key in enumerate(category_keys)
    }
    # Custom accent for LLM Engines & Platforms
    if "llm_engines" in accent_by_category:
        accent_by_category["llm_engines"] = "#f25877"  # warm rose
    # Title badge accents (can differ from section accent)
    title_accent_by_category = dict(accent_by_category)
    if "llm_engines" in title_accent_by_category:
        title_accent_by_category["llm_engines"] = "#6b3d7a"  # deep purple

    # Build repo -> accents map to handle repos listed in multiple sections
    repo_accents = {}
    for idx, category_key in enumerate(category_keys):
        category_data = projects_data[category_key]
        accent = accent_by_category.get(category_key, "#4dabf7")
        for repo in category_data.get("repos", []) or []:
            repo_path = repo.get("url_path")
            if not repo_path:
                continue
            repo_accents.setdefault(repo_path, [])
            if accent not in repo_accents[repo_path]:
                repo_accents[repo_path].append(accent)

    for category_key, category_data in projects_data.items():
        title = category_data.get("title", category_key.title())
        section_emoji = extract_leading_emoji(title)
        accent = accent_by_category.get(category_key, "#4dabf7")
        title_accent = title_accent_by_category.get(category_key, accent)
        bar_hash = hashlib.sha1(accent.encode("utf-8")).hexdigest()[:8]
        bar_filename = f"section_bar_{category_key}_{bar_hash}.png"
        bar_path = os.path.join(assets_dir, bar_filename)
        generate_section_bar_png(bar_path, accent, width=8, height=220)
        bar_asset = f"assets/{bar_filename}"
        sec_lines = []
        sec_lines.append(f"<h2 id='{category_key}'>{title}</h2>")
        sec_lines.append(f"<p><img src=\"{bar_asset}\" alt=\"\" width=\"24\" height=\"6\"> Section color</p>")
        sec_lines.append("")
        search_index["sections"].append({
            "id": category_key,
            "title": title,
            "description": category_data.get("description", ""),
            "repos": []
        })
        
        repos = category_data.get("repos", [])
        enriched_repos = []
        
        for repo in repos:
            stats = fetch_repo_stats(repo["url_path"], api_errors)
            
            manual_desc = repo.get("manual_desc")
            if stats:
                current_stars = stats.get("stargazers_count", 0)
                last_stars = parse_stars(repo.get("last_stars", current_stars))
                growth = current_stars - last_stars
                repo["last_stars"] = current_stars
                if manual_desc:
                    repo["last_desc"] = manual_desc.replace("|", "\\|")
                else:
                    repo["last_desc"] = (stats.get("description") or "No description provided").replace("|", "\\|")
                repo["last_lang"] = stats.get("language") or "N/A"
                repo["last_forks"] = stats.get("forks_count", 0)
                data_status = ""
            else:
                # FALLBACK: Use last known data if API fails (403 Rate Limit)
                current_stars = parse_stars(repo.get("last_stars", 0))
                growth = 0
                data_status = ""
                
            e = {
                "repo_path": repo["url_path"],
                "name": repo["url_path"].split("/")[-1],
                "html_url": f"https://github.com/{repo['url_path']}",
                "description": (manual_desc or repo.get("last_desc", "Description not available")),
                "language": repo.get("last_lang", "N/A"),
                "forks": repo.get("last_forks", 0),
                "stars": current_stars,
                "growth": growth,
                "category": title,
                "category_id": category_key,
                "status_tag": data_status,
                "accent": accent,
                "accents": repo_accents.get(repo["url_path"], [accent])[:2],
            }
            
            # Generate local custom SVG (include category to avoid overwriting)
            svg_filename = f"{e['repo_path'].replace('/', '_')}_{category_key}.svg"
            svg_path = os.path.join(assets_dir, svg_filename)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(generate_svg_card(e))
            
            e["svg_asset"] = f"assets/{svg_filename}"
            title_width = min(420, max(120, int(12 * len(e["name"]) + 60)))
            title_svg = generate_title_badge_svg(e["name"], title_accent, width=title_width, height=38)
            title_hash = hashlib.sha1(title_svg.encode("utf-8")).hexdigest()[:8]
            title_filename = f"title_{e['repo_path'].replace('/', '_')}_{category_key}_{title_hash}.svg"
            title_path = os.path.join(title_dir, title_filename)
            with open(title_path, "w", encoding="utf-8") as f:
                f.write(title_svg)
            e["title_badge"] = f"assets/title_badges/{title_filename}"
            enriched_repos.append(e)
            all_enriched_repos.append(e)
            search_index["sections"][-1]["repos"].append({
                "name": e["name"],
                "url_path": e["repo_path"],
                "html_url": e["html_url"],
                "description": (e["description"][:200] + "..." if len(e["description"]) > 200 else e["description"]),
            })
            
        enriched_repos.sort(key=lambda x: x["stars"], reverse=True)
        
        for e in enriched_repos:
            desc_limited = format_desc_fixed(e['description'], max_chars=180, line_len=60, min_lines=4, max_lines=4)
            section_anchor = e["category_id"]
            card_html = f"""
<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td width="58%" valign="top">
      <div>
        <a href="{e['html_url']}"><img src="{e['title_badge']}" alt="{e['name']}" height="38"></a>{e['status_tag']}
      </div>
      <p style="line-height: 1.5;">{desc_limited}</p>
    </td>
    <td width="42%" valign="middle" align="center">
      <a href="{e['html_url']}"><img src="{e['svg_asset']}" alt="{e['name']} stats" width="400"></a>
    </td>
  </tr>
  <tr>
    <td colspan="2" align="right">
      <a href="#{section_anchor}"><kbd>{section_emoji} Back to Section</kbd></a> · <a href="#contents"><kbd>📑 Contents</kbd></a>
    </td>
  </tr>
</table>
<div style="height: 16px;"></div>
"""
            sec_lines.append(card_html)
            
        if idx < len(category_keys) - 1:
            sec_lines.append("\n---\n")
        dynamic_sections.append("\n".join(sec_lines))

    return "\n".join(dynamic_sections), search_index, api_errors

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    projects_file = os.path.join(base_dir, "projects.json")
    template_file = os.path.join(base_dir, "README.md.template")
    output_file = os.path.join(os.path.dirname(base_dir), "README.md")
    
    print("Loading projects...")
    projects_data = load_projects(projects_file)
    
    print("Fetching statistics & generating visualization...")
    dynamic_md, search_index, api_errors = generate_markdown(projects_data, base_dir)
    if api_errors:
        codes = {}
        for _, c in api_errors:
            codes[c] = codes.get(c, 0) + 1
        msg = ", ".join(f"{c}: {n}" for c, n in sorted(codes.items(), key=lambda kv: str(kv[0])))
        print(f"  Note: Using cached data for some repos ({msg}). README was still generated.")
    
    print("Saving updated projects.json...")
    save_projects(projects_file, projects_data)
    
    toc_html = generate_toc(projects_data)
    docs_dir = os.path.join(os.path.dirname(base_dir), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    search_index_path = os.path.join(docs_dir, "search-index.json")
    with open(search_index_path, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)
    print(f"Search index written: {search_index_path}")
    
    print("Generating README.md...")
    with open(template_file, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    now_utc = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    final_readme = template_content.replace("<!-- TOC_PLACEHOLDER -->", toc_html)
    final_readme = final_readme.replace("<!-- DYNAMIC_CONTENT -->", dynamic_md)
    final_readme = final_readme.replace("{{ timestamp }}", now_utc)
    
    final_readme = final_readme.replace('src="assets/', 'src="GitTrendHub/assets/')
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_readme)
        
    print(f"Update complete! {output_file} successfully created.")

if __name__ == "__main__":
    main()
