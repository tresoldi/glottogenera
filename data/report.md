# Glottogenera: the release for Glottolog 5.3

Genera defined by a divergence threshold: the highest Glottolog clades whose crown divergence (normalized PMI alignment distance over the 40 ASJP core concepts, one doculect per language) does not exceed delta. See `docs/definition.md` and `docs/methods.md`.

- **delta = 0.81**: maximizes the mean ARI against WALS, averaged over a window of +-0.02, over 49 families with at least two WALS genera (1704 languages; mean ARI 0.635). Resampling families: delta 0.73/0.81/0.825 (5th/50th/95th percentiles); leaving one family out: {'0.808': 2, '0.809': 1, '0.81': 41, '0.813': 2, '0.814': 1, '0.817': 2}.
  At delta = 0.73: 1728 genera, 2962 languages in a different genus.
  At delta = 0.825: 1114 genera, 573 languages in a different genus.
- Other criteria: pooled ARI over all WALS languages picks delta = 0.864 (817 genera); Indo-European alone picks 0.767 (tied 0.728–0.806).
- 1190 genera over 7674 languages; 3609 nodes measured from 63954 language pairs (1304 from a single pair).
- Methods (languages): divergence 6944, isolate 183, single-language 273, unmeasured-clade 198, unmeasured-family 76.
- Bootstrap over core concepts and each node's language pairs (200 replicates): delta 0.749/0.795/0.831; mean language stability 0.774 with delta recalibrated, 0.809 with delta fixed.
- All WALS languages (2233): mean family ARI 0.654, pooled ARI 0.513, completeness 0.865, purity 0.980, WALS genera contained 68.4%.
- Outside Indo-European (2105): mean family ARI 0.647, pooled ARI 0.477, completeness 0.862, purity 0.980, WALS genera contained 67.8%.
- Crown divergence of measured multi-language genera: IQR 0.175.
