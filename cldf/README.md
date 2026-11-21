# Glottogenera as a CLDF dataset

The released genera as a [CLDF](https://cldf.clld.org/) StructureDataset,
built from the tables in `data/` by `scripts/build_cldf.py` (`make cldf`) and
validated with pycldf. Languages are identified by their Glottocodes, the join
key to any other CLDF dataset.

| file | contents |
|---|---|
| `languages.csv` | the 7,674 in-scope languages of Glottolog 5.3, with coordinates, ISO 639-3 code, macroarea, family, ASJP candidate and eligibility, and precomputed genus ID/name at δ = 0.75 |
| `parameters.csv` | one parameter, `genus`: the genus at the released threshold δ = 0.81 |
| `codes.csv` | the 1,190 genera, with the columns of `data/genera_summary.tsv` (size, method, crown divergence, margins, stability) |
| `values.csv` | the genus of every language (`Code_ID` is the Glottocode of the genus node) and how it was reached (`Method`) |
| `nodes.csv` | the crown divergence of every measured Glottolog node; with the Glottolog classification it gives the genera at any threshold |
| `sources.bib` | Glottolog, ASJP and WALS |
| `StructureDataset-metadata.json` | the CLDF metadata |

The columns are described in [`../data/README.md`](../data/README.md).
Licence: CC BY 4.0 (see [`../data/LICENSE`](../data/LICENSE)).

`Has_Usable_Wordlist` and `Has_Above_Threshold_Subclade` are CSVW booleans.
The CodeTable's `Macroareas` is a list with `;` as separator. The custom
LanguageTable fields `Genus_075_ID` and `Genus_075_Name` carry the sensitivity
partition; those IDs are Glottocodes of classification nodes and are not
foreign keys into the reference CodeTable, which remains the δ = 0.81 partition.
