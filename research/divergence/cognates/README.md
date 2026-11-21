# Expert cognate judgements on 40 core concepts, from fifteen datasets

The expert cognate judgements used to select the word distance (the
selection screen of the data descriptor, Table 8): the rows of fifteen
published cognate datasets on the 40 core concepts of the Automated
Similarity Judgment Program (ASJP), as aggregated by the author, one file per
source dataset (the dataset the cognate sets come from).
`compare_measures.py` reads this directory (or `COGNATE_DIR`).

**Licences differ from the rest of the repository**: each file keeps the
licence of its source, listed below.

## Files

One CSV per dataset (UTF-8, comma-separated), with the columns:

| column | description |
|---|---|
| `cognate_source` | the source dataset (file name) |
| `doculect` | identifier of the doculect in the aggregate |
| `Glottocode` | Glottolog code of the doculect |
| `concept` | one of the 40 ASJP core concepts, as a short label (e.g. `bod-ear`) |
| `Concepticon_ID` | the Concepticon concept set of `concept` |
| `Cognacy` | the dataset's cognate set, prefixed with the dataset name; several sets are separated by `;` |
| `source_language_id` | the language identifier in the source dataset |

Only judgements made by experts are included. A form may belong to several
cognate sets (`;`), and two forms are counted as cognate when they share one.
The forms themselves are not included and can be obtained from the sources.

## Sources and licences

Each file keeps the licence of its source. Please cite the sources as well as
glottogenera.

| file | source | version | licence | doculects | rows |
|---|---|---|---|---:|---:|
| `abvd2026.csv` | Greenhill, Blust & Gray, ABVD; https://github.com/lexibank/abvd | commit 81748db0c5 | CC BY 4.0 | 453 | 18,461 |
| `abvdphilippines.csv` | Greenhill, Blust & Gray, ABVD, Philippine languages; https://github.com/lexibank/abvdphilippines | v1.0 | CC BY 4.0 | 71 | 3,527 |
| `bowernpny.csv` | Bowern & Atkinson 2012, Pama-Nyungan; https://github.com/lexibank/bowernpny | v4.1 | CC BY 4.0 | 162 | 5,017 |
| `dravlex.csv` | Kolipakam et al., DravLex; https://github.com/lexibank/dravlex | commit 37578075e5 | CC BY 4.0 | 16 | 575 |
| `dunnaslian.csv` | Dunn, Kruspe & Burenhult 2013, Aslian; https://github.com/lexibank/dunnaslian | v1.1 | CC BY 4.0 | 7 | 365 |
| `gerarditupi.csv` | Ferraz Gerardi & Reichert 2021, Tupí-Guaraní; https://github.com/lexibank/gerarditupi | v2.1 | CC BY 4.0 | 12 | 333 |
| `grollemundbantu.csv` | Grollemund et al. 2015, Bantu; https://github.com/lexibank/grollemundbantu | v1.1 | CC BY-NC 4.0 | 215 | 8,078 |
| `iecor.csv` | Heggarty, Anderson & Scarborough, IE-CoR; https://github.com/lexibank/iecor | commit 700b635a04 | CC BY 4.0 | 160 | 5,250 |
| `kesslersignificance.csv` | Kessler 2001, cross-family lists; https://github.com/sequencecomparison/kesslersignificance | v1.1 | CC BY 4.0 | 1 | 40 |
| `nagarajakhasian.csv` | Nagaraja, Sidwell & Greenhill 2013, Khasian; https://github.com/lexibank/nagarajakhasian | v1.1 | CC BY 4.0 | 2 | 68 |
| `peirosaustroasiatic.csv` | Peiros 2004, Austroasiatic; https://github.com/lexibank/peirosaustroasiatic | v1.1 | CC BY 4.0 | 41 | 1,803 |
| `sagartst.csv` | Sagart et al. 2019, Sino-Tibetan; https://github.com/lexibank/sagartst | v2.1 | CC BY 4.0 | 38 | 1,445 |
| `savelyevturkic.csv` | Savelyev & Robbeets 2020, Turkic; https://github.com/lexibank/savelyevturkic | v2.1 | CC BY 4.0 | 18 | 656 |
| `tuled.csv` | Ferraz Gerardi et al., TuLeD; https://github.com/tupian-language-resources/tuled | commit 91c20e199a | CC BY 4.0 | 61 | 1,581 |
| `uralex.csv` | Syrjänen et al., UraLex; https://github.com/tresoldi/uralex | commit 6b3667f770 | CC BY 4.0 | 28 | 1,150 |

## Distribution change for the next release

The historical v1.3.0 analysis used sixteen sources. The next distribution
includes fifteen: fourteen CC BY 4.0 and Grollemund Bantu under CC BY-NC 4.0.
Its upstream v1.1 licence is copied in `LICENSE-grollemundbantu`; the aggregate
judgements retain the source attribution and contain no lexical forms.

Kogan Semitic (`kogansemitic.csv`, previously 928 rows) is omitted because
permission for redistribution has not been established. The stated upstream
repository and licence could not be retrieved during the 2026-11-21 audit.
The 66 Kogan-derived pair rows are also omitted from each screen-pair export.
Historical aggregate analysis summaries remain labelled as v1.3.0 evidence;
they must not be described as a fresh fifteen-source recomputation.
Reproducing that historical input requires a separately obtained lawful copy,
provided through `COGNATE_DIR`; it is not automatically fetched.
