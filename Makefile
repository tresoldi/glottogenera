# Reproduce the released artifacts end-to-end. `make all` fetches the sources,
# recomputes the genera and refreshes the package copies of the tables;
# `make release` also rebuilds the CLDF dataset and the web explorer's data.

PYTHON ?= python3
RUN = PYTHONPATH=src $(PYTHON) -m glottogenera
PKG_DATA = src/glottogenera/data
THREAD_ENV = OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1

.PHONY: all release update-glottolog fetch divergence bundle cldf web test lint clean

all: fetch divergence bundle

release: all cldf web

update-glottolog:
	$(PYTHON) scripts/update_glottolog.py

fetch:
	$(RUN) fetch

divergence:
	$(RUN) divergence

# The release copies shipped inside the package (read by load_genera() and
# friends), and the curated genus names, kept in the package, copied to data/.
bundle:
	cp data/genera.tsv data/genera_summary.tsv data/nodes.tsv $(PKG_DATA)/
	cp $(PKG_DATA)/genus_names.tsv data/

# The CLDF StructureDataset in cldf/ (needs the cldf extra).
cldf:
	$(PYTHON) scripts/build_cldf.py --validate

# Data of the web explorer in web/data/ (needs the web extra and the fetched
# WALS data).
web: fetch
	$(PYTHON) scripts/build_web.py
	$(PYTHON) scripts/dravidian_map.py

test:
	$(THREAD_ENV) PYTHONPATH=src $(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src scripts tests

# Remove fetched caches only; the derived artifacts under data/ are versioned.
clean:
	rm -rf data/sources
