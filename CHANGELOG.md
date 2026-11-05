# Changelog

## 1.0.0 — unreleased

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
