"""Download summary trees and tip metadata of every phlorest repository."""
import json, pathlib, sys, urllib.request

OUT = pathlib.Path(sys.argv[1])
API = "https://api.github.com/orgs/phlorest/repos?per_page=100"
repos = [r["name"] for r in json.load(urllib.request.urlopen(API)) if r["name"] not in {".github", "phlorest"}]
for repo in sorted(repos):
    out = OUT / repo
    out.mkdir(parents=True, exist_ok=True)
    for name in ("summary.trees", "languages.csv", "trees.csv"):
        url = f"https://raw.githubusercontent.com/phlorest/{repo}/main/cldf/{name}"
        try:
            (out / name).write_bytes(urllib.request.urlopen(url, timeout=60).read())
        except Exception as exc:
            print(f"{repo}/{name}: {exc}")
    print(repo)
