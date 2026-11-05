"""
Command-line interface: run the pipeline stages individually or end-to-end.

    glottogenera fetch        # cache WALS + ASJP sources (pinned versions)
    glottogenera divergence   # measure divergence, calibrate delta, write the genera
    glottogenera all          # both, in order

All stages read and write under ``--data-dir`` (default: ./data).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__
from .resources import DEFAULT_MAX_MEMORY_MB, configure_process


def _run_fetch(data_dir: Path, force: bool = False) -> int:
    from . import fetch

    return fetch.run(data_dir, force=force)


def _run_divergence(data_dir: Path) -> int:
    from . import divergence

    return divergence.run(data_dir)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="glottogenera",
        description="Genera defined by a divergence threshold on a language tree; the release for Glottolog 5.3.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="directory for source caches and artifacts (default: ./data)",
    )
    ap.add_argument(
        "--max-memory-mb",
        type=int,
        default=DEFAULT_MAX_MEMORY_MB,
        help=(
            "maximum address space for pipeline work "
            f"(default: {DEFAULT_MAX_MEMORY_MB} MiB)"
        ),
    )
    sub = ap.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="cache WALS + ASJP source data")
    p_fetch.add_argument("--force", action="store_true", help="refetch even if cached")
    sub.add_parser("divergence", help="measure divergence, calibrate delta, cut the genera")
    p_all = sub.add_parser("all", help="run every stage in order")
    p_all.add_argument(
        "--force", action="store_true", help="refetch sources even if cached"
    )

    args = ap.parse_args(argv)
    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_process(args.max_memory_mb)
    except ValueError as exc:
        ap.error(str(exc))

    if args.command == "fetch":
        return _run_fetch(data_dir, force=args.force)
    if args.command == "divergence":
        return _run_divergence(data_dir)
    if args.command == "all":
        for step in (
            lambda: _run_fetch(data_dir, force=args.force),
            lambda: _run_divergence(data_dir),
        ):
            rc = step()
            if rc:
                return rc
        return 0
    return 2  # unreachable


if __name__ == "__main__":
    raise SystemExit(main())
