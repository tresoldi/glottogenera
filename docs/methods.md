# Methods — genera defined by a divergence threshold

A summary of how `glottogenera divergence` builds the released partition. The
formal definition, with the propositions that genera are complete clades and
that the partitions nest, is in [`definition.md`](definition.md); the
validation scripts and their results are in
[`../research/divergence/`](../research/divergence/).

## The unit

A **genus** approximates Dryer's (1989) genus: a genealogical group comparable to
the major branches of Indo-European (Germanic, Romance, Slavic, Indo-Aryan,
Iranian, …), with a time depth of no more than about 3,500–4,000 years.
Operationally, for any rooted language tree and any divergence of its clades:

> A **genus** is the largest clade whose divergence does not exceed a threshold
> δ; a clade without a measurement takes the largest value of its sub-clades,
> and one with none anywhere within it counts as not exceeding δ.

The tree can be an expert classification or one estimated from data (UPGMA,
neighbour-joining, a Bayesian consensus tree), and the divergence the mean of
any distance between languages on different branches of the clade, or a value
of the clade itself, such as its age; `glottogenera.tree` implements the rule.
The release is one instance: the Glottolog 5.3 tree, PMI-alignment distances
on ASJP, and δ calibrated so that the genera agree best with those of WALS on
average across language families.

Every genus is a complete Glottolog clade restricted to the in-scope languages:
its id is that node's Glottocode and its name the node's Glottolog name, or a
curated name (see Names below).

## Scope

Glottolog 5.3 nodes with `level == language`, excluding non-genetic categories
(Bookkeeping, Artificial Language, Sign Language, Unattested, Unclassifiable,
Speech Register, Mixed Language, Pidgin): **7,674 languages**. Extinct but
attested languages (Latin, Sanskrit, …) are kept. No in-scope language lies
below another in the classification, which the propositions of the definition
assume; `params.json` records the check.

## Construction

**Wordlists.** One ASJP doculect per language, the one with most of the 40
core concepts (ties: smallest doculect ID), loans removed; languages need at
least 20 core concepts.

**Word distance.** Words are aligned (Needleman–Wunsch, linear gap penalty 2.5)
with substitution scores for ASJP symbols learned from the data after Jäger
(2013): same-concept words of 30,000 same-family language pairs are aligned,
close alignments are kept as probable cognates, and the association between
aligned symbols is estimated as ASymCat's smoothed PMI, with FreqProb's add-one
(Laplace) estimator (averaged over both directions); three iterations. The word distance is
`1 - 2 s(x,y) / (s(x,x) + s(y,y))`.

**Language distance.** The mean word distance over shared concepts (synonyms
averaged) divided by the mean over 60 sampled pairs of different concepts, as
LDND normalizes edit distance; at least 20 shared concepts.

**Crown divergence and the cut.** For every node, D is the mean language
distance over pairs on different child branches (all pairs, or 200 sampled).
A measured node uses its own D; an unmeasured node takes the largest value
among its children. A language's genus is the highest node on its path whose
value is at most δ; below a node above δ, an unmeasured clade or the language
itself is the genus; a family without any measurement is one genus. Every
genus is a complete clade and the partitions nest as δ varies.

**Calibration.** δ maximizes the mean ARI against WALS genera over the
Glottolog families whose WALS-labelled languages fall into at least two WALS
genera ("Creoles and Pidgins" excluded), averaged over a window of ±0.02 on a
0.001 grid; the median of tied values is used. Averaging over families keeps
the largest WALS genera (Bantoid, Oceanic) from dominating, as they do pooled
ARI; using all families keeps a single family's few deep nodes from fixing δ,
as Indo-European alone did. The window keeps δ from hinging on single node
crossings: unsmoothed, the objective is a jagged step function, and families
with two WALS genera switch between ARI 0 and 1. `params.json` records the
per-family optima, family resampling, leave-one-family-out choices,
alternative criteria (which give 0.807–0.829, or more for pooled ARI and with
single-genus families) and a permutation null.

**Uncertainty.** A bootstrap (200 replicates) resamples the concepts and, at
every node, the language pairs, recomputes crown divergence and recuts, with δ
recalibrated (`stability`) and with δ fixed (`stability_fixed_delta`). Doculect
choice and the learned correspondences are held fixed there, and varied
separately in `research/divergence/input_sensitivity.py`; the classification is
taken as given.

**Why PMI alignment on ASJP.** Against expert cognate judgements from twelve
datasets and crown ages from 18 dated phylogenies, PMI alignment tracked
lexical change better than LDND and every seqsim distance, on ASJP and on GLED
alike; ASJP was preferred for its coverage. See
[`../research/divergence/`](../research/divergence/).

**Names.** A genus takes the name of its Glottolog node unless
`src/glottogenera/data/genus_names.tsv` gives a better one: without Glottolog's
bookkeeping labels (such as "linkage"), the WALS genus name when the genus
coincides with a WALS genus, the established name in the literature, or a
transparent name where the node's name is misleading (e.g. an "Unclassified"
node, which is not a subgroup). Each row records its criterion, confidence,
rationale and sources, and [`genus-names.md`](genus-names.md) explains the
criteria and lists the cases considered. The names are applied after the cut and keyed by node,
so `glottogenera.genus_name()` also names the genera at other thresholds. The
original is kept in `genus_glottolog_name`.

## Known limitations

- Divergence is not on a perfectly common scale across families: the same
  distance corresponds to different amounts of cognate replacement and
  different ages in different families. No correction is attempted.
- Each language is represented by at most 40 concepts from one doculect.
- Genera reached without measurement (`unmeasured-clade`, `single-language`,
  `unmeasured-family`, `isolate`) rest on the Glottolog classification alone.
- The thresholds that best fit single families differ widely, so δ is a
  compromise between families; use the `stability` scores and report
  sensitivity to δ.
- The partition is tied to Glottolog 5.3 and ASJP 21.
