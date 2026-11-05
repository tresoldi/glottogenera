"""Crown ages of Glottolog nodes from dated published phylogenies (phlorest)."""
import csv, json, re, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "src")
import newick  # noqa: E402  (research/divergence/newick.py)
from glottogenera.glottolog import Glottolog

PH = Path(sys.argv[1]); OUT = Path(sys.argv[2])
UNIT = {"years": 1, "centuries": 100, "millennia": 1000}
g = Glottolog.load()
inscope = {r["glottocode"] for r in g.in_scope_languages()}

def language_of(gc):
    if gc in inscope: return gc
    for a in reversed(g.ancestors(gc)):
        if a in inscope: return a
    return None

rows = []
for repo in sorted(p for p in PH.iterdir() if p.is_dir()):
    try:
        unit = next(csv.DictReader(open(repo / "trees.csv")))["Tree_Branch_Length_Unit"]
    except Exception:
        continue
    if unit not in UNIT: continue
    text = (repo / "summary.trees").read_text()
    trans = {}
    m = re.search(r"translate(.*?);", text, re.S | re.I)
    if m:
        for k, v in re.findall(r"\s*(\S+)\s+([^,\s]+)\s*,?", m.group(1)): trans[k] = v.strip("'")
    nwk = re.search(r"tree\s+\S+\s*=\s*(?:\[[^\]]*\]\s*)?(\(.*?;)", text, re.S | re.I).group(1)
    nwk = re.sub(r"\[[^\]]*\]", "", nwk)
    root = newick.loads(nwk)[0]
    gc_of = {}
    for r in csv.DictReader(open(repo / "languages.csv")):
        if r.get("Glottocode"):
            gc_of[r["ID"]] = r["Glottocode"]; gc_of.setdefault(r["Name"], r["Glottocode"])
    # distance from root
    dist = {id(root): 0.0}
    for n in root.walk():
        for c in n.descendants:
            dist[id(c)] = dist[id(n)] + float(c.length or 0)
    leaves = root.get_leaves()
    H = max(dist[id(l)] for l in leaves)
    leaf_lang = {}
    for l in leaves:
        name = trans.get(l.name, l.name)
        gc = gc_of.get(name) or gc_of.get(name.replace("_", " "))
        lang = language_of(gc) if gc else None
        if lang: leaf_lang[id(l)] = lang
    # clade leaf sets for MRCA lookup
    under = {}
    for n in root.walk(mode="postorder"):
        under[id(n)] = {id(n)} if n.is_leaf else set().union(*(under[id(c)] for c in n.descendants))
    nodes_by_size = sorted(root.walk(), key=lambda n: len(under[id(n)]))
    groups = defaultdict(lambda: defaultdict(set))   # glottolog node -> child branch -> leaf ids
    for lid, lang in leaf_lang.items():
        lin = g.lineage(lang)
        for i in range(len(lin) - 1):
            groups[lin[i]][lin[i + 1]].add(lid)
    scale = UNIT[unit]
    for node, branches in groups.items():
        if len(branches) < 2: continue
        ids = set().union(*branches.values())
        mrca = next(n for n in nodes_by_size if ids <= under[id(n)])
        mono = all(lid in ids for lid in under[id(mrca)] if lid in leaf_lang)
        rows.append({"repo": repo.name, "node": node, "name": g.name(node), "family": g.family_name(g.family_gc(node)),
                     "age_years": (H - dist[id(mrca)]) * scale, "leaves": len(ids), "branches": len(branches),
                     "monophyletic": mono})
    print(f"{repo.name:24s} unit={unit:9s} tips mapped={len(leaf_lang):4d}/{len(leaves):4d} H={H*scale:8.0f} yrs nodes={sum(r['repo']==repo.name for r in rows)}")
json.dump(rows, open(OUT / "ages.json", "w"), indent=0)
