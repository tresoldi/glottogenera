# Sources, versions, and licensing

Every input of the release is either vendored in this repository at a fixed
version or fetched at a pinned reference, so the pipeline (`make all`) is
reproducible offline after one `glottogenera fetch`. Building the web
explorer's data also downloads the Natural Earth outlines (below).

## Vendored inputs (committed)

| source | where | version | license |
|--------|-------|---------|---------|
| **Glottolog** classification dump | `src/glottogenera/data/glottolog.v5.3-cldf-g072ca0d041.tsv` | release tag v5.3 (tag object `0e0d80653e4087cd4ded6b5664ac5dc06426c08b`, commit `eb7d58221bea745a21cb7b96582118e990a295c2`); CLDF commit `072ca0d0410039fb8b779be8fc165bac575d2cda`; doi:10.5281/zenodo.18840935 | CC-BY-4.0 |

## Fetched, pinned caches (not committed; `glottogenera fetch`)

| source | cache file | pinned reference | license |
|--------|-----------|------------------|---------|
| **WALS** CLDF `languages.csv` (Dryer genera) | `data/sources/wals_languages.csv` | [cldf-datasets/wals](https://github.com/cldf-datasets/wals) tag `v2020.1`; doi:10.5281/zenodo.4683137 | CC-BY-4.0 |
| **ASJP** CLDF `languages.csv` + `forms.csv` | `data/sources/asjp_*.csv` | [lexibank/asjp](https://github.com/lexibank/asjp) commit `0127953…` (tag `v21`); doi:10.5281/zenodo.16736409 | CC-BY-4.0 |

The pins live in `src/glottogenera/config.py` (`WALS_REF`, `ASJP_REF`); bump
them deliberately and re-run the pipeline.

The Glottolog compact dump is regenerated separately with `make
update-glottolog`. Its release, commits and source-file checksums are pinned in
`src/glottogenera/config.py` and `scripts/update_glottolog.py`; the updater is
also subject to the pipeline's 2 GiB memory ceiling.

## How each source is used

- **Glottolog** — the classification backbone: scope (which nodes are
  languages), lineages, names and stable ids for genera.
- **ASJP** — the 40-concept wordlists on which crown divergence is measured.
- **WALS** — Dryer's genus labels: δ is calibrated on agreement with them,
  averaged over language families, and they are the reference for agreement.
  Not copied into the output.

The web explorer draws its basemap and clips the genus areas with the
[Natural Earth](https://www.naturalearthdata.com/) 1:50m countries, v5.1.2
(public domain), downloaded by `scripts/build_web.py`.

The validation of the word distance (not part of the pipeline; see
[`../research/divergence/README.md`](../research/divergence/README.md)) also
used GLED (CLDF release v1.0, r20221127.1, doi:10.5281/zenodo.7368116), the
expert cognate judgements of twelve datasets (in
[`../research/divergence/cognates/`](../research/divergence/cognates/), each
under the licence of its source), and dated phylogenies from Phlorest. The research scripts include a Newick
reader forked from [python-newick](https://github.com/dlce-eva/python-newick),
which stays under the Apache License 2.0
([`../research/divergence/LICENSE-newick`](../research/divergence/LICENSE-newick)).

## Citations

This list covers the sources of the data.

- Bell, Alan (1978). Language samples. In Greenberg, Joseph H., Ferguson,
  Charles A. & Moravcsik, Edith A. (eds.), *Universals of Human Language*,
  vol. 1: *Method and Theory*, 123–156.
  Stanford: Stanford University Press.
- Dryer, Matthew S. (1989). Large linguistic areas and language sampling.
  *Studies in Language* 13(2): 257–292.
- Dryer, Matthew S. & Haspelmath, Martin (eds.) (2013). *The World Atlas of
  Language Structures Online* (WALS). Leipzig: Max Planck Institute for
  Evolutionary Anthropology. CLDF dataset v2020.1,
  doi:10.5281/zenodo.4683137.
- Hammarström, Harald, Forkel, Robert, Haspelmath, Martin & Bank, Sebastian
  (2026). *Glottolog 5.3*. Leipzig: Max Planck Institute for Evolutionary
  Anthropology. doi:10.5281/zenodo.18840935.
- Jäger, Gerhard (2018). Global-scale phylogenetic linguistic inference from
  lexical resources. *Scientific Data* 5: 180189. doi:10.1038/sdata.2018.189.
- Miestamo, Matti, Bakker, Dik & Arppe, Antti (2016). Sampling for variety.
  *Linguistic Typology* 20(2): 233–296. doi:10.1515/lingty-2016-0006.
- Tresoldi, Tiago (2023). A Global Lexical Database (GLED) for Computational
  Historical Linguistics. *Journal of Open Humanities Data* 9: 2.
  doi:10.5334/johd.96.
- Wichmann, Søren, Holman, Eric W., Brown, Cecil H., Dryer, Matthew S. & Ran,
  Qibin (eds.) (2025). *The ASJP Database* (version 21). CLDF dataset via
  [lexibank/asjp](https://github.com/lexibank/asjp) v21,
  doi:10.5281/zenodo.16736409.

## Licensing of this repository's outputs

The dataset (`data/`, `cldf/`, the copies and the Glottolog dump under
`src/glottogenera/data/`, and `web/data/`) is released under **CC-BY-4.0**
(`data/LICENSE`), as required by Glottolog's CC-BY-4.0 license, and
compatible with every upstream license above. The code is **MIT**
(`LICENSE`), except the Newick reader in `research/divergence/newick.py`
(Apache-2.0) and the libraries bundled in `web/vendor/` (their own licences,
`web/vendor/LICENSES.txt`).
