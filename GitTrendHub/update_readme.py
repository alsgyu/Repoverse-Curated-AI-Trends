import os
import json
import requests
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
    growth_color = "#3fb950" if e['growth'] > 0 else "#f85149"
    growth_icon = "▲" if e['growth'] > 0 else "▼"
    
    svg = f"""<svg width="400" height="150" viewBox="0 0 400 150" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="399" height="149" rx="9.5" fill="#0d1117" stroke="#30363d"/>
  <text x="20" y="35" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="#58a6ff">{e['name']}</text>
  <text x="20" y="55" font-family="Arial, sans-serif" font-size="12" fill="#8b949e">{e['repo_path']}</text>
  
  <g transform="translate(20, 80)">
    <circle cx="5" cy="0" r="5" fill="#e3b341"/>
    <text x="15" y="4" font-family="Arial, sans-serif" font-size="14" fill="#c9d1d9">{e['stars']:,} stars</text>
  </g>
  
  <g transform="translate(150, 80)">
    <path d="M5 0 L0 5 L5 10 M5 5 L10 5" stroke="#8b949e" stroke-width="2" fill="none"/>
    <text x="20" y="4" font-family="Arial, sans-serif" font-size="14" fill="#c9d1d9">{e['forks']:,} forks</text>
  </g>
  
  <g transform="translate(20, 115)">
    <text x="0" y="4" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="{growth_color}">Trending: {growth_icon} {abs(e['growth']):,}</text>
  </g>
  
  <rect x="300" y="20" width="80" height="25" rx="5" fill="#21262d" stroke="#30363d"/>
  <text x="340" y="37" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#c9d1d9" text-anchor="middle">{e['language']}</text>
</svg>"""
    return svg

# Static TOC entries (id, title, description) for template
STATIC_TOC_ENTRIES = [
    ("how-to-contribute", "🤝 Community & Participation", "How to contribute, PR guide, community"),
    ("ai-resource-navigator", "🌐 AI Resource Navigator", "Curated links: trends, news, tool discovery"),
    ("data-summary", "📝 Data Summary", "Data source and last generated timestamp"),
]


def generate_toc(projects_data):
    """Build Table of Contents as a GitHub-rendered Markdown table."""
    items = []
    for category_key, category_data in projects_data.items():
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


def generate_markdown(projects_data, base_dir):
    md_lines = []
    assets_dir = os.path.join(base_dir, "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
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

    for category_key, category_data in projects_data.items():
        title = category_data.get("title", category_key.title())
        accent = accent_by_category.get(category_key, "#4dabf7")
        sec_lines = []
        sec_lines.append(f"<h2 id='{category_key}'>{title}</h2>")
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
            
            if stats:
                current_stars = stats.get("stargazers_count", 0)
                last_stars = parse_stars(repo.get("last_stars", current_stars))
                growth = current_stars - last_stars
                repo["last_stars"] = current_stars
                repo["last_desc"] = (stats.get("description") or "No description provided").replace("|", "\\|")
                repo["last_lang"] = stats.get("language") or "N/A"
                repo["last_forks"] = stats.get("forks_count", 0)
                data_status = ""
            else:
                # FALLBACK: Use last known data if API fails (403 Rate Limit)
                current_stars = parse_stars(repo.get("last_stars", 0))
                growth = 0
                data_status = " <sub>(Vault Mode)</sub>"
                
            e = {
                "repo_path": repo["url_path"],
                "name": repo["url_path"].split("/")[-1],
                "html_url": f"https://github.com/{repo['url_path']}",
                "description": repo.get("last_desc", "Description not available"),
                "language": repo.get("last_lang", "N/A"),
                "forks": repo.get("last_forks", 0),
                "stars": current_stars,
                "growth": growth,
                "category": title,
                "category_id": category_key,
                "status_tag": data_status
            }
            
            # Generate local custom SVG
            svg_filename = f"{e['repo_path'].replace('/', '_')}.svg"
            svg_path = os.path.join(assets_dir, svg_filename)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(generate_svg_card(e))
            
            e["svg_asset"] = f"assets/{svg_filename}"
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
            desc_limited = e['description']
            if len(desc_limited) > 120:
                desc_limited = desc_limited[:117] + "..."
            section_anchor = e["category_id"]
            badge_text = title.replace('"', "&quot;")
            card_html = f"""
<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td width="8" bgcolor="{accent}"></td>
    <td width="60%" valign="top" style="padding-left: 10px;">
      <div style="display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: 0.2px; color: {accent}; border: 1px solid {accent}; border-radius: 999px; padding: 2px 8px; margin: 2px 0 6px 0;">
        {badge_text}
      </div>
      <h3><a href="{e['html_url']}">{e['name']}</a>{e['status_tag']}</h3>
      <p>{desc_limited}</p>
      <img src="{e['svg_asset']}" alt="{e['name']} stats" width="400">
    </td>
    <td width="40%" valign="top" align="center">
      <a href="https://star-history.com/#{e['repo_path']}&Date">
        <img src="https://api.star-history.com/svg?repos={e['repo_path']}&type=Date" alt="Star History" width="100%">
      </a>
    </td>
  </tr>
</table>
<p align="right"><a href="#{section_anchor}">🔼 Back to Section ({title})</a> · <a href="#contents">📑 Back to Contents</a></p>
"""
            sec_lines.append(card_html)
            
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
        msg = ", ".join(f"{c}: {n}" for c, n in sorted(codes.items()))
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
