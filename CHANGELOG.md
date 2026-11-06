# Changelog

## 1.3.0 — unreleased

Corrections after a second review; the genera are unchanged.

- **Distance screen.** A placeholder cognate set numbered 0 (in Peiros'
  Austroasiatic data, for loans and entries without a judgement) is no longer
  read as a shared judgement (`research/divergence/cognacy.py`, with tests);
  the released distance is now trained as the package trains it; the results
  are recomputed. New: the sensitivity of the screen to the pooling of source
  varieties (`variety_sensitivity.py`) and of the release to the envelope rule
  (`envelope_sensitivity.py`); the recovery of genera under GLED is reported
  by how many of their members GLED covers.
- **Calibration.** The threshold is the middle one of the grid values that
  maximize the objective (the lower of two), always a maximizer (before, the
  median of disconnected maximizers could be neither);
  the released δ is unchanged, three leave-one-family-out thresholds and the
  bootstrap stability of 29 genera (by one replicate in 200) change.
- **Precision.** Node values are released with six decimals, and the release
  is computed from these rounded values, so that recutting `nodes.tsv`
  reproduces every released result.
- **Residual groups.** `unclassified_node` is also in the CLDF CodeTable and
  in the explorer (genus pages and CSV exports).
- **Metadata.** The repository cites the DOI of all versions
  (10.5281/zenodo.23979574).
- **Archive.** The pair-level values of every screened distance
  (`screen_pairs_all.csv.gz`) and the estimated UPGMA and neighbour-joining
  trees (`estimated_trees.nwk`) are in `research/divergence/results/`.
- **Explorer.** Thresholds are kept on the 0.001 grid in addresses and cache.
- **Research scripts.** The ABVD source is pinned to the commit actually used;
  `fetch_phlorest.py` fails when a file is missing; `gled_cldf.py` keeps the
  ASJP form in `Value`.

## 1.2.0 — 2026-11-06

Corrections after review; the genera and their divergences are unchanged.

- **Cognate judgements.** The files in `research/divergence/cognates/` are now
  one per source dataset: the aggregate's grouping had put the judgements of
  several datasets under other names (the file labelled ACD held ABVD's
  Philippine subset, the one labelled Turkic held Savelyev & Robbeets' and
  Kessler's data, Austroasiatic and TuLeD also held Aslian, Khasian and
  Tupí-Guaraní data). Sixteen source datasets, with their own citations and
  licences. The distance screen now counts two forms as cognate when they
  share any of their cognate sets (several are separated by `;`); its results
  are recomputed.
- **Reproducibility.** The Phlorest trees are pinned to commits
  (`results/phlorest_manifest.json`), and the crown ages and the pair-level
  values of the screen are archived in `research/divergence/results/`;
  `gled_cldf.py` writes the GLED tables the screen reads from the GLED
  release.
- **Unclassified nodes.** `genera_summary.tsv` has a column
  `unclassified_node`, 1 for the 26 genera on Glottolog "Unclassified" nodes,
  which are residual groups rather than subgroups.
- **Names.** Two renamings are withdrawn, as they broke the naming policy:
  Sara-Bongo-Bagirmi (not Bongo-Bagirmi: the WALS genus also includes Birri)
  and North Borneo Malayo-Polynesian (not North Borneo, which in the
  literature is a smaller group); 30 genera are renamed.
- **Calibration curve.** `params.json` keeps the curve at every grid value.
- `scripts/dravidian_map.py` takes a width and a title size, and keeps its
  labels inside the panels.

## 1.1.0 — 2026-11-05

- **Cognate judgements.** The expert cognate judgements on the 40 ASJP core
  concepts from the twelve datasets used to select the word distance are now
  included in `research/divergence/cognates/`, each file under the licence of
  its source, so that the selection screen can be rerun. The released genera
  are unchanged.

## 1.0.0 — 2026-11-05

First public release, described in a data descriptor (MDPI *Data*, in
preparation).

- **The rule.** On a rooted language tree, a genus is the largest clade whose
  divergence does not exceed a threshold δ (`docs/definition.md`).
  `glottogenera.tree` applies it to any tree, read from Newick or from a table
  of parents, with node values from any distance between languages or
  supplied directly (such as ages). It also calibrates δ against a reference
  partition, and estimates UPGMA and neighbour-joining trees.
- **The release** for Glottolog 5.3: 7,674 in-scope languages in 1,190
  genera. Crown divergence comes from PMI alignment of the ASJP 21 wordlists
  (sound correspondences learned with ASymCat 0.9 and FreqProb 0.9), and
  δ = 0.81 is calibrated against the WALS genera, averaged over 49 families.
  Every genus is released with its crown divergence, margins and bootstrap
  stability, in `data/` (TSV) and `cldf/` (CLDF StructureDataset).
- **Curated names** for 32 genera whose Glottolog node names are bookkeeping
  labels, coinages or misleading (`data/genus_names.tsv`,
  `docs/genus-names.md`).
- **Web explorer** (<https://glottogenera.tresoldi.org>): genera, languages
  and families, maps with genus areas, recutting at any threshold,
  comparison with WALS, CSV and GeoJSON export.
- **Validation** scripts and results in `research/divergence/`: the choice of
  word distance against expert cognate judgements and dated phylogenies,
  robustness to another distance or lexical source, sensitivity to the
  inputs, and genera on estimated trees.
