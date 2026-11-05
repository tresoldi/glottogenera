"""
Fetch and cache external source data.

WALS `languages.csv` gives Dryer's genera, the calibration yardstick; ASJP
`languages.csv` and `forms.csv` give the wordlists divergence is measured on.

Downloads are cached under ``<data-dir>/sources/`` and skipped if already
present (use ``force=True`` to refetch). Network access goes through the
environment's proxy if one is configured; TLS uses a CA bundle from
``SSL_CERT_FILE`` / ``REQUESTS_CA_BUNDLE`` when set.
"""

from __future__ import annotations

import os
import ssl
import sys
import urllib.request
from pathlib import Path

from . import __version__
from .config import SOURCES_SPEC, sources_dir


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context, honoring an explicit CA bundle if one is set."""
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and Path(path).exists():
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


def _fetch(url: str, dest: Path, force: bool = False) -> None:
    if dest.exists() and not force:
        print(f"  cached  {dest.name} ({dest.stat().st_size:,} bytes)")
        return
    print(f"  fetch   {dest.name}  <-  {url}")
    # urllib honors http(s)_proxy env vars via the default opener.
    req = urllib.request.Request(url, headers={"User-Agent": f"glottogenera/{__version__}"})
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"          wrote {len(data):,} bytes")


def run(data_dir: Path, force: bool = False) -> int:
    sources = sources_dir(data_dir)
    sources.mkdir(parents=True, exist_ok=True)
    print(f"Caching sources into {sources}")
    for name, url in SOURCES_SPEC.items():
        try:
            _fetch(url, sources / name, force=force)
        except Exception as exc:  # noqa: BLE001 - report and stop
            print(f"  ERROR   {name}: {exc}", file=sys.stderr)
            return 1
    print("Done.")
    return 0
