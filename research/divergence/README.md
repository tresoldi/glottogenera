# Validation of the released genera

The scripts behind the validation reported in the data descriptor: the choice
of word distance, the robustness of the partition, its sensitivity to the
inputs, and the genera on trees estimated from the same distances. They are
not part of the release pipeline, and their results are committed in
`results/`, which is what the manuscript's tables read.

| script | writes | reported as |
|---|---|---|
| `fetch_phlorest.py OUT/phlorest` | the dated Phlorest trees (summary trees and tip metadata) | input of `ages.py` |
| `ages.py OUT/phlorest OUT` | `ages.json`: crown ages of Glottolog nodes in the dated trees | input of the screen |
| `compare_sources.py OUT` | `sources.json`, `sources_meta.json`; `source_values.pkl` | Table 5 (selection screen), the residual variance of log age between families (Limitations) |
| `measure_tests.py PKL BASE CANDIDATES…` | paired and blocked bootstrap of differences between distances | `source_tests.txt` (intervals in Validation) |
| `heldout_training.py OUT OUT/source_values.pkl` | `heldout_training.json`; `heldout_values.pkl` | with `measure_tests.py`, `heldout_tests.txt` (correspondences learned without the evaluated family) |
| `source_agreement.py OUT` | `source_agreement.json` | Table 7 (another distance or lexical source) |
| `input_sensitivity.py OUT 8` | `input_sensitivity.json` | Uncertainty (relearned correspondences, other doculects) |
| `estimated_trees.py OUT` | `estimated_trees.json`, `estimated_trees.nwk` | Table 8 (UPGMA and neighbour-joining trees) |

Helper modules: `compare_measures.py` (the cognate and dated-tree evidence and
its scoring), `measures.py` (alternative word distances and the GLED reader),
`pmi_variants.py` (the PMI estimators compared in the screen),
`ldnd_reference.py` (standard LDND) and `newick.py` (a Newick reader forked
from python-newick, under the Apache License 2.0 in `LICENSE-newick`, used by
`ages.py`).

The standard LDND baseline appears in the results as `asjp:ldnd (released)`,
the name it had when an earlier version of the package used it.

## Running

From the repository root, after `make fetch`, with the research extra
(`pip install -e ".[research]"`) and seqsim 0.4.0, which is not on PyPI
(`pip install git+https://github.com/tresoldi/seqsim@4a5d72cab887cbc2fa4c7dc18f79b530919bc5cc`):

```bash
PY=python; R=research/divergence; OUT=/tmp/divergence; mkdir -p $OUT/phlorest
$PY $R/fetch_phlorest.py $OUT/phlorest
$PY $R/ages.py $OUT/phlorest $OUT
$PY $R/compare_sources.py $OUT
$PY $R/measure_tests.py $OUT/source_values.pkl "asjp:ldnd (released)" \
    asjp:pmi-asymcat-smoothed gled:pmi-asymcat-smoothed asjp:pmi > $OUT/source_tests.txt
$PY $R/measure_tests.py $OUT/source_values.pkl gled:pmi-asymcat-smoothed \
    asjp:pmi-asymcat-smoothed >> $OUT/source_tests.txt
$PY $R/heldout_training.py $OUT $OUT/source_values.pkl
$PY $R/measure_tests.py $OUT/heldout_values.pkl "asjp:pmi (all families)" "asjp:pmi (family held out)" > $OUT/heldout_tests.txt
$PY $R/measure_tests.py $OUT/heldout_values.pkl "asjp:ldnd (released)" "asjp:pmi (family held out)" >> $OUT/heldout_tests.txt
$PY $R/source_agreement.py $OUT
$PY $R/input_sensitivity.py $OUT 8
$PY $R/estimated_trees.py $OUT          # about 30 minutes
```

## External inputs

- **Expert cognate judgements**: the expert judgements of the twelve cognate
  datasets on the 40 core concepts, one CSV per dataset, as deposited with the
  data descriptor (Zenodo, doi:[TO BE ASSIGNED]); set `COGNATE_DIR` to the
  directory (default `cognates/`).
- **GLED** (Global Lexical Database, CLDF release v1.0, r20221127.1,
  doi:10.5281/zenodo.7368116); set `GLED_CLDF` to its `cldf/`
  directory (default `gled/cldf`).
- **Phlorest**: `fetch_phlorest.py` downloads the current version of every
  Phlorest repository, so a later run may see updated trees.

The released distance itself is the package's (`glottogenera.divergence`
with `glottogenera.pmi`), and the scripts use it through the package.
