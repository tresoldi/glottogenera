# The released dataset

Genera for the 7,674 in-scope languages of Glottolog 5.3: the general rule (a
divergence threshold on a language tree) applied to the Glottolog tree, with
crown divergence from PMI alignment of the ASJP wordlists and δ = 0.81 (see
[`../docs/definition.md`](../docs/definition.md) and
[`../docs/methods.md`](../docs/methods.md)). Every genus is a complete
Glottolog clade, identified by the Glottocode of its node.

The tables are rebuilt by `make all` (the curated names are kept in the
package and copied here by `make bundle`); the same data are in
[`../cldf/`](../cldf/) as a CLDF StructureDataset. Licensed CC BY 4.0 (see
[`LICENSE`](LICENSE), and [`../docs/sources.md`](../docs/sources.md) for
upstream attribution).

| file | rows | contents |
|---|---:|---|
| `genera.tsv` | 7,674 | one row per language: its genus and how it was reached |
| `genera_summary.tsv` | 1,190 | one row per genus: size, crown divergence, margins, stability |
| `nodes.tsv` | 3,609 | one row per measured Glottolog node: crown divergence |
| `genus_names.tsv` | 32 | curated genus names replacing Glottolog node names |
| `params.json` | – | source versions, parameters, calibration and evaluation |
| `report.md` | – | a readable summary of the calibration, uncertainty and agreement |

## `genera.tsv`

| column | description |
|---|---|
| `glottocode` | Glottolog identifier of the language |
| `name` | Glottolog name of the language |
| `family` | name of its top-level Glottolog family |
| `genus_id` | Glottocode of the Glottolog node that defines its genus |
| `genus_name` | the curated name from `genus_names.tsv` if there is one, otherwise the Glottolog name of the node |
| `genus_glottolog_name` | Glottolog name of the node |
| `method` | how the genus was reached: `divergence` (the highest clade whose cut value is at most δ), `unmeasured-clade` (a clade without measurements below a node that exceeds δ), `single-language` (the language itself, below a node that exceeds δ), `unmeasured-family` (a family without any measurement, kept whole) or `isolate` |

## `genera_summary.tsv`

| column | description |
|---|---|
| `genus_id`, `genus_name`, `genus_glottolog_name`, `family` | as above |
| `n_languages` | in-scope languages in the genus |
| `method` | as above |
| `crown_divergence` | the genus node's own crown divergence; blank if the node is not measured |
| `crown_pairs` | language pairs behind `crown_divergence` |
| `cut_value` | the value the cut used: `crown_divergence`, or for an unmeasured node the largest value among its children |
| `upper_value` | the smallest cut value among the node's ancestors |
| `margin_below` | δ minus `cut_value` |
| `margin_above` | `upper_value` minus δ |
| `stability` | share of 200 bootstrap replicates (resampling concepts and language pairs, δ recalibrated in each) in which the genus reappears with exactly its members |
| `stability_fixed_delta` | the same with δ fixed at 0.81 |
| `unclassified_node` | 1 if the genus node is a Glottolog "Unclassified" node, which collects languages not placed in a subgroup: a residual group, not a subgroup |

A genus cut by divergence exists for every δ from `cut_value` up to, not
including, `upper_value`; `glottogenera.genera_at(delta)` recuts at any δ.

## `nodes.tsv`

One row per measured Glottolog node: `node`, `name`, `family`, `depth` (levels
below the family root), `crown_divergence`, `crown_pairs`, `cut_value`.
Because the partitions nest, any threshold can be applied to it directly.

## `genus_names.tsv`

The genera whose Glottolog node name is replaced (see
[`../docs/genus-names.md`](../docs/genus-names.md)): `genus_id`,
`glottolog_name`, `name`, `criterion` (one or more of `label`, `wals`,
`literature` and `misleading`, separated by `;`), `confidence` (`high`,
`medium` or `low`), `rationale` and `sources`. The names are applied after
the genera are computed; `genus_glottolog_name` keeps the original, and
`glottogenera.genus_name()` names the genera at any threshold.

## `params.json` and `report.md`

`params.json` holds the pinned source versions (`sources`), the check that no
in-scope language lies below another (`hierarchy`), and in its `divergence`
block the parameters of the word distance, the calibration (curve, per-family
optima, family resampling, leave-one-family-out), the bootstrap, and the
evaluation against WALS with fixed-depth baselines. `report.md` summarizes
them.

## `sources/` (not committed)

The WALS and ASJP caches, fetched at pinned versions by `glottogenera fetch`.
They carry their own upstream licences and are not redistributed here.
