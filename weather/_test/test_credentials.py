"""Tests of NSRDB credentials handling (#4, #6)"""

import json
import os
import subprocess
import sys

import pytest

import weather.weather as ww

# captured at import, before the autouse `offline` fixture mocks it
nsrdb_credentials = ww.nsrdb_credentials

@pytest.fixture(autouse=True)
def no_browser(monkeypatch):
    """Record sign-up page openings instead of opening a browser"""
    opened = []
    monkeypatch.setattr(ww.webbrowser, "open", lambda url: opened.append(url) or False)
    return opened

def test_valid(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text(json.dumps({"me@example.com": "TOKEN"}))
    assert nsrdb_credentials(str(path)) == ("me@example.com", "TOKEN")

def test_missing(tmp_path, no_browser, capsys):
    path = str(tmp_path / "credentials.json")
    with pytest.raises(RuntimeError, match="not found") as err:
        nsrdb_credentials(path)
    assert path in str(err.value)
    assert "weather register" in str(err.value)
    assert isinstance(err.value.__cause__, FileNotFoundError)
    assert no_browser == [ww.SIGNUP]
    assert capsys.readouterr().out == "" # library code does not print

@pytest.mark.parametrize("content", [
    "",                                         # empty file
    "not json",                                 # not JSON
    "{}",                                       # no entry
    '["me@example.com", "TOKEN"]',              # not a dict
    '{"me@example.com": ""}',                   # empty token
    '{"a@example.com": "A", "b@example.com": "B"}', # ambiguous
    ])
def test_malformed(tmp_path, content):
    path = tmp_path / "credentials.json"
    path.write_text(content)
    with pytest.raises(RuntimeError, match=str(path)):
        nsrdb_credentials(str(path))

def test_default_path(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert ww.credentials_path() == os.path.join(str(tmp_path), ".nsrdb", "credentials.json")

def test_import_without_home():
    env = {x: y for x, y in os.environ.items() if x not in {"HOME", "USERPROFILE"}}
    subprocess.run([sys.executable, "-c", "import weather"], env=env, check=True)
