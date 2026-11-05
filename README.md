# glottogenera

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23979575.svg)](https://doi.org/10.5281/zenodo.23979575)

Language **genera** defined by an explicit rule, as a reproducible
replacement for the expert-assigned genera of Dryer (1989) and WALS, with a
release for every in-scope language of Glottolog 5.3.

> Given a rooted tree over a set of languages and a divergence for its
> clades, a **genus** is the largest clade whose divergence does not exceed a
> threshold δ.

The tree can be an expert classification or one estimated from data (UPGMA,
neighbour-joining, a Bayesian consensus tree), and the divergence any distance
between languages averaged over pairs on different branches, or a value of the
clade such as its age: `glottogenera.tree` applies the rule to any of them.
In the release, the tree is Glottolog 5.3, divergence is the normalized
PMI-alignment distance between languages on different branches of the clade,
measured on the 40-concept ASJP wordlists, and δ is the value at which the
genera agree best with those of WALS, averaged over language families. The
formal definition is in [`docs/definition.md`](docs/definition.md).

**Explore online:** <https://glottogenera.tresoldi.org/> browses the genera,
languages and families, maps them (points, and genus areas as merged Voronoi
cells), recuts them at any threshold, compares them with WALS and exports CSV
and GeoJSON (see [`web/`](web/)).

## The release

- **7,674 in-scope languages → 1,190 genera**, every genus a complete
  Glottolog clade identified by the Glottocode of its node. δ = 0.81
  maximizes agreement with WALS averaged over 49 language families (smoothed
  over ±0.02); neighbouring criteria give 0.807–0.829, and the curve is
  nearly flat from about 0.74 to 0.80, where other choices of ASJP doculect
  can move δ: check results at δ = 0.75 too (about 1,600 genera).
- Every genus comes with its crown divergence where measurable, the range of
  δ over which it exists and a bootstrap **stability score**; 333 of the 714
  genera with more than one language reappear in at least 90% of replicates.
- Agreement with WALS: mean per-family ARI 0.654, completeness 0.865, purity
  0.980; better per family than any fixed-depth cut of the classification,
  also with families held out of the calibration. The thresholds that suit
  single families differ widely, so δ is a compromise between them.
- The word distance (PMI alignment with sound correspondences learned from
  the data, scored with ASymCat) tracks expert cognate judgements and dated
  phylogenies better than LDND, and most genera survive a change of distance
  or lexical source (ASJP or GLED).
- 32 genera carry a curated name where Glottolog's node name is a
  bookkeeping label, a coinage or misleading
  ([`docs/genus-names.md`](docs/genus-names.md)).

The data are in [`data/`](data/) as TSV (described in
[`data/README.md`](data/README.md)) and in [`cldf/`](cldf/) as a CLDF
StructureDataset; [`data/report.md`](data/report.md) summarizes them and
[`docs/methods.md`](docs/methods.md) describes how they are built.

## Using the data

The released tables also ship inside the Python package:

```python
import glottogenera

rows = glottogenera.load_genera()            # one dict per language
summary = glottogenera.load_genera_summary() # one dict per genus
nodes = glottogenera.load_nodes()            # crown divergence of every measured node
other = glottogenera.genera_at(0.75)         # {glottocode: genus_id} at another threshold
glottogenera.genus_name(other["stan1293"])   # 'Germanic'
```

A genealogically balanced sample takes at most one language per genus:

```python
import random
from collections import defaultdict

by_genus = defaultdict(list)
for row in glottogenera.load_genera():
    by_genus[row["genus_id"]].append(row["glottocode"])

rng = random.Random(42)
sample = sorted(rng.choice(sorted(members)) for members in by_genus.values())
```

Report the Glottolog release (5.3) and δ with any sample, and check results
against the `stability` scores: unstable genera lie close to the threshold.
Genera are sampling strata, not independent or equal-age units.

## Other trees and measures

`glottogenera.tree` applies the rule to any rooted tree: read from Newick or
from a table of parents, with node values computed from any distance between
languages or supplied directly, cut at a threshold or calibrated against a
reference partition. It also estimates UPGMA and neighbour-joining trees from
a distance matrix.

```python
from glottogenera.tree import Calibration, Tree, cut_values, genera, node_ages, threshold_grid

tree = Tree.from_newick(open("mcc.nwk").read())   # e.g. a dated tree with contemporary tips
c = cut_values(tree, node_ages(tree))             # or crown_divergence(tree, distance)
genus, method = genera(tree, c, 2000)             # genera no older than 2,000 years
cal = Calibration(tree, c, reference, grid=threshold_grid(c), half_width=100)
```

## Reproducing the release

The release:

```bash
pip install -e ".[dev]"
make all        # fetch WALS and ASJP, recompute the genera, refresh the package copies (network)
make test
```

The CLDF dataset and the web explorer's data:

```bash
pip install -e ".[cldf,web]"   # pycldf, shapely and matplotlib
make cldf                      # rebuild cldf/ and validate it
make web                       # rebuild web/data/ (downloads Natural Earth)
make release                   # all three: make all, make cldf and make web
```

To validate the CLDF dataset alone: `cldf validate cldf/StructureDataset-metadata.json`.
How to check the site in a browser is described in [`web/README.md`](web/README.md).

`glottogenera all` runs the first two stages of `make all` from the command line. All
stages read and write under `data/` (`--data-dir` to override). The Glottolog
dump is vendored in the package; WALS and ASJP are fetched at pinned versions
and cached under `data/sources/` (see [`docs/sources.md`](docs/sources.md)).
The pipeline is deterministic: a full run reproduces the committed artifacts
byte for byte.

Pipeline commands impose a 2 GiB address-space ceiling and use one numerical
library thread by default. Override the ceiling with, for example,
`glottogenera --max-memory-mb 4096 all`, and the thread count with
`GLOTTOGENERA_NUM_THREADS`.

The validation behind the choices of the release (word distance, robustness,
sensitivity, estimated trees) is in [`research/divergence/`](research/divergence/).

## Repository layout

| path | contents |
|------|----------|
| `src/glottogenera/` | the package: pipeline, generic tree module, CLI, vendored Glottolog dump, release tables, curated names |
| `data/` | the released dataset: genus, summary, node and name tables, `params.json`, report |
| `cldf/` | the same dataset as a CLDF StructureDataset |
| `docs/` | definition, methods, genus names, sources and attribution |
| `scripts/` | builders of the CLDF dataset and the explorer's data, Glottolog update |
| `web/` | the static web explorer |
| `research/` | validation scripts and their results |
| `tests/` | unit, release-integrity and web parity tests |

## Citation

Please cite the dataset, doi:[10.5281/zenodo.23979575](https://doi.org/10.5281/zenodo.23979575) (see [`CITATION.cff`](CITATION.cff)),
and Glottolog, ASJP and WALS, from which it derives. A data descriptor is in preparation.

## License

The dataset (`data/`, `cldf/`, the tables under `src/glottogenera/data/` and
`web/data/`) is under CC BY 4.0, as Glottolog's licence requires; the code is
under the MIT license (see [`LICENSE`](LICENSE), [`data/LICENSE`](data/LICENSE)
and [`docs/sources.md`](docs/sources.md) for upstream attribution).

## Origin

Developed at Uppsala University. Spun off from
[`samba_sampler`](https://github.com/tresoldi/samba_sampler), which consumes
genus assignments for genealogically balanced language sampling.
