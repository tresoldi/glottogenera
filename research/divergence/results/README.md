# Validation results and licensing

`screen_pairs.csv.gz` and `screen_pairs_all.csv.gz` contain pair-level
validation evidence, including expert cognate distances derived from
Grollemund et al. (2015). These two files are distributed under **CC BY-NC
4.0**, not the primary genus dataset's CC BY 4.0 licence. The licence is in
`LICENSE-screen-pairs`; source attribution and versions are in
`../cognates/README.md`, and each cognate row identifies its source dataset.

The Bantu input is pinned to lexibank/grollemundbantu v1.1; both its LICENSE
and metadata.json explicitly specify CC BY-NC 4.0:
https://github.com/lexibank/grollemundbantu/tree/v1.1

The Kogan source and its 66 pair-level rows in each export are omitted from
the next distribution because redistribution permission is not established.
`export_screen.py` omits them by default even when reading historical cached
pickles. Its explicit `--include-undistributed` option is for private
historical reproduction with separately obtained inputs, not release building.

The aggregate JSON summaries and statistical test reports preserve the
historical v1.3.0 sixteen-source analysis. Their numeric results have not been
silently replaced by a fifteen-source rerun. The independent Kitchen dated
Semitic tree is a different source and is not removed with the Kogan cognate
input. `screen_nodes.csv` remains the historical dated-node evidence.
`screen_provenance.json` records the historical and redistributed aggregate
pair counts separately, so manuscript generation does not mix the sanitized
export's sample counts with the historical correlations. It contains no
Kogan language-pair records. A new analysis must regenerate this provenance
alongside its aggregate results.

The source audit includes a separate sensitivity calculation excluding Kogan
pairs. The primary genus assignments, crown values and bootstrap scores use
Glottolog, ASJP and WALS, not these validation cognate judgements, and remain
under CC BY 4.0. Source code remains MIT except the vendored Newick reader.
