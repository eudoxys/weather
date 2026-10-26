"""Optional live test against the NSRDB

Runs only when NSRDB credentials are installed (see `weather register`),
and can be excluded with `pytest -m "not live"`. It does not use the
network mocks or the user's cache.
"""

import json
import os

import pytest

import weather.weather as ww

# captured at import, before the offline fixture replaces it with a mock
_REAL_PSM4 = ww.pvlib.iotools.get_nsrdb_psm4_aggregated

CREDENTIALS = ww.CREDENTIALS.format(HOME=os.path.expanduser("~"))

def _credentials():
    try:
        with open(CREDENTIALS, "r") as fh:
            return list(json.load(fh).items())[0]
    except (OSError, ValueError, IndexError):
        return None

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(_credentials() is None,
        reason=f"NSRDB credentials not found in {CREDENTIALS}"),
    ]

def test_nsrdb_live(monkeypatch):
    # undo the offline fixture's NSRDB mocks
    monkeypatch.setattr(ww, "nsrdb_credentials", _credentials)
    monkeypatch.setattr(ww.pvlib.iotools, "get_nsrdb_psm4_aggregated", _REAL_PSM4)
    data = ww.Weather("CA", "Alameda", year=2020, refresh=True)
    assert data.shape == (8784, 5)
    assert data["temperature_degF"].between(0, 120).all()
    assert data["humidity_pc"].between(0, 100).all()
