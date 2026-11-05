"""CLI smoke tests (no network, no heavy stages)."""

import subprocess
import sys

import pytest

from glottogenera.cli import main


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "glottogenera" in capsys.readouterr().out


def test_requires_subcommand():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_module_entrypoint():
    out = subprocess.run(
        [sys.executable, "-m", "glottogenera", "--version"],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0
    assert "glottogenera" in out.stdout


def test_all_runs_the_stages_in_order_and_stops_on_failure(tmp_path, monkeypatch):
    from glottogenera import cli

    calls = []
    monkeypatch.setattr(cli, "configure_process", lambda mb: None)
    monkeypatch.setattr(cli, "_run_fetch", lambda d, force: calls.append(("fetch", d, force)) or 0)
    monkeypatch.setattr(cli, "_run_divergence", lambda d: calls.append(("divergence", d)) or 0)
    assert main(["--data-dir", str(tmp_path), "all", "--force"]) == 0
    assert calls == [("fetch", tmp_path, True), ("divergence", tmp_path)]

    calls.clear()
    monkeypatch.setattr(cli, "_run_fetch", lambda d, force: calls.append("fetch") or 1)
    assert main(["--data-dir", str(tmp_path), "all"]) == 1
    assert calls == ["fetch"]
