"""
The released genera as a CLDF StructureDataset in cldf/, from the release
tables (data/) and the vendored Glottolog dump. Needs the cldf extra
(pip install -e ".[cldf]").

- LanguageTable: the 7,674 in-scope languages, with Glottolog coordinates,
  ISO 639-3 code, macroarea and family;
- ParameterTable: one parameter, the genus at the released threshold;
- CodeTable: the 1,190 genera, with the columns of genera_summary.tsv;
- ValueTable: the genus of every language, and how it was reached;
- nodes.csv: the crown divergence of every measured Glottolog node, from
  which the genera at any other threshold follow (glottogenera.genera_at);
- sources.bib: Glottolog, ASJP and WALS.

Usage: python scripts/build_cldf.py [--validate]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

from pycldf import Source, StructureDataset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import glottogenera  # noqa: E402
from glottogenera.glottolog import Glottolog  # noqa: E402

OUT = ROOT / "cldf"
DATA = ROOT / "data"
PARAMETER = "genus"

SOURCES = [
    Source("misc", "Glottolog", author="Hammarström, Harald and Forkel, Robert and Haspelmath, Martin and Bank, Sebastian",
           title="Glottolog 5.3", publisher="Max Planck Institute for Evolutionary Anthropology", address="Leipzig",
           year="2026", doi="10.5281/zenodo.18840935"),
    Source("misc", "ASJP", author="Wichmann, Søren and Holman, Eric W. and Brown, Cecil H. and Dryer, Matthew S. and Ran, Qibin",
           title="CLDF dataset derived from Wichmann et al.'s \"ASJP Database\" v21 from 2025", publisher="Zenodo",
           year="2025", doi="10.5281/zenodo.16736409"),
    Source("misc", "WALS", editor="Dryer, Matthew S. and Haspelmath, Martin",
           title="The World Atlas of Language Structures Online", publisher="Max Planck Institute for Evolutionary Anthropology",
           address="Leipzig", year="2013", note="CLDF release v2020.1", doi="10.5281/zenodo.4683137"),
]

# Columns of genera_summary.tsv added to the CodeTable: (column, CLDF name, datatype, description)
GENUS_COLUMNS = [
    ("genus_glottolog_name", "Glottolog_Name", "string", "Glottolog name of the genus node"),
    ("family", "Family", "string", "Top-level Glottolog family"),
    ("n_languages", "Languages", "integer", "In-scope languages in the genus"),
    ("method", "Method", "string", "How the genus was reached (see data/README.md)"),
    ("crown_divergence", "Crown_Divergence", "decimal", "The genus node's own crown divergence D; empty if unmeasured"),
    ("crown_pairs", "Crown_Pairs", "integer", "Language pairs behind Crown_Divergence"),
    ("cut_value", "Cut_Value", "decimal", "The value c used by the cut"),
    ("upper_value", "Upper_Value", "decimal", "The smallest cut value among the genus node's ancestors"),
    ("margin_below", "Margin_Below", "decimal", "delta minus Cut_Value"),
    ("margin_above", "Margin_Above", "decimal", "Upper_Value minus delta"),
    ("stability", "Stability", "decimal", "Share of bootstrap replicates (delta recalibrated) in which the genus reappears"),
    ("stability_fixed_delta", "Stability_Fixed_Delta", "decimal", "The same with delta fixed"),
    ("unclassified_node", "Unclassified_Node", "integer",
     "1 if the genus node is a Glottolog 'Unclassified' node, a residual group rather than a subgroup"),
]


def read(name):
    with (DATA / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def blank(value):
    return None if value in ("", None) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--validate", action="store_true", help="validate the written dataset")
    args = parser.parse_args()

    params = json.loads((DATA / "params.json").read_text(encoding="utf-8"))
    delta = params["divergence"]["delta"]
    g = Glottolog.load()
    languages = read("genera.tsv")
    genera = read("genera_summary.tsv")
    nodes = read("nodes.tsv")

    # Replace the generated files, keeping the hand-written README.md.
    OUT.mkdir(exist_ok=True)
    for path in OUT.iterdir():
        if path.name != "README.md":
            path.unlink()
    ds = StructureDataset.in_dir(OUT)
    ds.add_component("LanguageTable", {"name": "Family", "datatype": "string", "dc:description": "Top-level Glottolog family"})
    ds.add_component("ParameterTable")
    ds.add_component(
        "CodeTable",
        *({"name": name, "datatype": dtype, "dc:description": desc} for _, name, dtype, desc in GENUS_COLUMNS),
    )
    ds.add_columns("ValueTable", {"name": "Method", "datatype": "string",
                                  "dc:description": "How the genus was reached (see data/README.md)"})
    ds.add_table(
        "nodes.csv",
        {"name": "ID", "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#id"},
        {"name": "Name", "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#name"},
        {"name": "Glottocode", "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#glottocode"},
        {"name": "Family", "datatype": "string"},
        {"name": "Depth", "datatype": "integer", "dc:description": "Levels below the family root"},
        {"name": "Crown_Divergence", "datatype": "decimal",
         "dc:description": "Mean distance over at most 200 language pairs on different branches"},
        {"name": "Crown_Pairs", "datatype": "integer"},
        {"name": "Cut_Value", "datatype": "decimal"},
    )
    ds.tablegroup.tables[-1].common_props["dc:description"] = (
        "Crown divergence of every measured Glottolog node; with the Glottolog classification it gives the genera "
        "at any threshold (glottogenera.genera_at).")
    ds.add_sources(*SOURCES)

    language_rows = []
    for r in languages:
        row = g.by_gc[r["glottocode"]]
        language_rows.append({
            "ID": r["glottocode"],
            "Name": r["name"],
            "Glottocode": r["glottocode"],
            "ISO639P3code": blank(row["iso"]),
            "Macroarea": blank(row["macroareas"]),
            "Latitude": blank(row["latitude"]),
            "Longitude": blank(row["longitude"]),
            "Family": r["family"],
        })
    parameter = {
        "ID": PARAMETER,
        "Name": "Genus",
        "Description": (f"The genus of the language: the first node on its Glottolog lineage whose cut value is at most "
                        f"delta = {delta:g} (crown divergence from PMI alignment of ASJP wordlists), whose cut value is "
                        f"undefined, or the language itself."),
    }
    code_rows = []
    for r in genera:
        code = {"ID": r["genus_id"], "Parameter_ID": PARAMETER, "Name": r["genus_name"],
                "Description": f"Glottolog node {r['genus_id']}"}
        for column, name, _, _ in GENUS_COLUMNS:
            code[name] = blank(r[column])
        code_rows.append(code)
    value_rows = [{
        "ID": r["glottocode"],
        "Language_ID": r["glottocode"],
        "Parameter_ID": PARAMETER,
        "Value": r["genus_name"],
        "Code_ID": r["genus_id"],
        "Method": r["method"],
        "Source": ["Glottolog"] if r["method"] != "divergence" else ["Glottolog", "ASJP"],
    } for r in languages]
    node_rows = [{
        "ID": r["node"], "Name": r["name"], "Glottocode": r["node"], "Family": r["family"], "Depth": r["depth"],
        "Crown_Divergence": r["crown_divergence"], "Crown_Pairs": r["crown_pairs"], "Cut_Value": r["cut_value"],
    } for r in nodes]

    ds.properties.update({
        "dc:title": f"Glottogenera {glottogenera.__version__}: genera for the languages of Glottolog 5.3",
        "dc:description": (
            "Genera defined by a divergence threshold on a language tree: a genus is the largest clade whose "
            f"divergence does not exceed a threshold delta. This release cuts Glottolog 5.3, with crown divergence "
            f"from PMI alignment of ASJP 21 wordlists and delta = {delta:g} calibrated against the WALS genera."),
        "dc:license": "https://creativecommons.org/licenses/by/4.0/",
        "dc:creator": "Tiago Tresoldi",
        "dcat:accessURL": "https://github.com/tresoldi/glottogenera",
        "dc:source": "sources.bib",
        "prov:wasDerivedFrom": [
            {"rdf:about": "https://doi.org/10.5281/zenodo.18840935", "dc:title": "Glottolog 5.3"},
            {"rdf:about": "https://doi.org/10.5281/zenodo.16736409", "dc:title": "ASJP v21 (lexibank/asjp)"},
            {"rdf:about": "https://doi.org/10.5281/zenodo.4683137", "dc:title": "WALS Online (CLDF v2020.1)"},
        ],
    })
    ds.write(
        LanguageTable=language_rows,
        ParameterTable=[parameter],
        CodeTable=code_rows,
        ValueTable=value_rows,
        **{"nodes.csv": node_rows},
    )
    print(f"wrote {OUT}: {len(language_rows)} languages, {len(code_rows)} genera, {len(node_rows)} nodes")
    if args.validate:
        ds.validate()
        print("valid")


if __name__ == "__main__":
    main()
