"""
Download summary trees and tip metadata of the Phlorest repositories, pinned to
commits.

  fetch_phlorest.py OUT             every repository at its current head; writes
                                    OUT/phlorest_manifest.json (repository -> commit)
  fetch_phlorest.py OUT MANIFEST    the repositories and commits of MANIFEST, as
                                    archived in results/phlorest_manifest.json
"""
import json
import pathlib
import subprocess
import sys
import urllib.request

OUT = pathlib.Path(sys.argv[1])
if len(sys.argv) > 2:
    manifest = json.loads(pathlib.Path(sys.argv[2]).read_text())
else:
    API = "https://api.github.com/orgs/phlorest/repos?per_page=100"
    repos = [r["name"] for r in json.load(urllib.request.urlopen(API)) if r["name"] not in {".github", "phlorest"}]
    manifest = {}
    for repo in sorted(repos):
        head = subprocess.run(["git", "ls-remote", f"https://github.com/phlorest/{repo}", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.split()
        manifest[repo] = head[0]
(OUT / "phlorest_manifest.json").unlink(missing_ok=True)  # written again only when every file is in
failed = []
for repo, commit in sorted(manifest.items()):
    out = OUT / repo
    out.mkdir(parents=True, exist_ok=True)
    for name in ("summary.trees", "languages.csv", "trees.csv"):
        (out / name).unlink(missing_ok=True)  # no stale file survives a failed download
        url = f"https://raw.githubusercontent.com/phlorest/{repo}/{commit}/cldf/{name}"
        try:
            (out / name).write_bytes(urllib.request.urlopen(url, timeout=60).read())
        except Exception as exc:
            failed.append(f"{repo}/{name}: {exc}")
    print(repo, commit)
if failed:
    sys.exit("download failed, no manifest written:\n" + "\n".join(failed))
(OUT / "phlorest_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
