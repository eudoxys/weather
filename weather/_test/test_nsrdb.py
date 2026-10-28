"""Tests of the NSRDB actual weather (network calls mocked)"""

import numpy as np
import pandas as pd
import pytest

from fips.counties import Counties
from weather import Weather

from conftest import COLUMNS

@pytest.mark.parametrize("state,county", [
    ("CA", "Alameda"),
    ("ID", "Kootenai"),
    ("TX", "Harris"),
    ])
def test_county_latlon(nsrdb, state, county):
    """Regression test for #1: both the latitude and longitude of the county
    are passed to the NSRDB request"""
    Weather(state, county, year=2019)
    expected = Counties(use_index=["ST", "COUNTY"]).loc[(state, county)]
    assert len(nsrdb) == 1
    assert nsrdb[0]["latitude"] == pytest.approx(expected["LAT"])
    assert nsrdb[0]["longitude"] == pytest.approx(expected["LON"])
    assert nsrdb[0]["year"] == 2019
    assert nsrdb[0]["api_key"] == "TESTKEY"
    assert nsrdb[0]["email"] == "test@example.com"

@pytest.mark.parametrize("year,hours", [(2019, 8760), (2020, 8784)])
def test_shape_and_columns(nsrdb, year, hours):
    data = Weather("CA", "Alameda", year=year)
    assert data.shape == (hours, 5)
    assert list(data.columns) == COLUMNS
    assert data.index.name == "timestamp"
    assert str(data.index.tz) == "UTC"
    pd.testing.assert_frame_equal(data, data.round(1))

def test_start_of_interval(nsrdb):
    """Timestamps are moved from mid-interval (HH:30) to the start of the
    interval (HH:00)"""
    data = Weather("CA", "Alameda", year=2019)
    assert data.index[0] == pd.Timestamp("2019-01-01 00:00:00", tz="UTC")
    assert data.index[-1] == pd.Timestamp("2019-12-31 23:00:00", tz="UTC")
    assert (data.index.minute == 0).all()
    np.testing.assert_array_equal(data["direct_Wpms"].values, np.arange(8760))

def test_celsius_to_fahrenheit(nsrdb):
    data = Weather("CA", "Alameda", year=2019)
    hours = np.arange(8760)
    celsius = (5 + 20*np.sin(2*np.pi*hours/8760)).round(3)
    np.testing.assert_allclose(data["temperature_degF"].values,
        (celsius * 1.8 + 32).round(1))

def test_download_failure(nsrdb, monkeypatch):
    import weather.weather as ww
    def fail(*args, **kwargs):
        raise ConnectionError("no network")
    monkeypatch.setattr(ww.pvlib.iotools, "get_nsrdb_psm4_aggregated", fail)
    with pytest.raises(RuntimeError, match="NSRDB weather download") as err:
        Weather("CA", "Alameda", year=2019)
    assert isinstance(err.value.__cause__, ConnectionError)
