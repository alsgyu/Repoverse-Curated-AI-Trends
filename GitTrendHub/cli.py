#!/usr/bin/env python3
"""
Search the curated repo list from the terminal.
Run from repo root:  python3 -m GitTrendHub.cli search "keyword"
"""
import argparse
import json
import os
import sys


def find_repo_root():
    """Repo root is parent of GitTrendHub/."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_index():
    repo_root = find_repo_root()
    path = os.path.join(repo_root, "docs", "search-index.json")
    if not os.path.isfile(path):
        return None, f"Index not found: {path}\nRun 'python3 update_readme.py' from the repo root first."
    with open(path, encoding="utf-8") as f:
        return json.load(f), None


def search(query, index):
    q = (query or "").strip().lower()
    if not q:
        return []
    out = []
    for section in index.get("sections", []):
        section_text = (section.get("title", "") + " " + (section.get("description") or "")).lower()
        for repo in section.get("repos", []):
            repo_text = (
                repo.get("name", "")
                + " "
                + (repo.get("url_path") or "")
                + " "
                + (repo.get("description") or "")
            ).lower()
            if q in repo_text or q in section_text:
                out.append(
                    {
                        "section": section.get("title", ""),
                        "section_id": section.get("id", ""),
                        "name": repo.get("name", ""),
                        "url_path": repo.get("url_path", ""),
                        "html_url": repo.get("html_url", ""),
                        "description": (repo.get("description") or "")[:120],
                    }
                )
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Search AI TrendHub curated repos from the terminal.",
        epilog="Example: python3 -m GitTrendHub.cli search llama",
    )
    parser.add_argument(
        "args",
        nargs="*",
        metavar="query",
        help="Search keyword(s); e.g. 'search llama' or 'llama'",
    )
    args = parser.parse_args()
    # Allow "search keyword" or just "keyword"
    parts = args.args or []
    if parts and parts[0].lower() == "search":
        parts = parts[1:]
    query = " ".join(parts).strip()

    index, err = load_index()
    if err:
        print(err, file=sys.stderr)
        sys.exit(1)

    if not query:
        parser.print_help()
        print("\nExample: python3 -m GitTrendHub.cli search llama", file=sys.stderr)
        sys.exit(0)

    results = search(query, index)
    if not results:
        print(f"No matches for '{query}'.")
        sys.exit(0)
    print(f"Found {len(results)} match(es) for '{query}':\n")
    for r in results:
        print(f"  [{r['section']}] {r['name']}")
        print(f"    {r['html_url']}")
        if r["description"]:
            print(f"    {r['description']}...")
        print()
    sys.exit(0)


if __name__ == "__main__":
    main()
