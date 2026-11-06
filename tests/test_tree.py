"""
The general definition on arbitrary trees: Newick input, the cut by node
values or by a distance, calibration against a reference, and trees estimated
from distances.
"""

import doctest
import itertools
import random

import numpy as np

from glottogenera import tree
import pytest

from glottogenera.tree import (
    Calibration,
    Tree,
    crown_divergence,
    cut_values,
    genera,
    neighbor_joining,
    node_ages,
    threshold_grid,
    upgma,
)


def test_doctest():
    assert doctest.testmod(tree).failed == 0


def test_newick_round_trip():
    t = Tree.from_newick("((a:1,b:2)x:0.5,(c,'d e'),f)r;")
    assert sorted(t.leaves) == ["a", "b", "c", "d e", "f"]
    assert t.lineage("a") == ["r", "x", "a"]
    again = Tree.from_newick(t.to_newick())
    assert again.parent == t.parent


def test_node_values_and_methods():
    # a forest: one family with an unmeasured clade, one without values, one isolate
    t = Tree({"a": "x", "b": "x", "c": "y", "d": "y", "x": "r", "y": "r", "r": None,
              "e": "s", "f": "s", "s": None, "g": None})
    c = cut_values(t, {"r": {"D": 0.9}, "x": {"D": 0.3}})
    assert c == {"r": 0.9, "x": 0.3}
    genus, method = genera(t, c, 0.5)
    assert genus == {"a": "x", "b": "x", "c": "y", "d": "y", "e": "s", "f": "s", "g": "g"}
    assert method["a"] == "divergence" and method["c"] == "unmeasured-clade"
    assert method["e"] == "unmeasured-family" and method["g"] == "isolate"
    assert genera(t, c, 0.95)[0]["c"] == "r"


def random_tree(n, rng):
    nodes = [f"l{i}" for i in range(n)]
    parent, k = {}, 0
    while len(nodes) > 1:
        rng.shuffle(nodes)
        size = min(len(nodes), rng.choice([2, 2, 3]))
        k += 1
        node = f"n{k}"
        for x in nodes[:size]:
            parent[x] = node
        nodes = nodes[size:] + [node]
    parent[nodes[0]] = None
    return Tree(parent)


def test_partitions_nest_and_are_complete_clades():
    rng = random.Random(3)
    t = random_tree(40, rng)
    dist = {frozenset(p): rng.random() for p in itertools.combinations(t.leaves, 2)}
    c = cut_values(t, crown_divergence(t, lambda a, b: dist[frozenset((a, b))]))
    below = t.leaves_below()
    previous = None
    for delta in np.linspace(0, 1, 21):
        genus = genera(t, c, delta)[0]
        for g in set(genus.values()):  # Proposition 1
            assert sorted(x for x in genus if genus[x] == g) == sorted(below[g])
        if previous:  # Proposition 2
            for a, b in itertools.combinations(t.leaves, 2):
                if previous[a] == previous[b]:
                    assert genus[a] == genus[b]
        previous = genus


def test_upgma_height_is_mean_cross_branch_distance():
    rng = np.random.default_rng(1)
    pts = rng.random((12, 2))
    m = np.sqrt(((pts[:, None] - pts[None]) ** 2).sum(-1))
    names = [f"x{i}" for i in range(12)]
    t, height = upgma(names, m)
    idx = {n: i for i, n in enumerate(names)}
    crowns = crown_divergence(t, lambda a, b: m[idx[a], idx[b]], max_pairs=10**6)
    for node, h in height.items():
        assert np.isclose(crowns[node]["D"], h)


def test_neighbor_joining_recovers_an_additive_tree():
    true = Tree.from_newick("(((a,b)p,c)q,(d,(e,f)s)t)r;")
    lengths = {"a": 1, "b": 2, "p": 1, "c": 3, "q": 2, "d": 2, "e": 1, "f": 1, "s": 2, "t": 1}

    def path(x, y):
        lx, ly = true.lineage(x), true.lineage(y)
        common = len([1 for u, v in zip(lx, ly) if u == v])
        return sum(lengths[n] for n in lx[common:]) + sum(lengths[n] for n in ly[common:])

    names = true.leaves
    m = np.array([[path(x, y) for y in names] for x in names], dtype=float)
    t, _ = neighbor_joining(names, m)

    def splits(tr):
        out = set()
        for node, leaves in tr.leaves_below().items():
            s = frozenset(leaves)
            if 1 < len(s) < len(names):
                out.add(min(s, frozenset(names) - s, key=sorted))
        return out

    assert splits(t) == splits(true)


def test_calibration_on_a_reference():
    t = Tree.from_newick("((a,b)x,(c,d)y)r;((e,f)u,(g,h)v)s;")
    c = {"x": 0.3, "y": 0.4, "r": 0.9, "u": 0.6, "v": 0.65, "s": 0.95}
    ref = {"a": "A", "b": "A", "c": "B", "d": "B", "e": "C", "f": "C", "g": "D", "h": "D"}
    cal = Calibration(t, c, ref)
    assert sorted(cal.names) == ["r", "s"]  # both trees of the forest are calibration groups
    delta, objective, _ = cal.delta(half_width=0)
    assert 0.65 <= delta < 0.9 and objective == 1.0


def test_newick_forests_quotes_and_errors():
    t = Tree.from_newick("( a , ( b,c ) x )r;\n(d,'O''Brien')s;")
    assert sorted(t.leaves) == ["O'Brien", "a", "b", "c", "d"]
    assert t.root("O'Brien") == "s" and t.lineage("b") == ["r", "x", "b"]
    assert Tree.from_newick(t.to_newick()).parent == t.parent
    for bad in ["(a,b)r garbage;", "(a,b)r", "((a,b)r;", "(a,a)r;", "(a,)r;", "(a,b)r:x;"]:
        with pytest.raises(ValueError):
            Tree.from_newick(bad)


def test_newick_generated_names_and_support():
    t = Tree.from_newick("((n1,b)0.95,(c,d)0.95)r;")
    assert sorted(t.leaves) == ["b", "c", "d", "n1"]  # n1 stays a leaf
    inner = [x for x in t.parent if x not in t.leaves and x != "r"]
    assert len(inner) == 2 and "n1" not in inner
    assert sorted(t.support.values()) == ["0.95", "0.95"]


def test_ages_and_leaves_always_final():
    t = Tree.from_newick("((a:1000,b:1000)x:3000,(c:2500,d:2500)y:1500)r;")
    ages = node_ages(t)
    assert ages == {"x": 1000.0, "y": 2500.0, "r": 4000.0}
    genus = genera(t, cut_values(t, ages), 2000)[0]
    assert genus == {"a": "x", "b": "x", "c": "c", "d": "d"}
    # a value on a leaf never removes it from the partition
    t2 = Tree.from_newick("(a,b)r;")
    genus, method = genera(t2, cut_values(t2, {"r": 4000, "a": 2000, "b": 0}), 1000)
    assert genus == {"a": "a", "b": "b"} and method["a"] == "single-language"


def test_calibration_on_another_scale():
    t = Tree.from_newick("((a,b)x,(c,d)y)r;((e,f)u,(g,h)v)s;")
    c = {"x": 1200, "y": 1500, "r": 5000, "u": 2500, "v": 2600, "s": 6000}
    ref = {k: k.upper() if k in "ab" else ("B" if k in "cd" else ("C" if k in "ef" else "D")) for k in "abcdefgh"}
    ref.update({"a": "A", "b": "A"})
    cal = Calibration(t, c, ref, grid=threshold_grid(c), half_width=0)
    delta, objective, _ = cal.delta()
    assert 2600 <= delta < 5000 and objective == 1.0
    with pytest.raises(ValueError):
        Calibration(t, c, ref, grid=[0, 1, 5])
    with pytest.warns(UserWarning):
        Calibration(t, c, ref).delta(half_width=0)  # the default grid is on the scale 0.5-1.0


def test_estimated_trees_keep_names_and_leaves():
    m = np.array([[0, 1, 2], [1, 0, 2], [2, 2, 0.0]])
    t, _ = upgma(["u1", "b", "c"], m)
    assert sorted(t.leaves) == ["b", "c", "u1"] and not t.children.get("u1")
    t, _ = neighbor_joining(["j1", "b", "c"], m)
    assert sorted(t.leaves) == ["b", "c", "j1"] and not t.children.get("j1")
    t, _ = neighbor_joining(["a", "b", "c"], np.zeros((3, 3)))
    assert all(not t.children.get(x) for x in "abc")
    t, _ = neighbor_joining(["a", "b", "c"], np.array([[0, 1, 1], [1, 0, 10], [1, 10, 0.0]]))
    assert t.info["negative_lengths"] >= 1 and all(v >= 0 for v in t.length.values())
    for bad in [np.array([[0, 1], [2, 0.0]]), np.array([[0, np.nan], [np.nan, 0]]), np.array([[0, -1], [-1, 0.0]])]:
        with pytest.raises(ValueError):
            upgma(["a", "b"], bad)


def test_input_errors():
    with pytest.raises(ValueError):
        cut_values(Tree({"a": "r", "b": "r"}), {"r": 1.0}, rule="mean")
    with pytest.raises(ValueError):
        Tree({"a": "x", "x": "y", "y": "x"}, ["a"]).lineage("a")


def test_choose_picks_a_maximizer():
    # disconnected maxima: the median (0.1) would not be one
    import numpy as np
    from glottogenera.tree import Calibration

    delta, tied = Calibration.choose(np.array([1.0, 0.0, 1.0]), half_width=0, grid=[0.0, 0.1, 0.2])
    assert delta in (0.0, 0.2) and tied == [0.0, 0.2]
