"""Resource-containment tests for command-line pipeline runs."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

from glottogenera import cli
from glottogenera.resources import configure_process


def test_resource_guard_sets_address_space_and_threads(monkeypatch):
    setrlimit = Mock()
    fake_resource = SimpleNamespace(
        RLIMIT_AS=9,
        RLIM_INFINITY=-1,
        getrlimit=Mock(return_value=(-1, -1)),
        setrlimit=setrlimit,
    )
    monkeypatch.setitem(sys.modules, "resource", fake_resource)
    monkeypatch.setenv("GLOTTOGENERA_NUM_THREADS", "2")

    configure_process(768)

    setrlimit.assert_called_once_with(9, (768 * 1024 * 1024, -1))
    for name in (
        "OPENBLAS_NUM_THREADS",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        assert os.environ[name] == "2"


def test_cli_applies_resource_guard_before_dispatch(monkeypatch, tmp_path):
    guard = Mock()
    divergence = Mock(return_value=0)
    monkeypatch.setattr(cli, "configure_process", guard)
    monkeypatch.setattr(cli, "_run_divergence", divergence)

    assert (
        cli.main(
            [
                "--data-dir",
                str(tmp_path),
                "--max-memory-mb",
                "768",
                "divergence",
            ]
        )
        == 0
    )

    guard.assert_called_once_with(768)
    divergence.assert_called_once_with(tmp_path)
