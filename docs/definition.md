# The definition of the genera

The formal definition of the genera, the word distance and the calibration.
It is the text of the corresponding Methods sections of the data descriptor;
keep the two in step. Citation keys refer to `definition.bib`.

## Genera on a rooted tree

The rule takes three inputs: a rooted tree whose leaves are the languages, a divergence for its nodes, and a threshold $\delta$.

For a node $u$ whose languages with data lie on at least two child branches, let $\Pi(u)$ be the pairs of such languages on different branches, or a uniform sample of 200 of them when there are more. Given a distance $\Delta$ between languages, the crown divergence $D(u)$ is the mean of $\Delta$ over the pairs in $\Pi(u)$ for which it is defined, and $u$ is *measured* when there is at least one. A quantity of the node itself, such as its age in a dated tree, can take the place of $D(u)$. The value on which the cut is made is

$$
c(u) =
\begin{cases}
D(u) & \text{if } u \text{ is measured},\\
\max\{c(w) : w \text{ a child of } u,\ c(w) \text{ defined}\} & \text{otherwise,}
\end{cases}
$$

which is undefined when no node at or below $u$ is measured. Many nodes rest on few pairs, so a measured node is judged by its own $D(u)$ rather than by the largest value below it, which would let a single noisy descendant force a split.

Call a node $v$ *final* at threshold $\delta$ when $c(v)$ is undefined, when $c(v) \le \delta$, or when $v$ is a language. On the path $v_0(\ell), \ldots, v_k(\ell) = \ell$ from the root of its tree to a language $\ell$, let $j$ be the position of the first final node, which exists because $\ell$ itself is final. The genus of $\ell$ is

$$
h_\delta(\ell) = v_j(\ell).
$$

It is cut by divergence when $c(v_j(\ell)) \le \delta$ (`divergence`). Otherwise it is an unmeasured clade below a node that exceeds $\delta$ (`unmeasured-clade`), the language itself (`single-language`), or, when $j = 0$, a whole tree without any measurement, kept as one genus (`unmeasured-family`, or `isolate` for a tree of one language). Writing $\mathcal{L}(u)$ for the languages at or below $u$, two properties follow for any tree or forest under one condition, which holds whenever the languages are the leaves and which Glottolog 5.3 satisfies: no language lies below another language.

**Proposition 1** (genera are complete clades). Every class of $h_\delta$ is $\mathcal{L}(u)$ for its node $u$.

*Proof.* Whether a node is final depends on the node alone. Let $u = h_\delta(\ell)$. Every $\ell' \in \mathcal{L}(u)$ shares the nodes of $\ell$ above $u$, none of them final, and reaches $u$, which is final; so $h_\delta(\ell') = u$. Conversely, $h_\delta(\ell') = u$ places $\ell'$ at or below $u$. If $u$ is a language, $\mathcal{L}(u) = \{u\}$ by the condition. $\square$

**Proposition 2** (the partitions nest). For $\delta < \delta'$, every genus at $\delta$ lies inside a single genus at $\delta'$.

*Proof.* Whether $c(v)$ is defined, and whether $v$ is a language, do not depend on the threshold, and $c(v) \le \delta$ implies $c(v) \le \delta'$, so every node final at $\delta$ is final at $\delta'$, and the first final node on a path at $\delta'$ lies at or above the one at $\delta$. If $h_\delta(\ell_1) = h_\delta(\ell_2) = u$, then $\ell_2 \in \mathcal{L}(u) \subseteq \mathcal{L}(h_{\delta'}(\ell_1))$, and Proposition 1 gives $h_{\delta'}(\ell_2) = h_{\delta'}(\ell_1)$. $\square$

Every node above a genus that is not a whole tree has $c > \delta$, and a genus cut by measured divergence has $c \le \delta$; the released margins are these two distances. Because a measured node is judged by its own value, a genus can still contain a measured sub-clade whose own $D$ exceeds $\delta$.

## Word distance

Words are compared by global alignment with substitution scores for pairs of ASJP symbols learned from the data, after Jäger [@jager2013]. ASJP distances have also been used to classify and date the world's languages automatically [@holman2011; @jager2018]; in the release they measure divergence on an expert classification.

The scores are learned in three iterations. In each, the same-concept words of 30,000 random pairs of languages from the same family are aligned; families are drawn in proportion to their number of languages, and the first form of each concept is used, with the modifiers of ASJP's transcription removed. Pairs that align closely are taken as probable cognates: in the first iteration, those whose identical aligned symbols make up at least half of the longer word, and afterwards those with a word distance (below) of at most 0.5. The association between the symbols aligned in them is estimated as pointwise mutual information (PMI) [@church1990] with add-one (Laplace) smoothing, computed with the ASymCat library [@tresoldi2026asymcat] on FreqProb's estimators [@tresoldi2026freqprob] and averaged over its two directions, and the words are realigned with these scores.

With $s(x, y)$ the score of the best alignment of words $x$ and $y$ (Needleman–Wunsch, linear gap penalty 2.5), the word distance is

$$
d(x, y) = 1 - \frac{2\, s(x, y)}{s(x, x) + s(y, y)},
$$

which is 0 for identical words and exceeds 1 when the alignment score is negative; it is set to 1 when the denominator is not positive. For two languages $a$ and $b$, let $\bar d_{ij}$ be the mean of $d$ over the forms of concept $i$ in $a$ and concept $j$ in $b$, which averages over synonyms; let $S$ be the concepts attested in both, and $O$ a sample of 60 pairs $(i, j)$, $i \ne j$, of concepts attested in $a$ and $b$ respectively, drawn with a generator seeded by the language pair. The language distance divides the mean same-concept distance by the mean different-concept distance,

$$
\Delta(a, b) = \frac{\frac{1}{|S|}\sum_{i \in S} \bar d_{ii}}{\frac{1}{|O|}\sum_{(i, j) \in O} \bar d_{ij}},
$$

defined when $|S| \ge 20$ and the denominator is positive, in the way LDND, the Levenshtein distance normalized and divided, normalizes edit distance [@wichmann2010]. The denominator is a heuristic normalization for the similarity that unrelated words of two languages share through their phonotactics.

## Calibration

The threshold can be fixed or calibrated against a reference partition of some of the languages, here the WALS genera. The threshold is calibrated against the WALS genera of all families, giving each family equal weight:

$$
\begin{aligned}
A(\delta) &= \frac{1}{|F|} \sum_{f \in F} \mathrm{ARI}\left(W_f,\ h_\delta|_f\right),\\
M &= \operatorname*{arg\,max}_{\delta \in \Delta}\ \frac{1}{41} \sum_{k=-20}^{20} A(\delta + 0.001\,k),\\
\Delta &= \{0.520, 0.521, \ldots, 0.980\},
\end{aligned}
$$

and $\delta^*$ is the middle value of the maximizing set $M$ in increasing order (of an even number, the lower of the two in the middle), so that it is always a maximizer, where $F$ is the set of Glottolog families whose WALS-labelled in-scope languages fall into at least two WALS genera, $W_f$ the WALS genus partition of those languages, $h_\delta|_f$ the divergence partition restricted to them, and ARI the adjusted Rand index [@rand1971; @hubert1985]. The WALS label "Creoles and Pidgins" is not genealogical and is left out of calibration and evaluation alike. Averaging over families instead of pooling all languages kept the most populous WALS genera, such as Bantoid and Oceanic, from dominating the criterion. $A(\delta)$ is a step function that jumps whenever $\delta$ crosses the value of a node in one of the families; averaging it over a window of ±0.02 makes $\delta^*$ depend on the run of the curve rather than on single crossings.
