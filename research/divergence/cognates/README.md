# Expert cognate judgements on 40 core concepts, from twelve datasets

The expert cognate judgements used to select the word distance (the
selection screen of the data descriptor, Table 5): the rows of twelve
published cognate datasets on the 40 core concepts of the Automated
Similarity Judgment Program (ASJP), as aggregated by the author.
`compare_measures.py` reads this directory (or `COGNATE_DIR`).

**Licences differ from the rest of the repository**: each file keeps the
licence of its source, listed below.

## Files

One CSV per dataset (UTF-8, comma-separated), with the columns:

| column | description |
|---|---|
| `cognate_source` | the dataset (file name) |
| `doculect` | identifier of the doculect in the aggregate |
| `Glottocode` | Glottolog code of the doculect |
| `concept` | one of the 40 ASJP core concepts, as a short label (e.g. `bod-ear`) |
| `Concepticon_ID` | the Concepticon concept set of `concept` |
| `Cognacy` | the dataset's cognate set, prefixed with the dataset name |
| `source_language_id` | the language identifier in the source dataset |

Only judgements made by experts are included; a form may belong to more than
one cognate set. The forms themselves are not included and can be obtained
from the sources.

## Sources and licences

Each file keeps the licence of its source. Please cite the sources as well as
glottogenera.

| file | source | version | licence | doculects |
|---|---|---|---|---:|
| `iecor.csv` | Heggarty, Anderson & Scarborough, IE-CoR; https://github.com/lexibank/iecor | commit 700b635a04 | CC BY 4.0 | 161 |
| `abvd2026.csv` | Greenhill, Blust & Gray, ABVD; https://github.com/lexibank/abvd | commit 2af9f4ef6f | CC BY 4.0 | 454 |
| `acd.csv` | Blust, Trussel & Smith, ACD; https://github.com/lexibank/acd | v2.0 | CC BY 4.0 | 72 |
| `grollemundbantu.csv` | Grollemund et al. 2015; https://github.com/lexibank/grollemundbantu | v1.1 | CC BY-NC 4.0 | 216 |
| `bowernpny.csv` | Bowern & Atkinson 2012; https://github.com/lexibank/bowernpny | v4.1 | CC BY 4.0 | 163 |
| `tuled.csv` | Ferraz Gerardi et al., TuLeD; https://github.com/tupian-language-resources/tuled | commit 91c20e199a | CC BY 4.0 | 64 |
| `uralex.csv` | Syrjänen et al., UraLex; https://github.com/tresoldi/uralex | commit 6b3667f770 | CC BY 4.0 | 29 |
| `sagartst.csv` | Sagart et al. 2019; https://github.com/lexibank/sagartst | v2.1 | CC BY 4.0 | 39 |
| `kogansemitic.csv` | Kogan 2015; https://github.com/lingulist/semitic-reconstruction | commit 3b2dba0514 | none stated | 42 |
| `hruschkaturkic.csv` | Hruschka et al. 2015; https://github.com/lexibank/hruschkaturkic | v1.0 | CC BY-NC 4.0 | 20 |
| `dravlex.csv` | Kolipakam et al., DravLex; https://github.com/lexibank/dravlex | commit 37578075e5 | CC BY 4.0 | 17 |
| `peirosaustroasiatic.csv` | Peiros 2004; https://github.com/lexibank/peirosaustroasiatic | v1.1 | CC BY 4.0 | 51 |

The selection of rows and the added columns are released under CC BY 4.0;
the judgements remain under the licences above.
