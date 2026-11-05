"""
Genera on any rooted tree: the general definition.

A genus is the largest clade of a rooted tree whose divergence does not exceed
a threshold delta. The tree can be an expert classification (Glottolog, in the
release) or one estimated from data: UPGMA and neighbour-joining are given
here, and a tree from another program, such as a Bayesian maximum clade
credibility tree, can be read from Newick (``Tree.from_newick``, which keeps
branch lengths). The divergence of a node can come from any distance between
languages, as the mean over pairs of its languages on different branches
(``crown_divergence``), or be any value of the node itself, such as its age in
a dated tree (``node_ages``). delta can be set directly or calibrated against a
reference partition (``Calibration``).

    >>> from glottogenera.tree import Tree, crown_divergence, cut_values, genera
    >>> t = Tree.from_newick("((a,b)x,(c,d)y)r;")
    >>> close = {frozenset("ab"), frozenset("cd")}
    >>> crowns = crown_divergence(t, lambda p, q: 0.2 if frozenset((p, q)) in close else 0.9)
    >>> genera(t, cut_values(t, crowns), 0.5)[0]
    {'a': 'x', 'b': 'x', 'c': 'y', 'd': 'y'}
"""

from __future__ import annotations

import random
import re
import warnings
from collections import defaultdict
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

# Threshold grid and smoothing of the calibration objective, on the scale of
# the released distance (see Calibration for other scales).
GRID_STEP = 0.001
DELTA_GRID = [round(x, 3) for x in np.arange(0.5, 1.0005, GRID_STEP)]
SMOOTHING = 0.02  # half-width of the window averaged in the calibration
MAX_PAIRS = 200  # language pairs sampled per node for its crown divergence


def _fresh(prefix: str, taken: set) -> Callable[[], str]:
    """A generator of node names ``prefix1``, ``prefix2``, ... not in ``taken``."""
    counter = [0]

    def name():
        while True:
            counter[0] += 1
            candidate = f"{prefix}{counter[0]}"
            if candidate not in taken:
                taken.add(candidate)
                return candidate

    return name


class Tree:
    """
    A rooted tree, or a forest of rooted trees, given by the parent of every
    node (None for roots). ``leaves`` are the units being grouped (languages;
    by default the nodes without children). Node names must be unique.
    ``length`` optionally gives each node's branch length to its parent, and
    ``support`` the support values read from Newick.
    """

    def __init__(
        self,
        parent: Mapping[str, Optional[str]],
        leaves: Optional[Iterable[str]] = None,
        length: Optional[Mapping[str, float]] = None,
        support: Optional[Mapping[str, str]] = None,
    ):
        self.parent: Dict[str, Optional[str]] = dict(parent)
        for p in list(self.parent.values()):
            if p is not None and p not in self.parent:
                self.parent[p] = None
        self.children: Dict[str, List[str]] = defaultdict(list)
        for node, p in sorted(self.parent.items()):
            if p is not None:
                self.children[p].append(node)
        self.leaves: List[str] = sorted(leaves) if leaves is not None else sorted(
            n for n in self.parent if not self.children.get(n)
        )
        missing = [x for x in self.leaves if x not in self.parent]
        if missing:
            raise ValueError(f"leaves not in the tree: {missing[:5]}")
        self.length: Dict[str, float] = dict(length or {})
        self.support: Dict[str, str] = dict(support or {})
        self.info: Dict[str, object] = {}
        self._lineage: Dict[str, List[str]] = {}

    def lineage(self, node: str) -> List[str]:
        """The path from the root down to ``node``, both included."""
        if node not in self._lineage:
            if node not in self.parent:
                raise KeyError(f"{node!r} is not a node of the tree")
            path, seen = [], set()
            n: Optional[str] = node
            while n is not None:
                if n in seen:
                    raise ValueError(f"the parent table has a cycle through {n!r}")
                seen.add(n)
                path.append(n)
                n = self.parent.get(n)
            self._lineage[node] = path[::-1]
        return self._lineage[node]

    def root(self, node: str) -> str:
        return self.lineage(node)[0]

    def leaves_below(self) -> Dict[str, List[str]]:
        """{node: the leaves at or below it}."""
        out = defaultdict(list)
        for leaf in self.leaves:
            for n in self.lineage(leaf):
                out[n].append(leaf)
        return out

    @classmethod
    def from_newick(cls, text: str, prefix: str = "n") -> "Tree":
        """
        A tree, or a forest of trees each ended by ``;``, from Newick. Labels may
        be quoted ('' escapes a quote); comments in brackets are ignored. Leaf
        labels name the languages and must be unique. An internal node keeps its
        label as its name when the label is unique and not a number; numeric
        internal labels are read as support values (``Tree.support``), and
        unnamed internal nodes get names ``prefix1``, ``prefix2``, ... that
        clash with no label. Branch lengths are kept in ``Tree.length``.
        """
        tokens = _newick_tokens(text)
        pos = 0
        parsed = []  # (node id, label, length, children)
        labels: List[str] = []

        def peek():
            return tokens[pos] if pos < len(tokens) else None

        def node():
            nonlocal pos
            kids = []
            if peek() == "(":
                pos += 1
                while True:
                    kids.append(node())
                    tok = peek()
                    if tok == ",":
                        pos += 1
                    elif tok == ")":
                        pos += 1
                        break
                    else:
                        raise ValueError(f"Newick: expected ',' or ')' at token {pos}, found {tok!r}")
            label, length = None, None
            if peek() is not None and peek()[0] == "L":
                label = peek()[1:]
                pos += 1
            if peek() == ":":
                pos += 1
                tok = peek()
                try:
                    length = float(tok[1:]) if tok and tok[0] == "L" else None
                except ValueError:
                    length = None
                if length is None:
                    raise ValueError(f"Newick: bad branch length at token {pos}")
                pos += 1
            idx = len(parsed)
            parsed.append([None, label, length, kids])
            if label:
                labels.append(label)
            return idx

        roots = []
        while pos < len(tokens):
            roots.append(node())
            if peek() != ";":
                raise ValueError(f"Newick: expected ';' at token {pos}, found {peek()!r}")
            pos += 1
        if not roots:
            raise ValueError("Newick: no tree")

        leaf_labels = [p[1] for p in parsed if not p[3]]
        if any(not x for x in leaf_labels):
            raise ValueError("Newick: every leaf needs a label")
        if len(set(leaf_labels)) != len(leaf_labels):
            raise ValueError("Newick: leaf labels are not unique")
        counts = defaultdict(int)
        for x in labels:
            counts[x] += 1
        taken = set(labels)
        fresh = _fresh(prefix, taken)
        support = {}
        for p in parsed:
            label, kids = p[1], p[3]
            if not kids:
                p[0] = label
            elif label and counts[label] == 1 and not _is_number(label):
                p[0] = label
            else:
                p[0] = fresh()
                if label:
                    support[p[0]] = label
        parent, length = {}, {}
        for p in parsed:
            for k in p[3]:
                parent[parsed[k][0]] = p[0]
            if p[2] is not None:
                length[p[0]] = p[2]
        for r in roots:
            parent[parsed[r][0]] = None
        leaves = [p[0] for p in parsed if not p[3]]
        return cls(parent, leaves, length, support)

    def to_newick(self) -> str:
        """Newick of every tree in the forest, one per line, with branch lengths if known."""

        def quote(n):
            return n if re.fullmatch(r"[^,():;\[\]\s']+", n) else "'" + n.replace("'", "''") + "'"

        def write(n):
            kids = self.children.get(n, [])
            inner = "(" + ",".join(write(k) for k in kids) + ")" if kids else ""
            length = f":{self.length[n]:.10g}" if n in self.length else ""
            return inner + quote(n) + length

        return "\n".join(write(r) + ";" for r in sorted({self.root(leaf) for leaf in self.leaves}))


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def _newick_tokens(text: str) -> List[str]:
    """Tokens: ( ) , : ; and labels prefixed with L (quoted labels unquoted)."""
    out, i, n = [], 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch == "[":
            j = text.find("]", i)
            if j < 0:
                raise ValueError("Newick: unclosed comment")
            i = j + 1
        elif ch in "(),:;":
            out.append(ch)
            i += 1
        elif ch == "'":
            buf, i = [], i + 1
            while True:
                if i >= n:
                    raise ValueError("Newick: unclosed quote")
                if text[i] == "'":
                    if i + 1 < n and text[i + 1] == "'":
                        buf.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(text[i])
                i += 1
            out.append("L" + "".join(buf))
        else:
            m = re.match(r"[^\s(),:;\[\]']+", text[i:])
            if not m:
                raise ValueError(f"Newick: unexpected {ch!r} at character {i}")
            out.append("L" + m.group(0))
            i += m.end()
    return out


def node_ages(tree: Tree) -> Dict[str, float]:
    """
    The age of every internal node of a dated (ultrametric) tree, from its
    branch lengths: the mean distance from the node down to its leaves. This
    is an age only when all leaves are contemporary; for trees with extinct
    or ancient tips, supply the node ages directly. Pass the result to
    ``cut_values`` to cut the tree at an age.
    """
    if not tree.length:
        raise ValueError("the tree has no branch lengths")
    depth: Dict[str, float] = {}

    def down(n):
        if n not in depth:
            p = tree.parent[n]
            depth[n] = 0.0 if p is None else down(p) + tree.length.get(n, 0.0)
        return depth[n]

    below = tree.leaves_below()
    return {
        n: float(np.mean([down(x) for x in leaves]) - down(n))
        for n, leaves in below.items()
        if tree.children.get(n)
    }


# ----- crown divergence and the cut -----


def branches(tree: Tree, covered: Iterable[str]) -> Dict[str, Dict[str, List[str]]]:
    """{node: {child branch: covered leaves below it}}."""
    out: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for leaf in sorted(covered):
        lineage = tree.lineage(leaf)
        for i in range(len(lineage) - 1):
            out[lineage[i]][lineage[i + 1]].append(leaf)
    return out


def crown_pairs(tree: Tree, covered: Iterable[str], max_pairs: int = MAX_PAIRS) -> Dict[str, List[Tuple[str, str]]]:
    """
    Cross-branch pairs of covered leaves for every node with covered leaves on
    at least two child branches: all of them when there are at most
    ``max_pairs``, otherwise ``max_pairs`` drawn uniformly with a generator
    seeded by the node's name (so the sample depends on the names).
    """
    result = {}
    for node, kids in sorted(branches(tree, covered).items()):
        groups = [leaves for _, leaves in sorted(kids.items())]
        if len(groups) < 2:
            continue
        total = sum(len(a) * len(b) for i, a in enumerate(groups) for b in groups[i + 1 :])
        if total <= max_pairs:
            pairs = [(x, y) for i, a in enumerate(groups) for b in groups[i + 1 :] for x in a for y in b]
        else:
            rng = random.Random(node)
            pool = [(i, leaf) for i, leaves in enumerate(groups) for leaf in leaves]
            chosen = set()
            while len(chosen) < max_pairs:
                (i, x), (j, y) = rng.sample(pool, 2)
                if i != j:
                    chosen.add((min(x, y), max(x, y)))
            pairs = sorted(chosen)
        result[node] = [tuple(sorted(p)) for p in pairs]
    return result


def crown_divergence(
    tree: Tree,
    distance: Callable[[str, str], Optional[float]],
    covered: Optional[Iterable[str]] = None,
    max_pairs: int = MAX_PAIRS,
) -> Dict[str, dict]:
    """
    {node: {"D": mean distance, "n_pairs": pairs}} for every node at which the
    distance is defined for at least one cross-branch pair. ``distance`` takes
    two leaves and returns a number or None; ``covered`` are the leaves with
    data (all leaves by default).
    """
    covered = tree.leaves if covered is None else list(covered)
    out = {}
    for node, pairs in crown_pairs(tree, covered, max_pairs).items():
        values = [v for a, b in pairs if (v := distance(a, b)) is not None]
        if values:
            out[node] = {"D": float(np.mean(values)), "n_pairs": len(values)}
    return out


Values = Mapping[str, Union[float, Mapping[str, float]]]


def cut_values(tree: Tree, crowns: Values, rule: str = "own") -> Dict[str, float]:
    """
    c(u), the value the cut is made on (absent: no evidence at or below u).
    ``crowns`` maps nodes to a number, or to {"D": number} as returned by
    ``crown_divergence``; node quantities such as ages are passed the same way.

    rule "own": a node with a value uses it, and a node without one the
    largest value among its children. rule "max": the largest value at or
    below u.
    """
    if rule not in ("own", "max"):
        raise ValueError(f"unknown rule {rule!r}: use 'own' or 'max'")
    own = {n: (v["D"] if isinstance(v, Mapping) else float(v)) for n, v in crowns.items()}
    env: Dict[str, Optional[float]] = {}

    def visit(node):
        if node in env:
            return env[node]
        below = [e for c in sorted(tree.children.get(node, [])) if (e := visit(c)) is not None]
        if node in own and rule == "own":
            env[node] = own[node]
        else:
            values = ([own[node]] if node in own else []) + below
            env[node] = max(values) if values else None
        return env[node]

    for leaf in tree.leaves:
        visit(tree.root(leaf))
    return {n: e for n, e in env.items() if e is not None}


def genera(
    tree: Tree, c: Mapping[str, float], delta: float, leaves: Optional[Iterable[str]] = None
) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    ({leaf: genus}, {leaf: method}). Walking down each path, the genus is the
    first final node: one whose value is at most delta (`divergence`), one
    with no value at or below it, or the leaf itself, which is always final.
    A lone leaf is its own genus (`isolate`); a root without any value is one
    genus (`unmeasured-family`); below a node that exceeds delta, an
    unmeasured clade is the genus (`unmeasured-clade`), or the leaf itself
    when it is reached (`single-language`).
    """
    genus, method = {}, {}
    for leaf in tree.leaves if leaves is None else leaves:
        lineage = tree.lineage(leaf)
        for i, node in enumerate(lineage):
            e = c.get(node)
            if e is not None and e <= delta:
                genus[leaf], method[leaf] = node, "divergence"
                break
            if e is None or node == leaf:
                if len(lineage) == 1:
                    genus[leaf], method[leaf] = leaf, "isolate"
                elif i == 0:
                    genus[leaf], method[leaf] = node, "unmeasured-family"
                elif node == leaf:
                    genus[leaf], method[leaf] = leaf, "single-language"
                else:
                    genus[leaf], method[leaf] = node, "unmeasured-clade"
                break
    return genus, method


# ----- calibration against a reference partition -----


def adjusted_rand(a: Sequence, b: Sequence) -> float:
    """Adjusted Rand index between two labelings of the same items."""
    from sklearn.metrics import adjusted_rand_score

    return float(adjusted_rand_score(list(a), list(b)))


def calibration_groups(
    tree: Tree, reference: Mapping[str, str], min_labels: int = 2, group: Optional[Callable[[str], str]] = None
) -> Dict[str, List[str]]:
    """
    {group: its leaves with a reference label}, for groups with at least two
    such leaves in at least ``min_labels`` reference classes. Groups are the
    trees of the forest unless ``group`` maps leaves otherwise; on a single
    tree there is one group, and the criterion becomes the pooled ARI.
    Reference leaves that are not leaves of the tree are ignored.
    """
    group = group or tree.root
    inside = set(tree.leaves)
    by = defaultdict(list)
    for leaf in sorted(reference):
        if leaf in inside:
            by[group(leaf)].append(leaf)
    return {g: ls for g, ls in sorted(by.items()) if len(ls) >= 2 and len({reference[x] for x in ls}) >= min_labels}


def _step(grid: Sequence[float]) -> float:
    """The spacing of a uniform grid."""
    g = np.asarray(grid, dtype=float)
    if len(g) < 2:
        raise ValueError("the grid needs at least two values")
    d = np.diff(g)
    if not np.allclose(d, d[0], rtol=1e-6, atol=1e-12) or d[0] <= 0:
        raise ValueError("the grid must be increasing and evenly spaced")
    return float(d[0])


def threshold_grid(c: Mapping[str, float], points: int = 501) -> List[float]:
    """An evenly spaced grid of ``points`` thresholds over the range of the cut values."""
    values = list(c.values())
    lo, hi = min(values), max(values)
    if hi <= lo:
        hi = lo + 1.0
    return [float(x) for x in np.linspace(lo, hi, points)]


def stepwise(tree: Tree, c: Mapping[str, float], leaves, score, grid=DELTA_GRID) -> np.ndarray:
    """
    score(partition of ``leaves``) at every grid value. The partition only
    changes where delta crosses the cut value of a node on the leaves'
    lineages, so it is computed once per such value.
    """
    nodes = {n for leaf in leaves for n in tree.lineage(leaf)}
    values = sorted({c[n] for n in nodes if n in c})
    points = [values[0] - 1.0] + values if values else [0.0]
    scores = [score(genera(tree, c, d, leaves)[0]) for d in points]
    return np.array([scores[i] for i in np.searchsorted(values, grid, side="right")])


def smooth(objective: np.ndarray, half_width: float = SMOOTHING, step: float = GRID_STEP) -> np.ndarray:
    """
    The mean over a window of +-half_width (in the units of the threshold, on
    a grid of spacing ``step``); -inf where the window leaves the grid.
    """
    k = int(round(half_width / step))
    if k == 0:
        return objective.astype(float)
    if 2 * k + 1 > len(objective):
        raise ValueError("the smoothing window is wider than the grid")
    out = np.convolve(objective, np.ones(2 * k + 1) / (2 * k + 1), mode="same")
    out[:k] = out[-k:] = -np.inf
    return out


class Calibration:
    """
    Agreement with a reference partition of every calibration group across a
    grid of thresholds: the matrix ``ari`` has one row per group and one
    column per grid value. delta maximizes the mean over groups, averaged
    over a window of +-``half_width`` (the median of tied values).

    The grid and the window are on the scale of the divergence. The defaults
    (DELTA_GRID, 0.5 to 1.0 by 0.001, and SMOOTHING, 0.02) are those of the
    released distance; for another measure, such as ages, pass ``grid`` (e.g.
    ``threshold_grid(c)``) and ``half_width`` in its units, or 0 for none.
    """

    def __init__(
        self,
        tree: Tree,
        c: Mapping[str, float],
        reference: Mapping[str, str],
        min_labels: int = 2,
        group: Optional[Callable[[str], str]] = None,
        grid: Sequence[float] = DELTA_GRID,
        half_width: float = SMOOTHING,
    ):
        self.grid = [float(x) for x in grid]
        self.step = _step(self.grid)
        self.half_width = half_width
        values = [v for v in c.values()]
        if values and (max(values) < self.grid[0] or min(values) > self.grid[-1]):
            warnings.warn("no cut value lies within the grid; pass a grid on the scale of the divergence", stacklevel=2)
        self.groups = calibration_groups(tree, reference, min_labels, group)
        if not self.groups:
            raise ValueError("no calibration group: the reference needs two classes within a group")
        self.names = list(self.groups)
        self.ari = np.array(
            [
                stepwise(
                    tree,
                    c,
                    leaves,
                    lambda genus, leaves=leaves: adjusted_rand(
                        [reference[x] for x in leaves], [genus[x] for x in leaves]
                    ),
                    self.grid,
                )
                for leaves in self.groups.values()
            ]
        )

    @staticmethod
    def choose(
        objective: np.ndarray, half_width: float = SMOOTHING, grid: Sequence[float] = DELTA_GRID
    ) -> Tuple[float, List[float]]:
        """The median of the grid values that tie for the maximum of the smoothed objective."""
        smoothed = smooth(objective, half_width, _step(grid))
        if np.ptp(smoothed[np.isfinite(smoothed)]) < 1e-12:
            warnings.warn("the calibration objective is flat over the grid; delta is not determined", stacklevel=2)
        tied = [d for d, v in zip(grid, smoothed) if np.isclose(v, smoothed.max())]
        return round(float(np.median(tied)), 4), tied

    def objective(self, rows=None, weights=None) -> np.ndarray:
        """The (weighted) mean group ARI at every grid value, over ``rows``."""
        rows = np.arange(len(self.names)) if rows is None else np.asarray(rows)
        w = np.ones(len(rows)) if weights is None else np.asarray(weights, dtype=float)
        return (self.ari[rows] * w[:, None]).sum(axis=0) / w.sum()

    def delta(self, rows=None, weights=None, half_width: Optional[float] = None) -> Tuple[float, float, List[float]]:
        """(delta, smoothed objective at delta, tied grid values) over ``rows``."""
        hw = self.half_width if half_width is None else half_width
        objective = self.objective(rows, weights)
        delta, tied = self.choose(objective, hw, self.grid)
        return delta, float(smooth(objective, hw, self.step).max()), tied

    def at(self, delta: float) -> int:
        """The grid index of ``delta``."""
        return int(np.argmin(np.abs(np.array(self.grid) - delta)))

    def held_out(self, half_width: Optional[float] = None) -> List[Tuple[str, float, float]]:
        """(group, delta chosen without it, its ARI at that delta), leaving out each group."""
        rows = np.arange(len(self.names))
        out = []
        for f, name in enumerate(self.names):
            d, _, _ = self.delta(rows[rows != f], half_width=half_width)
            out.append((name, d, float(self.ari[f, self.at(d)])))
        return out


# ----- trees estimated from distances -----


def _check(names: Sequence[str], matrix) -> np.ndarray:
    m = np.asarray(matrix, dtype=float)
    if len(set(names)) != len(names):
        raise ValueError("the names must be unique")
    if m.shape != (len(names), len(names)):
        raise ValueError("the distance matrix must be square, one row per name")
    if not np.isfinite(m).all() or (m < 0).any():
        raise ValueError("the distances must be finite and non-negative (impute undefined ones first)")
    if not np.allclose(m, m.T) or not np.allclose(np.diag(m), 0):
        raise ValueError("the distance matrix must be symmetric with a zero diagonal")
    return m


def upgma(names: Sequence[str], matrix, prefix: str = "u") -> Tuple[Tree, Dict[str, float]]:
    """
    UPGMA (average linkage): (tree, {node: height}), the tree carrying branch
    lengths. A node's height is the mean distance between the leaves of its
    two branches, so it equals the node's crown divergence over all pairs;
    crown_divergence with a pair sample, or with undefined distances left
    out, only approximates it. Ties are broken as scipy breaks them.
    """
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    m = _check(names, matrix)
    if len(names) == 1:
        return Tree({names[0]: None}, names), {}
    link = linkage(squareform(m, checks=False), method="average")
    n = len(names)
    fresh = _fresh(prefix, set(names))
    label = list(names) + [fresh() for _ in range(n - 1)]
    parent: Dict[str, Optional[str]] = {}
    height = {x: 0.0 for x in names}
    for k, (a, b, h, _) in enumerate(link):
        node = label[n + k]
        parent[label[int(a)]] = node
        parent[label[int(b)]] = node
        height[node] = float(h)
    parent[label[-1]] = None
    length = {x: height[parent[x]] - height[x] for x in parent if parent[x] is not None}
    return Tree(parent, names, length), {k: v for k, v in height.items() if k not in names}


def neighbor_joining(names: Sequence[str], matrix, prefix: str = "j") -> Tuple[Tree, Dict[str, float]]:
    """
    Neighbour-joining (Saitou and Nei 1987), rooted at the midpoint of the
    longest path: (tree, {node: branch length to its parent}). A negative
    branch length is set to zero and the difference moved to the sister
    branch (Kuhner and Felsenstein 1994); how often this happened is in
    ``tree.info["negative_lengths"]``. The root always lies on an edge, so the
    named leaves stay leaves.
    """
    m = _check(names, matrix)
    n = len(names)
    fresh = _fresh(prefix, set(names))
    if n == 1:
        return Tree({names[0]: None}, names), {}
    if n == 2:
        root = fresh()
        lengths = {names[0]: m[0, 1] / 2, names[1]: m[0, 1] / 2}
        t = Tree({names[0]: root, names[1]: root, root: None}, names, lengths)
        t.info["negative_lengths"] = 0
        return t, lengths
    d = m.copy()
    active = list(names)
    edges: Dict[str, List[Tuple[str, float]]] = defaultdict(list)  # undirected tree
    negative = 0
    while len(active) > 2:
        r = len(active)
        total = d.sum(axis=1)
        q = (r - 2) * d - total[:, None] - total[None, :]
        np.fill_diagonal(q, np.inf)
        i, j = np.unravel_index(np.argmin(q), q.shape)
        if i > j:
            i, j = j, i
        node = fresh()
        li = 0.5 * d[i, j] + (total[i] - total[j]) / (2 * (r - 2))
        lj = d[i, j] - li
        if li < 0:
            li, lj, negative = 0.0, d[i, j], negative + 1
        elif lj < 0:
            li, lj, negative = d[i, j], 0.0, negative + 1
        edges[node] += [(active[i], li), (active[j], lj)]
        edges[active[i]].append((node, li))
        edges[active[j]].append((node, lj))
        new = 0.5 * (d[i] + d[j] - d[i, j])
        keep = [x for x in range(r) if x not in (i, j)]
        d2 = np.empty((len(keep) + 1, len(keep) + 1))
        d2[:-1, :-1] = d[np.ix_(keep, keep)]
        d2[-1, :-1] = d2[:-1, -1] = new[keep]
        d2[-1, -1] = 0.0
        d = d2
        active = [active[x] for x in keep] + [node]
    a, b = active
    w = max(d[0, 1], 0.0)
    edges[a].append((b, w))
    edges[b].append((a, w))
    tree, lengths = _midpoint_root(edges, names, fresh)
    tree.info["negative_lengths"] = negative
    return tree, lengths


def _midpoint_root(edges, names, fresh):
    """Root an unrooted tree on the edge holding the midpoint of its longest leaf-to-leaf path."""
    leafset = set(names)

    def farthest(start):
        dist, prev, stack = {start: 0.0}, {start: None}, [start]
        while stack:
            u = stack.pop()
            for v, w in edges[u]:
                if v not in dist:
                    dist[v], prev[v] = dist[u] + w, u
                    stack.append(v)
        others = sorted(x for x in dist if x in leafset and x != start)
        far = max(others, key=lambda x: dist[x])
        return far, dist, prev

    a, _, _ = farthest(sorted(names)[0])
    b, dist, prev = farthest(a)
    half = dist[b] / 2
    # the path from a to b, and the edge (p, q) on which the midpoint lies
    path = [b]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    path = path[::-1]  # a ... b
    p = q = None
    for x, y in zip(path, path[1:]):
        if dist[x] <= half <= dist[y]:
            p, q = x, y
            break
    root = fresh()
    w = dict(edges[p])[q]
    lp = min(max(half - dist[p], 0.0), w)
    parent: Dict[str, Optional[str]] = {root: None, p: root, q: root}
    lengths = {p: lp, q: w - lp}
    seen = {root, p, q}
    stack = [p, q]
    while stack:
        x = stack.pop()
        for y, wy in edges[x]:
            if y not in seen:
                seen.add(y)
                parent[y], lengths[y] = x, wy
                stack.append(y)
    return Tree(parent, names, lengths), lengths
