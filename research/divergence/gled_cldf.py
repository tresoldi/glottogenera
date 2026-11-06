"""
Write the CLDF tables of GLED that measures.load_gled() reads (forms.csv,
languages.csv, parameters.csv) from gled.tsv of the GLED release r20221127.1
(Zenodo, doi:10.5281/zenodo.7368116, file 20221127.1.zip).

Usage: python research/divergence/gled_cldf.py GLED_TSV OUT_DIR   (then set GLED_CLDF=OUT_DIR)
"""

import csv
import sys
from pathlib import Path


def main(tsv, out):
    out.mkdir(parents=True, exist_ok=True)
    csv.field_size_limit(10**8)
    languages, concepts = {}, {}
    with open(tsv, newline="", encoding="utf-8") as fh, \
            (out / "forms.csv").open("w", newline="", encoding="utf-8") as fo:
        w = csv.writer(fo)
        w.writerow(["ID", "Language_ID", "Parameter_ID", "Value", "Form", "Segments", "Cognacy", "Alignment", "Source"])
        for r in csv.DictReader(fh, delimiter="\t"):
            w.writerow([r["ID"], r["DOCULECT"], r["CONCEPT"], r["ASJP_FORM"], r["FORM"], r["IPA"], r["COGSET"],
                        r["ALIGNMENT"], "Tresoldi2022gled"])
            languages.setdefault(r["DOCULECT"], (r["LANGUAGE_NAME"], r["GLOTTOCODE"], r["GLOTTOLOG_NAME"], r["FAMILY"]))
            concepts.setdefault(r["CONCEPT"], r["CONCEPTICON_ID"])
    with (out / "languages.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "Name", "Glottocode", "Glottolog_Name", "Family"])
        for doc, (name, gc, gname, fam) in languages.items():
            w.writerow([doc, name, gc, gname, fam])
    with (out / "parameters.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "Name", "Concepticon_ID"])
        for c, cid in sorted(concepts.items()):
            w.writerow([c, c, cid])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]))
