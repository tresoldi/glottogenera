"""
Cognate memberships of a form, as written in the Cognacy column of the
deposited judgements (cognates/): one or more cognate sets separated by ";",
each prefixed with its source dataset. A set numbered 0 is a placeholder (in
Peiros' Austroasiatic data, for loans and entries without a judgement): it is
no judgement, so it never makes two forms cognate.
"""


def memberships(cognacy: str) -> set:
    """The cognate sets of a form, without placeholders; empty when it has no judgement."""
    sets = set()
    for token in cognacy.split(";"):
        token = token.strip()
        # the set itself is numbered 0 (e.g. peirosaustroasiatic_0); class labels that merely end in
        # _0, such as dunnaslian_8_blood_0, are real sets
        if token and token.split("_", 1)[-1] != "0":
            sets.add(token)
    return sets
