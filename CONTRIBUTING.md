## Contributing

Thanks for helping improve **AI TrendHub**. This repository is intentionally simple: the curated list lives in `GitTrendHub/projects.json`, and `README.md` is generated.

### Ways to contribute

- **Suggest a repo (fastest)**: Open a GitHub Issue and select the **Repo suggestion** form.
- **Add or update a repo**: Edit `GitTrendHub/projects.json`, regenerate outputs, then open a PR.
- **Improve the generator or CLI**: Work on `GitTrendHub/update_readme.py` or `GitTrendHub/cli.py`.
- **Fix data quality**: Report incorrect descriptions, dead links, or wrong categories.

### Local setup

Requirements:
- Python 3.10+ (you have Python 3)

Optional (recommended):
- Set `GITHUB_TOKEN` to avoid rate limits when fetching repo metadata

```bash
cp GitTrendHub/.env.example .env
# Edit .env and set GITHUB_TOKEN=...
```

### Regenerating outputs

From the repo root:

```bash
python3 update_readme.py
```

This will update:
- `README.md`
- `docs/search-index.json`
- `GitTrendHub/projects.json` (cache fields like last stars/desc/lang/forks)

### Adding a repo (PR workflow)

1. Edit `GitTrendHub/projects.json` and add a repo under the right section:

```json
{ "url_path": "OWNER/REPO", "last_stars": "Hot" }
```

2. Regenerate outputs:

```bash
python3 update_readme.py
```

3. Commit the generated files:

```bash
git add GitTrendHub/projects.json README.md docs/search-index.json
```

4. Open a Pull Request.

### CLI search

After generating the index, you can search from the terminal:

```bash
python3 -m GitTrendHub.cli search llama
python3 -m GitTrendHub.cli search \"stable diffusion\"
```

### Notes on GitHub rendering

GitHub sanitizes HTML/CSS inside `README.md`. If you want “table-like UI”, prefer **Markdown tables** and plain HTML tables without inline styles.

