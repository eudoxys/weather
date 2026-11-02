"""Tests of the weather command line interface"""

import os
import shutil
import subprocess
import sys

import pandas as pd
import pytest

from weather import cli

from conftest import COLUMNS, HOURS

# the `weather` command installed alongside the running interpreter
WEATHER = shutil.which("weather", path=os.path.dirname(sys.executable)) \
    or shutil.which("weather")

@pytest.fixture(autouse=True)
def argv(monkeypatch):
    """`cli.main()` overwrites `sys.argv`; restore it after each test"""
    monkeypatch.setattr(sys, "argv", list(sys.argv))

def test_info(capsys):
    assert cli.main("info") == cli.E_OK
    out = capsys.readouterr().out
    for name in ["Homepage", "Documentation", "Repository", "Issues"]:
        assert f"{name}: https://" in out

@pytest.mark.parametrize("suffix,compression", [(".csv", None), (".csv.gz", "gzip")])
def test_print_output(reference_source, tmp_path, suffix, compression):
    reference_source("CA", "Alameda")
    output = str(tmp_path / f"weather{suffix}")
    assert cli.main("print", "-S", "CA", "-C", "Alameda", "-o", output) == cli.E_OK
    data = pd.read_csv(output, index_col=["timestamp"], parse_dates=["timestamp"],
        compression=compression)
    assert data.shape == (HOURS, 5)
    assert list(data.columns) == COLUMNS
    if compression:
        with open(output, "rb") as fh:
            assert fh.read(2) == b"\x1f\x8b"

def test_print_stdout(reference_source, capsys):
    reference_source("CA", "Alameda")
    assert cli.main("print", "--state=CA", "--county=Alameda") == cli.E_OK
    out = capsys.readouterr().out
    assert "temperature_degF" in out
    assert "2018-12-31 23:00:00+00:00" in out

def test_plot_output(reference_source, tmp_path):
    reference_source("CA", "Alameda")
    output = str(tmp_path / "weather.png")
    assert cli.main("plot", "-S", "CA", "-C", "Alameda",
        "-V", "temperature_degF", "-o", output) == cli.E_OK
    assert os.path.getsize(output) > 0

@pytest.mark.parametrize("args", [
    ["print", "-C", "Alameda"],                   # missing state
    ["print", "-S", "CA"],                        # missing county
    ["print", "-S", "CA", "-C", "Alameda"],       # download fails (no source)
    ])
def test_failed(args, capsys):
    assert cli.main(*args) == cli.E_FAILED
    captured = capsys.readouterr()
    assert captured.err.startswith("ERROR [weather]: ")
    assert len(captured.err.splitlines()) == 1
    assert captured.out == ""

def test_invalid_output(reference_source, tmp_path, capsys):
    reference_source("CA", "Alameda")
    output = str(tmp_path / "weather.txt")
    assert cli.main("print", "-S", "CA", "-C", "Alameda", "-o", output) == cli.E_FAILED
    assert "is not valid" in capsys.readouterr().err
    assert not os.path.exists(output)

def test_debug_raises():
    with pytest.raises(ValueError, match="county is required"):
        cli.main("print", "-S", "CA", "--debug")

@pytest.mark.parametrize("args", [
    ["nosuchcommand"],
    ["print", "--nosuchoption"],
    ["print", "-Y", "notayear"],
    ])
def test_syntax_error(args):
    with pytest.raises(SystemExit) as err:
        cli.main(*args)
    assert err.value.code == cli.E_SYNTAX

@pytest.mark.skipif(WEATHER is None,
    reason="weather command not installed")
def test_print_variable(reference_source, capsys):
    reference_source("CA", "Alameda")
    assert cli.main("print", "-S", "CA", "-C", "Alameda",
        "-V", "temperature_degF,humidity_pc") == cli.E_OK
    header = capsys.readouterr().out.splitlines()[0].split()
    assert header == ["temperature_degF", "humidity_pc"]

def test_unknown_variable(reference_source, capsys):
    reference_source("CA", "Alameda")
    assert cli.main("print", "-S", "CA", "-C", "Alameda",
        "-V", "wind_mps") == cli.E_FAILED
    assert "wind_mps" in capsys.readouterr().err

def test_plot_show(reference_source, monkeypatch):
    """`plot` without `--output` shows the plot and returns `E_OK`"""
    reference_source("CA", "Alameda")
    shown = []
    monkeypatch.setattr(cli.plt, "show", lambda: shown.append(True))
    assert cli.main("plot", "-S", "CA", "-C", "Alameda") == cli.E_OK
    assert shown == [True]

@pytest.mark.parametrize("returncode", [0, 1])
def test_viewer(monkeypatch, returncode):
    """`viewer` returns the exit code of marimo, not a wait status"""
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, returncode)
    monkeypatch.setattr(cli.subprocess, "run", run)
    assert cli.main("viewer") == returncode
    assert calls[0][:4] == [sys.executable, "-m", "marimo", "run"]
    assert calls[0][4].endswith("viewer.py") and os.path.exists(calls[0][4])

def test_register(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: opened.append(url) or False)
    assert cli.main("register") == cli.E_OK
    assert opened == [cli.SIGNUP]
    out = capsys.readouterr().out
    assert cli.SIGNUP in out
    assert cli.credentials_path() in out

def test_error_before_parse(monkeypatch, capsys):
    """An error raised before the arguments are parsed is reported, not masked"""
    def fail(*args, **kwargs):
        raise RuntimeError("parser setup failed")
    monkeypatch.setattr(cli.argparse, "ArgumentParser", fail)
    assert cli.main("info") == cli.E_FAILED
    assert "parser setup failed" in capsys.readouterr().err

@pytest.mark.parametrize("args,code", [
    (["info"], cli.E_OK),
    (["print", "-S", "CA"], cli.E_FAILED),
    (["nosuchcommand"], cli.E_SYNTAX),
    ])
def test_exit_codes(args, code):
    """The installed `weather` command exits with the documented codes
    (none of these cases reach the network)"""
    result = subprocess.run([WEATHER, *args], capture_output=True, text=True,
        timeout=120)
    assert result.returncode == code, result.stdout + result.stderr
