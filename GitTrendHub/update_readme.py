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

def fetch_repo_stats(repo_path):
    url = f"https://api.github.com/repos/{repo_path}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {repo_path}: {response.status_code}")
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
    <text x="0" y="4" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="{growth_color}">Weekly Growth: {growth_icon} {abs(e['growth']):,}</text>
  </g>
  
  <rect x="300" y="20" width="80" height="25" rx="5" fill="#21262d" stroke="#30363d"/>
  <text x="340" y="37" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#c9d1d9" text-anchor="middle">{e['language']}</text>
</svg>"""
    return svg

def generate_markdown(projects_data, base_dir):
    md_lines = []
    assets_dir = os.path.join(base_dir, "assets")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    all_enriched_repos = []
    dynamic_sections = []
    
    for category_key, category_data in projects_data.items():
        title = category_data.get("title", category_key.title())
        sec_lines = [f"<h2 id='{category_key}'>{title}</h2>", ""]
        
        repos = category_data.get("repos", [])
        enriched_repos = []
        
        for repo in repos:
            stats = fetch_repo_stats(repo["url_path"])
            if not stats: continue
                
            current_stars = stats.get("stargazers_count", 0)
            last_stars = repo.get("last_stars", current_stars)
            growth = current_stars - last_stars
            repo["last_stars"] = current_stars
            
            e = {
                "repo_path": repo["url_path"],
                "name": stats.get("name"),
                "html_url": stats.get("html_url"),
                "description": (stats.get("description") or "No description provided").replace("|", "\\|"),
                "language": stats.get("language") or "N/A",
                "forks": stats.get("forks_count", 0),
                "issues": stats.get("open_issues_count", 0),
                "stars": current_stars,
                "growth": growth,
                "category": title
            }
            
            # Generate local custom SVG
            svg_filename = f"{e['repo_path'].replace('/', '_')}.svg"
            svg_path = os.path.join(assets_dir, svg_filename)
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(generate_svg_card(e))
            
            e["svg_asset"] = f"assets/{svg_filename}"
            enriched_repos.append(e)
            all_enriched_repos.append(e)
            
        enriched_repos.sort(key=lambda x: x["stars"], reverse=True)
        
        for e in enriched_repos:
            desc_limited = e['description']
            if len(desc_limited) > 120:
                desc_limited = desc_limited[:117] + "..."
                
            card_html = f"""
<table width="100%">
  <tr>
    <td width="60%" style="vertical-align: top;">
      <h3><a href="{e['html_url']}">{e['name']}</a></h3>
      <p>{desc_limited}</p>
      <img src="{e['svg_asset']}" alt="{e['name']} stats" width="400">
    </td>
    <td width="40%" style="vertical-align: top; text-align: center;">
      <a href="https://star-history.com/#{e['repo_path']}&Date">
        <img src="https://api.star-history.com/svg?repos={e['repo_path']}&type=Date" alt="Star History" width="100%">
      </a>
    </td>
  </tr>
</table>
<p align="right"><a href="#table-of-contents">🔼 Back to Top</a></p>
"""
            sec_lines.append(card_html)
            
        sec_lines.append("\n---\n")
        dynamic_sections.append("\n".join(sec_lines))

    # Generate "Trend of Trend" Chart (Top 7 Growers)
    all_enriched_repos.sort(key=lambda x: x["growth"], reverse=True)
    top_growers = all_enriched_repos[:7]
    
    chart_labels = [row['name'] for row in top_growers]
    chart_data = [row['growth'] for row in top_growers]
    
    chart_config = {
        "type": "bar",
        "data": {
            "labels": chart_labels,
            "datasets": [{
                "label": "7d Star Growth Portfolio",
                "backgroundColor": "rgba(88, 166, 255, 0.6)",
                "borderColor": "rgb(88, 166, 255)",
                "borderWidth": 1,
                "data": chart_data
            }]
        },
        "options": {
            "title": {"display": True, "text": "🔥 Weekly Hot Trends: Growth Leaderboard"},
            "scales": {"yAxes": [{"ticks": {"beginAtZero": True}}]}
        }
    }
    
    import urllib.parse
    chart_url = f"https://quickchart.io/chart?c={urllib.parse.quote(json.dumps(chart_config))}"
    
    header_viz = f"""
<h2 id="hot-trends">🔥 Trend of Trends: Hot Movers</h2>
<div align="center">
  <img src="{chart_url}" width="800" alt="Hot Trends Leaderboard">
  <p><i>The comparison above shows the real-time velocity of the fastest-growing projects in our curated collection.</i></p>
</div>
<br/>
"""
    
    return header_viz + "\n" + "\n".join(dynamic_sections)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    projects_file = os.path.join(base_dir, "projects.json")
    template_file = os.path.join(base_dir, "README.md.template")
    output_file = os.path.join(os.path.dirname(base_dir), "README.md")
    
    print("Loading projects...")
    projects_data = load_projects(projects_file)
    
    print("Fetching statistics & generating visualization...")
    dynamic_md = generate_markdown(projects_data, base_dir)
    
    print("Saving updated projects.json...")
    save_projects(projects_file, projects_data)
    
    print("Generating README.md...")
    with open(template_file, "r", encoding="utf-8") as f:
        template_content = f.read()
    
    now_utc = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")
    final_readme = template_content.replace("<!-- DYNAMIC_CONTENT -->", dynamic_md)
    final_readme = final_readme.replace("{{ timestamp }}", now_utc)
    
    final_readme = final_readme.replace('src="assets/', 'src="GitTrendHub/assets/')
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(final_readme)
        
    print(f"Update complete! {output_file} successfully created.")

if __name__ == "__main__":
    main()
